import asyncio
import json
from pathlib import Path

from sqlalchemy import func, select

from .db import SessionLocal, create_all
from .models import EvalCase, Run
from .orchestrator import process_run

CASE_DIR = Path(__file__).resolve().parent / "eval_cases"


def seed_eval_cases() -> None:
    with SessionLocal() as db:
        if db.scalar(select(func.count(EvalCase.id))):
            return
        for path in sorted(CASE_DIR.glob("*.json")):
            for item in json.loads(path.read_text(encoding="utf-8")):
                db.add(EvalCase(**item))
        db.commit()


async def seed_demo_runs() -> None:
    with SessionLocal() as db:
        if db.scalar(select(func.count(Run.id))):
            return
        completed = Run(
            owner_id="demo-user",
            user_query="What deadlines do I have this week and what does the handbook say about extensions?",
            provider="fake",
            model="deterministic-demo",
        )
        approval = Run(
            owner_id="demo-user",
            user_query=(
                "Find my upcoming assignment deadlines, review the extension policy, "
                "draft an email to my professor, and send it for my approval."
            ),
            provider="fake",
            model="deterministic-demo",
        )
        db.add_all([completed, approval])
        db.commit()
        ids = [completed.id, approval.id]
    for run_id in ids:
        await process_run(run_id)


async def seed_all() -> None:
    create_all()
    seed_eval_cases()
    await seed_demo_runs()


if __name__ == "__main__":
    asyncio.run(seed_all())
