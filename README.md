# Enterprise Financial Audit & Variance Multi-Agent System (EFAS)

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-v0.2+-FF6F00.svg?style=flat&logo=chainlink&logoColor=white)](https://github.com/langchain-ai/langgraph)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16-336791.svg?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Tests Passing](https://img.shields.io/badge/pytest-14%2F14%20passed-brightgreen.svg?style=flat&logo=pytest&logoColor=white)](tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Continuous Autonomous Ledger Surveillance, Deterministic Variance Analysis, and State-Preserving Human-in-the-Loop (HITL) Governance.**

---

## 1. Executive Overview & Business Case

### The Problem: Post-Hoc Audit Sampling is Obsolete
In traditional corporate audit operations, risk and accounting teams manually inspect a fractional sample (**< 5%**) of general ledger disbursements weeks or months after fiscal quarter-end. This retrospective sampling methodology suffers from critical operational vulnerabilities:
- **Sampling Blind Spots:** High-risk fraudulent structuring (invoice splitting below approval limits) and duplicate vendor billing systematically slip through randomized sampling.
- **Runaway Overruns:** Material budget variances remain unaddressed until the quarterly books close.
- **Labor Inefficiency:** Senior auditors expend hundreds of billable hours on repetitive spreadsheet three-way matching rather than high-risk investigation.

### The Solution: Continuous Autonomous Ledger Surveillance
**EFAS** replaces periodic statistical sampling with **100% continuous ledger surveillance**. Built to Big-4 (PwC / Deloitte) production engineering standards, EFAS continuously evaluates corporate transactions against ground-truth audit policies, computes variance risk scores, and halts execution when material risk is identified—requiring explicit senior auditor sign-off before reconciliation.

| Metric | Traditional Audit Sampling | EFAS Multi-Agent System |
| :--- | :--- | :--- |
| **Ledger Coverage** | 3% - 5% randomized sample | **100% full ledger scan** |
| **Detection Latency** | 30 to 90 days post-close | **Sub-second real-time detection** |
| **Policy Enforcement** | Heuristic, human-dependent | **Deterministic rule evaluation** |
| **Governance Gate** | Manual email thread sign-offs | **Stateful LangGraph `interrupt()` checkpoints** |
| **SQL Security** | Unrestricted analyst queries | **AST/Regex sanitized read-only transactions** |

---

## 2. System Architecture & Graph Topology

EFAS is orchestrated as a stateful, cyclic directed graph using **LangGraph**. Graph state persists across checkpoints, allowing long-running audits to suspend execution indefinitely at the Human-in-the-Loop gate and resume upon auditor sign-off.

```
                           [ User Directive / API Query ]
                                         │
                                         ▼
                     ┌───────────────────────────────────────┐
                     │          sql_extractor_node           │
                     │  - AST & Regex SQL Guardrail Check    │
                     │  - Dynamic Query Scoping (USING cc)   │
                     │  - Read-Only Transaction Context      │
                     └───────────────────┬───────────────────┘
                                         │
                                         ▼
                     ┌───────────────────────────────────────┐
                     │       compliance_evaluator_node       │
                     │  - Evaluates 5 Corporate Risk Rules   │
                     │  - Normalized Risk Scoring (0.0-1.0)  │
                     │  - Flags Material Threshold Breaches  │
                     └───────────────────┬───────────────────┘
                                         │
                                         ▼
                               /───────────────────\
                              <  Threshold Breach?  >
                               \───────────────────/
                                  │             │
                    Yes (> $5,000)│             │ No (Compliant)
                                  ▼             ▼
         ┌─────────────────────────────────┐    │
         │     hitl_approval_gate_node     │    │
         │  - Triggers interrupt(payload)  │    │
         │  - Awaits Human Decision via    │    │
         │    Command(resume=...)          │    │
         └────────────────┬────────────────┘    │
                          │                     │
                          │ Resumed with        │
                          │ Auditor Sign-off    │
                          ▼                     ▼
                     ┌───────────────────────────────────────┐
                     │         report_synthesis_node         │
                     │  - Generates Audit Reconciliation Memo│
                     │  - Formats Governance Audit Trail     │
                     └───────────────────┬───────────────────┘
                                         │
                                         ▼
                                      [ END ]
```

### Graph Node Responsibilities
1. **`sql_extractor_node`**: Formulates safe read-only SQL queries joining `general_ledger` and `cost_centers`. Resolves user directives into scoped filters using `USING (cost_center_code)` to eliminate column ambiguity while enforcing AST security barriers.
2. **`compliance_evaluator_node`**: Pure, deterministic domain evaluator inspecting transaction sets against the 5 corporate policy risk typologies.
3. **`route_after_evaluation`**: Conditional edge directing execution to `hitl_approval_gate` if `requires_human_approval` is `True`, or bypassing to `report_synthesis` if all transactions auto-clear.
4. **`hitl_approval_gate_node`**: Suspends workflow execution via LangGraph native `interrupt()`. Freezes execution state into the persistent checkpointer until an auditor issues an `APPROVE`, `REJECT`, or `ESCALATE` payload.
5. **`report_synthesis_node`**: Compiles an executive audit reconciliation memorandum detailing directive parameters, rows inspected, anomaly counts, auditor notes, and final governance status.

---

## 3. Regulatory Risk Typology Matrix

The synthetic test environment embeds 15 deterministic policy violations across 5 distinct risk categories within a 200-transaction corporate general ledger:

| Rule Code | Typology | Policy Constraint | Detection Logic | Planted Injections | Governance Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`RULE_1`** | **High-Value Materiality** | Line-item disbursements $> \$5,000.00$ require mandatory executive sign-off. | Single transaction `amount > 5000.00` or variance $> \$5,000.00$. | `TX-ANOM-9001`<br>`TX-ANOM-9002`<br>`TX-ANOM-9003` | **Halts at `hitl_approval_gate`** (`interrupt()`) |
| **`RULE_2`** | **Missing Purchase Order** | Three-way matching control failure: disbursements $> \$2,500.00$ lacking approved PO. | `amount > 2500.00` AND `po_number IS NULL`. | `TX-ANOM-9004`<br>`TX-ANOM-9005`<br>`TX-ANOM-9006` | Flagged as `MISSING_PO_VIOLATION` (Risk Score: 0.80) |
| **`RULE_3`** | **Structuring & Split Invoicing** | Bypassing manager $\$5,000$ limit via same-day split invoices. | Multiple invoices for same vendor on same date summing $> \$5,000.00$. | `TX-ANOM-9007`<br>`TX-ANOM-9008`<br>`TX-ANOM-9009` | Flagged as `STRUCTURING_SPLIT_TX` (Triggers HITL Review) |
| **`RULE_4`** | **Duplicate Billing** | Accidental or fraudulent re-submission of identical invoices. | Same vendor + exact identical dollar amount within a 48-hour window. | `TX-ANOM-9010` & `9011`<br>`TX-ANOM-9012` & `9013` | Flagged as `DUPLICATE_INVOICE` (Risk Score: 0.85) |
| **`RULE_5`** | **Unauthorized Weekend T&E** | Weekend entertainment/hospitality spend incurred without VP pre-approval. | Weekend date (`Sat/Sun`) + `TRAVEL_AND_ENTERTAINMENT` category without VP approval. | `TX-ANOM-9014`<br>`TX-ANOM-9015` | Flagged as `WEEKEND_UNAPPROVED_SPEND` (Triggers HITL Review) |

---

## 4. Repository Structure

```text
enterprise-audit-agent/
├── AGENT.md                        # Master architectural constraints & Big-4 standards
├── README.md                       # Comprehensive system documentation
├── docker-compose.yml              # PostgreSQL 16 container definition
├── Dockerfile                      # Production container image
├── requirements.txt                # Locked dependencies (Python 3.11+, LangGraph, FastAPI)
├── .env.example                    # Sanitized environment template
├── policies/
│   └── corporate_audit_policy.md   # Ground-truth audit rules & materiality thresholds
├── .agents/
│   └── rules/
│       └── audit_api_and_hitl_patterns.md  # Standardized HITL & SQL scoping rules
├── src/
│   ├── __init__.py
│   ├── config.py                   # Pydantic v2 Settings management
│   ├── db/
│   │   ├── __init__.py
│   │   ├── schema.sql              # DDL schema for GL accounts, ledger, audit logs
│   │   ├── connection.py           # Read-only psycopg connection pooling
│   │   └── seed.py                 # Synthetic ledger (200 rows + 15 planted needles)
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── state.py                # TypedDict state schema & Pydantic models
│   │   ├── nodes.py                # SQL extractor, compliance evaluator, HITL gate
│   │   └── graph.py                # StateGraph assembly & checkpointing
│   └── api/
│       ├── __init__.py
│       ├── schemas.py              # Pydantic v2 API request/response models
│       └── main.py                 # REST routes (/start, /resume, /status, /health)
└── tests/
    ├── __init__.py
    └── test_audit_graph.py         # Full automated Pytest suite (14 unit/integration tests)
```

---

## 5. Quickstart & Reproducibility Guide

Follow these steps to replicate the complete environment, seed the test ledger, and launch the service:

### 1. Environment & Dependencies
```bash
# Clone the repository
git clone https://github.com/your-org/enterprise-audit-system.git
cd enterprise-audit-system

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install locked dependencies
pip install -r requirements.txt
```

### 2. Configuration & Container Setup
```bash
# Initialize local environment variables from sanitized template
cp .env.example .env

# Launch PostgreSQL 16 container via Docker or Podman
docker compose up -d
```

### 3. Seed Database with Planted Anomalies
```bash
# Populate PostgreSQL with 185 compliant baselines + 15 planted audit needles
python src/db/seed.py
```
*Output: `Successfully seeded 5 cost centers and 200 ledger rows (15 planted audit anomalies)`*

### 4. Execute Full Automated Test Suite
```bash
pytest tests/test_audit_graph.py -v
```
*Output: `14 passed in <1.0s`*

### 5. Launch FastAPI Service
```bash
uvicorn src.api.main:app --reload --port 8000
```
- **API Health Check:** `http://localhost:8000/health`
- **Interactive Swagger Documentation:** `http://localhost:8000/docs`

---

## 6. Interactive Demonstration Walkthrough

The following walkthrough demonstrates the Human-in-the-Loop lifecycle using `curl`:

### Step 1: Trigger an Audit on High-Value Spend (Halts at HITL Gate)
Send an audit request with a directive filtering transactions exceeding the $\$5,000$ materiality threshold:

```bash
curl -X POST "http://localhost:8000/api/v1/audit/start" \
     -H "Content-Type: application/json" \
     -d '{
       "user_directive": "WHERE amount > 5000",
       "thread_id": "demo-thread-hitl"
     }'
```

**Expected Response (`HTTP 200` — Suspended at HITL Gate):**
```json
{
  "thread_id": "demo-thread-hitl",
  "status": "AWAITING_HUMAN_APPROVAL",
  "pending_node": "hitl_approval_gate",
  "requires_human_approval": true,
  "flagged_discrepancies": [
    {
      "txn_id": "TX-ANOM-9001",
      "vendor_name": "Snowflake Inc",
      "actual_amount": 14850.0,
      "variance_amount": 14850.0,
      "violation_type": "HIGH_VALUE_THRESHOLD",
      "rule": "RULE_1",
      "risk_score": 0.95,
      "rationale": "Transaction of $14,850.00 exceeds $5,000.00 materiality threshold requiring mandatory HITL sign-off."
    },
    {
      "txn_id": "TX-ANOM-9002",
      "vendor_name": "Deloitte Forensic Advisory",
      "actual_amount": 22500.0,
      "variance_amount": 22500.0,
      "violation_type": "HIGH_VALUE_THRESHOLD",
      "rule": "RULE_1",
      "risk_score": 0.95,
      "rationale": "Transaction of $22,500.00 exceeds $5,000.00 materiality threshold requiring mandatory HITL sign-off."
    }
  ]
}
```

---

### Step 2: Inspect Suspended Thread State
Verify that the LangGraph checkpointer maintains thread isolation and captures pending nodes:

```bash
curl -X GET "http://localhost:8000/api/v1/audit/status/demo-thread-hitl"
```

**Expected Response:**
```json
{
  "thread_id": "demo-thread-hitl",
  "status": "AWAITING_HUMAN_APPROVAL",
  "pending_node": "hitl_approval_gate",
  "requires_human_approval": true
}
```

---

### Step 3: Senior Auditor Signs Off via Resume Command
Resume the paused execution using `Command(resume=...)` by passing the auditor's decision and justification:

```bash
curl -X POST "http://localhost:8000/api/v1/audit/resume/demo-thread-hitl" \
     -H "Content-Type: application/json" \
     -d '{
       "decision": "APPROVE",
       "notes": "Verified VP pre-approval documentation for Q3 infrastructure burst overage."
     }'
```

**Expected Response (`HTTP 200` — Audit Completed & Reconciled):**
```json
{
  "thread_id": "demo-thread-hitl",
  "status": "COMPLETED",
  "human_decision": "APPROVE",
  "final_audit_memo": "### Executive Audit Reconciliation Memo\n- **Directive:** WHERE amount > 5000\n- **Transactions Inspected:** 6\n- **Anomalies Flagged:** 6\n- **Governance Status:** `APPROVE`\n- **Auditor Notes:** Verified VP pre-approval documentation for Q3 infrastructure burst overage.\n",
  "audit_summary": "Audit analysis complete. Flagged anomalies: 6. Summary: Anomalies detected."
}
```

---

### Step 4: Verify Clean Ledger Run (Auto-Cleared, Zero Invocations of HITL)
Demonstrate that compliant ledger subsets execute without triggering human intervention:

```bash
curl -X POST "http://localhost:8000/api/v1/audit/start" \
     -H "Content-Type: application/json" \
     -d '{
       "user_directive": "WHERE cost_center_code = '\''CC-100'\'' AND amount < 3500",
       "thread_id": "demo-thread-clean"
     }'
```

**Expected Response:**
```json
{
  "thread_id": "demo-thread-clean",
  "status": "COMPLETED",
  "requires_human_approval": false,
  "flagged_discrepancies": [],
  "audit_summary": "Audit analysis complete. Flagged anomalies: 0. Summary: Compliant."
}
```

---

## 7. Production Security & Guardrails

### 1. Multi-Stage SQL Injection Prevention
All incoming database queries are guarded by a defense-in-depth security model:
- **Pre-Execution API Layer:** User directives are inspected via regular expression tokenization. Any occurrence of destructive keywords (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `TRUNCATE`, `GRANT`, `REVOKE`, `EXEC`) is rejected immediately with `HTTP 400 Bad Request` prior to graph invocation.
- **Node-Level AST Validation:** `validate_readonly_sql()` confirms queries strictly begin with `SELECT` and contain no sub-query statement delimiters.
- **Read-Only Transaction Isolation:** Database connections are initiated with `conn.read_only = True` under PostgreSQL transaction semantics.

```bash
# Example: Immediate rejection of destructive payload
curl -i -X POST "http://localhost:8000/api/v1/audit/start" \
     -H "Content-Type: application/json" \
     -d '{"user_directive": "DROP TABLE general_ledger;"}'

# HTTP/1.1 400 Bad Request
# {"detail": "Security Violation: Destructive SQL keyword detected."}
```

### 2. State-Preserving Thread Isolation
- Graph checkpoints are keyed by unique `thread_id` UUIDs, preventing race conditions or state pollution between concurrent audit operations.
- Long-running interruptions are fully decoupled from HTTP connection lifetimes; the client or auditor can resume minutes, hours, or days later.

### 3. Strict Schema Validation (Pydantic v2)
- Models enforce strict type coercion via `ConfigDict(extra="ignore")`, preventing payload spoofing.
- Decision payloads tolerate both imperative (`APPROVE`, `REJECT`, `ESCALATE`) and past-tense (`APPROVED`, `REJECTED`, `ESCALATED`) literals to guarantee frictionless UI integration.

---

## 8. License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
