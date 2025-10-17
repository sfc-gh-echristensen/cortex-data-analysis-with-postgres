-- ============================================================================
-- Snowflake Sample Data Backup
-- Budget Tracker 9000 - Financial Analytics Demo
-- ============================================================================
--
-- This file contains sample data for Snowflake tables.
-- Run this script in your Snowflake worksheet to populate demo data.
--
-- Usage:
--   1. Open Snowflake UI
--   2. Navigate to Worksheets
--   3. Select your database and schema
--   4. Paste and run this script
--
-- ============================================================================

-- Set context
USE DATABASE YOUR_DATABASE;
USE SCHEMA PUBLIC;
USE WAREHOUSE YOUR_WAREHOUSE;

-- ============================================================================
-- CREATE TABLES
-- ============================================================================

-- Create ACCOUNTS table
CREATE TABLE IF NOT EXISTS ACCOUNTS (
    ACCOUNT_ID INTEGER AUTOINCREMENT PRIMARY KEY,
    ACCOUNT_NAME VARCHAR(100) NOT NULL UNIQUE,
    CURRENT_BALANCE NUMBER(14, 2) NOT NULL DEFAULT 0,
    CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Create TRANSACTIONS table
CREATE TABLE IF NOT EXISTS TRANSACTIONS (
    TRANSACTION_ID INTEGER AUTOINCREMENT PRIMARY KEY,
    DATE TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    AMOUNT NUMBER(12, 2) NOT NULL,
    MERCHANT VARCHAR(200),
    CATEGORY VARCHAR(100),
    NOTES VARCHAR(500),
    STATUS VARCHAR(20) NOT NULL DEFAULT 'APPROVED',
    ACCOUNT_ID INTEGER,
    CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    FOREIGN KEY (ACCOUNT_ID) REFERENCES ACCOUNTS(ACCOUNT_ID)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS IDX_TRANSACTIONS_DATE ON TRANSACTIONS(DATE);
CREATE INDEX IF NOT EXISTS IDX_TRANSACTIONS_STATUS ON TRANSACTIONS(STATUS);
CREATE INDEX IF NOT EXISTS IDX_TRANSACTIONS_CATEGORY ON TRANSACTIONS(CATEGORY);
CREATE INDEX IF NOT EXISTS IDX_TRANSACTIONS_ACCOUNT ON TRANSACTIONS(ACCOUNT_ID);

-- ============================================================================
-- CLEAR EXISTING DATA (Optional)
-- ============================================================================
-- Uncomment if you want to start fresh
-- TRUNCATE TABLE TRANSACTIONS;
-- TRUNCATE TABLE ACCOUNTS;

-- ============================================================================
-- INSERT SAMPLE ACCOUNTS
-- ============================================================================

INSERT INTO ACCOUNTS (ACCOUNT_NAME, CURRENT_BALANCE) 
SELECT * FROM (
    VALUES 
        ('Personal Checking', 5420.50),
        ('Savings Account', 15000.00),
        ('Credit Card', 2341.23),
        ('Investment Account', 25000.00),
        ('Emergency Fund', 10000.00)
) AS accounts(ACCOUNT_NAME, CURRENT_BALANCE);

-- ============================================================================
-- INSERT SAMPLE TRANSACTIONS
-- ============================================================================

-- Sample transactions for the last 6 months
-- Note: Replace with actual data dump for production use

INSERT INTO TRANSACTIONS (DATE, AMOUNT, MERCHANT, CATEGORY, STATUS, ACCOUNT_ID)
SELECT * FROM (
    VALUES
        -- October 2024
        (DATEADD(day, -1, CURRENT_TIMESTAMP()), 4.50, 'Starbucks', 'Food & Dining', 'APPROVED', 1),
        (DATEADD(day, -1, CURRENT_TIMESTAMP()), 15.75, 'Chipotle', 'Food & Dining', 'APPROVED', 1),
        (DATEADD(day, -2, CURRENT_TIMESTAMP()), 45.00, 'Shell Gas Station', 'Transportation', 'APPROVED', 1),
        (DATEADD(day, -3, CURRENT_TIMESTAMP()), 125.00, 'Amazon', 'Shopping', 'APPROVED', 1),
        (DATEADD(day, -4, CURRENT_TIMESTAMP()), 250.00, 'Electric Company', 'Bills & Utilities', 'APPROVED', 1),
        (DATEADD(day, -5, CURRENT_TIMESTAMP()), 12.99, 'Netflix', 'Entertainment', 'APPROVED', 2),
        (DATEADD(day, -6, CURRENT_TIMESTAMP()), 75.00, 'Whole Foods', 'Food & Dining', 'APPROVED', 1),
        (DATEADD(day, -7, CURRENT_TIMESTAMP()), 30.00, 'Uber', 'Transportation', 'APPROVED', 1),
        
        -- September 2024
        (DATEADD(day, -30, CURRENT_TIMESTAMP()), 85.00, 'Target', 'Shopping', 'APPROVED', 1),
        (DATEADD(day, -31, CURRENT_TIMESTAMP()), 150.00, 'Gas Company', 'Bills & Utilities', 'APPROVED', 1),
        (DATEADD(day, -32, CURRENT_TIMESTAMP()), 45.00, 'Regal Cinemas', 'Entertainment', 'APPROVED', 1),
        (DATEADD(day, -33, CURRENT_TIMESTAMP()), 25.00, 'Starbucks', 'Food & Dining', 'APPROVED', 1),
        (DATEADD(day, -34, CURRENT_TIMESTAMP()), 120.00, 'Best Buy', 'Shopping', 'APPROVED', 1),
        
        -- August 2024
        (DATEADD(day, -60, CURRENT_TIMESTAMP()), 200.00, 'Costco', 'Shopping', 'APPROVED', 1),
        (DATEADD(day, -61, CURRENT_TIMESTAMP()), 50.00, 'Shell Gas Station', 'Transportation', 'APPROVED', 1),
        (DATEADD(day, -62, CURRENT_TIMESTAMP()), 15.99, 'Spotify', 'Entertainment', 'APPROVED', 2),
        (DATEADD(day, -63, CURRENT_TIMESTAMP()), 75.00, 'Local Restaurant', 'Food & Dining', 'APPROVED', 1),
        
        -- Pending transactions
        (DATEADD(hour, -1, CURRENT_TIMESTAMP()), 500.00, 'Gadget Electronics', 'Shopping', 'PENDING', 1),
        (DATEADD(hour, -2, CURRENT_TIMESTAMP()), 150.00, 'Fancy Restaurant', 'Food & Dining', 'PENDING', 1),
        (DATEADD(hour, -3, CURRENT_TIMESTAMP()), 75.00, 'Online Store', 'Shopping', 'PENDING', 3)
) AS txn(DATE, AMOUNT, MERCHANT, CATEGORY, STATUS, ACCOUNT_ID);

-- ============================================================================
-- CREATE ANALYTICAL VIEWS
-- ============================================================================

-- Monthly spending summary view
CREATE OR REPLACE VIEW MONTHLY_SPENDING AS
SELECT 
    DATE_TRUNC('MONTH', DATE) AS MONTH,
    CATEGORY,
    COUNT(*) AS TRANSACTION_COUNT,
    SUM(AMOUNT) AS TOTAL_AMOUNT,
    AVG(AMOUNT) AS AVG_AMOUNT
FROM TRANSACTIONS
WHERE STATUS = 'APPROVED'
GROUP BY DATE_TRUNC('MONTH', DATE), CATEGORY
ORDER BY MONTH DESC, TOTAL_AMOUNT DESC;

-- Category spending view
CREATE OR REPLACE VIEW CATEGORY_SPENDING AS
SELECT 
    CATEGORY,
    COUNT(*) AS TRANSACTION_COUNT,
    SUM(AMOUNT) AS TOTAL_AMOUNT,
    AVG(AMOUNT) AS AVG_AMOUNT,
    MIN(AMOUNT) AS MIN_AMOUNT,
    MAX(AMOUNT) AS MAX_AMOUNT
FROM TRANSACTIONS
WHERE STATUS = 'APPROVED'
GROUP BY CATEGORY
ORDER BY TOTAL_AMOUNT DESC;

-- Account summary view
CREATE OR REPLACE VIEW ACCOUNT_SUMMARY AS
SELECT 
    a.ACCOUNT_ID,
    a.ACCOUNT_NAME,
    a.CURRENT_BALANCE,
    COUNT(t.TRANSACTION_ID) AS TRANSACTION_COUNT,
    COALESCE(SUM(t.AMOUNT), 0) AS TOTAL_SPENT
FROM ACCOUNTS a
LEFT JOIN TRANSACTIONS t ON a.ACCOUNT_ID = t.ACCOUNT_ID
GROUP BY a.ACCOUNT_ID, a.ACCOUNT_NAME, a.CURRENT_BALANCE
ORDER BY a.ACCOUNT_ID;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check record counts
SELECT 'Accounts' AS TABLE_NAME, COUNT(*) AS RECORD_COUNT FROM ACCOUNTS
UNION ALL
SELECT 'Transactions' AS TABLE_NAME, COUNT(*) AS RECORD_COUNT FROM TRANSACTIONS;

-- Transaction summary by status
SELECT 
    STATUS,
    COUNT(*) AS COUNT,
    SUM(AMOUNT) AS TOTAL_AMOUNT,
    AVG(AMOUNT) AS AVG_AMOUNT
FROM TRANSACTIONS
GROUP BY STATUS
ORDER BY COUNT DESC;

-- Monthly spending trends
SELECT 
    DATE_TRUNC('MONTH', DATE) AS MONTH,
    COUNT(*) AS TRANSACTION_COUNT,
    SUM(AMOUNT) AS TOTAL_SPENT
FROM TRANSACTIONS
WHERE STATUS = 'APPROVED'
GROUP BY DATE_TRUNC('MONTH', DATE)
ORDER BY MONTH DESC;

-- Top merchants
SELECT 
    MERCHANT,
    COUNT(*) AS VISIT_COUNT,
    SUM(AMOUNT) AS TOTAL_SPENT
FROM TRANSACTIONS
WHERE STATUS = 'APPROVED'
GROUP BY MERCHANT
ORDER BY TOTAL_SPENT DESC
LIMIT 10;

-- ============================================================================
-- CORTEX ANALYST SETUP (Optional)
-- ============================================================================

-- To use with Cortex Analyst, you may want to add semantic model
-- See Snowflake documentation for Cortex Analyst setup:
-- https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst

-- Example semantic model snippet:
/*
{
  "tables": [
    {
      "name": "TRANSACTIONS",
      "description": "Financial transaction records",
      "columns": [
        {"name": "AMOUNT", "description": "Transaction amount in USD"},
        {"name": "CATEGORY", "description": "Spending category"},
        {"name": "MERCHANT", "description": "Merchant name"},
        {"name": "DATE", "description": "Transaction date and time"}
      ]
    }
  ]
}
*/

-- ============================================================================
-- NOTES
-- ============================================================================
--
-- 1. This is a template file with minimal sample data.
--    For production use, replace with actual data dump.
--
-- 2. To export your populated data:
--    SELECT * FROM TRANSACTIONS;
--    Then save results or use COPY INTO command
--
-- 3. For bulk loading from files:
--    COPY INTO TRANSACTIONS FROM @your_stage/transactions.csv
--    FILE_FORMAT = (TYPE = 'CSV' SKIP_HEADER = 1);
--
-- 4. To create a full backup:
--    Use Snowflake's data sharing or COPY INTO @stage commands
--
-- 5. Python loader alternative:
--    python3 snowflake_loader_final.py
--
-- ============================================================================

-- Show completion message
SELECT 'Snowflake sample data loaded successfully!' AS STATUS;

