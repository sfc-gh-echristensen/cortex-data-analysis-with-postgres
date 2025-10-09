#!/usr/bin/env python3
"""
Simple test for transaction ID 5 without context managers
"""

from db_utils import create_postgres_engine
from sqlalchemy import text

def test_transaction_5():
    """Test transaction 5 with clean connection"""
    print("🔍 Testing transaction ID 5 with clean connection...")
    
    engine = create_postgres_engine()
    
    try:
        with engine.connect() as conn:
            # Check current state
            print("1. Checking current state...")
            result = conn.execute(text("""
                SELECT transaction_id, merchant, amount, status, notes
                FROM transactions 
                WHERE transaction_id = 5
            """))
            
            txn = result.fetchone()
            if not txn:
                print("❌ Transaction 5 not found!")
                return
            
            print(f"   Transaction 5: {txn.merchant} - Status: {txn.status}")
            print(f"   Notes: {txn.notes or '(empty)'}")
            
            if txn.status != 'pending':
                print(f"   Transaction is already {txn.status}, cannot test cancellation")
                return
            
            # Start explicit transaction
            print("\n2. Starting transaction to update status...")
            with conn.begin() as trans:
                print("   Updating status to declined...")
                
                update_result = conn.execute(text("""
                    UPDATE transactions 
                    SET status = 'declined'
                    WHERE transaction_id = 5 AND status = 'pending'
                """))
                
                print(f"   Update affected {update_result.rowcount} rows")
                
                # Verify within transaction
                verify_result = conn.execute(text("""
                    SELECT status FROM transactions WHERE transaction_id = 5
                """))
                
                new_status = verify_result.fetchone()[0]
                print(f"   Status within transaction: {new_status}")
                
                if new_status == 'declined':
                    print("   💾 Committing transaction...")
                    # Transaction will auto-commit when exiting the with block
                else:
                    print("   ❌ Status not changed, transaction will rollback")
                    trans.rollback()
                    return
            
            # Final verification outside transaction
            print("\n3. Final verification after commit...")
            final_result = conn.execute(text("""
                SELECT transaction_id, status, notes
                FROM transactions 
                WHERE transaction_id = 5
            """))
            
            final_txn = final_result.fetchone()
            print(f"   Final status: {final_txn.status}")
            
            if final_txn.status == 'declined':
                print("✅ SUCCESS: Transaction 5 status updated to declined!")
            else:
                print(f"❌ FAILED: Status is still {final_txn.status}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        engine.dispose()

if __name__ == "__main__":
    test_transaction_5()
