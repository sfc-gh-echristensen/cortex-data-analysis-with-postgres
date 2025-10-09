#!/usr/bin/env python3
"""
Bulk insert expanded Snowflake transaction data (1 year worth)
Uses the expanded_transactions_snowflake.csv file
"""

import pandas as pd
import streamlit as st
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_snowflake_session():
    """Get Snowflake session using Streamlit secrets"""
    try:
        return st.connection('snowflake').session()
    except Exception as e:
        logger.error(f"Failed to connect to Snowflake: {e}")
        return None

def bulk_insert_expanded_snowflake():
    """Insert expanded transactions from CSV into Snowflake"""
    
    print("🚀 Starting bulk insert of expanded Snowflake data...")
    
    try:
        # Get Snowflake session
        print("🔌 Connecting to Snowflake...")
        session = get_snowflake_session()
        if not session:
            return False, "Failed to connect to Snowflake"
        
        print("✅ Connected to Snowflake")
        
        # Read the expanded CSV file
        print("📁 Reading expanded CSV file...")
        csv_file = "expanded_transactions_snowflake.csv"
        df = pd.read_csv(csv_file)
        print(f"✅ Loaded {len(df)} transactions from {csv_file}")
        
        # Show data summary
        total_amount = df['amount'].sum()
        categories = df['category'].nunique()
        merchants = df['merchant'].nunique()
        accounts = df['account_name'].nunique()
        
        print(f"📊 Data Summary:")
        print(f"   - Total Transactions: {len(df):,}")
        print(f"   - Total Value: ${total_amount:,.2f}")
        print(f"   - Categories: {categories}")
        print(f"   - Merchants: {merchants}")
        print(f"   - Accounts: {accounts}")
        print(f"   - Date Range: {df['date'].min()} to {df['date'].max()}")
        
        # Check existing data
        print("📊 Checking existing Snowflake data...")
        try:
            existing_count_query = "SELECT COUNT(*) as count FROM TRANSACTIONS"
            existing_count_result = session.sql(existing_count_query).collect()
            existing_count = existing_count_result[0]['COUNT']
            print(f"   Found {existing_count:,} existing transactions")
            
            if existing_count > 0:
                response = input(f"\n🤔 Found {existing_count:,} existing transactions. Clear all and insert fresh data? (y/N): ")
                if response.lower() == 'y':
                    print("🗑️ Clearing existing Snowflake data...")
                    session.sql("DELETE FROM TRANSACTIONS").collect()
                    print("✅ Existing data cleared")
                    existing_count = 0
                    
        except Exception as e:
            print(f"⚠️  Could not count existing transactions: {e}")
            existing_count = 0
        
        # Upload data to Snowflake
        print(f"📤 Uploading {len(df):,} transactions to Snowflake...")
        
        try:
            # Use Snowflake's write_pandas method for efficient bulk insert
            success, nchunks, nrows, _ = session.write_pandas(
                df, 
                table_name='TRANSACTIONS',
                auto_create_table=False,  # Table should already exist
                overwrite=False,          # Append to existing data
                quote_identifiers=False   # Don't quote column names
            )
            
            if success:
                print(f"✅ Successfully uploaded {nrows:,} rows in {nchunks} chunks")
                
                # Verify the insert
                new_count_result = session.sql("SELECT COUNT(*) as count FROM TRANSACTIONS").collect()
                new_count = new_count_result[0]['COUNT']
                print(f"📈 Snowflake now contains {new_count:,} total transactions")
                print(f"➕ Added {new_count - existing_count:,} new transactions")
                
                # Show category breakdown
                print("\n📊 Transaction Summary by Category:")
                category_query = """
                SELECT 
                    category,
                    COUNT(*) as transaction_count,
                    SUM(amount) as total_amount,
                    AVG(amount) as avg_amount
                FROM TRANSACTIONS 
                GROUP BY category
                ORDER BY total_amount DESC
                LIMIT 10
                """
                
                category_results = session.sql(category_query).collect()
                for row in category_results:
                    print(f"   {row['CATEGORY']}: {row['TRANSACTION_COUNT']:,} txns, ${row['TOTAL_AMOUNT']:,.2f} total, ${row['AVG_AMOUNT']:.2f} avg")
                
                # Show monthly breakdown
                print("\n📅 Monthly Transaction Volume:")
                monthly_query = """
                SELECT 
                    DATE_TRUNC('month', TO_DATE(date)) as month,
                    COUNT(*) as transaction_count,
                    SUM(amount) as total_amount
                FROM TRANSACTIONS 
                GROUP BY DATE_TRUNC('month', TO_DATE(date))
                ORDER BY month DESC
                LIMIT 12
                """
                
                monthly_results = session.sql(monthly_query).collect()
                for row in monthly_results:
                    month_str = row['MONTH'].strftime('%Y-%m')
                    print(f"   {month_str}: {row['TRANSACTION_COUNT']:,} transactions, ${row['TOTAL_AMOUNT']:,.2f}")
                
                return True, f"Successfully inserted {nrows:,} transactions into Snowflake"
            else:
                return False, "Failed to upload data to Snowflake"
                
        except Exception as e:
            error_msg = f"Error during Snowflake upload: {e}"
            print(f"❌ {error_msg}")
            return False, error_msg
            
    except FileNotFoundError:
        error_msg = f"❌ CSV file 'expanded_transactions_snowflake.csv' not found. Run 'python3 generate_expanded_data.py' first."
        print(error_msg)
        return False, error_msg
        
    except Exception as e:
        error_msg = f"❌ Error during bulk insert: {e}"
        print(error_msg)
        logger.error(error_msg, exc_info=True)
        return False, error_msg

if __name__ == "__main__":
    print("❄️ Snowflake Expanded Data Loader")
    print("=" * 60)
    
    # Test Snowflake connection
    try:
        session = get_snowflake_session()
        if not session:
            print("❌ Snowflake connection failed")
            exit(1)
        print("✅ Snowflake connection successful")
        session.close()
    except Exception as e:
        print(f"❌ Snowflake connection test failed: {e}")
        exit(1)
    
    # Run the bulk insert
    success, message = bulk_insert_expanded_snowflake()
    
    if success:
        print(f"\n🎉 {message}")
        print("\n💡 You now have a full year of transaction data in Snowflake!")
        print("     - Rich dataset perfect for Cortex analysis")
        print("     - Multiple categories and merchants")
        print("     - Full seasonal patterns and trends")
        print("     - Ready for sophisticated AI queries!")
    else:
        print(f"\n❌ Bulk insert failed: {message}")
        exit(1)
