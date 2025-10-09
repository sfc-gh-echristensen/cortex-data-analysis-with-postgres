import streamlit as st
import pandas as pd
import json
import re
import os
from typing import Optional
import requests
import urllib3
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from db import init_db, make_engine, make_session_factory, save_completion_with_session, fetch_history_with_session
from db_utils import TransactionManager, test_connection, ensure_status_column_exists, get_db_connection

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Initialize connection to Snowflake using the connection from secrets
conn = st.connection("snowflake")
session = conn.session()

# --- Helpers: Postgres connection / operations
def make_postgres_engine(user: str, password: str, host: str, port: int, dbname: str, sslmode: str | None = None) -> Engine:
    # Build SQLAlchemy connection string for psycopg2
    # Include sslmode if provided (e.g. 'require')
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
    if sslmode:
        # append as query param
        url = f"{url}?sslmode={sslmode}"
    return create_engine(url, echo=False)


def ensure_table(engine: Engine):
    # Create tables via ORM metadata
    init_db(engine)

# =============================================================================
# APP HEADER / BANNER
# =============================================================================

# Create a professional banner header
st.markdown("""
<style>
.banner {
    background: linear-gradient(90deg, #1f4e79 0%, #2980b9 100%);
    padding: 1.5rem 2rem;
    border-radius: 10px;
    margin-bottom: 2rem;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}
.banner h1 {
    color: white;
    margin: 0;
    font-size: 2.5rem;
    font-weight: 700;
    text-align: center;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
}
.banner p {
    color: #e8f4f8;
    margin: 0.5rem 0 0 0;
    font-size: 1.1rem;
    text-align: center;
    font-weight: 300;
}
.feature-badge {
    display: inline-block;
    background: rgba(255,255,255,0.2);
    color: white;
    padding: 0.3rem 0.8rem;
    border-radius: 20px;
    margin: 0.2rem;
    font-size: 0.9rem;
    border: 1px solid rgba(255,255,255,0.3);
}
</style>

<div class="banner">
    <h1>💰 Budget Tracker 9000</h1>
    <p>AI-Powered Financial Analytics & Real-Time Data Insights</p>
    <div style="text-align: center; margin-top: 1rem;">
        <span class="feature-badge">🐘 PostgreSQL</span>
        <span class="feature-badge">❄️ Snowflake Cortex</span>
        <span class="feature-badge">🤖 AI-Powered SQL</span>
        <span class="feature-badge">💬 Chat Interface</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Sidebar: Postgres configuration
st.sidebar.header("PostgreSQL Configuration")
secrets_pg = st.secrets.get("postgres", {}) if hasattr(st, "secrets") else {}

pg_host_default = secrets_pg.get("host") or os.environ.get("PG_HOST", "")
pg_port_default = str(secrets_pg.get("port") or os.environ.get("PG_PORT", "5432"))
pg_db_default = secrets_pg.get("database") or os.environ.get("PG_DB", "postgres")
pg_user_default = secrets_pg.get("user") or os.environ.get("PG_USER", "")
pg_password_default = secrets_pg.get("password") or os.environ.get("PG_PASSWORD", "")
pg_sslmode_default = secrets_pg.get("sslmode") or os.environ.get("PG_SSLMODE", "")

pg_host = st.sidebar.text_input("Host", value=pg_host_default)
pg_port = st.sidebar.text_input("Port", value=pg_port_default)
pg_db = st.sidebar.text_input("Database", value=pg_db_default)
pg_user = st.sidebar.text_input("User", value=pg_user_default)
pg_password = st.sidebar.text_input("Password", value=pg_password_default, type="password")
pg_sslmode = st.sidebar.text_input("SSL mode (optional)", value=pg_sslmode_default)

use_postgres = st.sidebar.checkbox("Enable PostgreSQL", value=bool(pg_host_default and pg_user_default and pg_password_default and pg_db_default))

# PostgreSQL connection setup
engine: Optional[Engine] = None
if use_postgres:
    if not (pg_host and pg_user and pg_password and pg_db):
        st.sidebar.warning("Enter all PostgreSQL credentials to enable.")
        use_postgres = False
    else:
        try:
            engine = make_postgres_engine(pg_user, pg_password, pg_host, int(pg_port or 5432), pg_db, sslmode=pg_sslmode or None)
            ensure_table(engine)
            st.sidebar.success("PostgreSQL connection OK")
        except Exception as e:
            st.sidebar.error(f"PostgreSQL connection failed: {e}")
            use_postgres = False

# =============================================================================
# POSTGRESQL FINANCIAL DATA ANALYSIS
# =============================================================================

# --- Real Time Financial Data Search
st.title("🐘 Real Time Postgres Financial Data")

if use_postgres and engine is not None:
    st.write("### Select Account")
    
    # Load all accounts for dropdown
    SessionFactory = make_session_factory(engine)
    with SessionFactory() as db_sess:
        try:
            account_rows = db_sess.execute(
                text("SELECT account_id, account_name, current_balance FROM accounts ORDER BY account_name")
            ).fetchall()
            
            if account_rows:
                # Create dropdown options
                account_options = ["Select an account..."] + [f"{row[1]} (${row[2]:,.2f})" for row in account_rows]
                account_names = [""] + [row[1] for row in account_rows]
                
                selected_account_display = st.selectbox(
                    "Choose an account for financial queries:",
                    account_options,
                    index=0
                )
                
                # Store selected account name
                if selected_account_display != "Select an account...":
                    selected_index = account_options.index(selected_account_display)
                    selected_account_name = account_names[selected_index]
                    st.session_state["selected_account_name"] = selected_account_name
                    st.session_state["account_search_done"] = True
                    
                    # Show selected account details
                    selected_row = account_rows[selected_index - 1]  # -1 because we added "Select..." at index 0
                    st.success(f"✅ Selected: **{selected_row[1]}** (ID: {selected_row[0]}) — Balance: **${selected_row[2]:,.2f}**")
                else:
                    if "selected_account_name" in st.session_state:
                        del st.session_state["selected_account_name"]
                    st.session_state["account_search_done"] = False
                    
            else:
                st.warning("No accounts found in the database.")
                
        except Exception as e:
            st.error(f"Error loading accounts: {e}")

    # Financial Q&A with Cortex-powered Text-to-SQL
    st.write("### AI-Powered Financial Queries")
    user_question = st.text_input("Ask a question about your finances:", "How much did I spend on groceries last week?")

    def generate_sql_with_cortex(question: str, schema_info: str) -> dict:
        """Use Snowflake Cortex to generate SQL from natural language."""
        try:
            # Create a specialized prompt for text-to-SQL conversion
            sql_prompt = """You are an expert SQL generator for PostgreSQL. Convert the following natural language question into a SQL query.

Database Schema:
""" + schema_info + """

IMPORTANT: In this database, ALL transaction amounts are stored as POSITIVE numbers. Expenses like groceries, dining, utilities are positive amounts (e.g., 15.00 for a $15 meal). Do NOT filter by amount < 0.

Rules:
1. Generate only valid PostgreSQL SQL
2. Use parameterized queries with :param_name format for SQLAlchemy for user input values
3. For relative dates (like "last week", "this month"), embed date functions directly in SQL, not as parameters
4. Always JOIN accounts and transactions tables when needed
5. Use ILIKE for case-insensitive text matching
6. Use NOW() - INTERVAL for relative dates (e.g., NOW() - INTERVAL '7 days' for last week)
7. All amounts are positive - do not filter by amount < 0
8. Return a JSON object with 'sql' and 'params' keys

Question: """ + question + """

Return your response as a JSON object with:
- "sql": the SQL query string (with date functions embedded directly)
- "params": an object with parameter names and values (only for user input, not dates)
- "explanation": brief explanation of what the query does

Example response formats:
For category search: {"sql": "SELECT SUM(t.amount) FROM transactions t JOIN accounts a ON t.account_id = a.account_id WHERE t.category ILIKE :category", "params": {"category": "Groceries"}, "explanation": "Sums all transaction amounts for grocery purchases"}

For spending queries: {"sql": "SELECT SUM(t.amount) FROM transactions t WHERE t.date >= NOW() - INTERVAL '7 days'", "params": {}, "explanation": "Total spending in the last 7 days"}
"""

            # Use Cortex to generate SQL
            response = session.sql(
                "select snowflake.cortex.complete(?, ?)", 
                params=['claude-3-5-sonnet', sql_prompt]
            ).collect()[0][0]
            
            # Parse the JSON response
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                # If response isn't valid JSON, try to extract it
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                else:
                    return {"error": "Could not parse SQL generation response", "raw_response": response}
                    
        except Exception as e:
            return {"error": f"Failed to generate SQL: {str(e)}"}

    def get_schema_info() -> str:
        """Get schema information for the financial database."""
        return """
Tables:
1. accounts
   - account_id (INTEGER, PRIMARY KEY)
   - account_name (VARCHAR, NOT NULL, UNIQUE)
   - current_balance (NUMERIC(14,2), NOT NULL)

2. transactions
   - transaction_id (INTEGER, PRIMARY KEY)
   - date (TIMESTAMP, NOT NULL)
   - amount (NUMERIC(12,2), NOT NULL)
   - merchant (VARCHAR)
   - category (VARCHAR)
   - notes (TEXT)
   - account_id (INTEGER, FOREIGN KEY to accounts.account_id)

Common categories: Groceries, Bills & Utilities, Entertainment, Transportation, Shopping, Dining, etc.
"""

    def execute_cortex_query(engine: Engine, sql: str, params: dict):
        """Execute the Cortex-generated SQL query."""
        SessionFactory = sessionmaker(bind=engine)
        with SessionFactory() as s:
            try:
                result = s.execute(text(sql), params).fetchall()
                return {"success": True, "result": result, "sql": sql, "params": params}
            except Exception as e:
                return {"success": False, "error": str(e), "sql": sql, "params": params}

    if st.button("Run AI-Powered Financial Query"):
        if not st.session_state.get("account_search_done"):
            st.warning("Consider running the PostgreSQL account search first to identify available accounts.")
        
        with st.spinner("Generating SQL with Cortex AI..."):
            # Get schema information
            schema_info = get_schema_info()
            
            # Add selected account context if available
            context_question = user_question
            if st.session_state.get("selected_account_name"):
                context_question += f" (Focus on account: {st.session_state['selected_account_name']})"
            
            # Generate SQL using Cortex
            cortex_result = generate_sql_with_cortex(context_question, schema_info)
            
            if "error" in cortex_result:
                st.error(f"Error generating SQL: {cortex_result['error']}")
                if "raw_response" in cortex_result:
                    with st.expander("Raw Cortex Response"):
                        st.text(cortex_result["raw_response"])
            else:
                # Display the generated SQL and explanation
                st.success("✨ SQL Generated Successfully!")
                
                if "explanation" in cortex_result:
                    st.info(f"**Query Explanation:** {cortex_result['explanation']}")
                
                # Execute the query
                query_result = execute_cortex_query(engine, cortex_result["sql"], cortex_result.get("params", {}))
                
                if query_result["success"]:
                    result_data = query_result["result"]
                    
                    if result_data:
                        # Display results in a nice format
                        if len(result_data) == 1 and len(result_data[0]) == 1:
                            # Single value result (like SUM, COUNT)
                            value = result_data[0][0]
                            if isinstance(value, (int, float)):
                                st.metric("Result", f"${value:,.2f}" if "amount" in cortex_result["sql"].lower() else f"{value:,}")
                            else:
                                st.success(f"Result: {value}")
                        else:
                            # Multiple results - show as table
                            df_result = pd.DataFrame(result_data)
                            st.dataframe(df_result, use_container_width=True)
                    else:
                        st.info("Query executed successfully but returned no results.")
                else:
                    st.error(f"Error executing SQL: {query_result['error']}")
                
                # Show query details in collapsible section
                with st.expander("🔍 Query Details", expanded=False):
                    st.markdown("**Generated SQL:**")
                    st.code(cortex_result["sql"], language="sql")
                    st.markdown("**Parameters:**")
                    st.json(cortex_result.get("params", {}))
                    if not query_result["success"]:
                        st.markdown("**Error Details:**")
                        st.error(query_result["error"])

    # --- PostgreSQL Completion History
    with st.expander("📚 Saved Query History", expanded=False):
        try:
            SessionFactory = make_session_factory(engine)
            with SessionFactory() as db_sess:
                rows = fetch_history_with_session(db_sess, limit=10)
            if rows:
                for r in rows:
                    with st.expander(f"#{r.id} — {r.created_at}"):
                        st.write("**Query:**", r.prompt)
                        st.write("**Result:**")
                        try:
                            st.json(r.result)
                        except Exception:
                            st.write(r.result)
            else:
                st.write("No history found.")
        except Exception as e:
            st.error(f"Failed to load history: {e}")

    # =============================================================================
    # PENDING TRANSACTIONS AGENT
    # =============================================================================

    st.markdown("---")
    st.header("🤖 Pending Transaction Manager")

    # Check database status and connection
    with st.expander("🔧 Database Status & Debug Info", expanded=False):
        conn_success, conn_msg = test_connection()
        if conn_success:
            st.success(f"✅ {conn_msg}")
            
            # Check status column
            status_exists, status_msg = ensure_status_column_exists()
            if status_exists:
                st.success(f"✅ {status_msg}")
            else:
                st.warning(f"⚠️ {status_msg}")
                st.info("Run `python migrate_add_status.py` to add the status column")
            
            # Show transaction statistics
            try:
                stats = TransactionManager.get_transaction_stats()
                st.write("**Transaction Statistics:**")
                for status, data in stats.items():
                    st.write(f"- **{status.title()}**: {data['count']} transactions (${data['total_amount']:.2f} total)")
            except Exception as e:
                st.error(f"Could not load transaction statistics: {e}")
            
            # Real-time database query
            if st.button("🔍 Query Database Directly", key="debug_query"):
                try:
                    from db_utils import get_db_connection
                    with get_db_connection() as conn:
                        result = conn.execute(text("""
                            SELECT 
                                transaction_id,
                                merchant,
                                amount,
                                status,
                                date,
                                CASE 
                                    WHEN LENGTH(notes) > 50 THEN LEFT(notes, 50) || '...'
                                    ELSE notes
                                END as notes_preview
                            FROM transactions 
                            ORDER BY date DESC, transaction_id DESC
                            LIMIT 10
                        """))
                        
                        recent_txns = result.fetchall()
                        st.write("**Last 10 Transactions (Direct from Database):**")
                        
                        for txn in recent_txns:
                            status_emoji = {
                                'pending': '🟡',
                                'approved': '🟢', 
                                'declined': '🔴',
                                'cancelled': '❌'
                            }.get(txn.status, '⚪')
                            
                            st.write(f"**ID {txn.transaction_id}** {status_emoji} {txn.merchant} - ${txn.amount} ({txn.status})")
                            if txn.notes_preview:
                                st.write(f"   _Notes: {txn.notes_preview}_")
                        
                except Exception as e:
                    st.error(f"Direct database query failed: {e}")
        else:
            st.error(f"❌ {conn_msg}")
            st.info("Check your PostgreSQL connection settings in the sidebar")

    # Initialize session state for cancellation feedback
    if 'cancellation_success' not in st.session_state:
        st.session_state.cancellation_success = None
    if 'cancellation_message' not in st.session_state:
        st.session_state.cancellation_message = None
    if 'show_feedback' not in st.session_state:
        st.session_state.show_feedback = False

    # Add refresh button and auto-refresh controls
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("🔄 Refresh Data", key="refresh_transactions"):
            st.rerun()
    
    with col2:
        auto_refresh = st.checkbox("Auto-refresh", value=False, key="auto_refresh_checkbox")
    
    with col3:
        if auto_refresh:
            st.info("⚡ Auto-refresh enabled - page will refresh automatically")

    # Debug session state (remove this after testing)
    with st.expander("🐛 Debug Session State", expanded=False):
        st.write("Session State Values:")
        st.write(f"- show_feedback: {st.session_state.get('show_feedback', 'Not set')}")
        st.write(f"- cancellation_success: {st.session_state.get('cancellation_success', 'Not set')}")
        st.write(f"- cancellation_message: {st.session_state.get('cancellation_message', 'Not set')}")
    
    # Display any pending success message at the top - PERSISTENT FEEDBACK
    if st.session_state.get('show_feedback', False):
        if st.session_state.get('cancellation_success', False):
            st.success(f"✅ **TRANSACTION CANCELLED**: {st.session_state.get('cancellation_message', 'Unknown transaction')}")
            st.balloons()
            st.info(f"🔄 **Database Updated**: Transaction status changed to 'declined' in PostgreSQL")
            
            # Add verification section
            with st.expander("🔍 Verification Details", expanded=True):
                st.write("**What happened:**")
                st.write("1. ✅ Database transaction started")
                st.write("2. ✅ Transaction found and verified as 'pending'")
                st.write("3. ✅ Status updated to 'declined'")
                st.write("4. ✅ Cancellation reason added to notes")
                st.write("5. ✅ Database transaction committed")
                st.write("6. ✅ Changes verified in database")
                
                st.info("💡 **Tip**: Click 'Refresh Data' to see the updated transaction list")
            
            # Auto-clear after showing (but only after a manual clear button)
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
            
            # Add button to clear error feedback  
            if st.button("❌ Clear Error Message", key="clear_error"):
                st.session_state.show_feedback = False
                st.session_state.cancellation_success = None
                st.session_state.cancellation_message = None
                st.rerun()

    # DEBUG: Multiple test buttons to isolate UI issues
    st.write("---")
    st.write("🧪 **DEBUG: Button Tests**")
    
    # Test 1: Minimal button
    if st.button("🟢 MINIMAL TEST", key="minimal_test"):
        st.write("✅ Minimal button clicked!")
    
    # Test 2: Button with logging
    if st.button("🔵 LOGGING TEST", key="logging_test"):
        st.write("✅ Logging button clicked!")
        import logging
        logging.getLogger('db_utils').info("🧪 DEBUG: Button click detected in Streamlit")
    
    # Test 3: Database test button
    if st.button("🔥 DATABASE TEST", key="database_test"):
        st.write("✅ Database button clicked!")
        try:
            # Try to cancel transaction 5 (Gadget Store)
            st.info("🎯 About to call TransactionManager.cancel_transaction...")
            success, message = TransactionManager.cancel_transaction(5, "DEBUG: Streamlit UI button test")
            if success:
                st.success(f"✅ DATABASE TEST SUCCESS: {message}")
            else:
                st.error(f"❌ DATABASE TEST FAILED: {message}")
        except Exception as e:
            st.error(f"❌ DATABASE TEST EXCEPTION: {e}")
            import traceback
            st.code(traceback.format_exc())
    
    st.write("---")

    # Display pending transactions
    try:
        pending_transactions = TransactionManager.get_pending_transactions()
    except Exception as e:
        st.error(f"Failed to fetch pending transactions: {e}")
        pending_transactions = []

    if pending_transactions:
        st.write(f"**Found {len(pending_transactions)} pending transactions:**")
        
        # Create a DataFrame for better display
        df_pending = pd.DataFrame(pending_transactions)
        df_pending['amount'] = df_pending['amount'].apply(lambda x: f"${x:.2f}")
        df_pending['date'] = pd.to_datetime(df_pending['date']).dt.strftime('%Y-%m-%d')
        
        # Display the table
        st.dataframe(df_pending[['transaction_id', 'date', 'amount', 'merchant', 'category']], use_container_width=True)
        
        # Agent interaction section
        st.markdown("### 🔍 AI Transaction Analysis")
        st.info("💡 **I can help you identify and cancel problematic pending transactions!**")
        st.write("Try asking me things like:")
        st.write("- *'Are there any suspicious large transactions?'*")
        st.write("- *'Cancel transactions over $100'*")
        st.write("- *'Which transactions look unusual?'*")
        
        # Simple agent prompt with session state persistence
        if st.button("🤖 Analyze Pending Transactions"):
            with st.spinner("Analyzing pending transactions..."):
                st.write(f"**🔍 Analyzing {len(pending_transactions)} pending transactions...**")
                
                # Debug: Show all pending transactions first
                st.write("**All Pending Transactions:**")
                for i, t in enumerate(pending_transactions):
                    st.write(f"{i+1}. ID {t['transaction_id']}: {t['merchant']} - ${t['amount']:.2f}")
                
                # Simple rule-based analysis with more relaxed criteria
                high_amount_transactions = [t for t in pending_transactions if float(t['amount']) > 200]  # Lowered from 500
                unusual_merchants = [t for t in pending_transactions if any(word in t['merchant'].lower() 
                                   for word in ['gadget', 'airlines', 'electronics', 'store', 'unknown', 'luxury'])]
                
                # Store results in session state for persistence
                st.session_state.analysis_performed = True
                st.session_state.high_amount_transactions = high_amount_transactions
                st.session_state.unusual_merchants = unusual_merchants
                st.session_state.analysis_pending_count = len(pending_transactions)
                
                st.write(f"**Analysis Results:**")
                st.write(f"- High amount transactions (>$200): {len(high_amount_transactions)}")
                st.write(f"- Unusual merchants: {len(unusual_merchants)}")
        
        # Show analysis results if they exist in session state (persists across reruns)
        if st.session_state.get('analysis_performed', False):
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
                
                for txn in high_amount_transactions:
                    st.write(f"🚨 **High Amount**: {txn['merchant']} - ${txn['amount']:.2f} (ID: {txn['transaction_id']})")
                    cancel_key = f"cancel_high_{txn['transaction_id']}"
                    st.write(f"Button key: {cancel_key}")
                    
                    if st.button(f"❌ Cancel High Amount Transaction {txn['transaction_id']}", key=cancel_key):
                        st.info(f"🎯 HIGH AMOUNT: Button clicked for transaction {txn['transaction_id']}...")
                        
                        # Show immediate feedback
                        with st.spinner(f"Cancelling transaction {txn['transaction_id']}..."):
                            try:
                                success, message = TransactionManager.cancel_transaction(txn['transaction_id'], "High amount flagged by AI")
                                
                                if success:
                                    st.success(f"✅ SUCCESS: {message}")
                                    
                                    # Set session state for persistent feedback
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
                    
                for txn in unusual_merchants:
                    if txn not in high_amount_transactions:  # Don't duplicate
                        st.write(f"🔍 **Unusual Merchant**: {txn['merchant']} - ${txn['amount']:.2f} (ID: {txn['transaction_id']})")
                        cancel_key = f"cancel_unusual_{txn['transaction_id']}"
                        st.write(f"Button key: {cancel_key}")
                        
                        if st.button(f"❌ Cancel Unusual Merchant {txn['transaction_id']}", key=cancel_key):
                            st.info(f"🎯 UNUSUAL: Button clicked for transaction {txn['transaction_id']}...")
                            
                            # Show immediate feedback
                            with st.spinner(f"Cancelling unusual merchant transaction {txn['transaction_id']}..."):
                                try:
                                    success, message = TransactionManager.cancel_transaction(txn['transaction_id'], "Unusual merchant flagged by AI")
                                    
                                    if success:
                                        st.success(f"✅ SUCCESS: {message}")
                                        
                                        # Set session state for persistent feedback
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
            else:
                st.success("✅ All pending transactions appear normal.")
                st.info("💡 Try lowering the analysis thresholds or check if transactions match the criteria.")
        
        # Manual transaction cancellation
        with st.expander("🛠️ Manual Transaction Management"):
            st.write("**Cancel a specific transaction:**")
            
            # Create selectbox with transaction details
            transaction_options = [f"ID {t['transaction_id']}: {t['merchant']} - ${t['amount']:.2f}" for t in pending_transactions]
            selected_transaction = st.selectbox("Select transaction to cancel:", [""] + transaction_options)
            
            if selected_transaction:
                # Extract transaction ID from the selected option
                transaction_id = int(selected_transaction.split(":")[0].replace("ID ", ""))
                reason = st.text_input("Cancellation reason:", value="Manually cancelled by user")
                
                if st.button("Cancel Selected Transaction"):
                    st.info(f"🎯 Manual cancellation button clicked for transaction {transaction_id}...")
                    with st.spinner(f"Cancelling transaction {transaction_id}..."):
                        try:
                            success, message = TransactionManager.cancel_transaction(transaction_id, reason)
                            
                            if success:
                                st.success(f"✅ SUCCESS: {message}")
                                st.info(f"📝 Reason: {reason}")
                                
                                # Set session state for persistent feedback
                                st.session_state.cancellation_success = success
                                st.session_state.cancellation_message = f"{message} - Reason: {reason}"
                                st.session_state.show_feedback = True
                            else:
                                st.error(f"❌ FAILED: {message}")
                                st.session_state.cancellation_success = False
                                st.session_state.cancellation_message = f"Error: {message}"
                                st.session_state.show_feedback = True
                                
                        except Exception as e:
                            st.error(f"❌ Exception during manual cancellation: {e}")
                            st.session_state.cancellation_success = False
                            st.session_state.cancellation_message = f"Error: {e}"
                            st.session_state.show_feedback = True

    else:
        st.info("No pending transactions found.")
        
        # Show recently cancelled transactions for reference
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
                            # Extract cancellation reason
                            cancellation_note = [line for line in txn.notes.split('\n') if 'CANCELLED:' in line]
                            if cancellation_note:
                                st.write(f"   📝 {cancellation_note[0]}")
                else:
                    st.info("No recently cancelled transactions found.")
        except Exception as e:
            st.error(f"Could not load recently cancelled transactions: {e}")
    
    # Add troubleshooting section
    with st.expander("🔧 Troubleshooting Guide", expanded=False):
        st.write("**If transaction cancellations don't seem to work:**")
        st.write("1. **Check the logs**: Look at `db_operations.log` and `transaction_debug.log`")
        st.write("2. **Refresh the page**: Click the '🔄 Refresh Data' button above")
        st.write("3. **Check database directly**: Use the '🔍 Query Database Directly' button")
        st.write("4. **Verify transaction ID**: Make sure you're cancelling the correct transaction")
        st.write("5. **Check transaction status**: Only 'pending' transactions can be cancelled")
        
        st.write("\n**Debug Commands:**")
        st.code("python3 debug_transactions.py", language="bash")
        st.code("python3 test_gadget_store.py", language="bash")
        
        st.write("\n**Log Files:**")
        st.write("- `db_operations.log` - Database operation logs")  
        st.write("- `transaction_debug.log` - Debug session logs")
        
        if st.button("📊 Show Transaction Statistics", key="show_stats"):
            try:
                stats = TransactionManager.get_transaction_stats()
                st.json(stats)
            except Exception as e:
                st.error(f"Could not load statistics: {e}")

else:
    st.info("💡 Enable PostgreSQL connection in the sidebar to access financial data analysis.")

# =============================================================================
# SNOWFLAKE CORTEX AGENT
# =============================================================================

st.title(":material/network_intel_node: Snowflake Financial Analytics")

# =============================================================================
# SPENDING OVERVIEW CHART
# =============================================================================

st.subheader("📊 Monthly Spending Overview")

try:
    # Create spending chart from TRANSACTIONS table
    
    # Get sample data to understand the structure
    sample_df = session.sql("SELECT * FROM TRANSACTIONS LIMIT 5").to_pandas()
    
    # Detect column types automatically
    date_columns = [col for col in sample_df.columns if any(keyword in col.upper() for keyword in ['DATE', 'TIME', 'CREATED', 'UPDATED'])]
    amount_columns = [col for col in sample_df.columns if any(keyword in col.upper() for keyword in ['AMOUNT', 'SPENDING', 'EXPENSE', 'COST', 'PRICE', 'TOTAL'])]
    category_columns = [col for col in sample_df.columns if any(keyword in col.upper() for keyword in ['CATEGORY', 'TYPE', 'CLASS'])]
    
    if date_columns and amount_columns:
        # Use the first detected date and amount columns
        date_col = date_columns[0]
        amount_col = amount_columns[0]
        
        # Create the spending chart query
        if category_columns:
            # Include categories if available
            category_col = category_columns[0]
            chart_query = f"""
            SELECT 
                DATE_TRUNC('month', {date_col}) as month,
                {category_col} as category,
                SUM(ABS({amount_col})) as total_amount
            FROM TRANSACTIONS 
            WHERE {date_col} >= DATEADD('month', -12, CURRENT_DATE())
            GROUP BY DATE_TRUNC('month', {date_col}), {category_col}
            ORDER BY month DESC, total_amount DESC
            """
        else:
            # Just date and amount
            chart_query = f"""
            SELECT 
                DATE_TRUNC('month', {date_col}) as month,
                SUM(ABS({amount_col})) as total_amount
            FROM TRANSACTIONS 
            WHERE {date_col} >= DATEADD('month', -12, CURRENT_DATE())
            GROUP BY DATE_TRUNC('month', {date_col})
            ORDER BY month DESC
            """
        
        # Execute the query
        chart_df = session.sql(chart_query).to_pandas()
        
        if not chart_df.empty:
            # Create visualization
            chart_df['MONTH'] = pd.to_datetime(chart_df['MONTH'])
            
            if 'CATEGORY' in chart_df.columns:
                # Create stacked area chart by category
                import altair as alt
                
                chart = alt.Chart(chart_df).mark_area().encode(
                    x=alt.X('MONTH:T', title='Month'),
                    y=alt.Y('TOTAL_AMOUNT:Q', title='Total Amount ($)'),
                    color=alt.Color('CATEGORY:N', title='Category'),
                    tooltip=['MONTH:T', 'CATEGORY:N', 'TOTAL_AMOUNT:Q']
                ).properties(
                    width=700,
                    height=400,
                    title="Monthly Spending by Category"
                ).interactive()
                
                st.altair_chart(chart, use_container_width=True)
                
                # Also create a line chart of total spending
                monthly_totals = chart_df.groupby('MONTH')['TOTAL_AMOUNT'].sum().reset_index()
                
                line_chart = alt.Chart(monthly_totals).mark_line(
                    point=True,
                    strokeWidth=3,
                    color='#2980b9'
                ).encode(
                    x=alt.X('MONTH:T', title='Month'),
                    y=alt.Y('TOTAL_AMOUNT:Q', title='Total Spending ($)'),
                    tooltip=['MONTH:T', 'TOTAL_AMOUNT:Q']
                ).properties(
                    width=700,
                    height=300,
                    title="Total Monthly Spending Trend"
                )
                
                st.altair_chart(line_chart, use_container_width=True)
                
            else:
                # Simple line chart for total spending
                st.line_chart(chart_df.set_index('MONTH')['TOTAL_AMOUNT'])
            
            # Show key metrics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                latest_month_total = chart_df.groupby('MONTH')['TOTAL_AMOUNT'].sum().iloc[0]
                st.metric("Latest Month", f"${latest_month_total:,.2f}")
            
            with col2:
                avg_monthly = chart_df.groupby('MONTH')['TOTAL_AMOUNT'].sum().mean()
                st.metric("Monthly Average", f"${avg_monthly:,.2f}")
            
            with col3:
                total_months = len(chart_df['MONTH'].unique())
                st.metric("Months of Data", total_months)
            
            if 'CATEGORY' in chart_df.columns:
                # Show top categories
                st.write("**Top Spending Categories:**")
                top_categories = chart_df.groupby('CATEGORY')['TOTAL_AMOUNT'].sum().sort_values(ascending=False).head(5)
                for category, amount in top_categories.items():
                    st.write(f"- **{category}**: ${amount:,.2f}")
            
        else:
            st.warning("No spending data found in TRANSACTIONS table")
            
    else:
        st.error(f"Could not find suitable date or amount columns in TRANSACTIONS table")
        st.write(f"Available columns: {list(sample_df.columns)}")
        
except Exception as e:
    st.error(f"Error loading TRANSACTIONS data: {e}")
    st.write("**Connection Details:**")
    st.write("- Make sure your Snowflake connection is properly configured")
    st.write("- Check if the TRANSACTIONS table exists in your current database/schema")
    st.write("- Verify your credentials in secrets.toml")
    
    # Show sample chart as fallback
    st.info("📊 Showing sample chart due to connection issues")
    
    import pandas as pd
    from datetime import datetime, timedelta
    
    sample_dates = [datetime.now() - timedelta(days=30*i) for i in range(6)]
    sample_spending = [2000, 2200, 1800, 2400, 2100, 2300]
    
    sample_df = pd.DataFrame({
        'Month': sample_dates,
        'Spending': sample_spending
    })
    
    st.line_chart(sample_df.set_index('Month'))

st.markdown("---")

# Agent configuration
DATABASE = "BUILD25_POSTGRES_CORTEX"
SCHEMA = "AGENTS"
AGENT = "POSTGRES_AGENT"

# Build full URL
HOST = st.secrets.get("agent", {}).get("SNOWFLAKE_HOST")
print("Using Snowflake host:", HOST)
API_ENDPOINT = f"https://{HOST}/api/v2/databases/{DATABASE}/schemas/{SCHEMA}/agents/{AGENT}:run"
API_TIMEOUT = 60  # timeout in seconds for requests library

st.markdown("---")
st.header("❄️ Chat with Snowflake Cortex Agent")

# =============================================================================
# AGENTIC SUBSCRIPTION MANAGEMENT DEMO
# =============================================================================

# Demo subscription cancellation function
def cancel_subscription_demo(subscription_id, subscription_name):
    """Simulate canceling a subscription via API call"""
    import time
    import random
    
    # Simulate API call delay
    time.sleep(random.uniform(1, 2))
    
    # Update subscription status
    if subscription_id in st.session_state.demo_subscriptions:
        st.session_state.demo_subscriptions[subscription_id]["status"] = "cancelled"
        return True
    return False

# Add subscription management context to chat
def add_subscription_context_to_prompt(user_prompt):
    """Add subscription data context to user prompts about subscriptions"""
    subscription_keywords = ["subscription", "cancel", "unused", "recurring", "monthly", "netflix", "spotify", "adobe", "gym", "hulu"]
    
    if any(keyword in user_prompt.lower() for keyword in subscription_keywords):
        # Create subscription context
        active_subs = {k: v for k, v in st.session_state.demo_subscriptions.items() if v["status"] == "active"}
        
        context = f"""
SUBSCRIPTION CONTEXT:
The user has the following active subscriptions based on their financial data:

"""
        for sub_id, sub_data in active_subs.items():
            context += f"- {sub_data['name']}: ${sub_data['cost']}/month (last used: {sub_data['last_used']})\n"
        
        context += f"""
Current date: {pd.Timestamp.now().strftime('%Y-%m-%d')}

AVAILABLE ACTIONS:
If the user wants to cancel a subscription, you can help them by:
1. Analyzing usage patterns to identify unused subscriptions
2. Suggesting specific subscriptions to cancel
3. If user confirms cancellation, respond with: "I'll cancel [subscription name] for you now." and mention calling the cancellation API

When identifying unused subscriptions, consider:
- Subscriptions not used in the last 30+ days as potentially unused
- High-cost subscriptions with infrequent usage
- Duplicate services (e.g., multiple streaming services)

User's original question: {user_prompt}
"""
        return context
    
    return user_prompt

# Initialize session state for chat messages
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

# Initialize subscription demo data in session state
if "demo_subscriptions" not in st.session_state:
    st.session_state.demo_subscriptions = {
        "netflix": {"name": "Netflix", "cost": 15.99, "last_used": "2024-09-15", "status": "active"},
        "spotify": {"name": "Spotify Premium", "cost": 9.99, "last_used": "2024-10-07", "status": "active"},
        "adobe": {"name": "Adobe Creative Cloud", "cost": 52.99, "last_used": "2024-08-12", "status": "active"},
        "gym": {"name": "Planet Fitness", "cost": 24.99, "last_used": "2024-07-20", "status": "active"},
        "hulu": {"name": "Hulu + Live TV", "cost": 76.99, "last_used": "2024-10-05", "status": "active"},
        "microsoft": {"name": "Microsoft 365", "cost": 6.99, "last_used": "2024-10-08", "status": "active"}
    }

# Demo subscription management panel
with st.expander("💳 Current Subscriptions (Demo Data)", expanded=False):
    active_subs = {k: v for k, v in st.session_state.demo_subscriptions.items() if v["status"] == "active"}
    cancelled_subs = {k: v for k, v in st.session_state.demo_subscriptions.items() if v["status"] == "cancelled"}
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Active Subscriptions:**")
        total_monthly = 0
        for sub_data in active_subs.values():
            days_since_use = (pd.Timestamp.now() - pd.Timestamp(sub_data["last_used"])).days
            unused_indicator = " 🔴 (Unused 30+ days)" if days_since_use > 30 else " 🟢"
            st.write(f"- {sub_data['name']}: ${sub_data['cost']}/month{unused_indicator}")
            total_monthly += sub_data["cost"]
        
        st.metric("Total Monthly Cost", f"${total_monthly:.2f}")
    
    with col2:
        if cancelled_subs:
            st.write("**Recently Cancelled:**")
            total_savings = 0
            for sub_data in cancelled_subs.values():
                st.write(f"- ~~{sub_data['name']}~~: ${sub_data['cost']}/month")
                total_savings += sub_data["cost"]
            st.metric("Monthly Savings", f"${total_savings:.2f}")
        else:
            st.info("No subscriptions cancelled yet. Try asking the agent: 'Tell me about subscriptions I don't use'")

st.write("💡 **Try asking:** 'Tell me about subscriptions I don't use' or 'Which subscriptions should I cancel?'")

# Display chat messages
for message in st.session_state.chat_messages:
    with st.chat_message(message["role"]):
        if message["role"] == "user":
            st.markdown(message["content"])
        else:
            # Display assistant message with all content types
            content_items = message.get("content", [])
            
            for item in content_items:
                item_type = item.get("type")
                
                if item_type == "text":
                    st.markdown(item.get("text", ""))
                
                elif item_type == "thinking":
                    with st.expander("🤔 Thinking"):
                        st.write(item.get("thinking", {}).get("text", ""))
                
                elif item_type == "tool_use":
                    with st.expander(f"🔧 Tool Use: {item.get('tool_use', {}).get('name', 'Unknown')}"):
                        st.json(item.get("tool_use"))
                
                elif item_type == "tool_result":
                    with st.expander("📊 Tool Result"):
                        tool_result = item.get("tool_result", {})
                        content = tool_result.get("content", [])
                        for c in content:
                            if c.get("type") == "json":
                                json_data = c.get("json", {})
                                if "sql" in json_data:
                                    st.code(json_data["sql"], language="sql")
                
                elif item_type == "chart":
                    chart_spec = json.loads(item.get("chart", {}).get("chart_spec", "{}"))
                    st.vega_lite_chart(chart_spec, use_container_width=True)
                
                elif item_type == "table":
                    result_set = item.get("table", {}).get("result_set", {})
                    data_array = result_set.get("data", [])
                    row_type = result_set.get("result_set_meta_data", {}).get("row_type", [])
                    column_names = [col.get("name") for col in row_type]
                    
                    df_result = pd.DataFrame(data_array, columns=column_names)
                    st.dataframe(df_result)

# Chat input
if prompt := st.chat_input("Ask me about your financial data or subscriptions..."):
    # Add subscription context if relevant
    enhanced_prompt = add_subscription_context_to_prompt(prompt)
    
    # Add user message to chat history (original prompt for display)
    user_message_content = prompt
    st.session_state.chat_messages.append({"role": "user", "content": user_message_content})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Display assistant response
    with st.chat_message("assistant"):
        # Create message payload for agent (with enhanced prompt)
        user_message = {
            "role": "user",
            "content": [{"type": "text", "text": enhanced_prompt}]
        }
        
        payload = {
            "messages": [user_message]
        }
        
        # Show thinking indicator
        with st.status("Thinking...", expanded=True) as status:
            try:
                # Get authentication token
                token = st.secrets.get("agent", {}).get("SNOWFLAKE_PAT")
                
                # Make API call
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
                
                status.update(label="Connecting to agent...", state="running")
                
                response = requests.post(
                    API_ENDPOINT,
                    json=payload,
                    headers=headers,
                    timeout=API_TIMEOUT,
                    verify=False,
                    stream=True
                )
                
                if response.status_code != 200:
                    st.error(f"Error: Status {response.status_code}")
                    st.text(response.text)
                else:
                    # Process streaming response
                    text_buffer = ""
                    final_message = None
                    buffer = ""
                    
                    # Create placeholders for streaming
                    status.update(label="Processing response...", state="running")
                    response_placeholder = st.empty()
                    
                    # Stream the response
                    for line in response.iter_lines(decode_unicode=True):
                        if not line:
                            continue
                        
                        line = line.strip()
                        
                        if line.startswith('event:'):
                            event_type = line.split('event:', 1)[1].strip()
                            buffer = event_type
                            
                        elif line.startswith('data:'):
                            data_line = line.split('data:', 1)[1].strip()
                            
                            try:
                                data = json.loads(data_line)
                                
                                # Update status
                                if buffer == 'response.status':
                                    status.update(label=f"Status: {data.get('message', '')}", state="running")
                                
                                # Stream text updates
                                elif buffer == 'response.text.delta':
                                    text_buffer += data.get('text', '')
                                    response_placeholder.markdown(text_buffer)
                                
                                # Parse final response
                                elif buffer == 'response':
                                    final_message = data
                                    
                            except json.JSONDecodeError:
                                pass
                    
                    status.update(label="Complete!", state="complete")
                    
                    if final_message:
                        # Clear the streaming placeholder and show final response
                        response_placeholder.empty()
                        
                        # Extract and display content
                        content_items = final_message.get("content", [])
                        response_text = ""
                        
                        for item in content_items:
                            item_type = item.get("type")
                            
                            if item_type == "text":
                                text_content = item.get("text", "")
                                st.markdown(text_content)
                                response_text += text_content
                            
                            elif item_type == "thinking":
                                with st.expander("🤔 Thinking"):
                                    st.write(item.get("thinking", {}).get("text", ""))
                            
                            elif item_type == "tool_use":
                                with st.expander(f"🔧 Tool Use: {item.get('tool_use', {}).get('name', 'Unknown')}"):
                                    st.json(item.get("tool_use"))
                            
                            elif item_type == "tool_result":
                                with st.expander("📊 Tool Result"):
                                    tool_result = item.get("tool_result", {})
                                    content = tool_result.get("content", [])
                                    for c in content:
                                        if c.get("type") == "json":
                                            json_data = c.get("json", {})
                                            if "sql" in json_data:
                                                st.code(json_data["sql"], language="sql")
                            
                            elif item_type == "chart":
                                chart_spec = json.loads(item.get("chart", {}).get("chart_spec", "{}"))
                                st.vega_lite_chart(chart_spec, use_container_width=True)
                            
                            elif item_type == "table":
                                result_set = item.get("table", {}).get("result_set", {})
                                data_array = result_set.get("data", [])
                                row_type = result_set.get("result_set_meta_data", {}).get("row_type", [])
                                column_names = [col.get("name") for col in row_type]
                                
                                df_result = pd.DataFrame(data_array, columns=column_names)
                                st.dataframe(df_result)
                        
                        # Check if agent wants to cancel a subscription
                        if "i'll cancel" in response_text.lower() or "cancel" in response_text.lower():
                            for sub_id, sub_data in st.session_state.demo_subscriptions.items():
                                if sub_data["name"].lower() in response_text.lower() and sub_data["status"] == "active":
                                    # Show cancellation in progress
                                    with st.status("🔄 Processing cancellation...", expanded=True) as cancel_status:
                                        cancel_status.write(f"Calling subscription API for {sub_data['name']}...")
                                        
                                        # Simulate API call
                                        success = cancel_subscription_demo(sub_id, sub_data["name"])
                                        
                                        if success:
                                            cancel_status.update(label="✅ Subscription cancelled successfully!", state="complete")
                                            st.success(f"🎉 {sub_data['name']} has been cancelled! You'll save ${sub_data['cost']}/month.")
                                            
                                            # Show updated subscription status
                                            with st.expander("📋 Updated Subscription Status"):
                                                active_subs = {k: v for k, v in st.session_state.demo_subscriptions.items() if v["status"] == "active"}
                                                cancelled_subs = {k: v for k, v in st.session_state.demo_subscriptions.items() if v["status"] == "cancelled"}
                                                
                                                if active_subs:
                                                    st.write("**Active Subscriptions:**")
                                                    for sub_data in active_subs.values():
                                                        st.write(f"- {sub_data['name']}: ${sub_data['cost']}/month")
                                                
                                                if cancelled_subs:
                                                    st.write("**Recently Cancelled:**")
                                                    for sub_data in cancelled_subs.values():
                                                        st.write(f"- ~~{sub_data['name']}~~: ${sub_data['cost']}/month (cancelled)")
                                                
                                                total_savings = sum(sub['cost'] for sub in cancelled_subs.values())
                                                st.metric("Monthly Savings", f"${total_savings:.2f}")
                                        else:
                                            cancel_status.update(label="❌ Cancellation failed", state="error")
                                            st.error("Failed to cancel subscription. Please try again.")
                                    break
                        
                        # Add assistant message to chat history
                        st.session_state.chat_messages.append({
                            "role": "assistant", 
                            "content": final_message.get("content", [])
                        })
                        
                        # Save to PostgreSQL if enabled
                        if use_postgres and engine is not None:
                            try:
                                SessionFactory = make_session_factory(engine)
                                with SessionFactory() as db_sess:
                                    result_json = {"response": response_text} if isinstance(response_text, str) else response_text
                                    c = save_completion_with_session(db_sess, prompt, result_json)
                                st.success(f"💾 Saved to PostgreSQL (id={c.id})")
                            except Exception as e:
                                st.error(f"Failed to save to PostgreSQL: {e}")
                    else:
                        st.warning("No final response found in events")
                        
            except Exception as e:
                st.error(f"Agent request failed: {str(e)}")
                import traceback
                st.code(traceback.format_exc())

# Add a button to clear chat history
if st.button("🗑️ Clear Chat History"):
    st.session_state.chat_messages = []
    st.rerun()
