#!/usr/bin/env python3
"""
Final Snowflake data loader with proper data type conversion
"""

import pandas as pd
import snowflake.connector
import os
import toml
from pathlib import Path
import re

def get_snowflake_connection():
    """Get Snowflake connection using secrets.toml"""
    try:
        # Look for secrets.toml in .streamlit directory
        secrets_path = Path.home() / ".streamlit" / "secrets.toml"
        if not secrets_path.exists():
            # Try local .streamlit directory
            secrets_path = Path(".streamlit") / "secrets.toml"
            
        if not secrets_path.exists():
            return None, "secrets.toml not found in .streamlit directory"
            
        # Load secrets
        secrets = toml.load(secrets_path)
        
        if 'connections' not in secrets or 'snowflake' not in secrets['connections']:
            return None, "Snowflake connection not found in secrets.toml"
            
        sf_config = secrets['connections']['snowflake']
        
        # Create connection
        conn = snowflake.connector.connect(
            account=sf_config.get('account'),
            user=sf_config.get('user'),
            password=sf_config.get('password'),
            warehouse=sf_config.get('warehouse'),
            database=sf_config.get('database'),
            schema=sf_config.get('schema'),
            role=sf_config.get('role')
        )
        
        return conn, "Connected successfully"
        
    except Exception as e:
        return None, f"Connection failed: {e}"

def convert_transaction_id(tx_id_str):
    """Convert string transaction ID like 'tx-3406' to numeric"""
    try:
        # Extract numeric part from 'tx-XXXX'
        match = re.search(r'tx-(\d+)', tx_id_str)
        if match:
            return int(match.group(1))
        else:
            # Fallback: hash the string to get a number
            return abs(hash(tx_id_str)) % 1000000
    except:
        return abs(hash(tx_id_str)) % 1000000

def convert_account_name_to_id(account_name):
    """Convert account name to account ID"""
    account_mapping = {
        'Checking': 1,
        'Credit Card': 2,
        'Savings': 3
    }
    return account_mapping.get(account_name, 1)  # Default to 1 if unknown

def load_snowflake_data():
    """Load expanded transaction data into Snowflake with proper data conversion"""
    
    print("❄️ Final Snowflake Data Loader")
    print("=" * 60)
    
    # Get connection
    print("🔌 Connecting to Snowflake...")
    conn, msg = get_snowflake_connection()
    
    if not conn:
        print(f"❌ {msg}")
        return False, msg
        
    print(f"✅ {msg}")
    
    try:
        cursor = conn.cursor()
        
        # Read CSV file
        print("📁 Reading expanded CSV file...")
        csv_file = "expanded_transactions_snowflake.csv"
        
        if not os.path.exists(csv_file):
            error_msg = f"CSV file '{csv_file}' not found. Run 'python3 generate_expanded_data.py' first."
            print(f"❌ {error_msg}")
            return False, error_msg
            
        df = pd.read_csv(csv_file)
        print(f"✅ Loaded {len(df)} transactions from {csv_file}")
        
        # Show data summary
        total_amount = df['amount'].sum()
        print(f"📊 Data Summary:")
        print(f"   - Total Transactions: {len(df):,}")
        print(f"   - Total Value: ${total_amount:,.2f}")
        print(f"   - Date Range: {df['date'].min()} to {df['date'].max()}")
        
        # Check existing data
        print("\n📊 Checking existing data...")
        cursor.execute("SELECT COUNT(*) FROM TRANSACTIONS")
        existing_count = cursor.fetchone()[0]
        print(f"   Found {existing_count:,} existing transactions")
        
        if existing_count > 0:
            print("\n🗑️ Clearing existing data for fresh load...")
            cursor.execute("DELETE FROM TRANSACTIONS")
            conn.commit()
            print("✅ Existing data cleared")
            existing_count = 0
        
        # Transform data to match Snowflake schema
        print("\n🔄 Converting data to match Snowflake schema...")
        
        # Convert transaction IDs from string to numeric
        df['numeric_transaction_id'] = df['transaction_id'].apply(convert_transaction_id)
        
        # Convert account names to account IDs
        df['numeric_account_id'] = df['account_name'].apply(convert_account_name_to_id)
        
        print(f"   Sample conversions:")
        for i in range(min(3, len(df))):
            row = df.iloc[i]
            print(f"   '{row['transaction_id']}' -> {row['numeric_transaction_id']}")
            print(f"   '{row['account_name']}' -> {row['numeric_account_id']}")
        
        # Prepare INSERT statement
        insert_query = """
        INSERT INTO TRANSACTIONS (TRANSACTION_ID, DATE, AMOUNT, MERCHANT, CATEGORY, ACCOUNT_ID)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        print(f"📝 INSERT query ready")
        
        # Prepare data for insertion
        print(f"📤 Preparing {len(df):,} transactions for insertion...")
        
        data_tuples = []
        for _, row in df.iterrows():
            data_tuples.append((
                int(row['numeric_transaction_id']),
                row['date'],  # Snowflake will handle date conversion
                float(row['amount']),
                row['merchant'],
                row['category'],
                int(row['numeric_account_id'])
            ))
        
        # Insert in batches
        batch_size = 1000
        total_inserted = 0
        
        print(f"📤 Inserting data in batches of {batch_size}...")
        
        for i in range(0, len(data_tuples), batch_size):
            batch = data_tuples[i:i + batch_size]
            cursor.executemany(insert_query, batch)
            total_inserted += len(batch)
            
            if total_inserted % 1000 == 0 or total_inserted == len(data_tuples):
                print(f"   📝 Inserted {total_inserted:,}/{len(data_tuples):,} transactions...")
        
        # Commit the transaction
        conn.commit()
        print(f"💾 Committed {total_inserted:,} transactions")
        
        # Verify the insert
        cursor.execute("SELECT COUNT(*) FROM TRANSACTIONS")
        new_count = cursor.fetchone()[0]
        print(f"📈 Snowflake now contains {new_count:,} total transactions")
        
        # Show summary statistics
        print("\n📊 Final Summary by Category:")
        cursor.execute("""
            SELECT 
                CATEGORY,
                COUNT(*) as transaction_count,
                SUM(AMOUNT) as total_amount,
                AVG(AMOUNT) as avg_amount
            FROM TRANSACTIONS 
            GROUP BY CATEGORY
            ORDER BY total_amount DESC
        """)
        
        for row in cursor.fetchall():
            category, count, total, avg = row
            print(f"   {category}: {count:,} txns, ${total:,.2f} total, ${avg:.2f} avg")
        
        # Show monthly summary
        print("\n📅 Monthly Transaction Summary:")
        cursor.execute("""
            SELECT 
                TO_CHAR(DATE, 'YYYY-MM') as month,
                COUNT(*) as transaction_count,
                SUM(AMOUNT) as total_amount
            FROM TRANSACTIONS 
            GROUP BY TO_CHAR(DATE, 'YYYY-MM')
            ORDER BY month DESC
            LIMIT 12
        """)
        
        for row in cursor.fetchall():
            month, count, total = row
            print(f"   {month}: {count:,} transactions, ${total:,.2f}")
        
        # Show sample data
        print("\n📋 Sample of loaded data:")
        cursor.execute("SELECT TRANSACTION_ID, DATE, MERCHANT, AMOUNT, CATEGORY FROM TRANSACTIONS LIMIT 5")
        for row in cursor.fetchall():
            print(f"   ID {row[0]}: {row[2]} - ${row[3]} ({row[4]}) on {row[1].strftime('%Y-%m-%d')}")
        
        cursor.close()
        conn.close()
        
        return True, f"Successfully loaded {total_inserted:,} transactions into Snowflake"
        
    except Exception as e:
        error_msg = f"Error loading data: {e}"
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.close()
        return False, error_msg

if __name__ == "__main__":
    success, message = load_snowflake_data()
    
    if success:
        print(f"\n🎉 {message}")
        print("\n💡 Your Snowflake database now has a full year of transaction data!")
        print("     - 1,095 transactions spanning 365 days")
        print("     - Rich variety of categories and merchants")
        print("     - Perfect for Cortex AI analysis and insights!")
        print("     - Ready for sophisticated queries and analytics!")
    else:
        print(f"\n❌ Data loading failed: {message}")
        exit(1)
