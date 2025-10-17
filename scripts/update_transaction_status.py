#!/usr/bin/env python3
"""
Update existing PostgreSQL transactions to have mostly 'approved' status
Leave only 4 transactions as 'pending' for testing
"""

from db_utils import get_db_connection, TransactionManager
from sqlalchemy import text
import random

def update_transaction_statuses():
    """Update most transactions to approved, keep 4 as pending"""
    
    print("🔄 Updating transaction statuses in PostgreSQL...")
    
    try:
        with get_db_connection() as conn:
            # Get all current pending transactions
            pending_result = conn.execute(text("""
                SELECT transaction_id, merchant, amount 
                FROM transactions 
                WHERE status = 'pending'
                ORDER BY transaction_id
            """))
            
            pending_txns = pending_result.fetchall()
            print(f"📊 Found {len(pending_txns)} pending transactions")
            
            if len(pending_txns) <= 4:
                print("✅ Already have 4 or fewer pending transactions. No changes needed.")
                return True, f"Only {len(pending_txns)} pending transactions found"
            
            # Select 4 transactions to keep as pending (prefer higher amounts for testing)
            pending_list = list(pending_txns)
            # Sort by amount descending and take top 4 for better AI testing
            pending_list.sort(key=lambda x: float(x[2]), reverse=True)
            keep_pending = pending_list[:4]
            to_approve = pending_list[4:]
            
            print(f"🎯 Keeping these 4 transactions as PENDING:")
            for txn in keep_pending:
                print(f"   ID {txn[0]}: {txn[1]} - ${txn[2]}")
            
            print(f"✅ Approving {len(to_approve)} transactions...")
            
            # Update the transactions to approved
            approved_count = 0
            for txn in to_approve:
                try:
                    update_result = conn.execute(text("""
                        UPDATE transactions 
                        SET status = 'approved'
                        WHERE transaction_id = :txn_id
                    """), {"txn_id": txn[0]})
                    
                    if update_result.rowcount > 0:
                        approved_count += 1
                        
                except Exception as e:
                    print(f"❌ Failed to approve transaction {txn[0]}: {e}")
                    continue
            
            # Commit all changes
            conn.commit()
            print(f"💾 Committed {approved_count} status updates")
            
            # Verify the final state
            final_check = conn.execute(text("""
                SELECT 
                    status,
                    COUNT(*) as count,
                    SUM(amount) as total_amount
                FROM transactions 
                GROUP BY status
                ORDER BY status
            """))
            
            print("\n📈 Final transaction status summary:")
            for row in final_check.fetchall():
                print(f"   {row[0].title()}: {row[1]} transactions (${row[2]:.2f} total)")
            
            return True, f"Successfully updated {approved_count} transactions to approved status"
            
    except Exception as e:
        error_msg = f"Error updating transaction statuses: {e}"
        print(f"❌ {error_msg}")
        return False, error_msg

if __name__ == "__main__":
    print("🔧 Transaction Status Updater")
    print("=" * 50)
    
    # Test connection first
    try:
        from db_utils import test_connection
        success, msg = test_connection()
        if not success:
            print(f"❌ Database connection failed: {msg}")
            exit(1)
        print(f"✅ Database connection: {msg}")
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        exit(1)
    
    # Run the status update
    success, message = update_transaction_statuses()
    
    if success:
        print(f"\n🎉 {message}")
        print("\n💡 Now you have 4 pending transactions perfect for AI analysis testing!")
    else:
        print(f"\n❌ Status update failed: {message}")
        exit(1)
