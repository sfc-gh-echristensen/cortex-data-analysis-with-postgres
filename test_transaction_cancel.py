#!/usr/bin/env python3
"""
Direct test of the TransactionManager.cancel_transaction method
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db_utils import TransactionManager
import logging

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_transaction_cancellation():
    """Test the transaction cancellation directly"""
    print("🧪 Testing TransactionManager.cancel_transaction")
    print("=" * 50)
    
    try:
        # Get pending transactions
        print("1. Getting pending transactions...")
        pending = TransactionManager.get_pending_transactions()
        print(f"   Found {len(pending)} pending transactions")
        
        if not pending:
            print("   ❌ No pending transactions to test with")
            return
        
        # Show all pending transactions
        print("\n📋 Pending transactions:")
        for i, txn in enumerate(pending):
            print(f"   {i+1}. ID {txn['transaction_id']}: {txn['merchant']} ${txn['amount']} - {txn['status']}")
        
        # Test cancelling the first one
        test_txn = pending[0]
        test_id = test_txn['transaction_id']
        
        print(f"\n2. Testing cancellation of transaction {test_id}...")
        print(f"   Merchant: {test_txn['merchant']}")
        print(f"   Amount: ${test_txn['amount']}")
        print(f"   Current status: {test_txn['status']}")
        
        # Call the cancel_transaction method
        success, message = TransactionManager.cancel_transaction(test_id, "Direct test cancellation")
        
        print(f"\n3. Cancellation result:")
        print(f"   Success: {success}")
        print(f"   Message: {message}")
        
        # Verify the result by checking the transaction again
        print(f"\n4. Verifying cancellation...")
        updated_txn = TransactionManager.get_transaction_by_id(test_id)
        
        if updated_txn:
            print(f"   Transaction found:")
            print(f"   Status: {updated_txn['status']}")
            print(f"   Notes: {updated_txn['notes']}")
            
            if updated_txn['status'] == 'declined':
                print("   ✅ SUCCESS: Status was updated to 'declined'")
            else:
                print(f"   ❌ FAILURE: Status is still '{updated_txn['status']}'")
                
            if 'CANCELLED:' in str(updated_txn['notes']):
                print("   ✅ SUCCESS: Cancellation note was added")
            else:
                print("   ❌ FAILURE: No cancellation note found")
        else:
            print("   ❌ ERROR: Could not retrieve updated transaction")
        
        # Check pending transactions count after
        print(f"\n5. Final verification...")
        final_pending = TransactionManager.get_pending_transactions()
        print(f"   Pending transactions after cancellation: {len(final_pending)}")
        
        if len(final_pending) < len(pending):
            print("   ✅ SUCCESS: Pending transaction count decreased")
        else:
            print("   ❌ FAILURE: Pending transaction count unchanged")
        
    except Exception as e:
        print(f"❌ Exception during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_transaction_cancellation()
