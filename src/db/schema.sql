-- General Ledger Accounts Table
CREATE TABLE IF NOT EXISTS gl_accounts (
    account_id VARCHAR(20) PRIMARY KEY,
    account_name VARCHAR(100) NOT NULL,
    department VARCHAR(100) NOT NULL,
    quarterly_budget NUMERIC(12, 2) NOT NULL
);

-- General Ledger Transactions Table
CREATE TABLE IF NOT EXISTS ledger_transactions (
    txn_id VARCHAR(30) PRIMARY KEY,
    account_id VARCHAR(20) NOT NULL REFERENCES gl_accounts(account_id),
    vendor_name VARCHAR(150) NOT NULL,
    po_number VARCHAR(30),
    po_authorized_amount NUMERIC(12, 2),
    actual_amount NUMERIC(12, 2) NOT NULL,
    transaction_date DATE NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR(30) DEFAULT 'POSTED'
);

-- Audit Review Logs Table
CREATE TABLE IF NOT EXISTS audit_decision_logs (
    log_id SERIAL PRIMARY KEY,
    thread_id VARCHAR(100) NOT NULL,
    reviewer_id VARCHAR(100) NOT NULL,
    decision VARCHAR(20) NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for fast agent lookup
CREATE INDEX IF NOT EXISTS idx_txn_vendor ON ledger_transactions(vendor_name);
CREATE INDEX IF NOT EXISTS idx_txn_date ON ledger_transactions(transaction_date);
CREATE INDEX IF NOT EXISTS idx_txn_account ON ledger_transactions(account_id);
