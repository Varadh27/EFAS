import pytest
from langgraph.types import Command
from src.agents.nodes import (
    validate_readonly_sql,
    sql_extractor_node,
    compliance_evaluator_node,
)
from src.agents.graph import build_audit_graph


def test_sql_guardrail_blocks_destructive_queries():
    with pytest.raises(ValueError, match="Only SELECT queries"):
        validate_readonly_sql("DROP TABLE ledger_transactions;")

    with pytest.raises(ValueError, match="Destructive SQL keyword"):
        validate_readonly_sql(
            "SELECT * FROM ledger_transactions; DELETE FROM gl_accounts;"
        )

    valid = validate_readonly_sql(
        "SELECT txn_id, actual_amount FROM ledger_transactions;"
    )
    assert valid.startswith("SELECT")


def test_auto_clears_below_materiality_threshold():
    graph = build_audit_graph()
    config = {"configurable": {"thread_id": "test-thread-clean"}}

    clean_txns = [
        {
            "txn_id": "TXN-101",
            "vendor_name": "AWS Cloud",
            "po_number": "PO-9001",
            "po_authorized_amount": 1200.00,
            "actual_amount": 1200.00,
        }
    ]

    result = graph.invoke(
        {
            "user_directive": "Check routine cloud spend",
            "raw_transactions": clean_txns,
            "flagged_discrepancies": [],
            "requires_human_approval": False,
        },
        config=config,
    )

    snapshot = graph.get_state(config)
    assert snapshot.next == ()  # Did not pause
    assert "AUTO_CLEARED" in result["final_audit_memo"]


def test_hitl_interrupt_and_resume_on_material_variance():
    graph = build_audit_graph()
    config = {"configurable": {"thread_id": "test-thread-hitl"}}

    anomalous_txns = [
        {
            "txn_id": "TXN-999",
            "vendor_name": "Apex Strategy Group",
            "po_number": "PO-500",
            "po_authorized_amount": 4000.00,
            "actual_amount": 12500.00,  # $8.5k variance -> triggers >$5k gate
        }
    ]

    # Step 1: Run graph -> Expect pause at hitl_approval_gate
    graph.invoke(
        {
            "user_directive": "Audit Q3 consulting discrepancies",
            "raw_transactions": anomalous_txns,
            "flagged_discrepancies": [],
            "requires_human_approval": False,
        },
        config=config,
    )

    snapshot = graph.get_state(config)
    assert snapshot.next == ("hitl_approval_gate",)

    # Step 2: Resume execution with auditor decision
    final_state = graph.invoke(
        Command(
            resume={
                "decision": "REJECTED",
                "notes": "Unapproved $8.5k overrun; hold vendor payment.",
            }
        ),
        config=config,
    )

    assert final_state["human_review_decision"] == "REJECTED"
    assert "REJECTED" in final_state["final_audit_memo"]
    assert "hold vendor payment" in final_state["final_audit_memo"]


def test_detect_rule_1_high_value_transactions():
    """Rule 1: Single transactions > $5,000 requiring HITL sign-off."""
    state = {"user_directive": "Inspect high-value disbursements"}
    extracted = sql_extractor_node(state)
    assert len(extracted["raw_transactions"]) >= 200

    evaluation = compliance_evaluator_node(extracted)
    r1_items = [
        d for d in evaluation["flagged_discrepancies"] if d["rule"] == "RULE_1"
    ]
    r1_ids = {d["txn_id"] for d in r1_items}

    expected_ids = {"TX-ANOM-9001", "TX-ANOM-9002", "TX-ANOM-9003"}
    assert expected_ids.issubset(r1_ids)

    for item in r1_items:
        if item["txn_id"] in expected_ids:
            assert item["actual_amount"] > 5000.00
            assert item["violation_type"] == "HIGH_VALUE_THRESHOLD"
    assert evaluation["requires_human_approval"] is True


def test_detect_rule_2_missing_po_violations():
    """Rule 2: Transactions > $2,500 with missing/NULL po_number."""
    state = {"user_directive": "Inspect missing PO disbursements"}
    extracted = sql_extractor_node(state)
    evaluation = compliance_evaluator_node(extracted)

    r2_items = [
        d for d in evaluation["flagged_discrepancies"] if d["rule"] == "RULE_2"
    ]
    r2_ids = {d["txn_id"] for d in r2_items}

    expected_ids = {"TX-ANOM-9004", "TX-ANOM-9005", "TX-ANOM-9006"}
    assert expected_ids.issubset(r2_ids)

    for item in r2_items:
        if item["txn_id"] in expected_ids:
            assert item["actual_amount"] > 2500.00
            assert item["violation_type"] == "MISSING_PO_VIOLATION"


def test_detect_rule_3_split_transactions():
    """Rule 3: Split transactions (same vendor, same day, summing > $5,000)."""
    state = {"user_directive": "Inspect structuring & split transactions"}
    extracted = sql_extractor_node(state)
    evaluation = compliance_evaluator_node(extracted)

    r3_items = [
        d for d in evaluation["flagged_discrepancies"] if d["rule"] == "RULE_3"
    ]
    r3_ids = {d["txn_id"] for d in r3_items}

    expected_ids = {"TX-ANOM-9007", "TX-ANOM-9008", "TX-ANOM-9009"}
    assert expected_ids == r3_ids

    total_sum = sum(d["actual_amount"] for d in r3_items)
    assert total_sum == 14700.00  # 3 x $4,900
    for item in r3_items:
        assert item["vendor_name"] == "OmniChannel Events Pvt Ltd"
        assert item["violation_type"] == "STRUCTURING_SPLIT_TX"


def test_detect_rule_4_duplicate_invoices():
    """Rule 4: Duplicate invoices (same vendor, exact amount within 48h)."""
    state = {"user_directive": "Inspect duplicate billing"}
    extracted = sql_extractor_node(state)
    evaluation = compliance_evaluator_node(extracted)

    r4_items = [
        d for d in evaluation["flagged_discrepancies"] if d["rule"] == "RULE_4"
    ]
    r4_ids = {d["txn_id"] for d in r4_items}

    expected_ids = {
        "TX-ANOM-9010",
        "TX-ANOM-9011",
        "TX-ANOM-9012",
        "TX-ANOM-9013",
    }
    assert expected_ids == r4_ids

    datadog_items = [d for d in r4_items if d["vendor_name"] == "Datadog"]
    assert len(datadog_items) == 2
    assert datadog_items[0]["actual_amount"] == 3750.00

    blue_dart_items = [
        d for d in r4_items if d["vendor_name"] == "Blue Dart Express"
    ]
    assert len(blue_dart_items) == 2
    assert blue_dart_items[0]["actual_amount"] == 2980.00


def test_detect_rule_5_weekend_unapproved_spend():
    """Rule 5: Weekend transactions on T&E without VP approval."""
    state = {"user_directive": "Inspect weekend hospitality spend"}
    extracted = sql_extractor_node(state)
    evaluation = compliance_evaluator_node(extracted)

    r5_items = [
        d for d in evaluation["flagged_discrepancies"] if d["rule"] == "RULE_5"
    ]
    r5_ids = {d["txn_id"] for d in r5_items}

    expected_ids = {"TX-ANOM-9014", "TX-ANOM-9015"}
    assert expected_ids == r5_ids

    for item in r5_items:
        assert item["violation_type"] == "WEEKEND_UNAPPROVED_SPEND"
        assert item["actual_amount"] in (5800.00, 7400.00)


def test_full_database_audit_graph_all_planted_anomalies():
    """Audit graph execution against DB detecting all 15 planted anomalies."""
    graph = build_audit_graph()
    config = {"configurable": {"thread_id": "test-full-database-e2e"}}

    # Graph runs sql_extractor_node against PostgreSQL then evaluates
    graph.invoke(
        {"user_directive": "Execute full Q3 corporate reconciliation"},
        config=config,
    )

    snapshot = graph.get_state(config)
    # Paused at HITL review gate because material anomalies exceed $5,000
    assert snapshot.next == ("hitl_approval_gate",)

    flagged = snapshot.values.get("flagged_discrepancies", [])
    assert len(flagged) == 15

    all_anomaly_ids = {d["txn_id"] for d in flagged}
    expected_all_15 = {f"TX-ANOM-{i}" for i in range(9001, 9016)}
    assert all_anomaly_ids == expected_all_15

    # Resume the workflow via auditor sign-off
    resumed = graph.invoke(
        Command(
            resume={
                "decision": "APPROVED",
                "notes": (
                    "Reviewed and cleared all 15 flagged needles with VP "
                    "sign-offs."
                ),
            }
        ),
        config=config,
    )

    assert resumed["human_review_decision"] == "APPROVED"
    assert "**Transactions Inspected:** 200" in resumed["final_audit_memo"]
    assert "**Anomalies Flagged:** 15" in resumed["final_audit_memo"]
    assert "APPROVED" in resumed["final_audit_memo"]


def test_api_health_check():
    """Verify GET /health returns service and db connectivity status."""
    from fastapi.testclient import TestClient
    from src.api.main import app

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


def test_api_security_blocks_destructive_sql():
    """Verify POST /api/v1/audit/start rejects destructive SQL with 400."""
    from fastapi.testclient import TestClient
    from src.api.main import app

    client = TestClient(app)
    res_drop = client.post(
        "/api/v1/audit/start",
        json={"user_directive": "DROP TABLE general_ledger;"},
    )
    assert res_drop.status_code == 400
    assert "Destructive SQL keyword detected" in res_drop.json()["detail"]

    res_delete = client.post(
        "/api/v1/audit/start",
        json={"user_directive": "DELETE FROM cost_centers;"},
    )
    assert res_delete.status_code == 400
    assert "Destructive SQL keyword detected" in res_delete.json()["detail"]


def test_api_audit_start_compliant_subset():
    """Verify custom compliant query returns COMPLETED with 0 anomalies."""
    from fastapi.testclient import TestClient
    from src.api.main import app

    client = TestClient(app)
    response = client.post(
        "/api/v1/audit/start",
        json={
            "user_directive": (
                "WHERE cost_center_code = 'CC-100' AND amount < 3500"
            ),
            "thread_id": "test-api-compliant-thread",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["thread_id"] == "test-api-compliant-thread"
    assert data["status"] == "COMPLETED"
    assert data["requires_human_approval"] is False
    assert data["flagged_discrepancies"] == []
    assert (
        data["audit_summary"]
        == "Audit analysis complete. Flagged anomalies: 0. Summary: Compliant."
    )


def test_api_audit_hitl_pause_status_and_resume():
    """Verify end-to-end API flow: start -> pause -> status -> resume."""
    from fastapi.testclient import TestClient
    from src.api.main import app

    client = TestClient(app)
    thread_id = "test-api-hitl-thread"

    # 1. Start audit with anomaly filter (> 5000)
    start_res = client.post(
        "/api/v1/audit/start",
        json={
            "user_directive": "WHERE amount > 5000",
            "thread_id": thread_id,
        },
    )
    assert start_res.status_code == 200
    start_data = start_res.json()
    assert start_data["thread_id"] == thread_id
    assert start_data["status"] == "AWAITING_HUMAN_APPROVAL"
    assert start_data["pending_node"] == "hitl_approval_gate"
    assert len(start_data["flagged_discrepancies"]) > 0

    # 2. Check thread status via GET
    status_res = client.get(f"/api/v1/audit/status/{thread_id}")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["status"] == "AWAITING_HUMAN_APPROVAL"
    assert status_data["pending_node"] == "hitl_approval_gate"

    # 3. Resume with APPROVE
    resume_res = client.post(
        f"/api/v1/audit/resume/{thread_id}",
        json={"decision": "APPROVE", "notes": "Approved by senior auditor"},
    )
    assert resume_res.status_code == 200
    resume_data = resume_res.json()
    assert resume_data["status"] == "COMPLETED"
    assert resume_data["human_decision"] == "APPROVE"

    # 4. Check thread status after resume
    final_status_res = client.get(f"/api/v1/audit/status/{thread_id}")
    assert final_status_res.status_code == 200
    final_status_data = final_status_res.json()
    assert final_status_data["status"] == "COMPLETED"
    assert final_status_data["human_decision"] == "APPROVE"


def test_api_status_not_found():
    """Verify GET /api/v1/audit/status/{thread_id} returns 404 if missing."""
    from fastapi.testclient import TestClient
    from src.api.main import app

    client = TestClient(app)
    response = client.get("/api/v1/audit/status/non-existent-thread-id-999")
    assert response.status_code == 404
