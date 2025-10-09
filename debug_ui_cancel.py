#!/usr/bin/env python3
"""
Debug script to test UI cancellation step by step
"""

from db_utils import TransactionManager, get_db_connection
from sqlalchemy import text

def show_current_transactions():
    """Show current transaction statuses"""
    print("📊 Current transaction status:")
    try:
        with get_db_connection() as conn:
            result = conn.execute(text("""
                SELECT transaction_id, merchant, amount, status, 
                       CASE WHEN notes LIKE '%CANCELLED%' THEN 'HAS_CANCEL_NOTE' ELSE 'NO_CANCEL_NOTE' END as cancel_note
                FROM transactions 
                ORDER BY transaction_id
            """))
            
            for row in result:
                status_emoji = {'pending': '🟡', 'declined': '🔴', 'approved': '🟢'}.get(row.status, '⚪')
                print(f"   ID {row.transaction_id}: {row.merchant} ${row.amount} {status_emoji} {row.status} ({row.cancel_note})")
                
    except Exception as e:
        print(f"❌ Error: {e}")

def test_specific_cancel(transaction_id):
    """Test cancelling a specific transaction"""
    print(f"\n🎯 Testing cancellation of transaction {transaction_id}...")
    
    try:
        # Show before state
        txn = TransactionManager.get_transaction_by_id(transaction_id)
        if not txn:
            print(f"❌ Transaction {transaction_id} not found")
            return
            
        print(f"BEFORE: ID {txn['transaction_id']} - {txn['merchant']} - Status: {txn['status']}")
        
        if txn['status'] != 'pending':
            print(f"❌ Transaction is {txn['status']}, cannot cancel")
            return
        
        # Attempt cancellation
        print("🔄 Attempting cancellation...")
        success, message = TransactionManager.cancel_transaction(transaction_id, "Debug UI test")
        
        print(f"Result: success={success}")
        print(f"Message: {message}")
        
        # Show after state
        updated_txn = TransactionManager.get_transaction_by_id(transaction_id)
        if updated_txn:
            print(f"AFTER: ID {updated_txn['transaction_id']} - Status: {updated_txn['status']}")
            
            if updated_txn['status'] == 'declined':
                print("✅ SUCCESS: Status updated to declined")
            else:
                print(f"❌ FAILED: Status is still {updated_txn['status']}")
        else:
            print("❌ Could not retrieve updated transaction")
            
    except Exception as e:
        print(f"❌ Error during cancellation: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("🔍 DEBUG: UI Cancellation Test")
    print("=" * 50)
    
    # Step 1: Show current state
    show_current_transactions()
    
    # Step 2: Find a pending transaction to test
    try:
        pending = TransactionManager.get_pending_transactions()
        print(f"\n📋 Found {len(pending)} pending transactions")
        
        if pending:
            # Test the first pending transaction
            test_id = pending[0]['transaction_id']
            test_specific_cancel(test_id)
            
            # Show final state
            print(f"\n📊 Final state after cancellation:")
            show_current_transactions()
        else:
            print("❌ No pending transactions to test")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
