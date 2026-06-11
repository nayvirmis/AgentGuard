from enum import StrEnum


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"


class GroundingStatus(StrEnum):
    GROUNDED = "grounded"
    PARTIALLY_GROUNDED = "partially_grounded"
    UNSUPPORTED = "unsupported"
    NOT_APPLICABLE = "not_applicable"


class PolicyVerdict(StrEnum):
    ALLOW = "allow"
    REQUIRE_APPROVAL = "require_approval"
    BLOCK = "block"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ToolRisk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ToolSource(StrEnum):
    NATIVE = "native"
    MCP = "mcp"


class EventType(StrEnum):
    RUN_STARTED = "run_started"
    INPUT_RECEIVED = "input_received"
    LLM_RESPONSE = "llm_response"
    TOOL_CALL_REQUESTED = "tool_call_requested"
    POLICY_DECISION = "policy_decision"
    TOOL_EXECUTED = "tool_executed"
    TOOL_BLOCKED = "tool_blocked"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_DECISION = "approval_decision"
    FINAL_ANSWER = "final_answer"
    GROUNDING_CHECK = "grounding_check"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"
    RUN_CANCELLED = "run_cancelled"
