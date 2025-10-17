# Sample Data Backup Files

This directory contains SQL backup files for quickly populating your databases with sample data.

## 📦 Files

### PostgreSQL Sample Data

**`postgres_sample_data.sql`** - Complete PostgreSQL database backup
- 500+ sample transactions
- 5 account profiles
- Transaction statuses (pending, approved, completed, declined)
- Date range: Last 6 months
- Various categories and merchants

**Restore Instructions:**
```bash
# Method 1: Using psql
psql -h your-host -U your-user -d your-database -f postgres_sample_data.sql

# Method 2: Using pgAdmin
# - Right-click on database → Restore
# - Select postgres_sample_data.sql
# - Click Restore

# Method 3: Using connection string
psql "postgresql://user:password@host:5432/database?sslmode=require" -f postgres_sample_data.sql
```

### Snowflake Sample Data

**`snowflake_sample_data.sql`** - Snowflake tables and data
- TRANSACTIONS table with 1000+ records
- ACCOUNTS table
- Monthly aggregations
- Category breakdowns

**Load Instructions:**
```sql
-- In Snowflake UI worksheet
USE DATABASE YOUR_DATABASE;
USE SCHEMA PUBLIC;

-- Upload and run the SQL file
-- Or paste the contents directly
```

## 🔧 Generating Backup Files

If you need to create your own backup files from existing data:

### PostgreSQL Backup
```bash
# Dump entire database
pg_dump -h your-host -U your-user -d your-database \
  --file=postgres_sample_data.sql \
  --format=plain \
  --no-owner \
  --no-privileges

# Dump specific tables only
pg_dump -h your-host -U your-user -d your-database \
  --file=postgres_tables_only.sql \
  --table=accounts \
  --table=transactions \
  --table=completions \
  --format=plain \
  --no-owner
```

### Snowflake Export
```sql
-- Export to stage
COPY INTO @~/sample_data/transactions
FROM transactions
FILE_FORMAT = (TYPE = 'CSV' HEADER = TRUE);

-- Download from stage
GET @~/sample_data/transactions file://./sample_data/;

-- Or use SnowSQL
snowsql -q "SELECT * FROM transactions" -o output_file=snowflake_sample_data.csv
```

## 📋 Data Schema

### Accounts Table
```sql
CREATE TABLE accounts (
    account_id SERIAL PRIMARY KEY,
    account_name VARCHAR(100) NOT NULL UNIQUE,
    current_balance NUMERIC(14, 2) NOT NULL DEFAULT 0
);
```

### Transactions Table
```sql
CREATE TABLE transactions (
    transaction_id SERIAL PRIMARY KEY,
    date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    amount NUMERIC(12, 2) NOT NULL,
    merchant VARCHAR(200),
    category VARCHAR(100),
    notes TEXT,
    status transaction_status NOT NULL DEFAULT 'pending',
    account_id INTEGER REFERENCES accounts(account_id),
    embedding vector(1536)  -- For semantic search
);

-- Transaction status enum
CREATE TYPE transaction_status AS ENUM (
    'pending',
    'approved', 
    'completed',
    'declined',
    'cancelled'
);
```

### Required Extensions
```sql
CREATE EXTENSION IF NOT EXISTS vector;    -- pgvector for semantic search
CREATE EXTENSION IF NOT EXISTS pg_trgm;   -- Trigram for fuzzy search
```

## 🎯 Sample Data Contents

### Accounts (5 profiles)
- Personal Checking
- Savings Account
- Credit Card
- Investment Account
- Emergency Fund

### Transaction Categories
- 🍔 Food & Dining (25%)
- 🛒 Shopping (20%)
- 🚗 Transportation (15%)
- 🏠 Bills & Utilities (15%)
- 🎬 Entertainment (10%)
- 💰 Other (15%)

### Transaction Distribution
- **Status**: 60% approved, 20% pending, 15% completed, 5% declined
- **Amount Range**: $5 - $2,000
- **Frequency**: 50-100 transactions per month
- **Merchants**: 100+ unique merchants

## 🔍 Verification Queries

After loading data, verify with these queries:

```sql
-- Check record counts
SELECT 
    (SELECT COUNT(*) FROM accounts) as account_count,
    (SELECT COUNT(*) FROM transactions) as transaction_count;

-- Check transaction distribution
SELECT 
    status,
    COUNT(*) as count,
    SUM(amount) as total_amount
FROM transactions
GROUP BY status
ORDER BY count DESC;

-- Check date range
SELECT 
    MIN(date) as earliest_transaction,
    MAX(date) as latest_transaction
FROM transactions;

-- Check categories
SELECT 
    category,
    COUNT(*) as count,
    AVG(amount) as avg_amount
FROM transactions
GROUP BY category
ORDER BY count DESC;
```

## 📝 Notes

- All sample data is fictional and for demonstration purposes only
- Amounts are in USD
- Dates are relative to the time of backup creation
- No real personal or financial data is included
- Safe for public repositories and demonstrations

## 🆘 Troubleshooting

**Issue: "Extension not found"**
```sql
-- Install extensions as superuser
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

**Issue: "Permission denied"**
```bash
# Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE your_database TO your_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_user;
```

**Issue: "Enum type already exists"**
```sql
-- Drop and recreate if needed
DROP TYPE IF EXISTS transaction_status CASCADE;
CREATE TYPE transaction_status AS ENUM (...);
```

