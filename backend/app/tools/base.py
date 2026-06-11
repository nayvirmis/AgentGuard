from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from backend.app.domain import ToolRisk, ToolSource


def strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(schema)
    properties = normalized.get("properties")
    if isinstance(properties, dict):
        normalized["additionalProperties"] = False
        normalized["required"] = list(properties)
        normalized["properties"] = {
            key: strict_schema(value) if isinstance(value, dict) else value
            for key, value in properties.items()
        }
    if isinstance(normalized.get("items"), dict):
        normalized["items"] = strict_schema(normalized["items"])
    for branch_key in ("$defs", "definitions"):
        branches = normalized.get(branch_key)
        if isinstance(branches, dict):
            normalized[branch_key] = {
                key: strict_schema(value) if isinstance(value, dict) else value
                for key, value in branches.items()
            }
    return normalized


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    risk_level: ToolRisk
    requires_approval: bool
    source: ToolSource
    handler: Callable[..., Any] | None = None

    @property
    def input_schema(self) -> dict[str, Any]:
        return self.input_model.model_json_schema()

    @property
    def output_schema(self) -> dict[str, Any]:
        return self.output_model.model_json_schema()

    def validate(self, arguments: dict[str, Any]) -> BaseModel:
        return self.input_model.model_validate(arguments)

    def provider_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": strict_schema(self.input_schema),
            "strict": True,
        }
