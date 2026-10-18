from typing import Annotated, List, Optional, Literal
from typing_extensions import TypedDict
from pydantic import BaseModel, Field, ConfigDict
from langgraph.graph.message import add_messages


class DiscrepancyItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    txn_id: str = Field(description="Transaction ID from GL")
    vendor_name: str = Field(description="Vendor for transaction")
    actual_amount: float = Field(description="Actual posted dollar amount")
    variance_amount: float = Field(description="Dollar variance above PO")
    violation_type: Literal[
        "MATERIAL_VARIANCE",
        "HIGH_RISK_STRUCTURING",
        "MISSING_PO_CONTROL_FAILURE",
        "MISCLASSIFIED_EXPENSE",
        "HIGH_VALUE_THRESHOLD",
        "MISSING_PO_VIOLATION",
        "STRUCTURING_SPLIT_TX",
        "DUPLICATE_INVOICE",
        "WEEKEND_UNAPPROVED_SPEND",
    ]
    rule: Optional[str] = Field(
        default=None, description="Audit policy rule identifier (e.g. RULE_1)"
    )
    risk_score: float = Field(
        ge=0.0, le=1.0, description="Normalized risk score"
    )
    rationale: str = Field(
        description="Clear explanation of why this was flagged"
    )


class SQLQueryOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sql_query: str = Field(description="Read-only PostgreSQL SELECT statement")
    explanation: str = Field(description="Brief explanation of query filter")


class AuditState(TypedDict):
    messages: Annotated[list, add_messages]
    user_directive: str
    sql_query: Optional[str]
    raw_transactions: List[dict]
    flagged_discrepancies: List[dict]
    requires_human_approval: bool
    human_review_decision: Optional[
        Literal[
            "APPROVED",
            "REJECTED",
            "ESCALATED",
            "APPROVE",
            "REJECT",
            "ESCALATE",
        ]
    ]
    human_notes: Optional[str]
    final_audit_memo: Optional[str]
    audit_summary: Optional[str]
