#!/usr/bin/env python3
"""
Migration script to add the status column to the transactions table.
Run this script after updating your models to ensure existing transactions have the status column.
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
import streamlit as st

def get_postgres_engine():
    """Get PostgreSQL engine from environment or Streamlit secrets"""
    try:
        # Try to get from Streamlit secrets first
        secrets_pg = st.secrets.get("postgres", {})
        host = secrets_pg.get("host") or os.environ.get("PG_HOST")
        port = secrets_pg.get("port") or os.environ.get("PG_PORT", "5432")
        database = secrets_pg.get("database") or os.environ.get("PG_DB", "postgres")
        user = secrets_pg.get("user") or os.environ.get("PG_USER")
        password = secrets_pg.get("password") or os.environ.get("PG_PASSWORD")
        sslmode = secrets_pg.get("sslmode") or os.environ.get("PG_SSLMODE")
    except:
        # Fall back to environment variables if Streamlit not available
        host = os.environ.get("PG_HOST")
        port = os.environ.get("PG_PORT", "5432")
        database = os.environ.get("PG_DB", "postgres")
        user = os.environ.get("PG_USER")
        password = os.environ.get("PG_PASSWORD")
        sslmode = os.environ.get("PG_SSLMODE")
    
    if not all([host, user, password, database]):
        raise ValueError("Missing required PostgreSQL connection parameters")
    
    # Build connection URL
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"
    if sslmode:
        url = f"{url}?sslmode={sslmode}"
    
    return create_engine(url, echo=True)

def add_status_column():
    """Add status column to transactions table if it doesn't exist"""
    engine = get_postgres_engine()
    
    with engine.connect() as conn:
        # Start a transaction
        trans = conn.begin()
        try:
            # Check if status column already exists
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'transactions' AND column_name = 'status'
            """))
            
            if result.fetchone():
                print("✅ Status column already exists in transactions table")
                trans.rollback()
                return
            
            print("📝 Adding status column to transactions table...")
            
            # Add status column with default value
            conn.execute(text("""
                ALTER TABLE transactions 
                ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'pending'
            """))
            
            # Add comment for documentation
            conn.execute(text("""
                COMMENT ON COLUMN transactions.status IS 'Transaction status: pending, approved, declined, cancelled'
            """))
            
            # Update existing transactions to have appropriate status
            # You might want to set different default statuses based on your business logic
            print("📝 Setting default status for existing transactions...")
            
            # Set older transactions to 'approved' (assuming they're completed)
            # and recent ones to 'pending' - adjust this logic as needed
            conn.execute(text("""
                UPDATE transactions 
                SET status = CASE 
                    WHEN date < NOW() - INTERVAL '7 days' THEN 'approved'
                    ELSE 'pending'
                END
            """))
            
            trans.commit()
            print("✅ Successfully added status column and updated existing transactions!")
            
        except Exception as e:
            trans.rollback()
            print(f"❌ Error adding status column: {e}")
            raise

def verify_migration():
    """Verify that the migration was successful"""
    engine = get_postgres_engine()
    
    with engine.connect() as conn:
        # Check column exists and has expected data
        result = conn.execute(text("""
            SELECT 
                COUNT(*) as total_transactions,
                COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_count,
                COUNT(CASE WHEN status = 'approved' THEN 1 END) as approved_count,
                COUNT(CASE WHEN status = 'declined' THEN 1 END) as declined_count
            FROM transactions
        """))
        
        row = result.fetchone()
        print(f"\n📊 Migration Verification:")
        print(f"   Total transactions: {row[0]}")
        print(f"   Pending: {row[1]}")
        print(f"   Approved: {row[2]}")
        print(f"   Declined: {row[3]}")
        print("✅ Migration verification complete!")

if __name__ == "__main__":
    print("🚀 Starting transaction status column migration...")
    print("=" * 50)
    
    try:
        add_status_column()
        verify_migration()
        print("\n🎉 Migration completed successfully!")
        print("\nYou can now:")
        print("1. Run your Streamlit app")
        print("2. Use the transaction cancellation features")
        print("3. View pending transactions by status")
        
    except Exception as e:
        print(f"\n💥 Migration failed: {e}")
        print("\nPlease check:")
        print("1. PostgreSQL connection settings")
        print("2. Database permissions")
        print("3. Table exists and is accessible")
        exit(1)
