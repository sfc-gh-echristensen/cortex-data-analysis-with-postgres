#!/usr/bin/env python3
"""
Simple test to debug status update issue
"""

import os
from sqlalchemy import create_engine, text

def get_engine():
    """Create a simple engine"""
    # Use environment or hardcoded values for testing
    host = os.environ.get("PG_HOST", "localhost")  
    port = os.environ.get("PG_PORT", "5432")
    database = os.environ.get("PG_DB", "postgres")
    user = os.environ.get("PG_USER", "postgres")
    password = os.environ.get("PG_PASSWORD", "")
    
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"
    return create_engine(url, echo=True)  # Enable echo to see SQL

def test_status_update():
    """Test status update directly"""
    engine = get_engine()
    
    print("🧪 Testing status update...")
    
    with engine.connect() as conn:
        # Find a pending transaction
        result = conn.execute(text("""
            SELECT transaction_id, merchant, status, notes
            FROM transactions 
            WHERE status = 'pending' 
            LIMIT 1
        """))
        
        test_txn = result.fetchone()
        if not test_txn:
            print("❌ No pending transactions found")
            return
        
        print(f"📋 Found: ID {test_txn.transaction_id} - {test_txn.merchant}")
        print(f"   Status: {test_txn.status}")
        print(f"   Notes: {test_txn.notes or '(empty)'}")
        
        # Start transaction manually
        with conn.begin() as trans:
            print("\n🔄 Attempting status update...")
            
            # Simple status update first
            result = conn.execute(text("""
                UPDATE transactions 
                SET status = 'declined'
                WHERE transaction_id = :txn_id
            """), {"txn_id": test_txn.transaction_id})
            
            print(f"   Simple update affected {result.rowcount} rows")
            
            # Verify the change
            verify = conn.execute(text("""
                SELECT status, notes FROM transactions 
                WHERE transaction_id = :txn_id
            """), {"txn_id": test_txn.transaction_id})
            
            updated = verify.fetchone()
            print(f"   New status: {updated.status}")
            
            if updated.status == 'declined':
                print("✅ SUCCESS: Status update worked!")
                
                # Now test adding notes
                result2 = conn.execute(text("""
                    UPDATE transactions 
                    SET notes = COALESCE(notes, '') || E'\\nTEST: Status update successful'
                    WHERE transaction_id = :txn_id
                """), {"txn_id": test_txn.transaction_id})
                
                print(f"   Notes update affected {result2.rowcount} rows")
                
                # Final verification
                final_verify = conn.execute(text("""
                    SELECT status, notes FROM transactions 
                    WHERE transaction_id = :txn_id
                """), {"txn_id": test_txn.transaction_id})
                
                final = final_verify.fetchone()
                print(f"   Final status: {final.status}")
                print(f"   Final notes: {final.notes}")
                
            else:
                print(f"❌ FAILED: Status is still {updated.status}")
            
            # Commit the test
            print("💾 Committing changes...")

if __name__ == "__main__":
    try:
        test_status_update()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
