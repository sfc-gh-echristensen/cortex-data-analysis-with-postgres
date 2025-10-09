# Sample Data Loading Guide

This guide explains how to load sample transaction data into your PostgreSQL and Snowflake databases.

## 📁 Files Created

### CSV Data Files
- **`sample_transactions_postgresql.csv`** - 60 transactions for PostgreSQL (matches your transaction table schema)
- **`sample_transactions_snowflake.csv`** - 100 transactions for Snowflake (matches Snowflake TRANSACTIONS table)

### Loading Scripts
- **`bulk_insert_sample_data.py`** - PostgreSQL data loader
- **`bulk_insert_snowflake_data.py`** - Snowflake data loader  
- **`load_sample_data.py`** - Combined menu-driven loader for both databases

## 🚀 Quick Start

### Option 1: Interactive Menu (Recommended)
```bash
python3 load_sample_data.py
```
This gives you a menu to choose:
1. Load into PostgreSQL only
2. Load into Snowflake only  
3. Load into both databases
4. Exit

### Option 2: Individual Database Loading

**PostgreSQL only:**
```bash
python3 bulk_insert_sample_data.py
```

**Snowflake only:**
```bash
python3 bulk_insert_snowflake_data.py
```

## 📊 What Gets Loaded

### PostgreSQL Data (60 transactions)
- **Date Range**: December 1-20, 2024
- **Categories**: Groceries, Dining, Electronics, Travel, etc.
- **Merchants**: Realistic merchant names (Starbucks, Amazon, etc.)
- **Amounts**: $4.50 - $1,250.00
- **Status**: All set to 'pending' (perfect for testing cancellations)
- **Account ID**: All assigned to account_id = 1

### Snowflake Data (100 transactions)  
- **Date Range**: December 1-31, 2024
- **Transaction IDs**: tx-2001 to tx-2100
- **Account Names**: "Checking" and "Credit Card"
- **Same realistic categories and merchants**
- **Amounts**: $5.25 - $789.00

## 🎯 Perfect for Testing

This sample data is ideal for testing:

### PostgreSQL Features
- ✅ **AI Transaction Analysis** - Many transactions > $200
- ✅ **Unusual Merchant Detection** - Airlines, electronics stores, etc.
- ✅ **Transaction Cancellation** - All are 'pending' status
- ✅ **Category Analysis** - Good mix of spending categories
- ✅ **Date Range Queries** - Recent December 2024 data

### Snowflake Cortex Features
- ✅ **Monthly Spending Analysis** - Full December data
- ✅ **Category Breakdowns** - Travel, Electronics, Dining, etc.
- ✅ **Account Comparisons** - Checking vs Credit Card
- ✅ **Merchant Analytics** - Top spending merchants
- ✅ **SQL Generation** - Rich dataset for Cortex queries

## 🔧 Requirements

- **PostgreSQL**: Uses your existing `secrets.toml` connection settings
- **Snowflake**: Uses your existing Streamlit Snowflake connection
- **Python packages**: pandas, sqlalchemy (already in your project)

## ✅ Success Indicators

After loading, you should see:

**PostgreSQL:**
```
✅ Database now contains 69+ total transactions
📈 Added 60 new transactions
```

**Snowflake:**
```  
✅ Successfully uploaded 100 rows
📈 Snowflake now contains 100+ total transactions
```

## 🎉 Next Steps

After loading the data:

1. **Restart your Streamlit app** to see the new transactions
2. **Test AI Analysis** - Should find many high-value and unusual merchant transactions
3. **Try Snowflake Cortex** - Ask questions about spending patterns
4. **Practice Cancellations** - All PostgreSQL transactions are 'pending'

## 🔍 Verification

Check that data loaded correctly:

**PostgreSQL:**
```sql
SELECT COUNT(*) FROM transactions WHERE status = 'pending';
-- Should show 60+ pending transactions
```

**Snowflake:**
```sql
SELECT COUNT(*) FROM TRANSACTIONS;
-- Should show 100+ transactions
```

## 🆘 Troubleshooting

**Connection Issues:**
- Verify your `secrets.toml` file has correct database credentials
- Make sure PostgreSQL and Snowflake connections work in Streamlit

**Data Already Exists:**
- Scripts will append new data (won't overwrite)
- Transaction IDs are auto-generated (PostgreSQL) or unique (Snowflake)

**Permission Issues:**
- Ensure your database user has INSERT permissions
- Check that tables exist before running scripts

---
**Happy data loading! 🚀**
