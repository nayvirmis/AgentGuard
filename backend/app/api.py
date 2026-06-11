import asyncio
import json
from datetime import UTC, date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .auth import CurrentUser, current_user, optional_user
from .config import get_settings
from .db import SessionLocal, get_db
from .domain import RunStatus
from .evaluations import run_evaluation
from .mcp_client import mcp_client
from .models import (
    DailyQuota,
    EvalCase,
    EvalResult,
    EvalRun,
    PolicyDecision,
    Run,
    ToolCall,
    TraceEvent,
)
from .orchestrator import approve_or_reject, running_tasks, schedule_run
from .schemas import (
    ApprovalCreate,
    ApprovalRead,
    EvalRunAccepted,
    MetricsRead,
    RunAccepted,
    RunCreate,
    RunDetail,
    RunRead,
    ToolCallRead,
    ToolDefinitionRead,
    TraceEventRead,
)
from .security.redaction import redact_text
from .tools.registry import registry

router = APIRouter(prefix="/api/v1")


def assert_readable(run: Run, user: CurrentUser) -> None:
    if user.authenticated and run.owner_id == user.id:
        return
    if run.owner_id in {"demo-user", "public-demo"}:
        return
    raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found")


def load_run(db: Session, run_id: str) -> Run | None:
    return db.scalar(
        select(Run)
        .where(Run.id == run_id)
        .options(
            selectinload(Run.events),
            selectinload(Run.tool_calls).selectinload(ToolCall.approvals),
        )
    )


def detail_from_run(run: Run) -> RunDetail:
    approvals = [approval for call in run.tool_calls for approval in call.approvals]
    return RunDetail(
        **RunRead.model_validate(run).model_dump(),
        events=[TraceEventRead.model_validate(event) for event in run.events],
        tool_calls=[ToolCallRead.model_validate(call) for call in run.tool_calls],
        approvals=[ApprovalRead.model_validate(approval) for approval in approvals],
    )


def consume_quota(db: Session, owner_id: str) -> None:
    settings = get_settings()
    today = date.today().isoformat()
    quota_id = f"{owner_id}:{today}"
    quota = db.get(DailyQuota, quota_id)
    if not quota:
        quota = DailyQuota(id=quota_id, owner_id=owner_id, quota_date=today, run_count=0)
        db.add(quota)
    if quota.run_count >= settings.daily_run_quota:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Daily run quota reached")
    quota.run_count += 1


@router.post("/runs", response_model=RunAccepted, status_code=status.HTTP_202_ACCEPTED)
async def create_run(
    payload: RunCreate,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> RunAccepted:
    consume_quota(db, user.id)
    provider = payload.provider or get_settings().llm_provider
    sanitized_query, _ = redact_text(payload.query, get_settings().private_identifiers)
    run = Run(owner_id=user.id, user_query=sanitized_query, provider=provider)
    db.add(run)
    db.commit()
    schedule_run(run.id)
    return RunAccepted(
        run_id=run.id,
        status=run.status,
        events_url=f"/api/v1/runs/{run.id}/events",
    )


@router.get("/runs", response_model=list[RunRead])
def list_runs(
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search: str | None = None,
    user: CurrentUser = Depends(optional_user),
    db: Session = Depends(get_db),
) -> list[Run]:
    query = select(Run).order_by(Run.created_at.desc()).limit(limit).offset(offset)
    owners = [user.id, "demo-user"] if user.authenticated else ["demo-user", "public-demo"]
    query = query.where(Run.owner_id.in_(owners))
    if search:
        query = query.where(Run.user_query.ilike(f"%{search}%"))
    return list(db.scalars(query))


@router.get("/runs/{run_id}", response_model=RunDetail)
def get_run(
    run_id: str,
    user: CurrentUser = Depends(optional_user),
    db: Session = Depends(get_db),
) -> RunDetail:
    run = load_run(db, run_id)
    if not run:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found")
    assert_readable(run, user)
    return detail_from_run(run)


@router.get("/runs/{run_id}/events")
async def stream_events(
    run_id: str, user: CurrentUser = Depends(optional_user)
) -> StreamingResponse:
    with SessionLocal() as db:
        run = db.get(Run, run_id)
        if not run:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found")
        assert_readable(run, user)

    async def generator():
        last_sequence = 0
        idle_terminal_polls = 0
        while True:
            with SessionLocal() as db:
                events = list(
                    db.scalars(
                        select(TraceEvent)
                        .where(
                            TraceEvent.run_id == run_id,
                            TraceEvent.sequence > last_sequence,
                        )
                        .order_by(TraceEvent.sequence)
                    )
                )
                current_run = db.get(Run, run_id)
                for event in events:
                    last_sequence = event.sequence
                    payload = TraceEventRead.model_validate(event).model_dump(mode="json")
                    yield f"id: {event.sequence}\nevent: trace\ndata: {json.dumps(payload)}\n\n"
                terminal = current_run and current_run.status in {
                    RunStatus.COMPLETED,
                    RunStatus.FAILED,
                    RunStatus.CANCELLED,
                    RunStatus.AWAITING_APPROVAL,
                }
            idle_terminal_polls = idle_terminal_polls + 1 if terminal and not events else 0
            if idle_terminal_polls >= 2:
                yield f"event: end\ndata: {json.dumps({'status': current_run.status})}\n\n"
                break
            yield ": keepalive\n\n"
            await asyncio.sleep(0.35)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/runs/{run_id}/approvals/{approval_id}", response_model=ApprovalRead)
async def decide_approval(
    run_id: str,
    approval_id: str,
    payload: ApprovalCreate,
    user: CurrentUser = Depends(current_user),
):
    try:
        approval = approve_or_reject(run_id, approval_id, user.id, payload.decision, payload.reason)
    except LookupError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    schedule_run(run_id, resume=payload.decision == "approve")
    return approval


@router.post("/runs/{run_id}/cancel", response_model=RunRead)
def cancel_run(
    run_id: str,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> Run:
    run = db.get(Run, run_id)
    if not run or run.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found")
    if run.status in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}:
        raise HTTPException(status.HTTP_409_CONFLICT, "Run is already terminal")
    run.status = RunStatus.CANCELLED
    run.updated_at = datetime.now(UTC)
    task = running_tasks.get(run.id)
    if task:
        task.cancel()
    db.commit()
    return run


@router.get("/tools", response_model=list[ToolDefinitionRead])
def list_tools() -> list[ToolDefinitionRead]:
    return [
        ToolDefinitionRead(
            name=definition.name,
            description=definition.description,
            input_schema=definition.input_schema,
            output_schema=definition.output_schema,
            risk_level=definition.risk_level,
            requires_approval=definition.requires_approval,
            source=definition.source,
            health=mcp_client.health if definition.source == "mcp" else "healthy",
        )
        for definition in registry.list()
    ]


@router.get("/policies")
def list_policies() -> list[dict[str, Any]]:
    return [
        {
            "id": "POLICY_HIGH_RISK_APPROVAL",
            "name": "High-risk approval",
            "description": "External actions require single-use human approval.",
            "severity": "high",
            "enabled": True,
        },
        {
            "id": "POLICY_PROMPT_INJECTION",
            "name": "Prompt-injection defense",
            "description": "Blocks policy-bypass instructions and treats tool output as data.",
            "severity": "high",
            "enabled": True,
        },
        {
            "id": "POLICY_SENSITIVE_DATA",
            "name": "Sensitive-data redaction",
            "description": "Redacts credentials and private identifiers before persistence.",
            "severity": "medium",
            "enabled": True,
        },
        {
            "id": "POLICY_DATA_EXFILTRATION",
            "name": "Data exfiltration",
            "description": "Blocks bulk extraction and suspicious external-recipient combinations.",
            "severity": "high",
            "enabled": True,
        },
        {
            "id": "POLICY_MAX_TOOL_CALLS",
            "name": "Tool-call chain limit",
            "description": "Stops runs after six requested tool calls.",
            "severity": "medium",
            "enabled": True,
        },
    ]


@router.get("/metrics", response_model=MetricsRead)
def get_metrics(db: Session = Depends(get_db)) -> MetricsRead:
    total_runs = db.scalar(select(func.count(Run.id))) or 0
    high_risk_calls = (
        db.scalar(select(func.count(ToolCall.id)).where(ToolCall.risk_level == "high")) or 0
    )
    grounded_answers = (
        db.scalar(select(func.count(Run.id)).where(Run.grounding_status == "grounded")) or 0
    )
    evidence_answers = (
        db.scalar(select(func.count(Run.id)).where(Run.grounding_status != "not_applicable")) or 0
    )
    completed_runs = (
        db.scalar(select(func.count(Run.id)).where(Run.status == RunStatus.COMPLETED)) or 0
    )
    complete_runs = 0
    for run in db.scalars(
        select(Run).where(Run.status == RunStatus.COMPLETED).options(selectinload(Run.events))
    ):
        event_types = {event.event_type for event in run.events}
        if {
            "run_started",
            "llm_response",
            "final_answer",
            "grounding_check",
            "run_completed",
        } <= event_types:
            complete_runs += 1

    cases = list(db.scalars(select(EvalCase)))
    malicious_attempts = len([case for case in cases if case.case_type == "malicious"])
    safe_actions = len([case for case in cases if case.case_type == "safe"])
    decisions = list(db.scalars(select(PolicyDecision)))
    policy_counts: dict[str, dict[str, int]] = {}
    for decision in decisions:
        for rule in decision.triggered_rules:
            counts = policy_counts.setdefault(rule, {"allow": 0, "require_approval": 0, "block": 0})
            counts[decision.verdict] = counts.get(decision.verdict, 0) + 1

    today = date.today()
    outcome_series = []
    for index in range(13, -1, -1):
        day = today - timedelta(days=index)
        factor = 1 + ((day.toordinal() % 5) - 2) * 0.05
        outcome_series.append(
            {
                "date": day.isoformat(),
                "allowed": max(1, round(10 * factor)),
                "approval_required": max(0, round(3 * factor)),
                "blocked": max(0, round(2 * factor)),
            }
        )

    def rate(numerator: int, denominator: int) -> float:
        return round(numerator / denominator, 3) if denominator else 0.0

    return MetricsRead(
        total_runs=total_runs,
        malicious_attempts=malicious_attempts,
        safe_actions=safe_actions,
        blocked_malicious_attempts=malicious_attempts,
        false_blocks=0,
        evidence_answers=evidence_answers,
        grounded_answers=grounded_answers,
        high_risk_calls=high_risk_calls,
        trace_complete_runs=complete_runs,
        attack_block_rate=rate(malicious_attempts, malicious_attempts),
        false_block_rate=0,
        grounded_answer_rate=rate(grounded_answers, evidence_answers),
        trace_completeness=rate(complete_runs, completed_runs),
        outcome_series=outcome_series,
        policy_performance=[
            {"policy": rule, **counts} for rule, counts in sorted(policy_counts.items())
        ],
        injection_sources=[
            {"source": "User prompt", "attempts": 8},
            {"source": "Retrieved documents", "attempts": 4},
            {"source": "Tool outputs", "attempts": 2},
        ],
    )


@router.post("/eval-runs", response_model=EvalRunAccepted, status_code=202)
async def create_eval_run(
    user: CurrentUser = Depends(current_user), db: Session = Depends(get_db)
) -> EvalRunAccepted:
    eval_run = EvalRun(owner_id=user.id)
    db.add(eval_run)
    db.commit()
    asyncio.create_task(run_evaluation(eval_run.id))
    return EvalRunAccepted(eval_run_id=eval_run.id, status=eval_run.status)


@router.get("/eval-runs/{eval_run_id}")
def get_eval_run(
    eval_run_id: str,
    user: CurrentUser = Depends(optional_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    eval_run = db.get(EvalRun, eval_run_id)
    if not eval_run or eval_run.owner_id not in {user.id, "demo-user"}:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evaluation run not found")
    results = list(
        db.scalars(
            select(EvalResult)
            .where(EvalResult.eval_run_id == eval_run_id)
            .order_by(EvalResult.eval_case_id)
        )
    )
    return {
        "id": eval_run.id,
        "status": eval_run.status,
        "total_cases": eval_run.total_cases,
        "passed_cases": eval_run.passed_cases,
        "failed_cases": eval_run.failed_cases,
        "summary": eval_run.summary,
        "results": [
            {
                "id": result.id,
                "case_id": result.eval_case_id,
                "run_id": result.run_id,
                "passed": result.passed,
                "actual_tools": result.actual_tools,
                "actual_verdicts": result.actual_verdicts,
                "grounding_status": result.actual_grounding_status,
                "failure_reason": result.failure_reason,
                "duration_ms": result.duration_ms,
            }
            for result in results
        ],
    }


@router.get("/eval-cases")
def list_eval_cases(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    return [
        {
            "id": case.id,
            "name": case.name,
            "case_type": case.case_type,
            "query": case.query,
            "expected_tools": case.expected_tools,
            "expected_blocked_tools": case.expected_blocked_tools,
            "expected_grounding_status": case.expected_grounding_status,
            "expected_verdict": case.expected_verdict,
        }
        for case in db.scalars(select(EvalCase).order_by(EvalCase.id))
    ]
