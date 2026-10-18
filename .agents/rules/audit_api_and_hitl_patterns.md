# Enterprise Audit Multi-Agent API & HITL Patterns

## 1. HITL API Lifecycle
For stateful LangGraph multi-agent workflows with human-in-the-loop interruption gates:
- `POST /api/v1/audit/start`: Initiates or queues an audit run. Returns `COMPLETED` if compliant or `AWAITING_HUMAN_APPROVAL` with `pending_node: "hitl_approval_gate"` when thresholds are breached.
- `POST /api/v1/audit/resume/{thread_id}`: Resumes paused execution via `Command(resume={"decision": payload.decision, "notes": payload.notes})`.
- `GET /api/v1/audit/status/{thread_id}`: Inspects graph snapshot values and next pending nodes.
- `GET /health`: Verifies service status and live database connectivity.

## 2. Dynamic SQL Scoping & Safety
- **Avoid Ambiguous Columns**: When joining tables sharing primary/foreign keys (e.g. `cost_center_code`), use `USING (cost_center_code)` so user-supplied `WHERE` filters do not fail with ambiguous column reference errors.
- **Pre-Graph Guardrails**: Intercept destructive SQL keywords (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `TRUNCATE`, `GRANT`, `REVOKE`, `EXEC`) at the API layer with HTTP 400 before invoking graph builders.
- **Scoped Evaluation**: When a custom SQL filter is passed, the compliance evaluator must strictly evaluate only the rows returned by that query.

## 3. Pydantic v2 Contract Resilience
- Support both imperative (`APPROVE`, `REJECT`, `ESCALATE`) and past-tense (`APPROVED`, `REJECTED`, `ESCALATED`) decision literals in request schemas to prevent 422 validation errors across manual UI testing.
- Allow optional custom `thread_id` so demo testers can track and resume specific threads deterministically.
