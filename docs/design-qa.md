# AgentGuard Design QA

## Visual contract

- Reference 1: execution detail and approval inspector
- Reference 2: playground and configuration overview
- Reference 3: trace explorer and event inspector
- Reference 4: security dashboard
- Reference 5: evaluation suite
- Reference 6: tool registry
- Reference 7: compact mobile execution

## Verification

Tested locally on June 11, 2026 with the in-app browser.

- Desktop viewport: 1536 x 1024
- Mobile viewport: 430 x 932
- Routes: `/playground`, `/runs`, `/runs/[id]`, `/security`, `/evaluations`,
  `/tools`, and `/policies`
- Live flows: grounded document retrieval, approval-required mock send, approved
  resumption, blocked direct injection, and deterministic evaluation execution

## Resolved differences

| Priority | Difference | Resolution |
| --- | --- | --- |
| P0 | Local build fell back to a serif font | Bundled the local Geist package and applied Geist Sans/Mono variables |
| P0 | Local API data was blocked at the `127.0.0.1` origin | Added explicit local CORS origins and removed GET preflights |
| P0 | Approval resumption discarded earlier evidence | Deep-copied persisted orchestration JSON before nested mutations |
| P1 | Policy badges collided with long rule IDs | Reflowed the 320px inspector cards |
| P1 | Mobile shell omitted the product brand | Added a compact fixed AgentGuard header |
| P1 | Long run IDs crowded the mobile status | Enabled wrapping and bounded typography |
| P1 | Completed tools displayed `executed` | Mapped successful execution to the contract label `allowed` |
| P1 | Citation rows used placeholder handbook text | Rendered real supporting evidence from grounding details |
| P2 | Screenshot model names implied a fixed model | Kept provider/model values configurable |
| P2 | Inactive policies appeared blocked in references | Implemented `not_triggered` |

## Accepted differences

- IDs, dates, latency, and metrics are generated from the running demo rather than
  copied from the references.
- The mobile inspector stacks below execution content instead of using multiple
  collapsed accordions; all sections remain keyboard accessible and readable.
- Dev-only Next.js controls can appear during local screenshots and are absent in
  production builds.

## Result

No unresolved P0-P2 visual or interaction defects remain for the local demo.
