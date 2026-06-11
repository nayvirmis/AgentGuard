# ADR 0002: Use MCP for document search

Status: accepted

`document_search` runs in a separate MCP stdio process. Read-only retrieval is
the best v1 demonstration of untrusted external tool output and indirect prompt
injection without introducing real external side effects.

