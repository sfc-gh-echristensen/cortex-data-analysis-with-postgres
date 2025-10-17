#!/usr/bin/env python3
"""
Bulk insert sample transaction data into Snowflake using existing connections
Reads from sample_transactions_snowflake.csv and inserts into the TRANSACTIONS table
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

def bulk_insert_snowflake_transactions():
    """Insert sample transactions from CSV into Snowflake"""
    
    print("🚀 Starting bulk insert of sample transaction data into Snowflake...")
    
    try:
        # Get Snowflake session
        print("🔌 Connecting to Snowflake...")
        session = get_snowflake_session()
        if not session:
            return False, "Failed to connect to Snowflake"
        
        print("✅ Connected to Snowflake")
        
        # Read the CSV file
        print("📁 Reading CSV file...")
        csv_file = "sample_transactions_snowflake.csv"
        df = pd.read_csv(csv_file)
        print(f"✅ Loaded {len(df)} transactions from {csv_file}")
        
        # Check existing data
        try:
            existing_count_query = "SELECT COUNT(*) as count FROM TRANSACTIONS"
            existing_count_result = session.sql(existing_count_query).collect()
            existing_count = existing_count_result[0]['COUNT']
            print(f"📊 Found {existing_count} existing transactions in Snowflake")
        except Exception as e:
            print(f"⚠️  Could not count existing transactions: {e}")
            existing_count = 0
        
        # Convert DataFrame to Snowflake table
        print("📤 Uploading data to Snowflake...")
        
        # Write DataFrame directly to Snowflake (append mode)
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
                print(f"✅ Successfully uploaded {nrows} rows in {nchunks} chunks")
                
                # Verify the insert
                new_count_result = session.sql("SELECT COUNT(*) as count FROM TRANSACTIONS").collect()
                new_count = new_count_result[0]['COUNT']
                print(f"📈 Snowflake now contains {new_count} total transactions")
                print(f"➕ Added {new_count - existing_count} new transactions")
                
                # Show sample of newly inserted data
                print("\n📋 Sample of data in Snowflake:")
                sample_query = """
                SELECT transaction_id, date, merchant, amount, category, account_name
                FROM TRANSACTIONS 
                ORDER BY date DESC 
                LIMIT 5
                """
                
                sample_results = session.sql(sample_query).collect()
                for row in sample_results:
                    print(f"   {row['TRANSACTION_ID']}: {row['MERCHANT']} - ${row['AMOUNT']} ({row['CATEGORY']}) - {row['ACCOUNT_NAME']}")
                
                return True, f"Successfully inserted {nrows} transactions into Snowflake"
            else:
                return False, "Failed to upload data to Snowflake"
                
        except Exception as e:
            error_msg = f"Error during Snowflake upload: {e}"
            print(f"❌ {error_msg}")
            return False, error_msg
            
    except FileNotFoundError:
        error_msg = f"❌ CSV file '{csv_file}' not found"
        print(error_msg)
        return False, error_msg
        
    except Exception as e:
        error_msg = f"❌ Error during bulk insert: {e}"
        print(error_msg)
        logger.error(error_msg, exc_info=True)
        return False, error_msg

def show_snowflake_summary():
    """Show summary statistics from Snowflake"""
    print("\n📊 Snowflake Transaction Summary:")
    
    try:
        session = get_snowflake_session()
        if not session:
            print("❌ Could not connect to Snowflake for summary")
            return
            
        # Get summary by category
        summary_query = """
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
        
        results = session.sql(summary_query).collect()
        
        print("   Top Categories by Total Amount:")
        for row in results:
            print(f"   {row['CATEGORY']}: {row['TRANSACTION_COUNT']} txns, ${row['TOTAL_AMOUNT']:.2f} total, ${row['AVG_AMOUNT']:.2f} avg")
            
    except Exception as e:
        print(f"❌ Could not load Snowflake summary: {e}")

if __name__ == "__main__":
    print("❄️ Snowflake Bulk Data Insert Tool")
    print("=" * 50)
    
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
    success, message = bulk_insert_snowflake_transactions()
    
    if success:
        print(f"\n🎉 {message}")
        show_snowflake_summary()
        print("\n💡 You can now query this data using Snowflake Cortex in the Streamlit app!")
    else:
        print(f"\n❌ Bulk insert failed: {message}")
        exit(1)
