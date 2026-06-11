import asyncio
import json
import time
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select

from .config import get_settings
from .db import SessionLocal
from .domain import ApprovalStatus, EventType, PolicyVerdict, RunStatus, ToolSource
from .grounding import check_grounding
from .mcp_client import mcp_client
from .models import Approval, PolicyDecision, Run, ToolCall, utcnow
from .providers import ProviderToolCall, get_provider
from .security.policy import PolicyEngine
from .security.redaction import redact_data
from .tools.registry import registry
from .tracing import append_event, persist_output

running_tasks: dict[str, asyncio.Task] = {}


def load_state(run: Run, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    return deepcopy(run.orchestration_state or fallback or {})


def schedule_run(run_id: str, *, resume: bool = False) -> None:
    task = asyncio.create_task(process_run(run_id, resume=resume))
    running_tasks[run_id] = task
    task.add_done_callback(lambda _: running_tasks.pop(run_id, None))


def summarize_output(tool_name: str, output: dict[str, Any]) -> str:
    if tool_name == "calendar_search":
        return f"Returned {len(output.get('events', []))} calendar events."
    if tool_name == "document_search":
        return f"Returned {len(output.get('results', []))} document snippets."
    if tool_name == "email_draft":
        return f"Created local draft {output.get('draft_id', '')}."
    if tool_name == "email_send_mock":
        return output.get("message", "Mock send completed.")
    return "Tool completed."


async def execute_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    definition = registry.get(name)
    if not definition:
        raise ValueError(f"Unknown tool: {name}")
    validated = definition.validate(arguments)
    if definition.source == ToolSource.MCP:
        return await asyncio.wait_for(mcp_client.search(validated.model_dump()), timeout=5)
    if not definition.handler:
        raise RuntimeError(f"Tool {name} has no handler")
    result = definition.handler(validated)
    return result.model_dump()


def serialize_call(call: ProviderToolCall) -> dict[str, Any]:
    arguments, _ = redact_data(call.arguments, get_settings().private_identifiers)
    return {"call_id": call.call_id, "name": call.name, "arguments": arguments}


def deserialize_call(data: dict[str, Any]) -> ProviderToolCall:
    return ProviderToolCall(data["call_id"], data["name"], data["arguments"])


async def process_run(run_id: str, *, resume: bool = False) -> None:
    started = time.perf_counter()
    settings = get_settings()
    engine = PolicyEngine(settings.max_tool_calls, settings.private_identifiers)

    try:
        with SessionLocal() as db:
            run = db.get(Run, run_id)
            if not run or run.status == RunStatus.CANCELLED:
                return
            state = load_state(run)
            run.status = RunStatus.RUNNING
            run.updated_at = utcnow()
            if not resume:
                append_event(
                    db,
                    run,
                    EventType.RUN_STARTED,
                    "Run started",
                    summary="Execution initialized through the AgentGuard control plane.",
                    status="info",
                )
                append_event(
                    db,
                    run,
                    EventType.INPUT_RECEIVED,
                    "Input received",
                    summary="User request accepted and queued for provider planning.",
                    data={"query_length": len(run.user_query)},
                )
            db.commit()

        provider = get_provider(state.get("provider_name"))

        if not state.get("response_id"):
            turn = await provider.start(run.user_query, registry.provider_tools())
            state = {
                "provider_name": provider.name,
                "response_id": turn.response_id,
                "pending_calls": [serialize_call(call) for call in turn.tool_calls],
                "tool_outputs": [],
                "all_tool_outputs": [],
                "signatures": [],
                "turns": 1,
            }
            with SessionLocal() as db:
                run = db.get(Run, run_id)
                if not run:
                    return
                run.provider = provider.name
                run.model = provider.model
                run.provider_response_id = turn.response_id
                run.orchestration_state = state
                append_event(
                    db,
                    run,
                    EventType.LLM_RESPONSE,
                    "Provider response",
                    summary=f"Provider requested {len(turn.tool_calls)} tool call(s).",
                    data=turn.metadata,
                    latency_ms=int((time.perf_counter() - started) * 1000),
                )
                db.commit()
            if turn.content and not turn.tool_calls:
                await finalize_run(run_id, turn.content, state, started)
                return

        if resume and state.get("awaiting_tool_call_id"):
            await execute_approved_call(run_id, state)
            with SessionLocal() as db:
                run = db.get(Run, run_id)
                if not run:
                    return
                state = load_state(run)

        while True:
            with SessionLocal() as db:
                run = db.get(Run, run_id)
                if not run or run.status == RunStatus.CANCELLED:
                    return
                state = load_state(run, state)

            pending = list(state.get("pending_calls", []))
            if pending:
                call = deserialize_call(pending.pop(0))
                should_pause = await process_tool_call(run_id, call, state, pending, engine)
                if should_pause:
                    return
                continue

            outputs = list(state.get("tool_outputs", []))
            turn = await provider.continue_run(
                state["response_id"], outputs, registry.provider_tools()
            )
            state["response_id"] = turn.response_id
            state["pending_calls"] = [serialize_call(call) for call in turn.tool_calls]
            state["tool_outputs"] = []
            state["turns"] = int(state.get("turns", 1)) + 1
            with SessionLocal() as db:
                run = db.get(Run, run_id)
                if not run:
                    return
                run.provider_response_id = turn.response_id
                run.orchestration_state = state
                append_event(
                    db,
                    run,
                    EventType.LLM_RESPONSE,
                    "Provider response",
                    summary=(
                        f"Provider requested {len(turn.tool_calls)} additional tool call(s)."
                        if turn.tool_calls
                        else "Provider produced the final answer."
                    ),
                    data=turn.metadata,
                )
                db.commit()

            if turn.content and not turn.tool_calls:
                await finalize_run(run_id, turn.content, state, started)
                return
            if state["turns"] > settings.max_tool_calls + 2:
                raise RuntimeError("Provider exceeded the orchestration turn limit")
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        with SessionLocal() as db:
            run = db.get(Run, run_id)
            if run:
                run.status = RunStatus.FAILED
                run.error_code = type(exc).__name__
                run.updated_at = utcnow()
                append_event(
                    db,
                    run,
                    EventType.RUN_FAILED,
                    "Run failed",
                    summary="The run stopped at a controlled failure boundary.",
                    status="error",
                    data={"error_code": type(exc).__name__},
                )
                db.commit()


async def process_tool_call(
    run_id: str,
    call: ProviderToolCall,
    state: dict[str, Any],
    remaining: list[dict[str, Any]],
    engine: PolicyEngine,
) -> bool:
    definition = registry.get(call.name)
    with SessionLocal() as db:
        run = db.get(Run, run_id)
        if not run:
            return True
        if not definition:
            state["pending_calls"] = remaining
            state.setdefault("tool_outputs", []).append(
                {
                    "call_id": call.call_id,
                    "tool_name": call.name,
                    "denied": True,
                    "reason": "unknown_tool",
                }
            )
            state.setdefault("all_tool_outputs", []).append(state["tool_outputs"][-1])
            run.orchestration_state = state
            append_event(
                db,
                run,
                EventType.TOOL_BLOCKED,
                "Unknown tool blocked",
                summary=f"The provider requested unregistered tool {call.name}.",
                status="blocked",
            )
            db.commit()
            return False

        tool_call = ToolCall(
            run_id=run.id,
            provider_call_id=call.call_id,
            tool_name=call.name,
            arguments_json={},
            redacted_arguments_json={},
            risk_level=definition.risk_level,
            source=definition.source,
        )
        db.add(tool_call)
        db.flush()
        append_event(
            db,
            run,
            EventType.TOOL_CALL_REQUESTED,
            call.name,
            summary="Provider requested a registered tool.",
            data={"tool_call_id": tool_call.id, "tool_name": call.name},
        )

        result = engine.evaluate(
            tool_name=call.name,
            risk_level=definition.risk_level,
            requires_approval=definition.requires_approval,
            arguments=call.arguments,
            schema_validator=definition.validate,
            call_count=run.total_tool_calls,
            prior_signatures=set(state.get("signatures", [])),
        )
        signature = f"{call.name}:{json.dumps(result.effective_arguments, sort_keys=True)}"
        state.setdefault("signatures", []).append(signature)
        tool_call.redacted_arguments_json = result.effective_arguments
        tool_call.arguments_json = result.effective_arguments
        run.total_tool_calls += 1
        decision = PolicyDecision(
            run_id=run.id,
            tool_call_id=tool_call.id,
            verdict=result.verdict,
            reason=result.reason,
            triggered_rules=result.triggered_rules,
            redactions=result.redactions,
            effective_arguments=result.effective_arguments,
        )
        db.add(decision)
        append_event(
            db,
            run,
            EventType.POLICY_DECISION,
            "Policy decision",
            summary=result.reason,
            status=result.verdict,
            data={
                "tool_call_id": tool_call.id,
                "tool_name": call.name,
                "verdict": result.verdict,
                "triggered_rules": result.triggered_rules,
                "redactions": result.redactions,
            },
        )

        if result.verdict == PolicyVerdict.BLOCK:
            tool_call.status = "blocked"
            run.blocked_tool_calls += 1
            state["pending_calls"] = remaining
            state.setdefault("tool_outputs", []).append(
                {
                    "call_id": call.call_id,
                    "tool_name": call.name,
                    "denied": True,
                    "reason": result.reason,
                }
            )
            state.setdefault("all_tool_outputs", []).append(state["tool_outputs"][-1])
            run.orchestration_state = state
            append_event(
                db,
                run,
                EventType.TOOL_BLOCKED,
                f"{call.name} blocked",
                summary=result.reason,
                status="blocked",
                data={"tool_call_id": tool_call.id},
            )
            db.commit()
            return False

        if result.verdict == PolicyVerdict.REQUIRE_APPROVAL:
            expires_at = datetime.now(UTC) + timedelta(minutes=get_settings().approval_ttl_minutes)
            approval = Approval(
                run_id=run.id,
                tool_call_id=tool_call.id,
                owner_id=run.owner_id,
                expires_at=expires_at,
            )
            db.add(approval)
            db.flush()
            tool_call.status = "awaiting_approval"
            run.status = RunStatus.AWAITING_APPROVAL
            run.approval_tool_call_id = tool_call.id
            state["pending_calls"] = remaining
            state["awaiting_tool_call_id"] = tool_call.id
            state["awaiting_call_id"] = call.call_id
            run.orchestration_state = state
            append_event(
                db,
                run,
                EventType.APPROVAL_REQUESTED,
                "Approval requested",
                summary=f"{call.name} requires a human decision before execution.",
                status="awaiting_approval",
                data={
                    "approval_id": approval.id,
                    "tool_call_id": tool_call.id,
                    "expires_at": expires_at.isoformat(),
                },
            )
            db.commit()
            return True

        state["pending_calls"] = remaining
        run.orchestration_state = state
        db.commit()

    await execute_allowed_call(
        run_id, tool_call.id, call.call_id, result.effective_arguments, state
    )
    return False


async def execute_allowed_call(
    run_id: str,
    tool_call_id: str,
    provider_call_id: str,
    arguments: dict[str, Any],
    state: dict[str, Any],
) -> None:
    with SessionLocal() as db:
        tool_call = db.get(ToolCall, tool_call_id)
        if not tool_call:
            return
        tool_name = tool_call.tool_name
    started = time.perf_counter()
    output = await execute_tool(tool_name, arguments)
    latency_ms = int((time.perf_counter() - started) * 1000)
    with SessionLocal() as db:
        run = db.get(Run, run_id)
        tool_call = db.get(ToolCall, tool_call_id)
        if not run or not tool_call:
            return
        tool_call.status = "executed"
        tool_call.latency_ms = latency_ms
        summary = summarize_output(tool_name, output)
        output_row = persist_output(
            db, run_id=run.id, tool_call_id=tool_call.id, output=output, summary=summary
        )
        state = load_state(run, state)
        state.setdefault("tool_outputs", []).append(
            {
                "call_id": provider_call_id,
                "tool_name": tool_name,
                "output": output,
                "output_hash": output_row.output_hash,
            }
        )
        state.setdefault("all_tool_outputs", []).append(state["tool_outputs"][-1])
        run.orchestration_state = state
        append_event(
            db,
            run,
            EventType.TOOL_EXECUTED,
            tool_name,
            summary=summary,
            status="allowed",
            latency_ms=latency_ms,
            data={"tool_call_id": tool_call.id, "output_hash": output_row.output_hash},
        )
        db.commit()


async def execute_approved_call(run_id: str, state: dict[str, Any]) -> None:
    tool_call_id = state["awaiting_tool_call_id"]
    with SessionLocal() as db:
        tool_call = db.get(ToolCall, tool_call_id)
        approval = db.scalar(
            select(Approval).where(
                Approval.tool_call_id == tool_call_id, Approval.status == ApprovalStatus.APPROVED
            )
        )
        if not tool_call or not approval or approval.used:
            raise RuntimeError("Approved tool call could not be resumed")
        approval.used = True
        state.pop("awaiting_tool_call_id", None)
        provider_call_id = state.pop("awaiting_call_id")
        db.commit()
    await execute_allowed_call(
        run_id, tool_call_id, provider_call_id, tool_call.redacted_arguments_json, state
    )


async def finalize_run(run_id: str, content: str, state: dict[str, Any], started: float) -> None:
    with SessionLocal() as db:
        run = db.get(Run, run_id)
        if not run:
            return
        evidence = list(state.get("all_tool_outputs", state.get("tool_outputs", [])))
        grounding = check_grounding(content, evidence)
        run.final_answer = content
        run.grounding_status = grounding.status
        run.grounding_score = grounding.score
        run.grounding_details = grounding.details
        run.status = RunStatus.COMPLETED
        run.completed_at = utcnow()
        run.updated_at = utcnow()
        run.total_latency_ms = int((time.perf_counter() - started) * 1000)
        run.orchestration_state = {}
        append_event(
            db,
            run,
            EventType.FINAL_ANSWER,
            "Final answer",
            summary=content,
            status="success",
        )
        append_event(
            db,
            run,
            EventType.GROUNDING_CHECK,
            "Grounding check",
            summary=f"Grounding status: {grounding.status}.",
            status=grounding.status,
            data={"score": grounding.score, **grounding.details},
        )
        append_event(
            db,
            run,
            EventType.RUN_COMPLETED,
            "Run completed",
            summary="Execution completed with a fully persisted trace.",
            status="completed",
            data={"total_latency_ms": run.total_latency_ms},
        )
        db.commit()


def approve_or_reject(
    run_id: str, approval_id: str, owner_id: str, decision: str, reason: str | None
) -> Approval:
    with SessionLocal() as db:
        approval = db.get(Approval, approval_id)
        run = db.get(Run, run_id)
        if not approval or not run or approval.run_id != run_id:
            raise LookupError("Approval not found")
        if approval.owner_id != owner_id:
            raise PermissionError("Approval belongs to a different user")
        if approval.status != ApprovalStatus.PENDING or approval.used:
            raise ValueError("Approval has already been decided or consumed")
        expires_at = approval.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at < datetime.now(UTC):
            approval.status = ApprovalStatus.EXPIRED
            db.commit()
            raise ValueError("Approval expired")

        approval.status = (
            ApprovalStatus.APPROVED if decision == "approve" else ApprovalStatus.REJECTED
        )
        approval.decision_reason = reason
        approval.decided_at = utcnow()
        append_event(
            db,
            run,
            EventType.APPROVAL_DECISION,
            f"Approval {decision}d",
            summary=reason or f"User chose to {decision} the external action.",
            status=approval.status,
            data={"approval_id": approval.id, "decision": decision},
        )

        if decision == "reject":
            state = load_state(run)
            state.pop("awaiting_tool_call_id", None)
            provider_call_id = state.pop("awaiting_call_id", "")
            state.setdefault("tool_outputs", []).append(
                {
                    "call_id": provider_call_id,
                    "tool_name": "email_send_mock",
                    "denied": True,
                    "reason": "Human rejected the action.",
                }
            )
            state.setdefault("all_tool_outputs", []).append(state["tool_outputs"][-1])
            run.orchestration_state = state
            run.status = RunStatus.RUNNING
        db.commit()
        db.refresh(approval)
        return approval
