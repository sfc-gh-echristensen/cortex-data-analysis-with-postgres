#!/usr/bin/env python3
"""
Test what happens when we simulate button clicks from the Streamlit UI
"""

import streamlit as st
from db_utils import TransactionManager

def main():
    st.title("🧪 Button Test for Transaction Management")
    
    # Get pending transactions
    try:
        pending_transactions = TransactionManager.get_pending_transactions()
        st.write(f"Found {len(pending_transactions)} pending transactions")
        
        if pending_transactions:
            # Show the transactions
            for txn in pending_transactions:
                st.write(f"ID {txn['transaction_id']}: {txn['merchant']} ${txn['amount']} - {txn['status']}")
            
            # Create a simple test button for the first transaction
            test_txn = pending_transactions[0]
            st.write(f"\\n**Testing with: ID {test_txn['transaction_id']} - {test_txn['merchant']}**")
            
            if st.button(f"🧪 Test Cancel Transaction {test_txn['transaction_id']}", key="test_cancel"):
                st.info(f"Button clicked for transaction {test_txn['transaction_id']}!")
                
                with st.spinner("Testing cancellation..."):
                    try:
                        success, message = TransactionManager.cancel_transaction(
                            test_txn['transaction_id'], 
                            "Streamlit button test"
                        )
                        
                        if success:
                            st.success(f"✅ SUCCESS: {message}")
                            st.balloons()
                        else:
                            st.error(f"❌ FAILED: {message}")
                            
                    except Exception as e:
                        st.error(f"❌ EXCEPTION: {e}")
                        st.code(str(e))
            
            # Show current count
            st.write(f"\\n**Current pending count: {len(pending_transactions)}**")
            
            # Add refresh button
            if st.button("🔄 Refresh to see changes"):
                st.rerun()
        else:
            st.info("No pending transactions found")
            
    except Exception as e:
        st.error(f"Error loading transactions: {e}")

if __name__ == "__main__":
    main()
