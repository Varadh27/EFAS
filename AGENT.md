# AGENT.md — Autonomous Coding Rules for Enterprise Financial Audit System

## 1. Project Identity & Mission
You are building an **Enterprise Financial Audit & Variance Multi-Agent System** using **Python 3.11+, LangGraph, FastAPI, PostgreSQL, and Pytest**.
This codebase must reflect Big-4 (PwC) production standards: deterministic state transitions, strict SQL security, Human-in-the-Loop (HITL) governance, and 100% testable agent nodes.

---

## 2. Strict Framework & Syntax Constraints (CRITICAL)
1. **LangGraph Modern Syntax ONLY (`langgraph>=0.2.50`):**
   - **NEVER** use legacy LangChain `AgentExecutor`, `initialize_agent`, or `ConversationalRetrievalChain`.
   - Always use `StateGraph(AuditState)` from `langgraph.graph`.
   - For Human-in-the-Loop (HITL), **ALWAYS** use `from langgraph.types import interrupt, Command`.
   - When pausing execution, invoke `interrupt(payload)` inside the node and resume externally via `graph.invoke(Command(resume=user_input), config=config)`.
   - Use `PostgresSaver` from `langgraph.checkpoint.postgres` for production state persistence and `MemorySaver` for unit tests.

2. **Pydantic v2 ONLY (`pydantic>=2.7`):**
   - **NEVER** use `.dict()`, `.parse_obj()`, or `class Config:`.
   - Always use `.model_dump()`, `.model_validate()`, and `model_config = ConfigDict(...)`.
   - All LLM structured outputs must use `.with_structured_output(PydanticModel)`.

3. **Database & SQL Security:**
   - All LLM-generated SQL queries **MUST** be validated before execution:
     1. Must start with `SELECT` (case-insensitive).
     2. Must reject keywords: `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `TRUNCATE`, `GRANT`, `EXEC`.
   - Use `psycopg` (v3) or `SQLAlchemy 2.0` with read-only transaction scopes where possible.

4. **Testing & CI Discipline:**
   - Every new node added to `src/agents/nodes.py` must have a corresponding unit test in `tests/`.
   - Unit tests must **NOT** make live OpenAI/Anthropic API calls unless marked `@pytest.mark.integration`. Mock LLM calls or test deterministic state transitions directly.

5. **HITL API Lifecycle & Dynamic SQL Scoping:**
   - Standard REST routes: `POST /api/v1/audit/start`, `POST /api/v1/audit/resume/{thread_id}`, `GET /api/v1/audit/status/{thread_id}`, and `GET /health`.
   - Pre-validate SQL against destructive keywords (`DROP`, `DELETE`, `UPDATE`, `ALTER`, `TRUNCATE`) with HTTP 400 before graph invocation.
   - For table joins on common keys, use `USING (cost_center_code)` to prevent column ambiguity on dynamic user `WHERE` filters.
   - Accept both `APPROVE`/`APPROVED` and `REJECT`/`REJECTED` in request schemas to prevent 422 errors during manual UI demo runs.

---

## 3. Repository Directory Structure
Maintain this exact directory hierarchy:

```text
enterprise-audit-agent/
├── AGENT.md                        # Master instructions for Antigravity
├── README.md                       # Project documentation & architecture
├── docker-compose.yml              # PostgreSQL 16 service definition
├── Dockerfile                      # Production FastAPI container
├── requirements.txt                # Locked dependencies
├── .env.example                    # Environment variable template
├── policies/
│   └── corporate_audit_policy.md   # Ground-truth audit rules & materiality thresholds
├── src/
│   ├── __init__.py
│   ├── config.py                   # Pydantic Settings management
│   ├── db/
│   │   ├── __init__.py
│   │   ├── schema.sql              # DDL for GL accounts, transactions, invoices
│   │   ├── connection.py           # Safe read-only SQL execution & pooling
│   │   └── seed.py                 # Synthetic ledger + anomaly generator
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── state.py                # TypedDict & Pydantic schemas for LangGraph
│   │   ├── nodes.py                # Router, SQL Generator, Auditor, HITL Gate, Reporter
│   │   └── graph.py                # StateGraph assembly & checkpointer compilation
│   └── api/
│       ├── __init__.py
│       ├── schemas.py              # FastAPI Request/Response models
│       └── main.py                 # REST endpoints (/audit/start, /audit/resume)
└── tests/
    ├── __init__.py
    └── test_audit_graph.py         # Pytest suite for SQL safety, HITL pause/resume
```

---

## 4. Antigravity Execution Workflow
When asked to implement or modify features, follow this exact sequence:
1. **Inspect State & Policy First:** Check `src/agents/state.py` and `policies/corporate_audit_policy.md` before changing node logic.
2. **Modular Edits:** Modify one layer at a time (`db` -> `agents` -> `api` -> `tests`).
3. **Self-Verification:** After writing code, run `pytest -v` and `flake8 src/ tests/` in the terminal to verify zero regressions.