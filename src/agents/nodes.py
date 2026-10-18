from collections import defaultdict
from datetime import date, datetime
import os
import re
from typing import Any, Dict, Optional
from dotenv import load_dotenv
from langgraph.types import interrupt
import psycopg
from psycopg.rows import dict_row
from src.agents.state import AuditState

load_dotenv()

DEFAULT_SQL_QUERY = (
    "SELECT "
    "gl.transaction_id, "
    "gl.transaction_date, "
    "cost_center_code, "
    "gl.vendor_name, "
    "gl.amount, "
    "gl.currency, "
    "gl.po_number, "
    "gl.expense_category, "
    "gl.description, "
    "gl.submitted_by, "
    "gl.is_weekend_submission, "
    "gl.status, "
    "gl.created_at, "
    "cc.department_name, "
    "cc.quarterly_budget, "
    "cc.cost_center_owner "
    "FROM general_ledger gl "
    "LEFT JOIN cost_centers cc "
    "USING (cost_center_code) "
    "ORDER BY gl.transaction_date DESC, gl.transaction_id ASC"
)

BASE_SELECT_QUERY = (
    "SELECT "
    "gl.transaction_id, "
    "gl.transaction_date, "
    "cost_center_code, "
    "gl.vendor_name, "
    "gl.amount, "
    "gl.currency, "
    "gl.po_number, "
    "gl.expense_category, "
    "gl.description, "
    "gl.submitted_by, "
    "gl.is_weekend_submission, "
    "gl.status, "
    "gl.created_at, "
    "cc.department_name, "
    "cc.quarterly_budget, "
    "cc.cost_center_owner "
    "FROM general_ledger gl "
    "LEFT JOIN cost_centers cc "
    "USING (cost_center_code)"
)

FORBIDDEN_SQL_PATTERNS = re.compile(
    r"\b(DROP|DELETE|UPDATE|INSERT|ALTER|TRUNCATE|GRANT|REVOKE|EXEC)\b",
    re.IGNORECASE,
)


def validate_readonly_sql(sql: str) -> str:
    """Deterministic guardrail ensuring generated SQL is strictly read-only."""
    cleaned = sql.strip().rstrip(";")
    if not cleaned.upper().startswith("SELECT"):
        raise ValueError(
            "Security Violation: Only SELECT queries are permitted."
        )
    if FORBIDDEN_SQL_PATTERNS.search(cleaned):
        raise ValueError(
            "Security Violation: Destructive SQL keyword detected."
        )
    return cleaned


def get_database_url() -> str:
    """Retrieves PostgreSQL DATABASE_URL from .env or fallback config."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        from src.config import settings

        db_url = settings.database_url
    return db_url


def resolve_query_from_state(state: AuditState) -> str:
    """Builds SQL query from state.sql_query or user_directive."""
    explicit_query = state.get("sql_query")
    if explicit_query and explicit_query.strip():
        return explicit_query.strip()

    directive = state.get("user_directive", "")
    if directive and directive.strip():
        cleaned = directive.strip().rstrip(";")
        if cleaned.upper().startswith("SELECT"):
            return cleaned

        where_match = re.search(
            r"(\bWHERE\b.+)", cleaned, re.IGNORECASE | re.DOTALL
        )
        if where_match:
            where_clause = where_match.group(1).strip().rstrip(";")
            return (
                f"{BASE_SELECT_QUERY} {where_clause} "
                "ORDER BY gl.transaction_date DESC, gl.transaction_id ASC"
            )

    return DEFAULT_SQL_QUERY


def sql_extractor_node(state: AuditState) -> Dict[str, Any]:
    """Queries PostgreSQL (general_ledger & cost_centers) using psycopg."""
    existing_txns = state.get("raw_transactions")
    if existing_txns and len(existing_txns) > 0:
        return {
            "sql_query": state.get("sql_query") or DEFAULT_SQL_QUERY,
            "raw_transactions": existing_txns,
        }

    query_str = resolve_query_from_state(state)
    safe_sql = validate_readonly_sql(query_str)
    db_url = get_database_url()

    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(safe_sql)
            results = [dict(r) for r in cur.fetchall()]

    return {"sql_query": safe_sql, "raw_transactions": results}


# Backward-compatible alias
sql_generator_node = sql_extractor_node


def _to_float(val: Any) -> float:
    if val is None:
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def _to_date(val: Any) -> Optional[date]:
    if val is None:
        return None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, str):
        try:
            return date.fromisoformat(val)
        except ValueError:
            try:
                return datetime.fromisoformat(val).date()
            except ValueError:
                return None
    return None


def _get_txn_id(txn: Dict[str, Any]) -> str:
    return str(txn.get("transaction_id") or txn.get("txn_id") or "")


def _get_po_number(txn: Dict[str, Any]) -> Optional[str]:
    po = txn.get("po_number")
    if po is None:
        return None
    po_str = str(po).strip()
    if po_str == "" or po_str.lower() in ("none", "null"):
        return None
    return po_str


def compliance_evaluator_node(state: AuditState) -> Dict[str, Any]:
    """Evaluates raw transactions against all 5 corporate audit policies."""
    transactions = state.get("raw_transactions", [])
    requires_hitl = False

    categorized_ids = set()

    # --- Rule 5: Weekend transactions on Travel/Entertainment ---
    rule_5_flagged = []
    for txn in transactions:
        tid = _get_txn_id(txn)
        tx_date = _to_date(txn.get("transaction_date"))
        is_weekend = txn.get("is_weekend_submission") or (
            tx_date is not None and tx_date.weekday() in (5, 6)
        )
        cat = str(txn.get("expense_category") or "").upper()
        is_te = (
            "TRAVEL" in cat or "ENTERTAINMENT" in cat or "HOSPITALITY" in cat
        )
        desc = str(txn.get("description") or "").lower()
        has_vp = (
            any(
                k in desc
                for k in (
                    "vp approval",
                    "vp pre-approval",
                    "vp approved",
                    "vp sign-off",
                )
            )
            and "without" not in desc
            and "no" not in desc
        )
        amount = _to_float(
            txn.get("amount")
            if txn.get("amount") is not None
            else txn.get("actual_amount")
        )

        if is_weekend and is_te and not has_vp and amount > 500.0:
            categorized_ids.add(tid)
            if amount > 5000.0:
                requires_hitl = True
            rule_5_flagged.append({
                "txn_id": tid,
                "vendor_name": txn.get("vendor_name", ""),
                "actual_amount": amount,
                "variance_amount": amount,
                "violation_type": "WEEKEND_UNAPPROVED_SPEND",
                "rule": "RULE_5",
                "risk_score": 0.90,
                "rationale": (
                    f"Weekend transaction of ${amount:,.2f} on {cat} lacks "
                    "mandatory VP pre-approval."
                ),
            })

    # --- Rule 4: Duplicate invoices (same vendor, amount within 48h) ---
    rule_4_flagged = []
    r4_ids = set()
    n = len(transactions)
    for i in range(n):
        for j in range(i + 1, n):
            t1, t2 = transactions[i], transactions[j]
            id1, id2 = _get_txn_id(t1), _get_txn_id(t2)
            if id1 in categorized_ids or id2 in categorized_ids:
                continue
            if t1.get("vendor_name") != t2.get("vendor_name"):
                continue
            amt1 = _to_float(
                t1.get("amount")
                if t1.get("amount") is not None
                else t1.get("actual_amount")
            )
            amt2 = _to_float(
                t2.get("amount")
                if t2.get("amount") is not None
                else t2.get("actual_amount")
            )
            if abs(amt1 - amt2) >= 0.001:
                continue

            d1 = _to_date(t1.get("transaction_date"))
            d2 = _to_date(t2.get("transaction_date"))
            if d1 is not None and d2 is not None:
                day_diff = abs((d1 - d2).days)
                po1, po2 = t1.get("po_number"), t2.get("po_number")
                if 0 < day_diff <= 2 or (day_diff == 0 and po1 == po2):
                    for t, tid, amt in [(t1, id1, amt1), (t2, id2, amt2)]:
                        if tid not in r4_ids:
                            r4_ids.add(tid)
                            categorized_ids.add(tid)
                            if amt > 5000.0:
                                requires_hitl = True
                            rule_4_flagged.append({
                                "txn_id": tid,
                                "vendor_name": t.get("vendor_name", ""),
                                "actual_amount": amt,
                                "variance_amount": amt,
                                "violation_type": "DUPLICATE_INVOICE",
                                "rule": "RULE_4",
                                "risk_score": 0.85,
                                "rationale": (
                                    "Duplicate invoice: exact amount "
                                    f"${amt:,.2f} billed by vendor "
                                    f"'{t.get('vendor_name')}' within 48h."
                                ),
                            })

    # --- Rule 3: Split transactions (same vendor, same day > $5,000) ---
    rule_3_flagged = []
    groups = defaultdict(list)
    for t in transactions:
        tid = _get_txn_id(t)
        if tid in categorized_ids:
            continue
        v = t.get("vendor_name", "")
        d = _to_date(t.get("transaction_date"))
        if d is not None:
            groups[(v, d)].append(t)

    for (v, d), grp in groups.items():
        if len(grp) > 1:
            tot = sum(
                _to_float(
                    x.get("amount")
                    if x.get("amount") is not None
                    else x.get("actual_amount")
                )
                for x in grp
            )
            if tot > 5000.0:
                if all(
                    "- ref #" in str(x.get("description", "")).lower()
                    for x in grp
                ):
                    continue
                requires_hitl = True
                for x in grp:
                    tid = _get_txn_id(x)
                    categorized_ids.add(tid)
                    amt = _to_float(
                        x.get("amount")
                        if x.get("amount") is not None
                        else x.get("actual_amount")
                    )
                    rule_3_flagged.append({
                        "txn_id": tid,
                        "vendor_name": v,
                        "actual_amount": amt,
                        "variance_amount": tot,
                        "violation_type": "STRUCTURING_SPLIT_TX",
                        "rule": "RULE_3",
                        "risk_score": 0.92,
                        "rationale": (
                            f"Split transaction / structuring: {len(grp)} "
                            f"invoices for vendor '{v}' on {d} sum to "
                            f"${tot:,.2f}, exceeding the $5,000 limit."
                        ),
                    })

    # --- Rule 2: Missing PO (> $2,500 without valid PO number) ---
    rule_2_flagged = []
    for txn in transactions:
        tid = _get_txn_id(txn)
        if tid in categorized_ids:
            continue
        amt = _to_float(
            txn.get("amount")
            if txn.get("amount") is not None
            else txn.get("actual_amount")
        )
        po = _get_po_number(txn)
        if amt > 2500.0 and po is None:
            categorized_ids.add(tid)
            if amt > 5000.0:
                requires_hitl = True
            rule_2_flagged.append({
                "txn_id": tid,
                "vendor_name": txn.get("vendor_name", ""),
                "actual_amount": amt,
                "variance_amount": amt,
                "violation_type": "MISSING_PO_VIOLATION",
                "rule": "RULE_2",
                "risk_score": 0.80,
                "rationale": (
                    f"Disbursement of ${amt:,.2f} exceeds $2,500.00 without "
                    "a valid Purchase Order (PO)."
                ),
            })

    # --- Rule 1: High-Value Threshold (> $5,000) ---
    rule_1_flagged = []
    for txn in transactions:
        tid = _get_txn_id(txn)
        if tid in categorized_ids:
            continue
        amt = _to_float(
            txn.get("amount")
            if txn.get("amount") is not None
            else txn.get("actual_amount")
        )
        po_auth = (
            _to_float(txn.get("po_authorized_amount"))
            if txn.get("po_authorized_amount") is not None
            else amt
        )
        variance = amt - po_auth if amt > po_auth else 0.0

        if amt > 5000.0 or variance > 5000.0:
            requires_hitl = True
            rule_1_flagged.append({
                "txn_id": tid,
                "vendor_name": txn.get("vendor_name", ""),
                "actual_amount": amt,
                "variance_amount": variance if variance > 0 else amt,
                "violation_type": "HIGH_VALUE_THRESHOLD",
                "rule": "RULE_1",
                "risk_score": 0.95,
                "rationale": (
                    f"Transaction of ${amt:,.2f} exceeds $5,000.00 "
                    "materiality threshold requiring mandatory HITL sign-off."
                ),
            })

    flagged = (
        rule_1_flagged
        + rule_2_flagged
        + rule_3_flagged
        + rule_4_flagged
        + rule_5_flagged
    )

    return {
        "flagged_discrepancies": flagged,
        "requires_human_approval": requires_hitl,
    }


# Backward-compatible alias
auditor_evaluation_node = compliance_evaluator_node


def hitl_approval_gate_node(state: AuditState) -> Dict[str, Any]:
    """Pauses LangGraph execution and awaits human auditor sign-off."""
    review_payload = interrupt({
        "alert": "MANDATORY_HITL_AUDIT_REVIEW",
        "flagged_count": len(state.get("flagged_discrepancies", [])),
        "discrepancies": state.get("flagged_discrepancies", []),
        "instructions": (
            "Provide decision ('APPROVED', 'REJECTED', 'ESCALATED') and notes."
        ),
    })

    return {
        "human_review_decision": review_payload.get("decision", "ESCALATED"),
        "human_notes": review_payload.get("notes", "No notes provided."),
    }


def report_synthesis_node(state: AuditState) -> Dict[str, Any]:
    """Synthesizes findings and decisions into an executive audit memo."""
    flagged = state.get("flagged_discrepancies", [])
    decision = state.get("human_review_decision") or "AUTO_CLEARED"
    notes = (
        state.get("human_notes")
        or "Below materiality threshold; auto-reconciled."
    )

    memo = (
        f"### Executive Audit Reconciliation Memo\n"
        f"- **Directive:** {state.get('user_directive')}\n"
        f"- **Transactions Inspected:** "
        f"{len(state.get('raw_transactions', []))}\n"
        f"- **Anomalies Flagged:** {len(flagged)}\n"
        f"- **Governance Status:** `{decision}`\n"
        f"- **Auditor Notes:** {notes}\n"
    )
    summary_status = (
        "Compliant." if len(flagged) == 0 else "Anomalies detected."
    )
    summary = (
        f"Audit analysis complete. Flagged anomalies: {len(flagged)}. "
        f"Summary: {summary_status}"
    )
    return {
        "final_audit_memo": memo,
        "audit_summary": summary,
    }
