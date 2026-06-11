from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RunCreate(APIModel):
    query: str = Field(min_length=3, max_length=8_000)
    provider: Literal["fake", "openai"] | None = None


class ApprovalCreate(APIModel):
    decision: Literal["approve", "reject"]
    reason: str | None = Field(default=None, max_length=500)


class TraceEventRead(APIModel):
    id: str
    sequence: int
    event_type: str
    status: str
    title: str
    summary: str
    data: dict[str, Any]
    latency_ms: int | None
    created_at: datetime


class ToolCallRead(APIModel):
    id: str
    tool_name: str
    redacted_arguments_json: dict[str, Any]
    risk_level: str
    source: str
    status: str
    latency_ms: int | None
    created_at: datetime


class ApprovalRead(APIModel):
    id: str
    tool_call_id: str
    status: str
    expires_at: datetime
    decided_at: datetime | None


class RunRead(APIModel):
    id: str
    owner_id: str
    user_query: str
    provider: str
    model: str
    status: str
    final_answer: str | None
    grounding_status: str
    grounding_score: float | None
    grounding_details: dict[str, Any] | None
    total_latency_ms: int
    total_tool_calls: int
    blocked_tool_calls: int
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


class RunDetail(RunRead):
    events: list[TraceEventRead] = []
    tool_calls: list[ToolCallRead] = []
    approvals: list[ApprovalRead] = []


class RunAccepted(APIModel):
    run_id: str
    status: str
    events_url: str


class ToolDefinitionRead(APIModel):
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    risk_level: str
    requires_approval: bool
    source: str
    health: str


class MetricsRead(APIModel):
    total_runs: int
    malicious_attempts: int
    safe_actions: int
    blocked_malicious_attempts: int
    false_blocks: int
    evidence_answers: int
    grounded_answers: int
    high_risk_calls: int
    trace_complete_runs: int
    attack_block_rate: float
    false_block_rate: float
    grounded_answer_rate: float
    trace_completeness: float
    outcome_series: list[dict[str, Any]]
    policy_performance: list[dict[str, Any]]
    injection_sources: list[dict[str, Any]]


class EvalRunAccepted(APIModel):
    eval_run_id: str
    status: str
