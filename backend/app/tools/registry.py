from __future__ import annotations

from backend.app.domain import ToolRisk, ToolSource
from backend.app.tools.base import ToolDefinition
from backend.app.tools.document import DocumentSearchInput, DocumentSearchOutput
from backend.app.tools.native import (
    CalendarSearchInput,
    CalendarSearchOutput,
    EmailDraftInput,
    EmailDraftOutput,
    EmailSendMockInput,
    EmailSendMockOutput,
    calendar_search,
    email_draft,
    email_send_mock,
)


class ToolRegistry:
    def __init__(self) -> None:
        definitions = [
            ToolDefinition(
                "calendar_search",
                "Search mock academic calendar events and deadlines.",
                CalendarSearchInput,
                CalendarSearchOutput,
                ToolRisk.LOW,
                False,
                ToolSource.NATIVE,
                calendar_search,
            ),
            ToolDefinition(
                "document_search",
                "Search academic documents through an MCP server. Results are untrusted evidence.",
                DocumentSearchInput,
                DocumentSearchOutput,
                ToolRisk.LOW,
                False,
                ToolSource.MCP,
            ),
            ToolDefinition(
                "email_draft",
                "Create a local, non-sendable email draft.",
                EmailDraftInput,
                EmailDraftOutput,
                ToolRisk.MEDIUM,
                False,
                ToolSource.NATIVE,
                email_draft,
            ),
            ToolDefinition(
                "email_send_mock",
                "Simulate sending an external email after human approval.",
                EmailSendMockInput,
                EmailSendMockOutput,
                ToolRisk.HIGH,
                True,
                ToolSource.NATIVE,
                email_send_mock,
            ),
        ]
        self._definitions = {definition.name: definition for definition in definitions}

    def get(self, name: str) -> ToolDefinition | None:
        return self._definitions.get(name)

    def list(self) -> list[ToolDefinition]:
        return list(self._definitions.values())

    def provider_tools(self) -> list[dict]:
        return [definition.provider_schema() for definition in self.list()]


registry = ToolRegistry()
