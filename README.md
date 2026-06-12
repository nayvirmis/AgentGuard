# AgentGuard

AgentGuard is a developer platform for tracing, evaluating, and securing LLM
agents that call MCP-style tools. It places a deterministic policy and
observability control plane between a model and every tool execution.

## What ships

- FastAPI control plane with append-only traces and resumable approvals
- Native calendar, draft-email, and mock-send tools
- Real MCP stdio document-search server over seeded academic documents
- Deterministic fake provider plus an OpenAI Responses API adapter
- Prompt-injection, sensitive-data, exfiltration, and tool-limit policies
- Citation-aware grounding checks
- Next.js Evidence Workbench with playground, traces, security analytics,
  evaluations, tools, policies, and responsive approval workflows
- 24 deterministic evaluation cases and local/demo seed data

## Public demo

- Frontend: [agentguard-livid.vercel.app](https://agentguard-livid.vercel.app)
- Backend health: [backend-production-e897.up.railway.app/health/ready](https://backend-production-e897.up.railway.app/health/ready)

## Quick start

```bash
cp .env.example .env
make install
make seed
```

Run the services in separate terminals:

```bash
make backend
make frontend
```

Open [http://localhost:3000](http://localhost:3000). Development mode uses a
local demo identity and the deterministic provider, so no external credentials
are required.

## Live OpenAI mode

Set `LLM_PROVIDER=openai`, `OPENAI_API_KEY`, and optionally `OPENAI_MODEL`.
OpenAI-specific response objects remain inside the provider adapter.
Configure credentials only through private local or deployment environment
settings. Never commit, publish, paste, or request an API key.

## Security boundary

The model never executes a tool directly. Each request is schema-validated,
redacted, evaluated by deterministic policies, and persisted before an allowed
handler executes. High-risk external actions require a single-use human
approval. `email_send_mock` never sends real email.

## Documentation

- [Architecture](docs/architecture.md)
- [Threat model](docs/threat-model.md)
- [Metric contracts](docs/metrics.md)
- [Visual contract](docs/visual-contract.md)
- [Design QA](docs/design-qa.md)
- [Architecture decisions](docs/adr/)

## Verification

```bash
.venv/bin/ruff check backend mcp_server
.venv/bin/pytest -q backend/tests
npm run lint --workspace frontend
npm run test --workspace frontend
npm run build --workspace frontend
```

The deterministic evaluation suite contains 24 cases and is available from
`/evaluations`. The current seeded baseline passes 24/24 cases.
