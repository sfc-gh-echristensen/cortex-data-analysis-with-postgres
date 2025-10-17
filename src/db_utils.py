"""
Database utilities for PostgreSQL connection and transaction management.
Provides centralized database operations for the financial application.
"""

import os
import logging
from typing import Optional, Dict, Any, List, Tuple
from contextlib import contextmanager
from sqlalchemy import create_engine, text, Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
import streamlit as st

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create handlers if they don't exist
if not logger.handlers:
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # File handler
    file_handler = logging.FileHandler('db_operations.log')
    file_handler.setLevel(logging.DEBUG)
    
    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter) 
    file_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)


def get_postgres_config() -> Dict[str, Any]:
    """Get PostgreSQL configuration from Streamlit secrets or environment variables"""
    try:
        # Try Streamlit secrets first
        secrets_pg = st.secrets.get("postgres", {})
        return {
            "host": secrets_pg.get("host") or os.environ.get("PG_HOST"),
            "port": int(secrets_pg.get("port") or os.environ.get("PG_PORT", "5432")),
            "database": secrets_pg.get("database") or os.environ.get("PG_DB", "postgres"),
            "user": secrets_pg.get("user") or os.environ.get("PG_USER"),
            "password": secrets_pg.get("password") or os.environ.get("PG_PASSWORD"),
            "sslmode": secrets_pg.get("sslmode") or os.environ.get("PG_SSLMODE")
        }
    except:
        # Fall back to environment variables only
        return {
            "host": os.environ.get("PG_HOST"),
            "port": int(os.environ.get("PG_PORT", "5432")),
            "database": os.environ.get("PG_DB", "postgres"),
            "user": os.environ.get("PG_USER"),
            "password": os.environ.get("PG_PASSWORD"),
            "sslmode": os.environ.get("PG_SSLMODE")
        }


def create_postgres_engine() -> Engine:
    """Create a PostgreSQL engine using configuration"""
    config = get_postgres_config()
    
    if not all([config["host"], config["user"], config["password"], config["database"]]):
        raise ValueError("Missing required PostgreSQL connection parameters")
    
    # Build connection URL
    url = f"postgresql+psycopg2://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
    if config["sslmode"]:
        url = f"{url}?sslmode={config['sslmode']}"
    
    return create_engine(url, echo=False)


@contextmanager
def get_db_connection():
    """Context manager for database connections with automatic cleanup"""
    engine = None
    connection = None
    try:
        engine = create_postgres_engine()
        connection = engine.connect()
        yield connection
    except Exception as e:
        # Don't rollback here since we might not have an active transaction
        logger.error(f"Database connection error: {e}")
        raise e
    finally:
        if connection:
            connection.close()
        if engine:
            engine.dispose()


class TransactionManager:
    """Enhanced transaction management with proper PostgreSQL integration"""
    
    @staticmethod
    def get_pending_transactions() -> List[Dict[str, Any]]:
        """Fetch all pending transactions"""
        logger.info("📋 GET_PENDING_TRANSACTIONS: Starting to fetch pending transactions...")
        
        try:
            with get_db_connection() as conn:
                logger.debug("✅ Database connection established for pending transactions query")
                
                result = conn.execute(text("""
                    SELECT 
                        transaction_id, 
                        date, 
                        amount, 
                        merchant, 
                        category, 
                        notes, 
                        status,
                        account_id
                    FROM transactions 
                    WHERE status = 'pending' 
                    ORDER BY date DESC
                """))
                
                transactions = [dict(row._mapping) for row in result]
                logger.info(f"📊 Found {len(transactions)} pending transactions")
                
                for txn in transactions:
                    logger.debug(f"   - ID {txn['transaction_id']}: {txn['merchant']} ${txn['amount']} ({txn['status']})")
                
                return transactions
                
        except SQLAlchemyError as e:
            error_msg = f"Database error fetching pending transactions: {e}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Error fetching pending transactions: {e}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            raise Exception(error_msg)
    
    @staticmethod
    def get_transaction_by_id(transaction_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific transaction by ID"""
        try:
            with get_db_connection() as conn:
                result = conn.execute(text("""
                    SELECT 
                        t.transaction_id, 
                        t.date, 
                        t.amount, 
                        t.merchant, 
                        t.category, 
                        t.notes, 
                        t.status,
                        t.account_id,
                        a.account_name
                    FROM transactions t
                    JOIN accounts a ON t.account_id = a.account_id
                    WHERE t.transaction_id = :txn_id
                """), {"txn_id": transaction_id})
                
                row = result.fetchone()
                return dict(row._mapping) if row else None
        except SQLAlchemyError as e:
            raise Exception(f"Database error fetching transaction {transaction_id}: {e}")
        except Exception as e:
            raise Exception(f"Error fetching transaction {transaction_id}: {e}")
    
    @staticmethod
    def cancel_transaction(transaction_id: int, reason: str = "Cancelled by system") -> Tuple[bool, str]:
        """
        Cancel a pending transaction by updating its status to 'declined'
        
        Args:
            transaction_id: ID of the transaction to cancel
            reason: Reason for cancellation
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        logger.info(f"🎯 CANCEL_TRANSACTION: Starting cancellation for transaction {transaction_id}")
        logger.info(f"   Reason: {reason}")
        
        try:
            logger.debug(f"Creating database connection...")
            with get_db_connection() as conn:
                logger.debug(f"✅ Database connection established")
                
                # SQLAlchemy 2.x uses autobegin - no need to call begin() explicitly
                logger.debug(f"Using SQLAlchemy autobegin transaction...")
                
                try:
                    # First, check if transaction exists and is pending
                    logger.debug(f"Checking if transaction {transaction_id} exists and is pending...")
                    check_result = conn.execute(text("""
                        SELECT transaction_id, status, merchant, amount, notes
                        FROM transactions 
                        WHERE transaction_id = :txn_id
                    """), {"txn_id": transaction_id})
                    
                    transaction_row = check_result.fetchone()
                    logger.debug(f"Query result: {dict(transaction_row._mapping) if transaction_row else 'None'}")
                    
                    if not transaction_row:
                        logger.warning(f"❌ Transaction {transaction_id} not found in database")
                        conn.rollback()
                        return False, f"Transaction {transaction_id} not found"
                    
                    logger.info(f"📊 Found transaction: {transaction_row.merchant} ${transaction_row.amount} (status: {transaction_row.status})")
                    
                    if transaction_row.status != 'pending':
                        logger.warning(f"❌ Transaction {transaction_id} has status '{transaction_row.status}', cannot cancel")
                        conn.rollback()
                        return False, f"Transaction {transaction_id} is already {transaction_row.status} and cannot be cancelled"
                    
                    # Update the transaction status (simplified approach)
                    logger.info(f"🔄 Updating transaction {transaction_id} status to 'declined'...")
                    cancel_reason = f"CANCELLED: {reason}"
                    logger.debug(f"Adding cancellation reason: {cancel_reason}")
                    
                    # First, update just the status (simplified - no casting)
                    status_result = conn.execute(text("""
                        UPDATE transactions 
                        SET status = 'declined'
                        WHERE transaction_id = :txn_id AND status = 'pending'
                    """), {"txn_id": transaction_id})
                    
                    status_rows = status_result.rowcount
                    logger.info(f"📈 Status update affected {status_rows} rows")
                    
                    # Then, update the notes separately
                    notes_result = conn.execute(text("""
                        UPDATE transactions 
                        SET notes = COALESCE(notes, '') || :reason
                        WHERE transaction_id = :txn_id
                    """), {"txn_id": transaction_id, "reason": f"\n{cancel_reason}"})
                    
                    notes_rows = notes_result.rowcount
                    logger.info(f"📈 Notes update affected {notes_rows} rows")
                    
                    rows_affected = max(status_rows, notes_rows)  # Use the higher count
                    
                    if rows_affected > 0:
                        logger.info(f"💾 Committing transaction...")
                        conn.commit()
                        logger.info(f"✅ TRANSACTION SUCCESSFULLY CANCELLED!")
                        
                        # Verify the update
                        logger.debug(f"Verifying the cancellation...")
                        verify_result = conn.execute(text("""
                            SELECT transaction_id, status, notes
                            FROM transactions 
                            WHERE transaction_id = :txn_id
                        """), {"txn_id": transaction_id})
                        
                        verified_row = verify_result.fetchone()
                        if verified_row:
                            logger.info(f"✅ Verification: Transaction {transaction_id} now has status '{verified_row.status}'")
                            logger.debug(f"   Updated notes: {verified_row.notes}")
                        else:
                            logger.error(f"❌ Verification failed: Could not find transaction {transaction_id} after update")
                        
                        success_msg = f"Transaction {transaction_id} ({transaction_row.merchant}: ${transaction_row.amount}) successfully cancelled"
                        logger.info(f"🎉 {success_msg}")
                        return True, success_msg
                    else:
                        logger.error(f"❌ Update query affected 0 rows - rollback")
                        conn.rollback()
                        return False, f"Failed to cancel transaction {transaction_id} - no rows updated"
                        
                except Exception as e:
                    logger.error(f"❌ Exception during cancellation: {e}", exc_info=True)
                    logger.info(f"🔄 Rolling back transaction...")
                    conn.rollback()
                    raise e
                    
        except SQLAlchemyError as e:
            error_msg = f"Database error cancelling transaction: {e}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            return False, error_msg
        except Exception as e:
            error_msg = f"Error cancelling transaction: {e}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            return False, error_msg
    
    @staticmethod 
    def approve_transaction(transaction_id: int, reason: str = "Approved by system") -> Tuple[bool, str]:
        """
        Approve a pending transaction by updating its status to 'approved'
        
        Args:
            transaction_id: ID of the transaction to approve
            reason: Reason for approval
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            with get_db_connection() as conn:
                trans = conn.begin()
                
                try:
                    # Update the transaction status
                    result = conn.execute(text("""
                        UPDATE transactions 
                        SET 
                            status = 'approved', 
                            notes = COALESCE(notes, '') || 
                                    CASE WHEN COALESCE(notes, '') = '' THEN :reason 
                                         ELSE E'\n' || :reason END
                        WHERE transaction_id = :txn_id AND status = 'pending'
                    """), {"txn_id": transaction_id, "reason": f"APPROVED: {reason}"})
                    
                    if result.rowcount > 0:
                        trans.commit()
                        return True, f"Transaction {transaction_id} successfully approved"
                    else:
                        trans.rollback()
                        return False, f"Transaction {transaction_id} not found or already processed"
                        
                except Exception as e:
                    trans.rollback()
                    raise e
                    
        except SQLAlchemyError as e:
            return False, f"Database error approving transaction: {e}"
        except Exception as e:
            return False, f"Error approving transaction: {e}"
    
    @staticmethod
    def get_transaction_stats() -> Dict[str, Any]:
        """Get transaction statistics by status"""
        try:
            with get_db_connection() as conn:
                result = conn.execute(text("""
                    SELECT 
                        status,
                        COUNT(*) as count,
                        SUM(amount) as total_amount,
                        AVG(amount) as avg_amount
                    FROM transactions 
                    GROUP BY status
                    ORDER BY count DESC
                """))
                
                stats = {}
                for row in result:
                    stats[row.status] = {
                        "count": row.count,
                        "total_amount": float(row.total_amount) if row.total_amount else 0,
                        "avg_amount": float(row.avg_amount) if row.avg_amount else 0
                    }
                
                return stats
                
        except SQLAlchemyError as e:
            raise Exception(f"Database error fetching transaction stats: {e}")
        except Exception as e:
            raise Exception(f"Error fetching transaction stats: {e}")


def test_connection() -> Tuple[bool, str]:
    """Test PostgreSQL connection"""
    try:
        with get_db_connection() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            return True, f"Connected successfully to PostgreSQL: {version[:50]}..."
    except Exception as e:
        return False, f"Connection failed: {e}"


def ensure_status_column_exists() -> Tuple[bool, str]:
    """Ensure the status column exists in the transactions table"""
    try:
        with get_db_connection() as conn:
            # Check if status column exists
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'transactions' AND column_name = 'status'
            """))
            
            if result.fetchone():
                return True, "Status column already exists"
            else:
                return False, "Status column does not exist - run migrate_add_status.py"
                
    except Exception as e:
        return False, f"Error checking status column: {e}"
