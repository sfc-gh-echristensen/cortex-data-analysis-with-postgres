#!/usr/bin/env python3
"""
Setup script for transaction management functionality.
This script will:
1. Test database connection
2. Add status column if needed
3. Create sample data for testing
4. Verify everything works
"""

import sys
from db_utils import TransactionManager, test_connection, ensure_status_column_exists
from migrate_add_status import add_status_column, verify_migration

def setup_transaction_management():
    """Complete setup for transaction management"""
    print("🚀 Setting up Transaction Management System")
    print("=" * 50)
    
    # Step 1: Test connection
    print("\n1️⃣  Testing database connection...")
    conn_success, conn_msg = test_connection()
    if conn_success:
        print(f"✅ {conn_msg}")
    else:
        print(f"❌ {conn_msg}")
        print("\n💡 Please check:")
        print("   - PostgreSQL server is running")
        print("   - Connection credentials are correct")
        print("   - Database exists and is accessible")
        return False
    
    # Step 2: Ensure status column exists
    print("\n2️⃣  Checking status column...")
    status_exists, status_msg = ensure_status_column_exists()
    if status_exists:
        print(f"✅ {status_msg}")
    else:
        print(f"⚠️ {status_msg}")
        print("   Adding status column...")
        try:
            add_status_column()
            print("✅ Status column added successfully!")
        except Exception as e:
            print(f"❌ Failed to add status column: {e}")
            return False
    
    # Step 3: Test transaction management functions
    print("\n3️⃣  Testing transaction management functions...")
    try:
        # Get transaction stats
        stats = TransactionManager.get_transaction_stats()
        print(f"✅ Transaction stats retrieved: {len(stats)} different statuses found")
        
        for status, data in stats.items():
            print(f"   - {status}: {data['count']} transactions, total: ${data['total_amount']:.2f}")
        
        # Get pending transactions
        pending = TransactionManager.get_pending_transactions()
        print(f"✅ Found {len(pending)} pending transactions")
        
        if pending:
            print("\n   Pending transactions:")
            for txn in pending[:3]:  # Show first 3
                print(f"   - ID {txn['transaction_id']}: {txn['merchant']} ${txn['amount']}")
        
    except Exception as e:
        print(f"❌ Error testing transaction functions: {e}")
        return False
    
    # Step 4: Verify migration if we just ran it
    if not status_exists:
        print("\n4️⃣  Verifying migration...")
        try:
            verify_migration()
        except Exception as e:
            print(f"❌ Migration verification failed: {e}")
            return False
    
    print("\n🎉 Transaction Management Setup Complete!")
    print("\n✨ You can now:")
    print("   1. Run your Streamlit app: streamlit run streamlit_app.py")
    print("   2. Use the pending transaction manager")
    print("   3. Cancel transactions with full audit trail")
    print("   4. View transaction status and statistics")
    
    return True

def create_sample_pending_transactions():
    """Create some sample pending transactions for testing"""
    from db_utils import get_db_connection
    from sqlalchemy import text
    
    print("\n🧪 Creating sample pending transactions for testing...")
    
    try:
        with get_db_connection() as conn:
            # First check if we have any accounts
            result = conn.execute(text("SELECT account_id FROM accounts LIMIT 1"))
            account = result.fetchone()
            
            if not account:
                print("⚠️ No accounts found. Creating a sample account...")
                conn.execute(text("""
                    INSERT INTO accounts (account_name, current_balance) 
                    VALUES ('Test Account', 5000.00)
                """))
                conn.commit()
                
                result = conn.execute(text("SELECT account_id FROM accounts WHERE account_name = 'Test Account'"))
                account = result.fetchone()
            
            account_id = account[0]
            
            # Create some sample pending transactions
            sample_transactions = [
                ("2024-10-09", 1500.00, "Luxury Electronics Store", "Electronics", "pending"),
                ("2024-10-08", 750.00, "Expensive Restaurant", "Dining", "pending"),
                ("2024-10-08", 50.00, "Local Coffee Shop", "Dining", "pending"),
                ("2024-10-07", 2000.00, "Unknown Merchant XYZ", "Unknown", "pending"),
                ("2024-10-06", 25.00, "Gas Station", "Transportation", "pending"),
            ]
            
            trans = conn.begin()
            try:
                for date, amount, merchant, category, status in sample_transactions:
                    conn.execute(text("""
                        INSERT INTO transactions (date, amount, merchant, category, status, account_id)
                        VALUES (:date, :amount, :merchant, :category, :status, :account_id)
                    """), {
                        "date": date,
                        "amount": amount,
                        "merchant": merchant,
                        "category": category,
                        "status": status,
                        "account_id": account_id
                    })
                
                trans.commit()
                print(f"✅ Created {len(sample_transactions)} sample pending transactions")
                
                # Show what was created
                result = conn.execute(text("""
                    SELECT transaction_id, merchant, amount, status 
                    FROM transactions 
                    WHERE status = 'pending' 
                    ORDER BY date DESC
                """))
                
                print("\n   Sample transactions created:")
                for row in result:
                    print(f"   - ID {row[0]}: {row[1]} ${row[2]} ({row[3]})")
                    
            except Exception as e:
                trans.rollback()
                raise e
                
    except Exception as e:
        print(f"❌ Error creating sample transactions: {e}")
        return False
        
    return True

if __name__ == "__main__":
    success = setup_transaction_management()
    
    if success:
        # Ask if user wants sample data
        create_samples = input("\n❓ Create sample pending transactions for testing? (y/N): ").lower().startswith('y')
        if create_samples:
            create_sample_pending_transactions()
        
        print("\n🎯 Next steps:")
        print("   1. Run: streamlit run streamlit_app.py")
        print("   2. Go to the 'Pending Transaction Manager' section")
        print("   3. Test the cancellation functionality")
        
    else:
        print(f"\n💥 Setup failed. Please check the errors above.")
        sys.exit(1)
