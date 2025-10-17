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

# Import search page
from pages.search import show_search_page

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

# Create a professional banner header with navigation
st.markdown("""
<style>
/* Hide the default Streamlit navigation */
[data-testid="stSidebarNav"] {
    display: none;
}
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
    color: #e8f4f8;
    margin: 0 0.8rem;
    font-size: 0.95rem;
    font-weight: 400;
}
.nav-buttons {
    text-align: center;
    margin-top: 1.5rem;
    padding-top: 1rem;
    border-top: 1px solid rgba(255,255,255,0.2);
}
.nav-button {
    display: inline-block;
    background: rgba(255,255,255,0.15);
    color: white !important;
    padding: 0.35rem 0.6rem;
    border-radius: 15px;
    margin: 0.1rem 0.2rem;
    text-decoration: none !important;
    font-weight: 500;
    font-size: 0.8rem;
    border: 1px solid rgba(255,255,255,0.3);
    transition: all 0.3s ease;
    cursor: pointer;
    white-space: nowrap;
}
.nav-button:hover {
    background: rgba(255,255,255,0.25);
    border-color: rgba(255,255,255,0.6);
    color: white !important;
    text-decoration: none !important;
    transform: translateY(-1px);
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}
.nav-button:active {
    transform: translateY(0);
}
.nav-button:visited {
    color: white !important;
}
</style>

<div class="banner">
    <h1>💰 Budget Tracker 9000</h1>
    <p>AI-Powered Financial Analytics & Real-Time Data Insights</p>
    <div style="text-align: center; margin-top: 1rem;">
        <span class="feature-badge">🐘 PostgreSQL</span>
        <span style="color: rgba(255,255,255,0.4); margin: 0 0.3rem;">•</span>
        <span class="feature-badge">❄️ Snowflake Cortex</span>
        <span style="color: rgba(255,255,255,0.4); margin: 0 0.3rem;">•</span>
        <span class="feature-badge">🤖 AI-Powered SQL</span>
        <span style="color: rgba(255,255,255,0.4); margin: 0 0.3rem;">•</span>
        <span class="feature-badge">💬 Chat Interface</span>
    </div>
    <div class="nav-buttons">
        <a href="#budget-dashboard" class="nav-button">💰 Budget</a>
        <a href="?page=search" class="nav-button">🔍 Search Demo</a>
        <a href="#ai-queries" class="nav-button">🤖 AI Queries</a>
        <a href="#transaction-manager" class="nav-button">🔧 Transactions</a>
        <a href="#snowflake-analytics" class="nav-button">❄️ Analytics</a>
    </div>
</div>
""", unsafe_allow_html=True)

# =============================================================================
# MULTI-PAGE NAVIGATION
# =============================================================================

# Check for page parameter in URL
query_params = st.query_params
current_page = query_params.get("page", "dashboard")

# Add navigation in sidebar
st.sidebar.markdown("---")
st.sidebar.header("📄 Pages")

if st.sidebar.button("🏦 Dashboard", use_container_width=True):
    st.query_params.page = "dashboard"
    st.rerun()

if st.sidebar.button("🔍 Search Demo", use_container_width=True):
    st.query_params.page = "search"
    st.rerun()

# Route to the appropriate page
if current_page == "search":
    show_search_page()
    st.stop()

# Continue with dashboard (default page) content below
st.sidebar.markdown("---")

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
# BUDGET DASHBOARD
# =============================================================================

st.markdown('<div id="budget-dashboard"></div>', unsafe_allow_html=True)
st.header("💰 Budget Dashboard")

if use_postgres and engine is not None:
    try:
        # Get current date info
        from datetime import datetime, timedelta
        import calendar
        
        today = datetime.now()
        current_month = today.replace(day=1)
        last_month = (current_month - timedelta(days=1)).replace(day=1)
        current_week_start = today - timedelta(days=today.weekday())
        last_week_start = current_week_start - timedelta(days=7)
        
        # Fetch spending data
        with get_db_connection() as conn:
            # Daily spending (today)
            today_result = conn.execute(text("""
                SELECT COALESCE(SUM(ABS(amount)), 0) as daily_spending
                FROM transactions 
                WHERE DATE(date) = CURRENT_DATE 
                AND status = 'approved'
            """)).fetchone()
            
            # Weekly spending (current vs last week)
            weekly_result = conn.execute(text("""
                SELECT 
                    COALESCE(SUM(CASE 
                        WHEN date >= DATE_TRUNC('week', CURRENT_DATE) 
                        THEN ABS(amount) ELSE 0 END), 0) as current_week,
                    COALESCE(SUM(CASE 
                        WHEN date >= DATE_TRUNC('week', CURRENT_DATE) - INTERVAL '1 week'
                             AND date < DATE_TRUNC('week', CURRENT_DATE)
                        THEN ABS(amount) ELSE 0 END), 0) as last_week
                FROM transactions 
                WHERE date >= DATE_TRUNC('week', CURRENT_DATE) - INTERVAL '1 week'
                AND status = 'approved'
            """)).fetchone()
            
            # Monthly spending (current vs last month)
            monthly_result = conn.execute(text("""
                SELECT 
                    COALESCE(SUM(CASE 
                        WHEN date >= DATE_TRUNC('month', CURRENT_DATE) 
                        THEN ABS(amount) ELSE 0 END), 0) as current_month,
                    COALESCE(SUM(CASE 
                        WHEN date >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month'
                             AND date < DATE_TRUNC('month', CURRENT_DATE)
                        THEN ABS(amount) ELSE 0 END), 0) as last_month,
                    COALESCE(AVG(CASE 
                        WHEN date >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '3 month'
                             AND date < DATE_TRUNC('month', CURRENT_DATE)
                        THEN ABS(amount) END), 0) as avg_monthly
                FROM transactions 
                WHERE date >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '3 month'
                AND status = 'approved'
            """)).fetchone()
            
            # Category spending (current month)
            category_result = conn.execute(text("""
                SELECT 
                    category,
                    SUM(ABS(amount)) as spending
                FROM transactions 
                WHERE date >= DATE_TRUNC('month', CURRENT_DATE)
                AND status = 'approved'
                GROUP BY category
                ORDER BY spending DESC
                LIMIT 6
            """)).fetchall()
            
        # Budget targets (you can make these configurable later)
        DAILY_BUDGET = 75.00
        WEEKLY_BUDGET = 400.00
        MONTHLY_BUDGET = 1500.00
        
        # Category budgets
        CATEGORY_BUDGETS = {
            'Food & Dining': 400,
            'Shopping': 300,
            'Entertainment': 200,
            'Transportation': 150,
            'Utilities': 250,
            'Other': 200
        }
        
        # Extract values
        daily_spending = float(today_result.daily_spending)
        current_week = float(weekly_result.current_week)
        last_week = float(weekly_result.last_week)
        current_month = float(monthly_result.current_month)
        last_month = float(monthly_result.last_month)
        
        # =============================================================================
        # DAILY BUDGET STATUS
        # =============================================================================
        
        st.subheader("📅 Today's Budget Status")
        
        # Calculate daily budget status
        daily_percent = (daily_spending / DAILY_BUDGET) * 100 if DAILY_BUDGET > 0 else 0
        daily_remaining = DAILY_BUDGET - daily_spending
        
        # Color coding for budget status
        if daily_percent <= 50:
            daily_color = "🟢"
            daily_status = "Great! You're on budget"
            daily_style = "color: green;"
        elif daily_percent <= 80:
            daily_color = "🟡"
            daily_status = "Good progress, watch spending"
            daily_style = "color: orange;"
        elif daily_percent <= 100:
            daily_color = "🟠"
            daily_status = "Close to budget limit"
            daily_style = "color: #ff8c00;"
        else:
            daily_color = "🔴"
            daily_status = "Over budget!"
            daily_style = "color: red;"
        
        # Display daily status
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.markdown(f"<h3 style='{daily_style}'>{daily_color} {daily_status}</h3>", unsafe_allow_html=True)
            st.progress(min(daily_percent / 100, 1.0))
            st.caption(f"${daily_spending:.2f} of ${DAILY_BUDGET:.2f} daily budget used")
        
        with col2:
            st.metric("Today's Spending", f"${daily_spending:.2f}")
        
        with col3:
            remaining_label = "Remaining" if daily_remaining >= 0 else "Over Budget"
            remaining_color = "normal" if daily_remaining >= 0 else "inverse"
            st.metric(remaining_label, f"${abs(daily_remaining):.2f}", 
                     delta=None, delta_color=remaining_color)
        
        # =============================================================================
        # WEEKLY COMPARISON
        # =============================================================================
        
        st.subheader("📈 Weekly Spending Comparison")
        
        # Calculate weekly changes
        weekly_change = current_week - last_week
        weekly_percent_change = (weekly_change / last_week * 100) if last_week > 0 else 0
        
        # Weekly status
        if weekly_percent_change <= -10:
            weekly_status = "📉 Spending down significantly"
            weekly_color = "green"
        elif weekly_percent_change <= -5:
            weekly_status = "📉 Spending decreased"
            weekly_color = "green"
        elif weekly_percent_change <= 5:
            weekly_status = "➡️ Spending similar to last week"
            weekly_color = "normal"
        elif weekly_percent_change <= 15:
            weekly_status = "📈 Spending increased"
            weekly_color = "orange"
        else:
            weekly_status = "📈 Spending up significantly"
            weekly_color = "red"
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("This Week", f"${current_week:.2f}", 
                     delta=f"${weekly_change:.2f}" if weekly_change != 0 else None,
                     delta_color="inverse" if weekly_change > 0 else "normal")
        
        with col2:
            st.metric("Last Week", f"${last_week:.2f}")
        
        with col3:
            weekly_budget_percent = (current_week / WEEKLY_BUDGET) * 100 if WEEKLY_BUDGET > 0 else 0
            st.metric("Weekly Budget Used", f"{weekly_budget_percent:.1f}%")
        
        st.markdown(f"**{weekly_status}**")
        
        # =============================================================================
        # MONTHLY BUDGET TRACKING
        # =============================================================================
        
        st.subheader("📊 Monthly Budget Tracking")
        
        # Calculate monthly metrics
        monthly_percent = (current_month / MONTHLY_BUDGET) * 100 if MONTHLY_BUDGET > 0 else 0
        days_in_month = calendar.monthrange(today.year, today.month)[1]
        days_elapsed = today.day
        expected_spending = (MONTHLY_BUDGET / days_in_month) * days_elapsed
        spending_vs_expected = current_month - expected_spending
        
        # Monthly status
        if current_month > MONTHLY_BUDGET:
            monthly_status = "🚨 Over monthly budget!"
            monthly_alert_color = "red"
        elif monthly_percent > 90:
            monthly_status = "⚠️ Close to monthly limit"
            monthly_alert_color = "orange"
        elif current_month < expected_spending * 0.8:
            monthly_status = "✅ Well under budget"
            monthly_alert_color = "green"
        else:
            monthly_status = "👍 On track with budget"
            monthly_alert_color = "normal"
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("This Month", f"${current_month:.2f}")
        
        with col2:
            last_month_change = current_month - last_month
            st.metric("Last Month", f"${last_month:.2f}", 
                     delta=f"${last_month_change:.2f}" if last_month_change != 0 else None,
                     delta_color="inverse" if last_month_change > 0 else "normal")
        
        with col3:
            st.metric("Expected by Now", f"${expected_spending:.2f}")
        
        with col4:
            st.metric("Budget Progress", f"{monthly_percent:.1f}%")
        
        # Monthly progress bar
        st.progress(min(monthly_percent / 100, 1.0))
        st.markdown(f"**{monthly_status}**")
        
        # Spending pace indicator
        if spending_vs_expected > 50:
            st.warning(f"⚡ You're spending ${spending_vs_expected:.2f} above expected pace")
        elif spending_vs_expected < -50:
            st.success(f"💰 You're ${abs(spending_vs_expected):.2f} under expected spending")
        
        # =============================================================================
        # CATEGORY BUDGET BREAKDOWN
        # =============================================================================
        
        st.subheader("🏷️ Category Budget Breakdown")
        
        if category_result:
            category_data = [(row.category, float(row.spending)) for row in category_result]
            
            for category, spending in category_data:
                budget = CATEGORY_BUDGETS.get(category, 200)  # Default budget
                category_percent = (spending / budget) * 100 if budget > 0 else 0
                
                # Create columns for category display
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    # Color code based on budget usage
                    if category_percent <= 50:
                        color = "🟢"
                    elif category_percent <= 75:
                        color = "🟡"
                    elif category_percent <= 100:
                        color = "🟠"
                    else:
                        color = "🔴"
                    
                    st.write(f"{color} **{category}**")
                    st.progress(min(category_percent / 100, 1.0))
                    st.caption(f"${spending:.2f} of ${budget:.2f} budget ({category_percent:.1f}%)")
                
                with col2:
                    remaining = budget - spending
                    if remaining >= 0:
                        st.metric("Remaining", f"${remaining:.2f}")
                    else:
                        st.metric("Over", f"${abs(remaining):.2f}", delta_color="inverse")
        else:
            st.info("No spending data available for this month")
        
        # =============================================================================
        # QUICK INSIGHTS & RECOMMENDATIONS
        # =============================================================================
        
        st.subheader("💡 Budget Insights & Tips")
        
        insights = []
        
        # Generate personalized insights
        if daily_spending > DAILY_BUDGET:
            insights.append("🎯 **Today**: Try to avoid unnecessary purchases for the rest of the day")
        
        if weekly_percent_change > 20:
            insights.append("📊 **This Week**: Your spending is up significantly. Review recent purchases")
        elif weekly_percent_change < -20:
            insights.append("📊 **This Week**: Great job reducing spending compared to last week!")
        
        if current_month > expected_spending * 1.2:
            insights.append("📈 **This Month**: You're spending faster than usual. Consider reviewing your budget")
        elif current_month < expected_spending * 0.7:
            insights.append("📈 **This Month**: You're spending less than expected. Good budget control!")
        
        # Category insights
        for category, spending in category_data[:3]:  # Top 3 categories
            budget = CATEGORY_BUDGETS.get(category, 200)
            if spending > budget * 1.1:
                insights.append(f"🏷️ **{category}**: Over budget by ${spending - budget:.2f}")
        
        if insights:
            for insight in insights:
                st.info(insight)
        else:
            st.success("🎉 Your spending looks healthy across all categories!")
            
    except Exception as e:
        st.error(f"Error loading budget dashboard: {e}")
        st.info("Make sure you have transaction data in your PostgreSQL database.")
else:
    st.info("💡 Enable PostgreSQL connection in the sidebar to access your budget dashboard.")

# Search functionality moved to separate page - access via /search

# =============================================================================
# SNOWFLAKE CORTEX AI QUERIES
# =============================================================================

st.markdown('<div id="ai-queries"></div>', unsafe_allow_html=True)
st.header("🤖 Snowflake Cortex AI Queries")

# --- Real Time Financial Data Search

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
else:
    st.info("💡 Enable PostgreSQL connection in the sidebar to access Snowflake Cortex AI queries.")

# =============================================================================
# TRANSACTION MANAGER
# =============================================================================

st.markdown('<div id="transaction-manager"></div>', unsafe_allow_html=True)
st.header("🔧 Transaction Manager")

if use_postgres and engine is not None:


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

    # Display any pending success message at the top - PERSISTENT FEEDBACK
    if st.session_state.get('show_feedback', False):
        if st.session_state.get('cancellation_success', False):
            st.success(f"✅ **TRANSACTION CANCELLED**: {st.session_state.get('cancellation_message', 'Unknown transaction')}")
            
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
        
        # Display first 2 rows by default
        if len(df_pending) <= 2:
            # Show all if 2 or fewer transactions
            st.dataframe(df_pending[['transaction_id', 'date', 'amount', 'merchant', 'category']], use_container_width=True)
        else:
            # Show first 2 rows
            st.write("**First 2 transactions:**")
            st.dataframe(df_pending.head(2)[['transaction_id', 'date', 'amount', 'merchant', 'category']], use_container_width=True)
            
            # Show remaining transactions in expandable section
            with st.expander(f"📋 View all {len(df_pending)} transactions", expanded=False):
                st.dataframe(df_pending[['transaction_id', 'date', 'amount', 'merchant', 'category']], use_container_width=True, height=300)
        
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
    

else:
    st.info("💡 Enable PostgreSQL connection in the sidebar to access transaction management features.")

# =============================================================================
# SNOWFLAKE ANALYTICS
# =============================================================================

# =============================================================================
# SNOWFLAKE CORTEX AGENT
# =============================================================================

st.markdown('<div id="snowflake-analytics"></div>', unsafe_allow_html=True)
st.title("❄️ Snowflake Financial Analytics")

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
