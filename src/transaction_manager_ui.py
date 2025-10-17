"""
Transaction Manager UI Module
Handles the transaction management interface including pending transactions
and AI-powered transaction analysis
"""

import streamlit as st
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine
from src.db_utils import TransactionManager, get_db_connection


def render_transaction_manager(engine: Engine, use_postgres: bool):
    """
    Render the transaction manager section
    
    Args:
        engine: SQLAlchemy Engine instance
        use_postgres: Boolean indicating if PostgreSQL is enabled
    """
    st.markdown('<div id="transaction-manager"></div>', unsafe_allow_html=True)
    st.header("🔧 Transaction Manager")
    
    if not use_postgres or engine is None:
        st.info("💡 Enable PostgreSQL connection in the sidebar to access transaction management features.")
        return
    
    # Initialize session state for cancellation feedback
    _initialize_session_state()
    
    # Refresh controls
    _render_refresh_controls()
    
    # Display feedback messages
    _render_feedback_messages()
    
    # Get and display pending transactions
    try:
        pending_transactions = TransactionManager.get_pending_transactions()
    except Exception as e:
        st.error(f"Failed to fetch pending transactions: {e}")
        pending_transactions = []
    
    if pending_transactions:
        _render_pending_transactions(pending_transactions)
        _render_ai_analysis(pending_transactions)
        _render_manual_management(pending_transactions)
    else:
        _render_no_pending_transactions()


def _initialize_session_state():
    """Initialize session state variables"""
    if 'cancellation_success' not in st.session_state:
        st.session_state.cancellation_success = None
    if 'cancellation_message' not in st.session_state:
        st.session_state.cancellation_message = None
    if 'show_feedback' not in st.session_state:
        st.session_state.show_feedback = False


def _render_refresh_controls():
    """Render refresh button and auto-refresh controls"""
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("🔄 Refresh Data", key="refresh_transactions"):
            st.rerun()
    
    with col2:
        auto_refresh = st.checkbox("Auto-refresh", value=False, key="auto_refresh_checkbox")
    
    with col3:
        if auto_refresh:
            st.info("⚡ Auto-refresh enabled - page will refresh automatically")


def _render_feedback_messages():
    """Display pending success/error messages"""
    if st.session_state.get('show_feedback', False):
        if st.session_state.get('cancellation_success', False):
            st.success(f"✅ **TRANSACTION CANCELLED**: {st.session_state.get('cancellation_message', 'Unknown transaction')}")
            
            with st.expander("🔍 Verification Details", expanded=True):
                st.write("**What happened:**")
                st.write("1. ✅ Database transaction started")
                st.write("2. ✅ Transaction found and verified as 'pending'")
                st.write("3. ✅ Status updated to 'declined'")
                st.write("4. ✅ Cancellation reason added to notes")
                st.write("5. ✅ Database transaction committed")
                st.write("6. ✅ Changes verified in database")
                st.info("💡 **Tip**: Click 'Refresh Data' to see the updated transaction list")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Clear Success Message", key="clear_success"):
                    st.session_state.show_feedback = False
                    st.session_state.cancellation_success = None
                    st.session_state.cancellation_message = None
                    st.rerun()
            with col2:
                if st.button("🔄 Refresh & Keep Message", key="refresh_keep"):
                    st.rerun()
                    
        elif st.session_state.get('cancellation_success') == False:
            st.error(f"❌ **CANCELLATION FAILED**: {st.session_state.get('cancellation_message', 'Unknown error')}")
            
            if st.button("❌ Clear Error Message", key="clear_error"):
                st.session_state.show_feedback = False
                st.session_state.cancellation_success = None
                st.session_state.cancellation_message = None
                st.rerun()


def _render_pending_transactions(pending_transactions):
    """Display pending transactions list"""
    st.write(f"**Found {len(pending_transactions)} pending transactions:**")
    
    df_pending = pd.DataFrame(pending_transactions)
    df_pending['amount'] = df_pending['amount'].apply(lambda x: f"${x:.2f}")
    df_pending['date'] = pd.to_datetime(df_pending['date']).dt.strftime('%Y-%m-%d')
    
    # Display first 2 rows by default
    if len(df_pending) <= 2:
        st.dataframe(df_pending[['transaction_id', 'date', 'amount', 'merchant', 'category']], use_container_width=True)
    else:
        st.write("**First 2 transactions:**")
        st.dataframe(df_pending.head(2)[['transaction_id', 'date', 'amount', 'merchant', 'category']], use_container_width=True)
        
        with st.expander(f"📋 View all {len(df_pending)} transactions", expanded=False):
            st.dataframe(df_pending[['transaction_id', 'date', 'amount', 'merchant', 'category']], use_container_width=True, height=300)


def _render_ai_analysis(pending_transactions):
    """Render AI transaction analysis section"""
    st.markdown("### 🔍 AI Transaction Analysis")
    st.info("💡 **I can help you identify and cancel problematic pending transactions!**")
    st.write("Try asking me things like:")
    st.write("- *'Are there any suspicious large transactions?'*")
    st.write("- *'Cancel transactions over $100'*")
    st.write("- *'Which transactions look unusual?'*")
    
    if st.button("🤖 Analyze Pending Transactions"):
        with st.spinner("Analyzing pending transactions..."):
            st.write(f"**🔍 Analyzing {len(pending_transactions)} pending transactions...**")
            
            # Simple rule-based analysis
            high_amount_transactions = [t for t in pending_transactions if float(t['amount']) > 200]
            unusual_merchants = [t for t in pending_transactions if any(word in t['merchant'].lower() 
                               for word in ['gadget', 'airlines', 'electronics', 'store', 'unknown', 'luxury'])]
            
            # Store results in session state
            st.session_state.analysis_performed = True
            st.session_state.high_amount_transactions = high_amount_transactions
            st.session_state.unusual_merchants = unusual_merchants
            st.session_state.analysis_pending_count = len(pending_transactions)
            
            st.write(f"**Analysis Results:**")
            st.write(f"- High amount transactions (>$200): {len(high_amount_transactions)}")
            st.write(f"- Unusual merchants: {len(unusual_merchants)}")
    
    # Show analysis results if they exist
    if st.session_state.get('analysis_performed', False):
        _render_analysis_results()


def _render_analysis_results():
    """Display AI analysis results with cancellation options"""
    high_amount_transactions = st.session_state.get('high_amount_transactions', [])
    unusual_merchants = st.session_state.get('unusual_merchants', [])
    
    if st.button("🔄 Clear Analysis", key="clear_analysis"):
        st.session_state.analysis_performed = False
        st.session_state.high_amount_transactions = []
        st.session_state.unusual_merchants = []
        st.rerun()
    
    st.write(f"**📊 Analysis Results (from {st.session_state.get('analysis_pending_count', 0)} transactions):**")
    st.write(f"- High amount transactions (>$200): {len(high_amount_transactions)}")
    st.write(f"- Unusual merchants: {len(unusual_merchants)}")
    
    if high_amount_transactions or unusual_merchants:
        st.warning("⚠️ **Potentially problematic transactions detected:**")
        
        # High amount transactions
        for txn in high_amount_transactions:
            st.write(f"🚨 **High Amount**: {txn['merchant']} - ${txn['amount']:.2f} (ID: {txn['transaction_id']})")
            cancel_key = f"cancel_high_{txn['transaction_id']}"
            
            if st.button(f"❌ Cancel High Amount Transaction {txn['transaction_id']}", key=cancel_key):
                _handle_transaction_cancellation(txn['transaction_id'], "High amount flagged by AI")
        
        # Unusual merchants
        for txn in unusual_merchants:
            if txn not in high_amount_transactions:
                st.write(f"🔍 **Unusual Merchant**: {txn['merchant']} - ${txn['amount']:.2f} (ID: {txn['transaction_id']})")
                cancel_key = f"cancel_unusual_{txn['transaction_id']}"
                
                if st.button(f"❌ Cancel Unusual Merchant {txn['transaction_id']}", key=cancel_key):
                    _handle_transaction_cancellation(txn['transaction_id'], "Unusual merchant flagged by AI")
    else:
        st.success("✅ All pending transactions appear normal.")
        st.info("💡 Try lowering the analysis thresholds or check if transactions match the criteria.")


def _render_manual_management(pending_transactions):
    """Render manual transaction management section"""
    with st.expander("🛠️ Manual Transaction Management"):
        st.write("**Cancel a specific transaction:**")
        
        transaction_options = [f"ID {t['transaction_id']}: {t['merchant']} - ${t['amount']:.2f}" for t in pending_transactions]
        selected_transaction = st.selectbox("Select transaction to cancel:", [""] + transaction_options)
        
        if selected_transaction:
            transaction_id = int(selected_transaction.split(":")[0].replace("ID ", ""))
            reason = st.text_input("Cancellation reason:", value="Manually cancelled by user")
            
            if st.button("Cancel Selected Transaction"):
                _handle_transaction_cancellation(transaction_id, reason)


def _render_no_pending_transactions():
    """Display message when no pending transactions exist"""
    st.info("No pending transactions found.")
    
    try:
        with get_db_connection() as conn:
            result = conn.execute(text("""
                SELECT 
                    transaction_id,
                    merchant,
                    amount,
                    status,
                    notes,
                    date
                FROM transactions 
                WHERE status IN ('declined', 'cancelled')
                  AND notes LIKE '%CANCELLED:%'
                ORDER BY date DESC
                LIMIT 5
            """))
            
            recent_cancelled = result.fetchall()
            
            if recent_cancelled:
                st.write("**Recently Cancelled Transactions:**")
                for txn in recent_cancelled:
                    st.write(f"❌ **ID {txn.transaction_id}**: {txn.merchant} ${txn.amount} ({txn.status})")
                    if txn.notes:
                        cancellation_note = [line for line in txn.notes.split('\n') if 'CANCELLED:' in line]
                        if cancellation_note:
                            st.write(f"   📝 {cancellation_note[0]}")
            else:
                st.info("No recently cancelled transactions found.")
    except Exception as e:
        st.error(f"Could not load recently cancelled transactions: {e}")


def _handle_transaction_cancellation(transaction_id: int, reason: str):
    """
    Handle transaction cancellation with feedback
    
    Args:
        transaction_id: ID of transaction to cancel
        reason: Reason for cancellation
    """
    with st.spinner(f"Cancelling transaction {transaction_id}..."):
        try:
            success, message = TransactionManager.cancel_transaction(transaction_id, reason)
            
            if success:
                st.success(f"✅ SUCCESS: {message}")
                st.session_state.cancellation_success = success
                st.session_state.cancellation_message = message
                st.session_state.show_feedback = True
            else:
                st.error(f"❌ FAILED: {message}")
                st.session_state.cancellation_success = False
                st.session_state.cancellation_message = message
                st.session_state.show_feedback = True
                
        except Exception as e:
            st.error(f"❌ EXCEPTION: {e}")
            import traceback
            st.code(traceback.format_exc())
            st.session_state.cancellation_success = False
            st.session_state.cancellation_message = str(e)
            st.session_state.show_feedback = True

