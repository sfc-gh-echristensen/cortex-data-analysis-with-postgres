#!/usr/bin/env python3
"""
Direct psycopg2 test to fix transaction 5 status
"""

import psycopg2
import os
from contextlib import contextmanager

@contextmanager
def get_raw_connection():
    """Get raw psycopg2 connection"""
    conn = None
    try:
        # Get connection parameters
        host = os.environ.get("PG_HOST", "localhost")
        port = os.environ.get("PG_PORT", "5432") 
        database = os.environ.get("PG_DB", "postgres")
        user = os.environ.get("PG_USER", "postgres")
        password = os.environ.get("PG_PASSWORD", "")
        
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        
        yield conn
        
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()

def fix_transaction_5():
    """Fix transaction 5 status using raw psycopg2"""
    print("🔧 Fixing transaction 5 status with raw psycopg2...")
    
    try:
        # Try to get connection details from Streamlit secrets
        import streamlit as st
        pg_config = st.secrets.get("postgres", {})
        
        conn = psycopg2.connect(
            host=pg_config.get("host"),
            port=pg_config.get("port", 5432),
            database=pg_config.get("database"),
            user=pg_config.get("user"),
            password=pg_config.get("password")
        )
        
        print("✅ Raw psycopg2 connection established")
        
        cur = conn.cursor()
        
        # Check current state
        print("1. Checking current state...")
        cur.execute("SELECT transaction_id, merchant, status, notes FROM transactions WHERE transaction_id = 5")
        row = cur.fetchone()
        
        if row:
            txn_id, merchant, status, notes = row
            print(f"   ID {txn_id}: {merchant} - Status: {status}")
            print(f"   Notes: {notes}")
            
            if status == 'pending':
                print("\n2. Attempting to update status...")
                
                # Direct status update
                cur.execute("""
                    UPDATE transactions 
                    SET status = 'declined'
                    WHERE transaction_id = 5 AND status = 'pending'
                """)
                
                rows_affected = cur.rowcount
                print(f"   Status update affected {rows_affected} rows")
                
                if rows_affected > 0:
                    # Verify the change
                    cur.execute("SELECT status FROM transactions WHERE transaction_id = 5")
                    new_status = cur.fetchone()[0]
                    print(f"   New status: {new_status}")
                    
                    if new_status == 'declined':
                        conn.commit()
                        print("✅ SUCCESS: Transaction 5 status updated and committed!")
                    else:
                        conn.rollback()
                        print(f"❌ FAILED: Status is still {new_status}")
                else:
                    print("❌ No rows were updated")
            else:
                print(f"   Transaction 5 is already {status}")
        else:
            print("❌ Transaction 5 not found")
            
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_transaction_5()
