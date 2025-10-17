#!/usr/bin/env python3
"""
Script to safely reset test transactions back to pending status.
"""

import logging
from db_utils import get_db_connection
from sqlalchemy import text

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def show_current_status():
    """Show current transaction status distribution"""
    logger.info("📊 Current transaction status distribution:")
    
    try:
        with get_db_connection() as conn:
            result = conn.execute(text("""
                SELECT 
                    status, 
                    COUNT(*) as count, 
                    SUM(amount) as total_amount,
                    ROUND(AVG(amount), 2) as avg_amount
                FROM transactions 
                GROUP BY status 
                ORDER BY count DESC
            """))
            
            for row in result:
                logger.info(f"  {row.status}: {row.count} transactions, ${row.total_amount:.2f} total, ${row.avg_amount:.2f} avg")
    
    except Exception as e:
        logger.error(f"❌ Error showing status: {e}")

def reset_test_transactions():
    """Reset transactions that appear to be test data back to pending"""
    logger.info("🔄 Resetting test transactions to pending status...")
    
    try:
        with get_db_connection() as conn:
            trans = conn.begin()
            
            try:
                # First, show what will be affected
                preview_result = conn.execute(text("""
                    SELECT 
                        transaction_id,
                        merchant,
                        amount,
                        status,
                        notes
                    FROM transactions 
                    WHERE 
                        status IN ('declined', 'cancelled')
                        AND (
                            LOWER(notes) LIKE '%test%' 
                            OR LOWER(notes) LIKE '%debug%'
                            OR LOWER(notes) LIKE '%cancelled:%'
                            OR LOWER(merchant) LIKE '%test%'
                            OR LOWER(merchant) LIKE '%debug%'
                            OR LOWER(merchant) LIKE '%gadget%'
                            OR LOWER(merchant) LIKE '%airlines%'
                            OR LOWER(merchant) = 'raw sql test'
                        )
                """))
                
                transactions_to_reset = preview_result.fetchall()
                
                if not transactions_to_reset:
                    logger.info("ℹ️ No test transactions found to reset")
                    trans.rollback()
                    return
                
                logger.info(f"📋 Found {len(transactions_to_reset)} test transactions to reset:")
                for txn in transactions_to_reset:
                    logger.info(f"  ID {txn.transaction_id}: {txn.merchant} ${txn.amount} ({txn.status})")
                
                # Ask for confirmation
                response = input(f"\n❓ Reset these {len(transactions_to_reset)} transactions to pending? (y/N): ")
                if not response.lower().startswith('y'):
                    logger.info("❌ Reset cancelled by user")
                    trans.rollback()
                    return
                
                # Perform the reset
                reset_result = conn.execute(text("""
                    UPDATE transactions 
                    SET 
                        status = 'pending',
                        notes = REGEXP_REPLACE(notes, E'\\nCANCELLED:.*$', '', 'g')
                    WHERE 
                        status IN ('declined', 'cancelled')
                        AND (
                            LOWER(notes) LIKE '%test%' 
                            OR LOWER(notes) LIKE '%debug%'
                            OR LOWER(notes) LIKE '%cancelled:%'
                            OR LOWER(merchant) LIKE '%test%'
                            OR LOWER(merchant) LIKE '%debug%'
                            OR LOWER(merchant) LIKE '%gadget%'
                            OR LOWER(merchant) LIKE '%airlines%'
                            OR LOWER(merchant) = 'raw sql test'
                        )
                """))
                
                rows_updated = reset_result.rowcount
                trans.commit()
                
                logger.info(f"✅ Successfully reset {rows_updated} transactions to pending status")
                
            except Exception as e:
                trans.rollback()
                raise e
    
    except Exception as e:
        logger.error(f"❌ Error resetting transactions: {e}")

def reset_specific_merchants():
    """Reset specific merchant transactions to pending"""
    merchants_to_reset = [
        'Gadget Store',
        'Debug Gadget Store', 
        'Luxury Electronics Store',
        'Unknown Merchant XYZ',
        'Raw SQL Test',
        'Major Airlines'
    ]
    
    logger.info("🎯 Resetting specific merchant transactions to pending...")
    
    try:
        with get_db_connection() as conn:
            trans = conn.begin()
            
            try:
                # Build the merchant list for SQL
                merchant_placeholders = ','.join([f':merchant_{i}' for i in range(len(merchants_to_reset))])
                merchant_params = {f'merchant_{i}': merchant for i, merchant in enumerate(merchants_to_reset)}
                
                # Preview what will be reset
                preview_result = conn.execute(text(f"""
                    SELECT 
                        transaction_id,
                        merchant,
                        amount,
                        status
                    FROM transactions 
                    WHERE 
                        status IN ('declined', 'cancelled')
                        AND merchant IN ({merchant_placeholders})
                """), merchant_params)
                
                transactions_to_reset = preview_result.fetchall()
                
                if not transactions_to_reset:
                    logger.info("ℹ️ No matching merchant transactions found to reset")
                    trans.rollback()
                    return
                
                logger.info(f"📋 Found {len(transactions_to_reset)} merchant transactions to reset:")
                for txn in transactions_to_reset:
                    logger.info(f"  ID {txn.transaction_id}: {txn.merchant} ${txn.amount} ({txn.status})")
                
                # Perform the reset
                reset_result = conn.execute(text(f"""
                    UPDATE transactions 
                    SET 
                        status = 'pending',
                        notes = REGEXP_REPLACE(notes, E'\\nCANCELLED:.*$', '', 'g')
                    WHERE 
                        status IN ('declined', 'cancelled')
                        AND merchant IN ({merchant_placeholders})
                """), merchant_params)
                
                rows_updated = reset_result.rowcount
                trans.commit()
                
                logger.info(f"✅ Successfully reset {rows_updated} merchant transactions to pending status")
                
            except Exception as e:
                trans.rollback()
                raise e
    
    except Exception as e:
        logger.error(f"❌ Error resetting merchant transactions: {e}")

def main():
    """Main function with user options"""
    logger.info("🚀 Transaction Reset Utility")
    logger.info("=" * 40)
    
    # Show current status
    show_current_status()
    
    print("\nReset Options:")
    print("1. Reset test transactions (safest - looks for test/debug keywords)")
    print("2. Reset specific merchants (Gadget Store, Airlines, etc.)")
    print("3. Show current status only")
    print("4. Exit")
    
    choice = input("\nSelect an option (1-4): ").strip()
    
    if choice == '1':
        reset_test_transactions()
    elif choice == '2':
        reset_specific_merchants()
    elif choice == '3':
        pass  # Already showed status above
    elif choice == '4':
        logger.info("👋 Exiting without changes")
        return
    else:
        logger.error("❌ Invalid choice")
        return
    
    # Show status after reset
    print("\n" + "=" * 40)
    logger.info("📊 Status after reset:")
    show_current_status()

if __name__ == "__main__":
    main()
