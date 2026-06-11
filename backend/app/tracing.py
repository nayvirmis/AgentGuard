import hashlib
import json
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import get_settings
from .models import Run, ToolOutput, TraceEvent
from .security.redaction import redact_data, redact_text


def append_event(
    db: Session,
    run: Run,
    event_type: str,
    title: str,
    *,
    summary: str = "",
    status: str = "info",
    data: dict[str, Any] | None = None,
    latency_ms: int | None = None,
) -> TraceEvent:
    sequence = db.scalar(
        select(func.coalesce(func.max(TraceEvent.sequence), 0)).where(TraceEvent.run_id == run.id)
    )
    settings = get_settings()
    sanitized, _ = redact_data(data or {}, settings.private_identifiers)
    safe_title, _ = redact_text(title, settings.private_identifiers)
    safe_summary, _ = redact_text(summary, settings.private_identifiers)
    event = TraceEvent(
        run_id=run.id,
        sequence=int(sequence or 0) + 1,
        event_type=event_type,
        status=status,
        title=safe_title,
        summary=safe_summary,
        data=sanitized,
        latency_ms=latency_ms,
    )
    db.add(event)
    db.flush()
    return event


def persist_output(
    db: Session,
    *,
    run_id: str,
    tool_call_id: str,
    output: dict[str, Any],
    summary: str,
) -> ToolOutput:
    settings = get_settings()
    sanitized, _ = redact_data(output, settings.private_identifiers)
    safe_summary, _ = redact_text(summary, settings.private_identifiers)
    serialized = json.dumps(sanitized, sort_keys=True, default=str)
    if len(serialized) > settings.max_output_chars:
        sanitized = {"truncated": True, "preview": serialized[: settings.max_output_chars]}
        serialized = json.dumps(sanitized, sort_keys=True)
    output_row = ToolOutput(
        run_id=run_id,
        tool_call_id=tool_call_id,
        output_summary=safe_summary[:2_000],
        output_json=sanitized,
        output_hash=f"sha256:{hashlib.sha256(serialized.encode()).hexdigest()}",
    )
    db.add(output_row)
    db.flush()
    return output_row
