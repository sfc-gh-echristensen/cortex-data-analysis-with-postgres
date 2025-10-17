#!/usr/bin/env python3
"""
Bulk insert expanded PostgreSQL transaction data (60 days worth)
Uses the expanded_transactions_postgresql.csv file
"""

import pandas as pd
from datetime import datetime
from db_utils import get_db_connection, TransactionManager
from sqlalchemy import text
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def bulk_insert_expanded_transactions():
    """Insert expanded transactions from CSV into PostgreSQL"""
    
    print("🚀 Starting bulk insert of expanded transaction data...")
    
    try:
        # Read the expanded CSV file
        print("📁 Reading expanded CSV file...")
        csv_file = "expanded_transactions_postgresql.csv"
        df = pd.read_csv(csv_file)
        print(f"✅ Loaded {len(df)} transactions from {csv_file}")
        
        # Show data summary
        pending_count = len(df[df['status'] == 'pending'])
        approved_count = len(df[df['status'] == 'approved'])
        total_amount = df['amount'].sum()
        
        print(f"📊 Data Summary:")
        print(f"   - Pending: {pending_count} transactions")
        print(f"   - Approved: {approved_count} transactions")
        print(f"   - Total Value: ${total_amount:,.2f}")
        print(f"   - Date Range: {df['date'].min()} to {df['date'].max()}")
        
        # Convert date strings to datetime objects
        df['date'] = pd.to_datetime(df['date'])
        
        # Connect to database and insert data
        print("🔌 Connecting to PostgreSQL...")
        
        with get_db_connection() as conn:
            print("✅ Connected to database")
            
            # Check current transaction count
            existing_count = conn.execute(text("SELECT COUNT(*) FROM transactions")).fetchone()[0]
            print(f"📊 Found {existing_count} existing transactions in database")
            
            # Clear existing data if user wants fresh start
            response = input(f"\n🤔 Found {existing_count} existing transactions. Clear all and insert fresh data? (y/N): ")
            if response.lower() == 'y':
                print("🗑️ Clearing existing transaction data...")
                conn.execute(text("DELETE FROM transactions"))
                conn.commit()
                print("✅ Existing data cleared")
                existing_count = 0
            
            # Insert each transaction
            successful_inserts = 0
            
            for index, row in df.iterrows():
                try:
                    # Insert transaction using parameterized query
                    insert_query = text("""
                        INSERT INTO transactions (date, amount, merchant, category, notes, status, account_id)
                        VALUES (:date, :amount, :merchant, :category, :notes, :status, :account_id)
                    """)
                    
                    conn.execute(insert_query, {
                        'date': row['date'],
                        'amount': float(row['amount']),
                        'merchant': row['merchant'],
                        'category': row['category'],
                        'notes': row['notes'],
                        'status': row['status'],
                        'account_id': int(row['account_id'])
                    })
                    
                    successful_inserts += 1
                    
                    # Progress indicator
                    if successful_inserts % 50 == 0:
                        print(f"   📝 Inserted {successful_inserts}/{len(df)} transactions...")
                        
                except Exception as e:
                    logger.warning(f"❌ Failed to insert transaction {index + 1}: {e}")
                    continue
            
            # Commit all changes
            conn.commit()
            print(f"💾 Committed {successful_inserts} transactions to database")
            
            # Verify the insert
            new_count = conn.execute(text("SELECT COUNT(*) FROM transactions")).fetchone()[0]
            print(f"✅ Database now contains {new_count} total transactions")
            print(f"📈 Added {new_count - existing_count} new transactions")
            
            # Show status breakdown
            status_query = text("""
                SELECT 
                    status,
                    COUNT(*) as count,
                    SUM(amount) as total_amount
                FROM transactions 
                GROUP BY status
                ORDER BY status
            """)
            
            print("\n📊 Final Status Summary:")
            results = conn.execute(status_query).fetchall()
            for row in results:
                print(f"   {row[0].title()}: {row[1]} transactions (${row[2]:,.2f} total)")
            
            # Show recent transactions
            print("\n📋 Sample of recent transactions:")
            sample_query = text("""
                SELECT transaction_id, date, merchant, amount, status
                FROM transactions 
                ORDER BY date DESC 
                LIMIT 5
            """)
            
            sample_results = conn.execute(sample_query).fetchall()
            for row in sample_results:
                print(f"   ID {row[0]}: {row[2]} - ${row[3]} ({row[4]}) on {row[1].strftime('%Y-%m-%d')}")
            
            return True, f"Successfully inserted {successful_inserts} transactions"
            
    except FileNotFoundError:
        error_msg = f"❌ CSV file 'expanded_transactions_postgresql.csv' not found. Run 'python3 generate_expanded_data.py' first."
        print(error_msg)
        return False, error_msg
        
    except Exception as e:
        error_msg = f"❌ Error during bulk insert: {e}"
        print(error_msg)
        logger.error(error_msg, exc_info=True)
        return False, error_msg

if __name__ == "__main__":
    print("🗂️ PostgreSQL Expanded Data Loader")
    print("=" * 60)
    
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
    
    # Run the bulk insert
    success, message = bulk_insert_expanded_transactions()
    
    if success:
        print(f"\n🎉 {message}")
        print("\n💡 You now have 60 days of realistic transaction data!")
        print("     - Most transactions are 'approved' (historical data)")
        print("     - 4 transactions are 'pending' (perfect for AI testing)")
        print("     - Rich variety of merchants and categories")
        print("     - Ready for comprehensive analysis and testing!")
    else:
        print(f"\n❌ Bulk insert failed: {message}")
        exit(1)
