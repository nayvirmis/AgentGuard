from backend.app.db import SessionLocal
from backend.app.domain import RunStatus
from backend.app.models import Approval, Run, ToolCall
from backend.app.orchestrator import approve_or_reject, process_run
from sqlalchemy import select


async def test_safe_run_completes_with_trace():
    with SessionLocal() as db:
        run = Run(owner_id="demo-user", user_query="What deadlines are on my calendar?")
        db.add(run)
        db.commit()
        run_id = run.id

    await process_run(run_id)

    with SessionLocal() as db:
        run = db.get(Run, run_id)
        assert run.status == RunStatus.COMPLETED
        assert run.final_answer
        assert [event.sequence for event in run.events] == list(range(1, len(run.events) + 1))
        assert {"run_started", "final_answer", "grounding_check", "run_completed"} <= {
            event.event_type for event in run.events
        }


async def test_high_risk_run_pauses_and_resumes_once():
    with SessionLocal() as db:
        run = Run(
            owner_id="demo-user",
            user_query="Draft a polite email and send it for approval.",
        )
        db.add(run)
        db.commit()
        run_id = run.id

    await process_run(run_id)

    with SessionLocal() as db:
        run = db.get(Run, run_id)
        approval = db.scalar(select(Approval).where(Approval.run_id == run_id))
        assert run.status == RunStatus.AWAITING_APPROVAL
        assert approval is not None
        approval_id = approval.id

    approve_or_reject(run_id, approval_id, "demo-user", "approve", None)
    await process_run(run_id, resume=True)

    with SessionLocal() as db:
        run = db.get(Run, run_id)
        approval = db.get(Approval, approval_id)
        sent = db.scalar(
            select(ToolCall).where(
                ToolCall.run_id == run_id,
                ToolCall.tool_name == "email_send_mock",
            )
        )
        assert run.status == RunStatus.COMPLETED
        assert approval.used is True
        assert sent.status == "executed"
        assert "simulated" in run.final_answer.lower()
