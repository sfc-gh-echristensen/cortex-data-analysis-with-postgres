#!/usr/bin/env python3
"""
Debug script to investigate transaction management issues.
This will help us understand why cancellations aren't persisting to the database.
"""

import logging
import sys
from datetime import datetime
from db_utils import get_db_connection, TransactionManager, test_connection
from sqlalchemy import text

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('transaction_debug.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def check_database_state():
    """Check the current state of transactions in the database"""
    logger.info("🔍 Checking current database state...")
    
    try:
        with get_db_connection() as conn:
            # Check if status column exists
            logger.info("Checking if status column exists...")
            result = conn.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default 
                FROM information_schema.columns 
                WHERE table_name = 'transactions' AND column_name = 'status'
            """))
            
            status_col = result.fetchone()
            if status_col:
                logger.info(f"✅ Status column exists: {dict(status_col._mapping)}")
            else:
                logger.error("❌ Status column does not exist!")
                return False
            
            # Get all transactions with their status
            logger.info("Fetching all transactions...")
            result = conn.execute(text("""
                SELECT 
                    transaction_id, 
                    date, 
                    amount, 
                    merchant, 
                    category, 
                    status,
                    notes
                FROM transactions 
                ORDER BY date DESC, transaction_id DESC
                LIMIT 20
            """))
            
            transactions = result.fetchall()
            logger.info(f"Found {len(transactions)} recent transactions:")
            
            status_counts = {}
            for txn in transactions:
                status = txn.status
                status_counts[status] = status_counts.get(status, 0) + 1
                logger.info(f"  ID {txn.transaction_id}: {txn.merchant} ${txn.amount} - {txn.status}")
                if txn.notes:
                    logger.info(f"    Notes: {txn.notes}")
            
            logger.info(f"Status breakdown: {status_counts}")
            
            # Check specifically for gadget store transactions
            logger.info("Looking for gadget store transactions...")
            result = conn.execute(text("""
                SELECT transaction_id, merchant, amount, status, notes
                FROM transactions 
                WHERE LOWER(merchant) LIKE '%gadget%' 
                   OR LOWER(merchant) LIKE '%electronics%'
                   OR LOWER(merchant) LIKE '%store%'
                ORDER BY date DESC
            """))
            
            gadget_txns = result.fetchall()
            if gadget_txns:
                logger.info(f"Found {len(gadget_txns)} gadget/electronics related transactions:")
                for txn in gadget_txns:
                    logger.info(f"  ID {txn.transaction_id}: {txn.merchant} ${txn.amount} - {txn.status}")
                    if txn.notes:
                        logger.info(f"    Notes: {txn.notes}")
            else:
                logger.info("No gadget/electronics related transactions found")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Error checking database state: {e}", exc_info=True)
        return False

def test_cancel_operation():
    """Test the cancellation operation directly"""
    logger.info("🧪 Testing transaction cancellation operation...")
    
    try:
        # First, get a pending transaction to test with
        pending_transactions = TransactionManager.get_pending_transactions()
        logger.info(f"Found {len(pending_transactions)} pending transactions")
        
        if not pending_transactions:
            logger.warning("No pending transactions found. Creating a test transaction...")
            
            # Create a test transaction
            with get_db_connection() as conn:
                # Get an account to use
                result = conn.execute(text("SELECT account_id FROM accounts LIMIT 1"))
                account = result.fetchone()
                
                if not account:
                    logger.info("Creating test account...")
                    conn.execute(text("""
                        INSERT INTO accounts (account_name, current_balance) 
                        VALUES ('Debug Test Account', 1000.00)
                    """))
                    conn.commit()
                    
                    result = conn.execute(text("SELECT account_id FROM accounts WHERE account_name = 'Debug Test Account'"))
                    account = result.fetchone()
                
                account_id = account[0]
                
                # Create test transaction
                logger.info(f"Creating test transaction for account {account_id}...")
                result = conn.execute(text("""
                    INSERT INTO transactions (date, amount, merchant, category, status, account_id, notes)
                    VALUES (NOW(), 999.99, 'Debug Gadget Store', 'Electronics', 'pending', :account_id, 'Test transaction for debugging')
                    RETURNING transaction_id
                """), {"account_id": account_id})
                
                test_txn_id = result.fetchone()[0]
                conn.commit()
                logger.info(f"✅ Created test transaction with ID {test_txn_id}")
                
                # Refresh pending transactions
                pending_transactions = TransactionManager.get_pending_transactions()
        
        if pending_transactions:
            # Test cancelling the first pending transaction
            test_txn = pending_transactions[0]
            test_txn_id = test_txn['transaction_id']
            
            logger.info(f"🎯 Testing cancellation of transaction {test_txn_id}: {test_txn['merchant']} ${test_txn['amount']}")
            
            # Log the before state
            with get_db_connection() as conn:
                result = conn.execute(text("""
                    SELECT transaction_id, merchant, amount, status, notes
                    FROM transactions 
                    WHERE transaction_id = :txn_id
                """), {"txn_id": test_txn_id})
                
                before_state = result.fetchone()
                logger.info(f"BEFORE cancellation: {dict(before_state._mapping)}")
            
            # Attempt cancellation
            logger.info("Attempting cancellation...")
            success, message = TransactionManager.cancel_transaction(test_txn_id, "Debug test cancellation")
            
            logger.info(f"Cancellation result: success={success}, message='{message}'")
            
            # Check the after state
            with get_db_connection() as conn:
                result = conn.execute(text("""
                    SELECT transaction_id, merchant, amount, status, notes
                    FROM transactions 
                    WHERE transaction_id = :txn_id
                """), {"txn_id": test_txn_id})
                
                after_state = result.fetchone()
                logger.info(f"AFTER cancellation: {dict(after_state._mapping)}")
                
                # Compare states
                if before_state.status != after_state.status:
                    logger.info(f"✅ Status changed from '{before_state.status}' to '{after_state.status}'")
                else:
                    logger.error(f"❌ Status did not change! Still '{after_state.status}'")
                    
                if before_state.notes != after_state.notes:
                    logger.info(f"✅ Notes updated: '{after_state.notes}'")
                else:
                    logger.warning("Notes were not updated")
            
            return success
        else:
            logger.error("No pending transactions available for testing")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error testing cancellation: {e}", exc_info=True)
        return False

def test_raw_sql_update():
    """Test a raw SQL update to see if database writes work at all"""
    logger.info("🔧 Testing raw SQL update operations...")
    
    try:
        with get_db_connection() as conn:
            # Create a test transaction first
            trans = conn.begin()
            try:
                result = conn.execute(text("""
                    INSERT INTO transactions (date, amount, merchant, category, status, account_id, notes)
                    VALUES (NOW(), 1.00, 'Raw SQL Test', 'Test', 'pending', 
                           (SELECT account_id FROM accounts LIMIT 1), 'Raw SQL test')
                    RETURNING transaction_id
                """))
                
                test_id = result.fetchone()[0]
                trans.commit()
                logger.info(f"✅ Created test transaction {test_id}")
                
                # Now try to update it
                trans2 = conn.begin()
                try:
                    logger.info(f"Attempting to update transaction {test_id}...")
                    
                    update_result = conn.execute(text("""
                        UPDATE transactions 
                        SET status = 'declined', 
                            notes = COALESCE(notes, '') || E'\nRaw SQL test update'
                        WHERE transaction_id = :txn_id
                    """), {"txn_id": test_id})
                    
                    logger.info(f"Update affected {update_result.rowcount} rows")
                    trans2.commit()
                    
                    # Verify the update
                    result = conn.execute(text("""
                        SELECT transaction_id, status, notes 
                        FROM transactions 
                        WHERE transaction_id = :txn_id
                    """), {"txn_id": test_id})
                    
                    updated_row = result.fetchone()
                    logger.info(f"Updated transaction: {dict(updated_row._mapping)}")
                    
                    if updated_row.status == 'declined':
                        logger.info("✅ Raw SQL update successful!")
                        return True
                    else:
                        logger.error(f"❌ Raw SQL update failed - status is '{updated_row.status}'")
                        return False
                        
                except Exception as e:
                    trans2.rollback()
                    raise e
                    
            except Exception as e:
                trans.rollback()
                raise e
                
    except Exception as e:
        logger.error(f"❌ Raw SQL test failed: {e}", exc_info=True)
        return False

def main():
    """Run all debug tests"""
    logger.info("🚀 Starting transaction debug session...")
    logger.info("=" * 60)
    
    # Test connection first
    success, msg = test_connection()
    if not success:
        logger.error(f"❌ Database connection failed: {msg}")
        return
    else:
        logger.info(f"✅ Database connection successful: {msg}")
    
    # Check database state
    if not check_database_state():
        logger.error("❌ Database state check failed")
        return
    
    # Test raw SQL operations
    if not test_raw_sql_update():
        logger.error("❌ Raw SQL test failed")
        return
    
    # Test the transaction manager
    if not test_cancel_operation():
        logger.error("❌ Transaction manager test failed")
        return
    
    logger.info("🎉 All debug tests completed!")
    logger.info("Check transaction_debug.log for detailed logs")

if __name__ == "__main__":
    main()
