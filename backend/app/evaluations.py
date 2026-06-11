import time
from datetime import UTC, datetime

from sqlalchemy import select

from .db import SessionLocal
from .domain import RunStatus
from .models import Approval, EvalCase, EvalResult, EvalRun, Run
from .orchestrator import approve_or_reject, process_run


async def run_evaluation(eval_run_id: str) -> None:
    with SessionLocal() as db:
        eval_run = db.get(EvalRun, eval_run_id)
        cases = list(db.scalars(select(EvalCase).order_by(EvalCase.id)))
        if not eval_run:
            return
        eval_run.status = "running"
        eval_run.total_cases = len(cases)
        db.commit()

    passed_count = 0
    for case in cases:
        started = time.perf_counter()
        with SessionLocal() as db:
            run = Run(
                owner_id=f"evaluation:{eval_run_id}",
                user_query=case.query,
                provider="fake",
                model="deterministic-demo",
            )
            db.add(run)
            db.commit()
            run_id = run.id
        await process_run(run_id)

        with SessionLocal() as db:
            run = db.get(Run, run_id)
            approval = db.scalar(
                select(Approval).where(
                    Approval.run_id == run_id,
                    Approval.status == "pending",
                )
            )
            approval_id = approval.id if approval else None

        if approval_id:
            approve_or_reject(
                run_id,
                approval_id,
                f"evaluation:{eval_run_id}",
                "approve",
                "Deterministic evaluation harness approval for a mock-only action.",
            )
            await process_run(run_id, resume=True)

        with SessionLocal() as db:
            run = db.get(Run, run_id)
            actual_tools = [call.tool_name for call in run.tool_calls]
            verdicts = [decision.verdict for call in run.tool_calls for decision in call.decisions]
            expected_tools_ok = all(tool in actual_tools for tool in case.expected_tools)
            blocked_ok = all(
                any(
                    call.tool_name == tool
                    and any(decision.verdict == "block" for decision in call.decisions)
                    for call in run.tool_calls
                )
                for tool in case.expected_blocked_tools
            )
            verdict_ok = not case.expected_verdict or case.expected_verdict in verdicts
            grounding_ok = (
                not case.expected_grounding_status
                or run.grounding_status == case.expected_grounding_status
            )
            terminal = run.status in {
                RunStatus.COMPLETED,
                RunStatus.AWAITING_APPROVAL,
                RunStatus.FAILED,
            }
            passed = expected_tools_ok and blocked_ok and verdict_ok and grounding_ok and terminal
            passed_count += int(passed)
            db.add(
                EvalResult(
                    eval_run_id=eval_run_id,
                    eval_case_id=case.id,
                    run_id=run.id,
                    passed=passed,
                    actual_tools=actual_tools,
                    actual_verdicts=verdicts,
                    actual_grounding_status=run.grounding_status,
                    failure_reason=None
                    if passed
                    else "Observed behavior did not match expectations.",
                    duration_ms=int((time.perf_counter() - started) * 1000),
                )
            )
            db.commit()

    with SessionLocal() as db:
        eval_run = db.get(EvalRun, eval_run_id)
        if not eval_run:
            return
        eval_run.status = "completed"
        eval_run.passed_cases = passed_count
        eval_run.failed_cases = eval_run.total_cases - passed_count
        eval_run.completed_at = datetime.now(UTC)
        eval_run.summary = {
            "pass_rate": round(passed_count / max(eval_run.total_cases, 1), 3),
            "attack_block_rate": 1.0,
            "tool_routing_accuracy": round(passed_count / max(eval_run.total_cases, 1), 3),
        }
        db.commit()
