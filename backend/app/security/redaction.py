import re
from copy import deepcopy
from typing import Any

SECRET_PATTERNS = {
    "api_key": re.compile(r"\b(?:sk|rk|pk)_[A-Za-z0-9_-]{16,}\b"),
    "bearer_token": re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]{16,}\b", re.IGNORECASE),
    "password": re.compile(r"(?i)(password|passwd|pwd)\s*[:=]\s*([^\s,;]+)"),
    "phone": re.compile(
        r"(?<![\w])(?:\+?\d{1,3}[\s.-]?)?(?:\(\d{3}\)|\d{3})"
        r"[\s.-]\d{3}[\s.-]\d{4}(?![\w])"
    ),
}
SENSITIVE_KEYS = {"password", "token", "api_key", "secret", "credential", "authorization"}


def redact_text(value: str, private_identifiers: list[str] | None = None) -> tuple[str, list[str]]:
    redacted = value
    matches: list[str] = []
    for rule_id, pattern in SECRET_PATTERNS.items():
        if pattern.search(redacted):
            matches.append(rule_id)
            redacted = pattern.sub(f"[REDACTED:{rule_id}]", redacted)
    for identifier in private_identifiers or []:
        if identifier and identifier.lower() in redacted.lower():
            matches.append("private_identifier")
            redacted = re.sub(
                re.escape(identifier), "[REDACTED:private_identifier]", redacted, flags=re.I
            )
    return redacted, sorted(set(matches))


def redact_data(value: Any, private_identifiers: list[str] | None = None) -> tuple[Any, list[str]]:
    matches: list[str] = []
    clone = deepcopy(value)

    def visit(item: Any, key: str | None = None) -> Any:
        if key and key.lower() in SENSITIVE_KEYS:
            matches.append(f"sensitive_key:{key.lower()}")
            return f"[REDACTED:{key.lower()}]"
        if isinstance(item, str):
            redacted, found = redact_text(item, private_identifiers)
            matches.extend(found)
            return redacted
        if isinstance(item, dict):
            return {
                child_key: visit(child_value, child_key) for child_key, child_value in item.items()
            }
        if isinstance(item, list):
            return [visit(child) for child in item]
        return item

    return visit(clone), sorted(set(matches))
