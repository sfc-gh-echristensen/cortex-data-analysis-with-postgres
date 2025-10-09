# Transaction Management System

This document explains the enhanced transaction management functionality for connecting to PostgreSQL and handling transaction cancellations.

## Overview

The system provides:
- ✅ **Robust PostgreSQL connection management**
- ✅ **Transaction cancellation with proper rollback/commit**
- ✅ **Status tracking** (pending, approved, declined, cancelled)
- ✅ **Audit trail** with cancellation reasons
- ✅ **AI-powered transaction analysis**
- ✅ **Manual transaction management**

## Setup Instructions

### 1. Quick Setup (Recommended)

Run the automated setup script:

```bash
python setup_transaction_management.py
```

This will:
- Test your database connection
- Add the status column if needed
- Create sample test data (optional)
- Verify everything works

### 2. Manual Setup

If you prefer manual setup:

```bash
# 1. Add status column to transactions table
python migrate_add_status.py

# 2. Test the connection
python -c "from db_utils import test_connection; print(test_connection())"
```

## Database Schema Changes

The system adds a `status` column to the `transactions` table:

```sql
ALTER TABLE transactions 
ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'pending';
```

**Status Values:**
- `pending` - New transactions awaiting approval
- `approved` - Approved transactions 
- `declined` - Declined transactions
- `cancelled` - Cancelled transactions

## Usage

### 1. In Streamlit App

The transaction manager is integrated into the main Streamlit app (`streamlit_app.py`):

1. **Navigate to "Pending Transaction Manager"** section
2. **View database status** in the expandable status panel
3. **See pending transactions** in the main table
4. **Use AI analysis** to identify problematic transactions
5. **Cancel transactions** manually or through AI recommendations

### 2. Programmatic Usage

```python
from db_utils import TransactionManager

# Get pending transactions
pending = TransactionManager.get_pending_transactions()

# Cancel a transaction
success, message = TransactionManager.cancel_transaction(
    transaction_id=123, 
    reason="Suspicious activity detected"
)

# Approve a transaction
success, message = TransactionManager.approve_transaction(
    transaction_id=456,
    reason="Verified with customer"
)

# Get transaction statistics
stats = TransactionManager.get_transaction_stats()
```

## Features

### 🤖 AI-Powered Analysis

The system automatically flags transactions based on:
- **High amounts** (>$500)
- **Unusual merchants** (keywords like 'gadget', 'electronics', 'airlines')
- Custom rules can be easily added

### 🔒 Transaction Safety

- **ACID compliance** - All database operations use proper transactions
- **Rollback on failure** - Failed operations don't leave partial updates
- **Connection pooling** - Efficient database connection management
- **Error handling** - Comprehensive error messages and logging

### 📊 Status Tracking

View transaction statistics by status:
```python
{
    'pending': {'count': 5, 'total_amount': 2500.00, 'avg_amount': 500.00},
    'approved': {'count': 150, 'total_amount': 45000.00, 'avg_amount': 300.00},
    'declined': {'count': 8, 'total_amount': 1200.00, 'avg_amount': 150.00}
}
```

### 🔍 Audit Trail

All cancellations are tracked with:
- **Timestamp** - When the action occurred
- **Reason** - Why the transaction was cancelled
- **Status change** - From pending → declined
- **Notes** - Additional context preserved

## Configuration

### Environment Variables

```bash
# PostgreSQL connection
export PG_HOST="your-postgres-host"
export PG_PORT="5432"
export PG_DB="your-database"
export PG_USER="your-username" 
export PG_PASSWORD="your-password"
export PG_SSLMODE="require"  # optional
```

### Streamlit Secrets

Add to `.streamlit/secrets.toml`:

```toml
[postgres]
host = "your-postgres-host"
port = 5432
database = "your-database"
user = "your-username"
password = "your-password"
sslmode = "require"  # optional
```

## API Reference

### TransactionManager Class

#### `get_pending_transactions() -> List[Dict]`
Returns all transactions with status='pending'

#### `get_transaction_by_id(transaction_id: int) -> Optional[Dict]`
Get specific transaction details including account info

#### `cancel_transaction(transaction_id: int, reason: str) -> Tuple[bool, str]`
Cancel a pending transaction, returns (success, message)

#### `approve_transaction(transaction_id: int, reason: str) -> Tuple[bool, str]`
Approve a pending transaction, returns (success, message)

#### `get_transaction_stats() -> Dict[str, Dict]`
Get statistics grouped by transaction status

### Utility Functions

#### `test_connection() -> Tuple[bool, str]`
Test PostgreSQL connection, returns (success, message)

#### `ensure_status_column_exists() -> Tuple[bool, str]`
Check if status column exists, returns (exists, message)

## Troubleshooting

### Common Issues

1. **"Status column does not exist"**
   - Run: `python migrate_add_status.py`

2. **"Connection failed"**
   - Check PostgreSQL server is running
   - Verify credentials in secrets.toml or environment variables
   - Check network connectivity

3. **"Permission denied"**
   - Ensure database user has UPDATE privileges on transactions table
   - Check database user has CREATE privileges if running migration

4. **"Transaction not found"**
   - Verify transaction_id exists and has status='pending'
   - Check if transaction was already processed

### Debug Mode

Enable SQL logging by setting `echo=True` in engine creation:

```python
engine = create_engine(url, echo=True)  # Shows all SQL queries
```

## Security Considerations

- ✅ **SQL Injection Protection** - All queries use parameterized statements
- ✅ **Connection Security** - Supports SSL/TLS connections
- ✅ **Audit Logging** - All changes are logged with reasons
- ✅ **Transaction Isolation** - Proper ACID transaction boundaries

## Performance

- **Connection Pooling** - Reuses database connections efficiently
- **Context Managers** - Automatic connection cleanup
- **Optimized Queries** - Uses indexes on transaction_id and status
- **Batch Operations** - Support for bulk operations (future enhancement)

## Future Enhancements

Planned features:
- [ ] Bulk transaction operations
- [ ] Transaction approval workflows
- [ ] Email notifications for cancelled transactions
- [ ] Advanced fraud detection rules
- [ ] Transaction scheduling and recurring payments
- [ ] Integration with external payment processors
