# ADR 0001: Own the orchestration loop

Status: accepted

AgentGuard does not use a multi-agent framework. The project owns provider
translation, tool validation, policy enforcement, persistence, approvals, and
grounding so those boundaries remain observable and testable.

