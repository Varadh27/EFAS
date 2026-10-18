# Enterprise Financial Audit & Variance Multi-Agent System

An enterprise-grade financial audit, three-way matching, and variance reconciliation multi-agent system built with **LangGraph**, **FastAPI**, **PostgreSQL**, and **Pytest**.

## Architecture & Workflow

1. **SQL Generator Node (`sql_generator_node`)**: Formulates safe read-only queries against ledger transactions with strict AST/regex security checks.
2. **Auditor Evaluation Node (`auditor_evaluation_node`)**: Applies corporate compliance policy (e.g. $5,000 materiality gate, missing PO detection).
3. **HITL Approval Gate Node (`hitl_approval_gate_node`)**: Pauses workflow execution using LangGraph `interrupt()`, awaiting senior auditor sign-off.
4. **Report Synthesis Node (`report_synthesis_node`)**: Compiles reconciliation decisions into a formal audit memorandum.

## Directory Structure

```text
.
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

## Running the Application

### 1. Start Database
```bash
docker compose up -d
```

### 2. Run Tests
```bash
pytest -v
```

### 3. Launch API
```bash
uvicorn src.api.main:app --reload --port 8000
```
