from typing import List, Optional, Literal, Any, Dict
from pydantic import BaseModel, Field, ConfigDict


class StartAuditRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    user_directive: Optional[str] = Field(
        default="Execute full corporate ledger reconciliation",
        description="Natural language directive or SQL query/filter",
        examples=[
            "Audit Q3 IT & Consulting spend",
            "WHERE cost_center_code = 'CC-100' AND amount < 4000",
        ],
    )
    thread_id: Optional[str] = Field(
        default=None,
        description="Optional custom thread ID; auto-generated if omitted",
        examples=["demo-thread-101"],
    )
    mock_transactions: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Optional mock ledger transactions for testing",
    )


class ResumeAuditRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    decision: Literal[
        "APPROVE", "REJECT", "ESCALATE", "APPROVED", "REJECTED", "ESCALATED"
    ] = Field(
        ...,
        description="Human auditor decision on flagged anomalies",
        examples=["APPROVE", "REJECT", "ESCALATE"],
    )
    notes: Optional[str] = Field(
        default="",
        description="Auditor justification notes",
        examples=["Verified VP pre-approval email; clearing variance."],
    )


class AuditResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    thread_id: str
    status: Literal["COMPLETED", "AWAITING_HUMAN_APPROVAL"]
    pending_node: Optional[str] = None
    requires_human_approval: Optional[bool] = None
    flagged_discrepancies: Optional[List[Dict[str, Any]]] = None
    human_decision: Optional[str] = None
    audit_summary: Optional[str] = None
    final_audit_memo: Optional[str] = None
