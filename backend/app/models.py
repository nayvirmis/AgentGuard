import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def utcnow() -> datetime:
    return datetime.now(UTC)


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("run"))
    owner_id: Mapped[str] = mapped_column(String(128), index=True)
    user_query: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(32), default="fake")
    model: Mapped[str] = mapped_column(String(80), default="deterministic-demo")
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    final_answer: Mapped[str | None] = mapped_column(Text)
    grounding_status: Mapped[str] = mapped_column(String(32), default="not_applicable")
    grounding_score: Mapped[float | None] = mapped_column(Float)
    grounding_details: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    total_latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    total_tool_calls: Mapped[int] = mapped_column(Integer, default=0)
    blocked_tool_calls: Mapped[int] = mapped_column(Integer, default=0)
    approval_tool_call_id: Mapped[str | None] = mapped_column(String(40))
    provider_response_id: Mapped[str | None] = mapped_column(String(128))
    orchestration_state: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error_code: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    events: Mapped[list["TraceEvent"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="TraceEvent.sequence"
    )
    tool_calls: Mapped[list["ToolCall"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class TraceEvent(Base):
    __tablename__ = "trace_events"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("evt"))
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(32), default="info")
    title: Mapped[str] = mapped_column(String(160))
    summary: Mapped[str] = mapped_column(Text, default="")
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    run: Mapped[Run] = relationship(back_populates="events")


class ToolCall(Base):
    __tablename__ = "tool_calls"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("call"))
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    provider_call_id: Mapped[str | None] = mapped_column(String(128))
    tool_name: Mapped[str] = mapped_column(String(80), index=True)
    arguments_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    redacted_arguments_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    risk_level: Mapped[str] = mapped_column(String(16))
    source: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(32), default="requested")
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    run: Mapped[Run] = relationship(back_populates="tool_calls")
    decisions: Mapped[list["PolicyDecision"]] = relationship(
        back_populates="tool_call", cascade="all, delete-orphan"
    )
    outputs: Mapped[list["ToolOutput"]] = relationship(
        back_populates="tool_call", cascade="all, delete-orphan"
    )
    approvals: Mapped[list["Approval"]] = relationship(
        back_populates="tool_call", cascade="all, delete-orphan"
    )


class PolicyDecision(Base):
    __tablename__ = "policy_decisions"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pol"))
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    tool_call_id: Mapped[str] = mapped_column(ForeignKey("tool_calls.id"), index=True)
    verdict: Mapped[str] = mapped_column(String(32))
    reason: Mapped[str] = mapped_column(Text)
    triggered_rules: Mapped[list[str]] = mapped_column(JSON, default=list)
    redactions: Mapped[list[str]] = mapped_column(JSON, default=list)
    effective_arguments: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    tool_call: Mapped[ToolCall] = relationship(back_populates="decisions")


class ToolOutput(Base):
    __tablename__ = "tool_outputs"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("out"))
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    tool_call_id: Mapped[str] = mapped_column(ForeignKey("tool_calls.id"), index=True)
    output_summary: Mapped[str] = mapped_column(Text)
    output_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    output_hash: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    tool_call: Mapped[ToolCall] = relationship(back_populates="outputs")


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("apr"))
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    tool_call_id: Mapped[str] = mapped_column(ForeignKey("tool_calls.id"), index=True)
    owner_id: Mapped[str] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(String(24), default="pending")
    decision_reason: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    tool_call: Mapped[ToolCall] = relationship(back_populates="approvals")


class EvalCase(Base):
    __tablename__ = "eval_cases"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    case_type: Mapped[str] = mapped_column(String(40), index=True)
    query: Mapped[str] = mapped_column(Text)
    expected_tools: Mapped[list[str]] = mapped_column(JSON, default=list)
    expected_blocked_tools: Mapped[list[str]] = mapped_column(JSON, default=list)
    expected_grounding_status: Mapped[str | None] = mapped_column(String(32))
    expected_verdict: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EvalRun(Base):
    __tablename__ = "eval_runs"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("eval"))
    owner_id: Mapped[str] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(String(24), default="queued")
    total_cases: Mapped[int] = mapped_column(Integer, default=0)
    passed_cases: Mapped[int] = mapped_column(Integer, default=0)
    failed_cases: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EvalResult(Base):
    __tablename__ = "eval_results"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("res"))
    eval_run_id: Mapped[str] = mapped_column(ForeignKey("eval_runs.id"), index=True)
    eval_case_id: Mapped[str] = mapped_column(ForeignKey("eval_cases.id"))
    run_id: Mapped[str | None] = mapped_column(ForeignKey("runs.id"))
    passed: Mapped[bool] = mapped_column(Boolean)
    actual_tools: Mapped[list[str]] = mapped_column(JSON, default=list)
    actual_verdicts: Mapped[list[str]] = mapped_column(JSON, default=list)
    actual_grounding_status: Mapped[str | None] = mapped_column(String(32))
    failure_reason: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DailyQuota(Base):
    __tablename__ = "daily_quotas"

    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(128), index=True)
    quota_date: Mapped[str] = mapped_column(String(10), index=True)
    run_count: Mapped[int] = mapped_column(Integer, default=0)
