import json
import re
from dataclasses import dataclass
from typing import Any

from backend.app.domain import PolicyVerdict, ToolRisk
from backend.app.security.redaction import redact_data

RULE_SCHEMA = "POLICY_SCHEMA_VALID"
RULE_TOOL_SCOPE = "POLICY_TOOL_SCOPE"
RULE_HIGH_RISK = "POLICY_HIGH_RISK_APPROVAL"
RULE_SENSITIVE = "POLICY_SENSITIVE_DATA"
RULE_PROMPT_INJECTION = "POLICY_PROMPT_INJECTION"
RULE_EXFILTRATION = "POLICY_DATA_EXFILTRATION"
RULE_CALL_LIMIT = "POLICY_MAX_TOOL_CALLS"
RULE_DUPLICATE = "POLICY_DUPLICATE_TOOL_CALL"

INJECTION = re.compile(
    r"(ignore (all|any|the|previous).{0,30}(rules|instructions|policy)|"
    r"reveal.{0,20}(system prompt|hidden prompt)|bypass.{0,20}(guardrail|policy)|"
    r"do not follow.{0,20}(policy|instructions))",
    re.IGNORECASE,
)
EXFILTRATION = re.compile(
    r"(send|email|upload|forward|dump|export).{0,50}(all|private|secret|documents|calendar|data)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PolicyResult:
    verdict: PolicyVerdict
    reason: str
    triggered_rules: list[str]
    redactions: list[str]
    effective_arguments: dict[str, Any]


class PolicyEngine:
    def __init__(self, max_tool_calls: int = 6, private_identifiers: list[str] | None = None):
        self.max_tool_calls = max_tool_calls
        self.private_identifiers = private_identifiers or []

    def evaluate(
        self,
        *,
        tool_name: str,
        risk_level: ToolRisk,
        requires_approval: bool,
        arguments: dict[str, Any],
        schema_validator: Any,
        call_count: int,
        prior_signatures: set[str],
    ) -> PolicyResult:
        effective, redactions = redact_data(arguments, self.private_identifiers)
        triggered: list[str] = [RULE_TOOL_SCOPE]

        if call_count >= self.max_tool_calls:
            return PolicyResult(
                PolicyVerdict.BLOCK,
                f"Run reached the {self.max_tool_calls}-tool-call limit.",
                [RULE_CALL_LIMIT],
                redactions,
                effective,
            )

        signature = f"{tool_name}:{json.dumps(effective, sort_keys=True)}"
        if signature in prior_signatures:
            return PolicyResult(
                PolicyVerdict.BLOCK,
                "Repeated identical tool call detected.",
                [RULE_DUPLICATE],
                redactions,
                effective,
            )

        try:
            schema_validator(arguments)
            triggered.append(RULE_SCHEMA)
        except Exception:
            return PolicyResult(
                PolicyVerdict.BLOCK,
                "Tool arguments did not match the registered schema.",
                [RULE_SCHEMA],
                redactions,
                effective,
            )

        haystack = json.dumps(arguments, sort_keys=True)
        if "[REDACTED:" in haystack:
            redactions = sorted(set([*redactions, "ingestion_boundary"]))
        if INJECTION.search(haystack):
            return PolicyResult(
                PolicyVerdict.BLOCK,
                "Prompt-injection or policy-bypass language was detected.",
                [RULE_PROMPT_INJECTION],
                redactions,
                effective,
            )
        if EXFILTRATION.search(haystack):
            return PolicyResult(
                PolicyVerdict.BLOCK,
                "Arguments indicate bulk data extraction or exfiltration.",
                [RULE_EXFILTRATION],
                redactions,
                effective,
            )

        if redactions:
            triggered.append(RULE_SENSITIVE)

        if requires_approval or risk_level == ToolRisk.HIGH:
            triggered.append(RULE_HIGH_RISK)
            return PolicyResult(
                PolicyVerdict.REQUIRE_APPROVAL,
                "High-risk external action requires explicit human approval.",
                triggered,
                redactions,
                effective,
            )

        return PolicyResult(
            PolicyVerdict.ALLOW,
            "Tool is within scope and arguments satisfy deterministic policy.",
            triggered,
            redactions,
            effective,
        )
