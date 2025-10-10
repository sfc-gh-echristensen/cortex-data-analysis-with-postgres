#!/usr/bin/env python3
"""
Bulk insert search-optimized transaction data into PostgreSQL.

This loads the specially crafted transaction data designed to showcase
the differences between ILIKE, pg_trgm, and pgvector search capabilities.
"""

import pandas as pd
import sys
from db_utils import get_db_connection
from sqlalchemy import text

def load_search_data_csv(csv_file="search_optimized_transactions.csv"):
    """Load and insert search-optimized transaction data."""
    
    try:
        # Read CSV file
        print(f"Reading {csv_file}...")
        df = pd.read_csv(csv_file)
        print(f"Found {len(df)} transactions in CSV")
        
        # Display sample of data
        print("\nSample transactions:")
        print(df.head(10)[['merchant', 'description', 'amount', 'category']].to_string(index=False))
        
        # Connect to database and insert data
        print(f"\nConnecting to PostgreSQL...")
        with get_db_connection() as conn:
            
            # Check current transaction count
            result = conn.execute(text("SELECT COUNT(*) as count FROM transactions")).fetchone()
            existing_count = result.count
            print(f"Current transactions in database: {existing_count}")
            
            # Insert new transactions
            print(f"\nInserting {len(df)} search-optimized transactions...")
            
            inserted = 0
            for _, row in df.iterrows():
                try:
                    # Check if transaction already exists
                    existing = conn.execute(text("""
                        SELECT COUNT(*) as count 
                        FROM transactions 
                        WHERE transaction_id = :txn_id
                    """), {"txn_id": int(row['transaction_id'])}).fetchone()
                    
                    if existing.count == 0:
                        # Insert new transaction
                        # Combine merchant and description for richer search content
                        search_text = f"{row['merchant']} - {row['description']}"
                        
                        conn.execute(text("""
                            INSERT INTO transactions (
                                transaction_id, account_id, date, amount, 
                                merchant, category, status, notes
                            ) VALUES (
                                :transaction_id,
                                (SELECT account_id FROM accounts WHERE account_name = :account_name LIMIT 1),
                                :date,
                                :amount,
                                :merchant,
                                :category,
                                :status,
                                :notes
                            )
                        """), {
                            'transaction_id': int(row['transaction_id']),
                            'account_name': row['account_name'],
                            'date': row['date'],
                            'amount': float(row['amount']),
                            'merchant': search_text,  # Use combined text for richer search
                            'category': row['category'],
                            'status': row['status'],
                            'notes': f"Search demo: {row['description']}"
                        })
                        inserted += 1
                        
                        if inserted % 20 == 0:
                            print(f"  Inserted {inserted} transactions...")
                            
                except Exception as e:
                    print(f"  Error inserting transaction {row['transaction_id']}: {e}")
                    continue
            
            # Commit all changes
            conn.commit()
            
            # Verify final count
            result = conn.execute(text("SELECT COUNT(*) as count FROM transactions")).fetchone()
            final_count = result.count
            
            print(f"\n✅ Success!")
            print(f"  • Inserted: {inserted} new transactions")
            print(f"  • Skipped: {len(df) - inserted} existing transactions")
            print(f"  • Total in database: {final_count} transactions")
            
            # Show search-ready categories
            print(f"\n📊 Search Test Data Summary:")
            category_counts = conn.execute(text("""
                SELECT category, COUNT(*) as count
                FROM transactions 
                WHERE notes = 'Search demo data'
                GROUP BY category 
                ORDER BY count DESC
            """)).fetchall()
            
            for cat in category_counts:
                print(f"  • {cat.category}: {cat.count} transactions")
            
            print(f"\n🔍 Ready for search testing!")
            print(f"  Try searching for:")
            print(f"  • 'coffee' (ILIKE: exact matches)")
            print(f"  • 'cofee' (pg_trgm: handles typos)")
            print(f"  • 'morning drink' (pgvector: semantic)")
            print(f"  • 'starbucks' vs 'starbuks'")
            print(f"  • 'streaming' (finds Netflix, Spotify, etc.)")
            
    except FileNotFoundError:
        print(f"❌ Error: {csv_file} not found!")
        print("Run 'python3 generate_search_sample_data.py' first")
        return False
        
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return False
        
    return True

if __name__ == "__main__":
    csv_file = "search_optimized_transactions.csv"
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    
    print("🔍 PostgreSQL Search Demo - Data Loader")
    print("=" * 50)
    
    success = load_search_data_csv(csv_file)
    
    if success:
        print(f"\n🚀 Search demo data loaded successfully!")
        print(f"Visit your Streamlit app and try the 'Search Demo' section!")
    else:
        print(f"\n❌ Failed to load search demo data")
        sys.exit(1)
