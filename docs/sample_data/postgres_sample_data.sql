-- ============================================================================
-- PostgreSQL Sample Data Backup
-- Budget Tracker 9000 - Financial Analytics Demo
-- ============================================================================
-- 
-- This file contains sample data for the PostgreSQL database.
-- Run this script to populate your database with demo transactions and accounts.
--
-- Usage:
--   psql -h your-host -U your-user -d your-database -f postgres_sample_data.sql
--
-- ============================================================================

-- Create extensions (if not already installed)
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create transaction status enum
DO $$ BEGIN
    CREATE TYPE transaction_status AS ENUM (
        'pending',
        'approved',
        'completed',
        'declined',
        'cancelled'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create accounts table
CREATE TABLE IF NOT EXISTS accounts (
    account_id SERIAL PRIMARY KEY,
    account_name VARCHAR(100) NOT NULL UNIQUE,
    current_balance NUMERIC(14, 2) NOT NULL DEFAULT 0
);

-- Create transactions table
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id SERIAL PRIMARY KEY,
    date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    amount NUMERIC(12, 2) NOT NULL,
    merchant VARCHAR(200),
    category VARCHAR(100),
    notes TEXT,
    status transaction_status NOT NULL DEFAULT 'pending',
    account_id INTEGER REFERENCES accounts(account_id),
    embedding vector(1536)
);

-- Create completions table (for AI query history)
CREATE TABLE IF NOT EXISTS completions (
    id SERIAL PRIMARY KEY,
    prompt TEXT NOT NULL,
    result JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status);
CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category);
CREATE INDEX IF NOT EXISTS idx_transactions_merchant_trgm ON transactions USING gin (merchant gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_transactions_notes_trgm ON transactions USING gin (notes gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_transactions_embedding ON transactions USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ============================================================================
-- SAMPLE DATA
-- ============================================================================

-- Clear existing data (optional - remove if you want to keep existing data)
-- TRUNCATE TABLE transactions, accounts, completions RESTART IDENTITY CASCADE;

-- Insert sample accounts
INSERT INTO accounts (account_name, current_balance) VALUES
    ('Personal Checking', 5420.50),
    ('Savings Account', 15000.00),
    ('Credit Card', -2341.23),
    ('Investment Account', 25000.00),
    ('Emergency Fund', 10000.00)
ON CONFLICT (account_name) DO NOTHING;

-- ============================================================================
-- Note: Add your actual sample transaction data here
-- ============================================================================
-- 
-- To generate this data, you can:
--
-- 1. Export from existing database:
--    pg_dump -h your-host -U your-user -d your-database --table=transactions --data-only
--
-- 2. Use the Python scripts:
--    python3 load_sample_data.py
--    python3 bulk_insert_expanded_data.py
--
-- 3. Create custom data using the pattern below:
--
-- INSERT INTO transactions (date, amount, merchant, category, status, account_id) VALUES
--     ('2024-10-01 09:15:00', 4.50, 'Starbucks', 'Food & Dining', 'approved', 1),
--     ('2024-10-01 12:30:00', 15.75, 'Chipotle', 'Food & Dining', 'approved', 1),
--     ('2024-10-02 08:00:00', 45.00, 'Shell Gas Station', 'Transportation', 'approved', 1);
--     -- Add more transactions...
--
-- ============================================================================

-- Example: Insert a few sample transactions
INSERT INTO transactions (date, amount, merchant, category, notes, status, account_id) VALUES
    (NOW() - INTERVAL '1 day', 4.50, 'Starbucks', 'Food & Dining', 'Morning coffee', 'approved', 1),
    (NOW() - INTERVAL '1 day', 15.75, 'Chipotle', 'Food & Dining', 'Lunch', 'approved', 1),
    (NOW() - INTERVAL '2 days', 45.00, 'Shell Gas Station', 'Transportation', 'Gas fill-up', 'approved', 1),
    (NOW() - INTERVAL '3 days', 125.00, 'Amazon', 'Shopping', 'Home supplies', 'approved', 1),
    (NOW() - INTERVAL '4 days', 250.00, 'Electric Company', 'Bills & Utilities', 'Monthly electric bill', 'approved', 1),
    (NOW() - INTERVAL '5 days', 12.99, 'Netflix', 'Entertainment', 'Monthly subscription', 'approved', 2),
    (NOW() - INTERVAL '1 hour', 500.00, 'Gadget Electronics Store', 'Shopping', 'New laptop', 'pending', 1),
    (NOW() - INTERVAL '2 hours', 75.00, 'Fancy Restaurant', 'Food & Dining', 'Dinner', 'pending', 1)
ON CONFLICT DO NOTHING;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check inserted data
SELECT 
    'Accounts' as table_name,
    COUNT(*) as record_count
FROM accounts
UNION ALL
SELECT 
    'Transactions' as table_name,
    COUNT(*) as record_count
FROM transactions;

-- Transaction summary by status
SELECT 
    status,
    COUNT(*) as count,
    SUM(amount) as total_amount,
    AVG(amount) as avg_amount
FROM transactions
GROUP BY status
ORDER BY count DESC;

-- ============================================================================
-- NOTES
-- ============================================================================
--
-- 1. This is a template file. Replace with actual backup data for production use.
-- 
-- 2. To create a full backup of your populated database:
--    pg_dump -h your-host -U your-user -d your-database -f postgres_backup.sql
--
-- 3. For the sample data used in demos, run the Python scripts:
--    - load_sample_data.py (basic sample data)
--    - bulk_insert_expanded_data.py (expanded dataset with 500+ records)
--
-- 4. For semantic search functionality, generate embeddings after loading:
--    python3 setup_embeddings.py
--
-- ============================================================================

