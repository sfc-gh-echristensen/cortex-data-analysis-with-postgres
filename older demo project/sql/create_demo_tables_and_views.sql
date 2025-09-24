-- SQL helper: create demo tables and convenience views for the Cortex demo
-- Replace database/schema names or run after doing: USE DATABASE <DB>; USE SCHEMA <SCHEMA>;

-- 1) Create transactions table (if needed)
CREATE TABLE IF NOT EXISTS transactions (
  transaction_id VARCHAR(64) PRIMARY KEY,
  "DATE" DATE,
  account_name VARCHAR(128),
  amount NUMBER(18,2),
  category VARCHAR(128),
  merchant VARCHAR(256)
);

-- 2) Create accounts table (if needed)
CREATE TABLE IF NOT EXISTS accounts (
  account_id VARCHAR(64) PRIMARY KEY,
  account_name VARCHAR(128),
  current_balance NUMBER(18,2)
);

-- 3) Insert a few sample rows if table is empty
INSERT INTO transactions (transaction_id, "DATE", account_name, amount, category, merchant)
SELECT * FROM VALUES
  ('tx-1001', TO_DATE('2025-09-10'), 'Checking', 42.75, 'Groceries', 'Whole Foods'),
  ('tx-1002', TO_DATE('2025-09-09'), 'Checking', 18.50, 'Dining', 'Pizzeria'),
  ('tx-1003', TO_DATE('2025-08-30'), 'Credit Card', 120.00, 'Travel', 'Airline Co')
WHERE NOT EXISTS (SELECT 1 FROM transactions LIMIT 1);

INSERT INTO accounts (account_id, account_name, current_balance)
SELECT * FROM VALUES
  ('acct-1', 'Checking', 2345.12),
  ('acct-2', 'Credit Card', -523.45)
WHERE NOT EXISTS (SELECT 1 FROM accounts LIMIT 1);

-- 4) Create a convenient view that maps the "DATE" column to a friendly name
--    This lets existing code refer to transaction_date without quoting the DATE identifier.
CREATE OR REPLACE VIEW transactions_view AS
SELECT
  transaction_id,
  "DATE" AS transaction_date,
  account_name,
  amount,
  category,
  merchant
FROM transactions;

-- 5) Optional summary views for quick context injection
CREATE OR REPLACE VIEW category_totals_90d AS
SELECT
  category,
  SUM(amount) AS total_amount,
  COUNT(*) AS txn_count
FROM transactions
WHERE "DATE" >= DATEADD(day, -90, CURRENT_DATE())
GROUP BY category
ORDER BY total_amount DESC;

CREATE OR REPLACE VIEW top_merchants_90d AS
SELECT
  merchant,
  SUM(amount) AS total_amount
FROM transactions
WHERE "DATE" >= DATEADD(day, -90, CURRENT_DATE())
GROUP BY merchant
ORDER BY total_amount DESC
LIMIT 20;

-- End of script
