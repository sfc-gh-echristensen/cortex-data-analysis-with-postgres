#!/usr/bin/env python3
"""
Test script specifically for the Gadget Store transaction issue.
"""

import logging
from db_utils import TransactionManager, get_db_connection
from sqlalchemy import text

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_gadget_store_transaction():
    """Test the specific Gadget Store transaction"""
    logger.info("🔍 Testing Gadget Store transaction specifically...")
    
    try:
        # First, let's see the current state of all Gadget Store transactions
        with get_db_connection() as conn:
            result = conn.execute(text("""
                SELECT transaction_id, merchant, amount, status, notes, date
                FROM transactions 
                WHERE LOWER(merchant) LIKE '%gadget%'
                ORDER BY transaction_id
            """))
            
            gadget_transactions = result.fetchall()
            
            if not gadget_transactions:
                logger.warning("❌ No Gadget Store transactions found!")
                return
            
            logger.info(f"📊 Found {len(gadget_transactions)} Gadget Store transactions:")
            for txn in gadget_transactions:
                logger.info(f"   ID {txn.transaction_id}: {txn.merchant} ${txn.amount} - {txn.status}")
                logger.info(f"      Date: {txn.date}")
                if txn.notes:
                    logger.info(f"      Notes: {txn.notes}")
                logger.info("")
            
            # Find the pending one
            pending_gadget = [txn for txn in gadget_transactions if txn.status == 'pending']
            
            if not pending_gadget:
                logger.warning("⚠️ No pending Gadget Store transactions found")
                logger.info("All gadget transactions have already been processed")
                return
            
            # Test cancelling the pending Gadget Store transaction
            test_txn = pending_gadget[0]
            logger.info(f"🎯 Testing cancellation of Gadget Store transaction {test_txn.transaction_id}")
            
            success, message = TransactionManager.cancel_transaction(
                test_txn.transaction_id, 
                "Test cancellation from debug script"
            )
            
            logger.info(f"Cancellation result: success={success}")
            logger.info(f"Message: {message}")
            
            # Verify the result
            result = conn.execute(text("""
                SELECT transaction_id, merchant, amount, status, notes
                FROM transactions 
                WHERE transaction_id = :txn_id
            """), {"txn_id": test_txn.transaction_id})
            
            updated_txn = result.fetchone()
            logger.info(f"✅ After cancellation - Status: {updated_txn.status}")
            logger.info(f"   Notes: {updated_txn.notes}")
            
            if updated_txn.status == 'declined':
                logger.info("🎉 SUCCESS: Gadget Store transaction was successfully cancelled!")
            else:
                logger.error(f"❌ FAILED: Transaction status is still '{updated_txn.status}'")
    
    except Exception as e:
        logger.error(f"❌ Error testing Gadget Store transaction: {e}", exc_info=True)

def show_all_pending_transactions():
    """Show all current pending transactions"""
    logger.info("📋 Current pending transactions:")
    
    try:
        pending = TransactionManager.get_pending_transactions()
        
        if not pending:
            logger.info("   No pending transactions found")
            return
        
        for txn in pending:
            logger.info(f"   ID {txn['transaction_id']}: {txn['merchant']} ${txn['amount']}")
            logger.info(f"      Status: {txn['status']}")
            logger.info(f"      Date: {txn['date']}")
            if txn['notes']:
                logger.info(f"      Notes: {txn['notes']}")
            logger.info("")
    
    except Exception as e:
        logger.error(f"❌ Error fetching pending transactions: {e}")

if __name__ == "__main__":
    logger.info("🚀 Testing Gadget Store Transaction Management")
    logger.info("=" * 50)
    
    # Show current pending transactions
    show_all_pending_transactions()
    
    # Test the gadget store transaction specifically
    test_gadget_store_transaction()
    
    # Show pending transactions after test
    logger.info("\n" + "=" * 50)
    logger.info("After cancellation test:")
    show_all_pending_transactions()
