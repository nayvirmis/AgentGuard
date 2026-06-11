# Threat Model

## Protected assets

- User queries and retrieved academic documents
- Tool arguments and outputs
- Provider credentials and authentication tokens
- Approval authority and trace integrity

## Primary threats

- Direct and indirect prompt injection
- Sensitive-data disclosure
- External-recipient exfiltration
- Excessive agency and runaway tool loops
- Approval replay or cross-user approval
- Secret leakage through traces and errors

## Controls

- Deterministic policy rules before tool execution
- Structured schemas and bounded arguments
- Retrieved content labelled as untrusted evidence
- Single-use, expiring, owner-bound approvals
- Six-call and repeated-call limits
- Pre-persistence redaction and bounded output hashing
- Ownership checks, quotas, CORS, and structured errors

## Explicit non-goals

- Real email delivery
- Destructive file, financial, or infrastructure operations
- Enterprise tenant isolation guarantees

