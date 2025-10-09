#!/usr/bin/env python3
"""
Debug what the Streamlit analysis actually finds
"""

from db_utils import TransactionManager

print('🔍 Debugging Streamlit AI Analysis Logic...')

try:
    # Get pending transactions (same as Streamlit does)
    pending_transactions = TransactionManager.get_pending_transactions()
    print(f'Found {len(pending_transactions)} pending transactions:')
    
    for txn in pending_transactions:
        print(f'  ID {txn["transaction_id"]}: {txn["merchant"]} ${txn["amount"]} - {txn["status"]}')
    
    # Apply the same AI analysis logic as Streamlit
    high_amount_transactions = [t for t in pending_transactions if float(t['amount']) > 200]
    unusual_merchants = [t for t in pending_transactions if any(word in t['merchant'].lower() 
                       for word in ['gadget', 'airlines', 'electronics', 'store', 'unknown', 'luxury'])]
    
    print(f'\\nAI Analysis Results:')
    print(f'High amount transactions (>$200): {len(high_amount_transactions)}')
    for txn in high_amount_transactions:
        print(f'  🚨 ID {txn["transaction_id"]}: {txn["merchant"]} ${txn["amount"]}')
    
    print(f'\\nUnusual merchants: {len(unusual_merchants)}')
    for txn in unusual_merchants:
        print(f'  🔍 ID {txn["transaction_id"]}: {txn["merchant"]} ${txn["amount"]}')
    
    # Test what would happen if we clicked cancel on the first high amount transaction
    if high_amount_transactions:
        test_txn = high_amount_transactions[0]
        print(f'\\n🧪 What would happen if we cancel ID {test_txn["transaction_id"]}:')
        print(f'   Merchant: {test_txn["merchant"]}')
        print(f'   Amount: ${test_txn["amount"]}')
        print(f'   Current Status: {test_txn["status"]}')
        print(f'   Button Key Would Be: cancel_high_{test_txn["transaction_id"]}')
        
        # Test the actual cancellation
        print(f'\\n🎯 Testing actual cancellation...')
        success, message = TransactionManager.cancel_transaction(test_txn["transaction_id"], "Debug test from script")
        print(f'   Result: success={success}')
        print(f'   Message: {message}')
    else:
        print('\\n❌ No high amount transactions found to test')
        
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
