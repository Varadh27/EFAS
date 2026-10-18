import uuid
import psycopg
from fastapi import FastAPI, HTTPException
from langgraph.types import Command
from src.agents.graph import build_audit_graph
from src.agents.nodes import (
    validate_readonly_sql,
    FORBIDDEN_SQL_PATTERNS,
    get_database_url,
)
from src.api.schemas import (
    StartAuditRequest,
    ResumeAuditRequest,
)

app = FastAPI(
    title="Enterprise Financial Audit Multi-Agent API",
    version="1.0.0",
    description="LangGraph + HITL Stateful Financial Reconciliation Engine",
)

# Shared compiled graph instance with in-memory checkpointer
audit_graph = build_audit_graph()


@app.get("/health")
def health_check():
    """System and PostgreSQL database connectivity check."""
    db_status = "connected"
    is_healthy = True
    try:
        with psycopg.connect(get_database_url()) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
    except Exception:
        db_status = "disconnected"
        is_healthy = False

    return {
        "status": "healthy" if is_healthy else "degraded",
        "service": "enterprise-audit-agent",
        "database": db_status,
    }


@app.post("/api/v1/audit/start")
def start_audit_workflow(payload: StartAuditRequest):
    """Starts or queues an audit run."""
    # Pre-execution security check on user_directive
    if payload.user_directive:
        directive = payload.user_directive.strip()
        if FORBIDDEN_SQL_PATTERNS.search(directive):
            raise HTTPException(
                status_code=400,
                detail="Security Violation: Destructive SQL keyword detected.",
            )
        if directive.upper().startswith("SELECT"):
            try:
                validate_readonly_sql(directive)
            except ValueError as err:
                raise HTTPException(status_code=400, detail=str(err))

    thread_id = payload.thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "user_directive": (
            payload.user_directive
            or "Execute full corporate ledger reconciliation"
        ),
        "raw_transactions": payload.mock_transactions or [],
        "flagged_discrepancies": [],
        "requires_human_approval": False,
    }

    result = audit_graph.invoke(initial_state, config=config)
    snapshot = audit_graph.get_state(config)

    if snapshot.next:
        return {
            "thread_id": thread_id,
            "status": "AWAITING_HUMAN_APPROVAL",
            "pending_node": snapshot.next[0],
            "requires_human_approval": True,
            "flagged_discrepancies": result.get("flagged_discrepancies", []),
        }

    flagged = result.get("flagged_discrepancies", [])
    requires_approval = result.get("requires_human_approval", False)
    summary = result.get("audit_summary")
    if not summary:
        summary_status = (
            "Compliant." if len(flagged) == 0 else "Anomalies detected."
        )
        summary = (
            f"Audit analysis complete. Flagged anomalies: {len(flagged)}. "
            f"Summary: {summary_status}"
        )

    return {
        "thread_id": thread_id,
        "status": "COMPLETED",
        "requires_human_approval": requires_approval,
        "flagged_discrepancies": flagged,
        "audit_summary": summary,
        "final_audit_memo": result.get("final_audit_memo"),
    }


@app.post("/api/v1/audit/resume/{thread_id}")
def resume_audit_workflow(thread_id: str, payload: ResumeAuditRequest):
    """Resumes a paused Human-in-the-Loop thread."""
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = audit_graph.get_state(config)

    if not snapshot.next:
        raise HTTPException(
            status_code=400,
            detail="Thread is not paused at a Human-in-the-Loop checkpoint.",
        )

    resumed_result = audit_graph.invoke(
        Command(
            resume={
                "decision": payload.decision,
                "notes": payload.notes or "",
            }
        ),
        config=config,
    )

    return {
        "thread_id": thread_id,
        "status": "COMPLETED",
        "human_decision": resumed_result.get("human_review_decision"),
        "final_audit_memo": resumed_result.get("final_audit_memo"),
        "audit_summary": (
            resumed_result.get("audit_summary")
            or resumed_result.get("final_audit_memo")
        ),
    }


@app.get("/api/v1/audit/status/{thread_id}")
def get_audit_status(thread_id: str):
    """Inspects current graph snapshot and pending nodes for a thread."""
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = audit_graph.get_state(config)

    if not snapshot.values and not snapshot.next:
        raise HTTPException(
            status_code=404,
            detail=f"Audit thread '{thread_id}' not found.",
        )

    if snapshot.next:
        return {
            "thread_id": thread_id,
            "status": "AWAITING_HUMAN_APPROVAL",
            "pending_node": snapshot.next[0],
            "requires_human_approval": True,
            "flagged_discrepancies": snapshot.values.get(
                "flagged_discrepancies", []
            ),
            "audit_summary": snapshot.values.get("audit_summary"),
        }

    flagged = snapshot.values.get("flagged_discrepancies", [])
    requires_approval = snapshot.values.get("requires_human_approval", False)
    summary = snapshot.values.get("audit_summary")
    if not summary:
        summary_status = (
            "Compliant." if len(flagged) == 0 else "Anomalies detected."
        )
        summary = (
            f"Audit analysis complete. Flagged anomalies: {len(flagged)}. "
            f"Summary: {summary_status}"
        )

    return {
        "thread_id": thread_id,
        "status": "COMPLETED",
        "pending_node": None,
        "requires_human_approval": requires_approval,
        "flagged_discrepancies": flagged,
        "human_decision": snapshot.values.get("human_review_decision"),
        "final_audit_memo": snapshot.values.get("final_audit_memo"),
        "audit_summary": summary,
    }
