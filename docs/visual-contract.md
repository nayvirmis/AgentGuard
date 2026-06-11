# Visual Contract

The files in `Design References/ChatGPT Images/` are design references, not
runtime assets.

| Reference | Route | Purpose |
| --- | --- | --- |
| `1.png` | `/runs/[id]` | Awaiting-approval execution detail |
| `2.png` | `/playground` | Ready-state agent playground |
| `3.png` | `/runs/[id]?view=trace` | Ordered trace explorer |
| `4.png` | `/security` | Security and reliability analytics |
| `5.png` | `/evaluations` | Evaluation suite and case inspector |
| `6.png` | `/tools` | Tool registry and MCP inspector |
| `7.png` | `/runs/[id]` mobile | Responsive approval flow |

## Intentional corrections

- A policy that did not match is `not_triggered`, never `blocked`.
- `document_search` is the only MCP tool in v1.
- Provider traces expose metadata and summaries, never hidden reasoning.
- Metrics render from API data and do not copy illustrative screenshot values.
- Mobile content fills the viewport; the reference image's outer canvas is not
  part of the application.

