# Corporate Financial Audit & Expense Compliance Policy (FY 2026)

## 1. Materiality Thresholds
- **Standard Variance Tolerance:** Line-item invoices may vary from the approved Purchase Order (PO) by up to **2.0%** or **$250.00** (whichever is lower) without escalating.
- **Hard Materiality Gate (HITL Trigger):** Any single transaction or cumulative vendor variance exceeding **$5,000.00** requires mandatory Human-in-the-Loop (HITL) Senior Auditor sign-off before reconciliation completion.

## 2. Structuring & Invoice Splitting Rules
- **Department Manager Approval Limit:** $5,000.00 per invoice.
- **Structuring Red Flag:** Multiple invoices from the **same vendor** submitted within a **5-calendar-day window** where individual amounts are between **$2,000.00 and $4,999.99** and the combined sum exceeds **$5,000.00** must be flagged as `HIGH_RISK_STRUCTURING`.

## 3. Three-Way Matching Requirements
- Every General Ledger (GL) disbursement above **$1,000.00** must link to a valid `po_number` and an itemized invoice record.
- Disbursements missing a `po_number` above $1,000.00 are automatically flagged as `MISSING_PO_CONTROL_FAILURE`.

## 4. Prohibited & Restricted Category Spend
- **IT & Cloud Infrastructure (`ACCT-1002`):** Must only contain software licenses, cloud hosting, or hardware peripherals. Meals, entertainment, or travel booked under this GL code are flagged as `MISCLASSIFIED_EXPENSE`.
- **Weekend & Holiday Disbursements:** Consulting or Meals & Entertainment expenses incurred on Saturday or Sunday exceeding **$500.00** require explicit justification.
