#!/usr/bin/env python3
"""
Bulk insert sample transaction data into PostgreSQL using existing connections
Reads from sample_transactions_postgresql.csv and inserts into the transactions table
"""

import pandas as pd
from datetime import datetime
from db_utils import get_db_connection, TransactionManager
from sqlalchemy import text
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def bulk_insert_transactions():
    """Insert sample transactions from CSV into PostgreSQL"""
    
    print("🚀 Starting bulk insert of sample transaction data...")
    
    try:
        # Read the CSV file
        print("📁 Reading CSV file...")
        csv_file = "sample_transactions_postgresql.csv"
        df = pd.read_csv(csv_file)
        print(f"✅ Loaded {len(df)} transactions from {csv_file}")
        
        # Convert date strings to datetime objects
        df['date'] = pd.to_datetime(df['date'])
        
        # Connect to database and insert data
        print("🔌 Connecting to PostgreSQL...")
        
        with get_db_connection() as conn:
            print("✅ Connected to database")
            
            # Check if we have any existing transactions to avoid duplicates
            existing_count = conn.execute(text("SELECT COUNT(*) FROM transactions")).fetchone()[0]
            print(f"📊 Found {existing_count} existing transactions in database")
            
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
                    if successful_inserts % 20 == 0:
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
            
            # Show some sample data
            print("\n📋 Sample of newly inserted data:")
            sample_query = text("""
                SELECT transaction_id, date, merchant, amount, status
                FROM transactions 
                ORDER BY transaction_id DESC 
                LIMIT 5
            """)
            
            results = conn.execute(sample_query).fetchall()
            for row in results:
                print(f"   ID {row[0]}: {row[2]} - ${row[3]} ({row[4]}) on {row[1].strftime('%Y-%m-%d')}")
            
            return True, f"Successfully inserted {successful_inserts} transactions"
            
    except FileNotFoundError:
        error_msg = f"❌ CSV file '{csv_file}' not found"
        print(error_msg)
        return False, error_msg
        
    except Exception as e:
        error_msg = f"❌ Error during bulk insert: {e}"
        print(error_msg)
        logger.error(error_msg, exc_info=True)
        return False, error_msg

def show_transaction_summary():
    """Show summary statistics after inserting data"""
    print("\n📊 Transaction Summary:")
    
    try:
        stats = TransactionManager.get_transaction_stats()
        
        for status, data in stats.items():
            print(f"   {status.title()}: {data['count']} transactions (${data['total_amount']:.2f})")
            
    except Exception as e:
        print(f"❌ Could not load transaction stats: {e}")

if __name__ == "__main__":
    print("🗂️ PostgreSQL Bulk Data Insert Tool")
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
    
    # Run the bulk insert
    success, message = bulk_insert_transactions()
    
    if success:
        print(f"\n🎉 {message}")
        show_transaction_summary()
        print("\n💡 You can now use the Streamlit app to view and manage these transactions!")
    else:
        print(f"\n❌ Bulk insert failed: {message}")
        exit(1)
