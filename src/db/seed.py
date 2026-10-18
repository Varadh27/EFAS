"""
Database Seeding Script for Enterprise Financial Audit & Variance Multi-Agent System.

Populates PostgreSQL (`general_ledger` and `cost_centers`) with:
1. Standard compliant corporate transactions across departments.
2. Five deterministic corporate audit policy anomalies (planted needles in the haystack)
   specifically designed to trigger the Evaluator-Optimizer and HITL interrupt gates.
"""

import os
import random
from datetime import date, datetime, timedelta
from decimal import Decimal
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://audit_admin:audit_secret_pw@localhost:5432/enterprise_audit_db"
)

COST_CENTERS = [
    ("CC-100", "Information Technology", Decimal("250000.00"), "Vikram Deshmukh"),
    ("CC-200", "Marketing & Growth", Decimal("180000.00"), "Ananya Sharma"),
    ("CC-300", "Legal & Compliance", Decimal("120000.00"), "Rajeshwari Iyer"),
    ("CC-400", "Operations & Supply Chain", Decimal("350000.00"), "Sandeep Kulkarni"),
    ("CC-500", "Human Resources", Decimal("950000.00"), "Meera Nair"),
]

NORMAL_VENDORS = {
    "CC-100": [
        ("Amazon Web Services", "Monthly cloud infrastructure hosting", (1200, 4200)),
        ("GitHub Inc", "Enterprise seat licenses", (400, 1500)),
        ("Cloudflare", "Edge security and DNS services", (250, 900)),
        ("Datadog", "APM and log observability suite", (1800, 3900)),
    ],
    "CC-200": [
        ("LinkedIn Ireland", "B2B sponsored lead generation", (1500, 4500)),
        ("Google Ads", "Search engine marketing campaign", (2000, 4800)),
        ("Canva Enterprise", "Design team subscription", (300, 850)),
        ("HubSpot Inc", "CRM marketing automation tier", (1200, 3200)),
    ],
    "CC-300": [
        ("LexisNexis", "Legal research database subscription", (950, 2800)),
        ("DocuSign", "Enterprise e-signature envelopes", (450, 1400)),
        ("Cyril Amarchand Mangaldas", "External regulatory advisory retainer", (2500, 4900)),
    ],
    "CC-400": [
        ("Blue Dart Express", "Domestic priority freight logistics", (600, 3400)),
        ("Delhivery Corporate", "Warehouse fulfillment batch", (1100, 4600)),
        ("Maersk Line", "Container port handling charges", (2200, 4850)),
    ],
    "CC-500": [
        ("Pluralsight", "L&D technical upskilling licenses", (800, 2900)),
        ("Mercer Consulting", "Annual compensation benchmarking", (1900, 4400)),
        ("WeWork India", "Offsite training room booking", (500, 1800)),
    ],
}

SUBMITTERS = [
    "arjun.mehta@enterprise.internal",
    "priya.menon@enterprise.internal",
    "rohan.joshi@enterprise.internal",
    "sneha.patil@enterprise.internal",
    "karan.malhotra@enterprise.internal",
]


def random_weekday_between(start_date: date, end_date: date) -> date:
    """Return a random weekday (Mon-Fri) between start_date and end_date."""
    delta_days = (end_date - start_date).days
    while True:
        candidate = start_date + timedelta(days=random.randint(0, delta_days))
        if candidate.weekday() < 5:  # 0=Mon .. 4=Fri
            return candidate


def generate_normal_transactions(count: int = 185) -> list[dict]:
    """Generate compliant corporate ledger entries that pass all audit rules."""
    random.seed(42)
    start_date = date(2026, 7, 1)
    end_date = date(2026, 9, 30)
    rows = []

    for i in range(1, count + 1):
        cc_code = random.choice(list(NORMAL_VENDORS.keys()))
        vendor, desc, (low, high) = random.choice(NORMAL_VENDORS[cc_code])
        tx_date = random_weekday_between(start_date, end_date)
        amount = Decimal(str(round(random.uniform(low, high), 2)))

        rows.append({
            "transaction_id": f"TX-2026-{i:04d}",
            "transaction_date": tx_date,
            "cost_center_code": cc_code,
            "vendor_name": vendor,
            "amount": amount,
            "currency": "USD",
            "po_number": f"PO-2026-{random.randint(10000, 99999)}",
            "expense_category": "OPERATING_EXPENSE",
            "description": f"{desc} - Ref #{i}",
            "submitted_by": random.choice(SUBMITTERS),
            "is_weekend_submission": False,
            "status": "POSTED",
        })

    return rows


def generate_planted_anomalies() -> list[dict]:
    """
    Generate 15 deterministic policy violations across 5 distinct audit risk typologies:
    - Rule 1 (HIGH_VALUE_THRESHOLD): Single transaction > $5,000 requiring HITL sign-off.
    - Rule 2 (MISSING_PO_VIOLATION): Transaction > $2,500 without a valid PO number.
    - Rule 3 (STRUCTURING_SPLIT_TX): Split invoices under $5,000 same vendor/day to bypass HITL.
    - Rule 4 (DUPLICATE_INVOICE): Exact same vendor + amount within 48 hours.
    - Rule 5 (WEEKEND_UNAPPROVED_SPEND): High-value weekend hospitality/entertainment spend.
    """
    return [
        # --- TYPE 1: High-Value Threshold (> $5,000) -> Triggers HITL Interrupt ---
        {
            "transaction_id": "TX-ANOM-9001",
            "transaction_date": date(2026, 8, 12),
            "cost_center_code": "CC-100",
            "vendor_name": "Snowflake Inc",
            "amount": Decimal("14850.00"),
            "currency": "USD",
            "po_number": "PO-2026-88412",
            "expense_category": "CLOUD_INFRASTRUCTURE",
            "description": "Q3 dedicated virtual warehouse burst capacity overage",
            "submitted_by": "arjun.mehta@enterprise.internal",
            "is_weekend_submission": False,
            "status": "FLAGGED_FOR_REVIEW",
        },
        {
            "transaction_id": "TX-ANOM-9002",
            "transaction_date": date(2026, 8, 24),
            "cost_center_code": "CC-300",
            "vendor_name": "Deloitte Forensic Advisory",
            "amount": Decimal("22500.00"),
            "currency": "USD",
            "po_number": "PO-2026-88901",
            "expense_category": "EXTERNAL_CONSULTING",
            "description": "Cross-border regulatory compliance diagnostic engagement",
            "submitted_by": "priya.menon@enterprise.internal",
            "is_weekend_submission": False,
            "status": "FLAGGED_FOR_REVIEW",
        },
        {
            "transaction_id": "TX-ANOM-9003",
            "transaction_date": date(2026, 9, 15),
            "cost_center_code": "CC-400",
            "vendor_name": "DHL Global Forwarding",
            "amount": Decimal("9420.50"),
            "currency": "USD",
            "po_number": "PO-2026-90112",
            "expense_category": "EMERGENCY_FREIGHT",
            "description": "Expedited air freight charter for customs-delayed shipment",
            "submitted_by": "sandeep.k@enterprise.internal",
            "is_weekend_submission": False,
            "status": "FLAGGED_FOR_REVIEW",
        },

        # --- TYPE 2: Missing Purchase Order (> $2,500 with NULL po_number) ---
        {
            "transaction_id": "TX-ANOM-9004",
            "transaction_date": date(2026, 7, 22),
            "cost_center_code": "CC-200",
            "vendor_name": "Creative Pulse Media LLP",
            "amount": Decimal("4650.00"),
            "currency": "USD",
            "po_number": None,
            "expense_category": "MARKETING_AGENCY",
            "description": "Ad-hoc product launch video production without procurement PO",
            "submitted_by": "rohan.joshi@enterprise.internal",
            "is_weekend_submission": False,
            "status": "POSTED",
        },
        {
            "transaction_id": "TX-ANOM-9005",
            "transaction_date": date(2026, 8, 19),
            "cost_center_code": "CC-100",
            "vendor_name": "NeuralScale AI Solutions",
            "amount": Decimal("6200.00"),
            "currency": "USD",
            "po_number": None,
            "expense_category": "SOFTWARE_SUBSCRIPTION",
            "description": "Unapproved GPU cluster fine-tuning run billed directly",
            "submitted_by": "arjun.mehta@enterprise.internal",
            "is_weekend_submission": False,
            "status": "FLAGGED_FOR_REVIEW",
        },
        {
            "transaction_id": "TX-ANOM-9006",
            "transaction_date": date(2026, 9, 3),
            "cost_center_code": "CC-500",
            "vendor_name": "Apex Executive Search",
            "amount": Decimal("3890.00"),
            "currency": "USD",
            "po_number": None,
            "expense_category": "RECRUITMENT_FEES",
            "description": "Retainer deposit for lateral leadership hiring (missing PO)",
            "submitted_by": "sneha.patil@enterprise.internal",
            "is_weekend_submission": False,
            "status": "POSTED",
        },

        # --- TYPE 3: Split Transaction / Structuring (3 invoices @ $4,900 same vendor/day = $14,700) ---
        {
            "transaction_id": "TX-ANOM-9007",
            "transaction_date": date(2026, 9, 10),
            "cost_center_code": "CC-200",
            "vendor_name": "OmniChannel Events Pvt Ltd",
            "amount": Decimal("4900.00"),
            "currency": "USD",
            "po_number": "PO-2026-77101",
            "expense_category": "EVENTS_SPONSORSHIP",
            "description": "Annual summit booth fabrication - Installment Part 1 of 3",
            "submitted_by": "rohan.joshi@enterprise.internal",
            "is_weekend_submission": False,
            "status": "POSTED",
        },
        {
            "transaction_id": "TX-ANOM-9008",
            "transaction_date": date(2026, 9, 10),
            "cost_center_code": "CC-200",
            "vendor_name": "OmniChannel Events Pvt Ltd",
            "amount": Decimal("4900.00"),
            "currency": "USD",
            "po_number": "PO-2026-77102",
            "expense_category": "EVENTS_SPONSORSHIP",
            "description": "Annual summit AV & lighting rig - Installment Part 2 of 3",
            "submitted_by": "rohan.joshi@enterprise.internal",
            "is_weekend_submission": False,
            "status": "POSTED",
        },
        {
            "transaction_id": "TX-ANOM-9009",
            "transaction_date": date(2026, 9, 10),
            "cost_center_code": "CC-200",
            "vendor_name": "OmniChannel Events Pvt Ltd",
            "amount": Decimal("4900.00"),
            "currency": "USD",
            "po_number": "PO-2026-77103",
            "expense_category": "EVENTS_SPONSORSHIP",
            "description": "Annual summit catering & branding - Installment Part 3 of 3",
            "submitted_by": "rohan.joshi@enterprise.internal",
            "is_weekend_submission": False,
            "status": "POSTED",
        },

        # --- TYPE 4: Duplicate Invoice Billing (Same vendor, exact amount within 24-48h) ---
        {
            "transaction_id": "TX-ANOM-9010",
            "transaction_date": date(2026, 8, 5),
            "cost_center_code": "CC-100",
            "vendor_name": "Datadog",
            "amount": Decimal("3750.00"),
            "currency": "USD",
            "po_number": "PO-2026-66200",
            "expense_category": "OPERATING_EXPENSE",
            "description": "August APM & log ingestion invoice #DD-8821",
            "submitted_by": "karan.malhotra@enterprise.internal",
            "is_weekend_submission": False,
            "status": "POSTED",
        },
        {
            "transaction_id": "TX-ANOM-9011",
            "transaction_date": date(2026, 8, 6),
            "cost_center_code": "CC-100",
            "vendor_name": "Datadog",
            "amount": Decimal("3750.00"),
            "currency": "USD",
            "po_number": "PO-2026-66200",
            "expense_category": "OPERATING_EXPENSE",
            "description": "Re-submitted August APM invoice #DD-8821 (duplicate clearing)",
            "submitted_by": "karan.malhotra@enterprise.internal",
            "is_weekend_submission": False,
            "status": "POSTED",
        },
        {
            "transaction_id": "TX-ANOM-9012",
            "transaction_date": date(2026, 9, 17),
            "cost_center_code": "CC-400",
            "vendor_name": "Blue Dart Express",
            "amount": Decimal("2980.00"),
            "currency": "USD",
            "po_number": "PO-2026-69110",
            "expense_category": "OPERATING_EXPENSE",
            "description": "Regional distribution batch #BD-409",
            "submitted_by": "priya.menon@enterprise.internal",
            "is_weekend_submission": False,
            "status": "POSTED",
        },
        {
            "transaction_id": "TX-ANOM-9013",
            "transaction_date": date(2026, 9, 18),
            "cost_center_code": "CC-400",
            "vendor_name": "Blue Dart Express",
            "amount": Decimal("2980.00"),
            "currency": "USD",
            "po_number": "PO-2026-69110",
            "expense_category": "OPERATING_EXPENSE",
            "description": "Regional distribution batch #BD-409 duplicate entry",
            "submitted_by": "priya.menon@enterprise.internal",
            "is_weekend_submission": False,
            "status": "POSTED",
        },

        # --- TYPE 5: Weekend Non-Business / Unapproved Hospitality Spend ---
        {
            "transaction_id": "TX-ANOM-9014",
            "transaction_date": date(2026, 8, 16),  # Sunday
            "cost_center_code": "CC-200",
            "vendor_name": "Taj Lands End Luxury Banquets",
            "amount": Decimal("5800.00"),
            "currency": "USD",
            "po_number": None,
            "expense_category": "TRAVEL_AND_ENTERTAINMENT",
            "description": "Sunday executive hospitality suite & dining (no PO or pre-approval)",
            "submitted_by": "rohan.joshi@enterprise.internal",
            "is_weekend_submission": True,
            "status": "FLAGGED_FOR_REVIEW",
        },
        {
            "transaction_id": "TX-ANOM-9015",
            "transaction_date": date(2026, 9, 20),  # Sunday
            "cost_center_code": "CC-500",
            "vendor_name": "luxury-charters-goa.example",
            "amount": Decimal("7400.00"),
            "currency": "USD",
            "po_number": None,
            "expense_category": "TRAVEL_AND_ENTERTAINMENT",
            "description": "Weekend offsite yacht venue booking submitted without VP sign-off",
            "submitted_by": "karan.malhotra@enterprise.internal",
            "is_weekend_submission": True,
            "status": "FLAGGED_FOR_REVIEW",
        },
    ]


def seed_database() -> None:
    """Connect to PostgreSQL, clear existing data, and insert cost centers + 200 ledger rows."""
    normal_rows = generate_normal_transactions(185)
    anomaly_rows = generate_planted_anomalies()
    all_transactions = normal_rows + anomaly_rows

    print(f"Connecting to PostgreSQL at: {DATABASE_URL.split('@')[-1]}")
    with psycopg.connect(DATABASE_URL, autocommit=False, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            # Ensure tables exist (safe idempotent DDL check)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS cost_centers (
                    cost_center_code VARCHAR(20) PRIMARY KEY,
                    department_name VARCHAR(100) NOT NULL,
                    quarterly_budget NUMERIC(12, 2) NOT NULL,
                    cost_center_owner VARCHAR(100) NOT NULL
                );

                CREATE TABLE IF NOT EXISTS general_ledger (
                    transaction_id VARCHAR(30) PRIMARY KEY,
                    transaction_date DATE NOT NULL,
                    cost_center_code VARCHAR(20) REFERENCES cost_centers(cost_center_code),
                    vendor_name VARCHAR(150) NOT NULL,
                    amount NUMERIC(12, 2) NOT NULL,
                    currency VARCHAR(10) DEFAULT 'USD',
                    po_number VARCHAR(50),
                    expense_category VARCHAR(50) NOT NULL,
                    description TEXT,
                    submitted_by VARCHAR(100) NOT NULL,
                    is_weekend_submission BOOLEAN DEFAULT FALSE,
                    status VARCHAR(30) DEFAULT 'POSTED',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Truncate for clean idempotent re-seeding
            cur.execute("TRUNCATE TABLE general_ledger, cost_centers RESTART IDENTITY CASCADE;")

            # Insert Cost Centers
            cur.executemany(
                """
                INSERT INTO cost_centers (
                    cost_center_code, department_name, quarterly_budget, cost_center_owner
                ) VALUES (%s, %s, %s, %s);
                """,
                COST_CENTERS,
            )

            # Insert General Ledger Transactions
            cur.executemany(
                """
                INSERT INTO general_ledger (
                    transaction_id, transaction_date, cost_center_code, vendor_name,
                    amount, currency, po_number, expense_category, description,
                    submitted_by, is_weekend_submission, status
                ) VALUES (
                    %(transaction_id)s, %(transaction_date)s, %(cost_center_code)s, %(vendor_name)s,
                    %(amount)s, %(currency)s, %(po_number)s, %(expense_category)s, %(description)s,
                    %(submitted_by)s, %(is_weekend_submission)s, %(status)s
                );
                """,
                all_transactions,
            )

        conn.commit()

    print(f"Successfully seeded {len(COST_CENTERS)} cost centers and {len(all_transactions)} ledger rows")
    print(f"  -> {len(normal_rows)} compliant baseline transactions")
    print(f"  -> {len(anomaly_rows)} planted audit anomalies (IDs: TX-ANOM-9001 .. TX-ANOM-9015)")


if __name__ == "__main__":
    seed_database()