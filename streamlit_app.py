import streamlit as st
import pandas as pd
import json
import re
import os
from typing import Optional
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from db import init_db, make_engine, make_session_factory, save_completion_with_session, fetch_history_with_session

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

st.title(":material/network_intel_node: Past Financials")

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

# Retrieve Snowflake data
data = session.sql("SELECT * FROM BUILD25_POSTGRES_CORTEX.PUBLIC.BUDGET_ANALYSIS")
df = data.to_pandas()

st.header("Search Snowflake with Cortex")

# Prompting
user_queries = ["Provide a summary of my spending for Bills & Utilities.", "What's my biggest spending category in the last year, and how has it changed over time?"]

questions_list = st.selectbox("What would you like to know?", user_queries)

# Create a text area for the user to enter or edit a prompt
question = st.text_area("Enter a question:", value=questions_list)

messages = [
    {
        'role': 'system',
        'content': 'You are a helpful assistant that uses provided data to answer natural language questions.'
    },
    {
        'role': 'user',
        'content': (
            f'The user has asked a question: {question}. '
            f'Please use this data to answer the question: {df.to_markdown(index=False)}'
        )
    }
]

# Cortex parameters
cortex_params = {
    'temperature': 0.7,
    # 'max_tokens': 1000,
    'guardrails': True
}

# Response generation
def generate_response(messages, params=None):
    if params is None:
        params = {}
    
    # Prepare the prompt data for Cortex
    prompt_data = {
        'messages': messages,
        **params
    }
    
    prompt_json = escape_sql_string(json.dumps(prompt_data))
    response = session.sql(
        "select snowflake.cortex.complete(?, ?)", 
        params=['claude-3-5-sonnet', prompt_json]
    ).collect()[0][0]
    
    return response

def escape_sql_string(s):
    return s.replace("'", "''")



if st.button("Submit"):
    with st.spinner("Generating response ...", show_time=True):
        with st.expander(":material/output: Generated Output", expanded=True):
            response = generate_response(messages, cortex_params)
            st.write(response)
            
            # Optionally save the prompt/result to PostgreSQL using ORM
            if use_postgres and engine is not None:
                try:
                    SessionFactory = make_session_factory(engine)
                    with SessionFactory() as db_sess:
                        # Convert response to JSON if it's a string
                        result_json = {"response": response} if isinstance(response, str) else response
                        c = save_completion_with_session(db_sess, question, result_json)
                    st.info(f"Saved completion to PostgreSQL (id={c.id})")
                except Exception as e:
                    st.error(f"Failed to save to PostgreSQL: {e}")

with st.expander(":material/database: See Data", expanded=False):
    df

# Create visualizations
st.subheader("Budget Analysis Charts")

if not df.empty:
    col1, col2 = st.columns(2)
    
    with col1:
        # Chart 1: Spending by Category
        if 'CATEGORY' in df.columns and 'TOTAL_SPEND' in df.columns:
            category_spend = df.groupby('CATEGORY')['TOTAL_SPEND'].sum().sort_values(ascending=False)
            st.bar_chart(category_spend, use_container_width=True)
            st.caption("Total Spending by Category")
    
    with col2:
        # Chart 2: Budget vs Actual Spending
        if 'CATEGORY' in df.columns and 'BUDGET_ALLOCATION' in df.columns and 'TOTAL_SPEND' in df.columns:
            budget_comparison = df.groupby('CATEGORY').agg({
                'BUDGET_ALLOCATION': 'sum',
                'TOTAL_SPEND': 'sum'
            }).sort_values('TOTAL_SPEND', ascending=False)
            st.bar_chart(budget_comparison, use_container_width=True)
            st.caption("Budget vs Actual Spending by Category")
else:
    st.info("No data available for visualization.")

# --- Real Time Financial Data Search
st.markdown("---")
st.header("Real Time Financial Data Search")

if use_postgres and engine is not None:
    st.write("### Search Account in PostgreSQL")
    acct_search_input = st.text_input("Account name to search (PostgreSQL):", value="")
    
    if "account_search_done" not in st.session_state:
        st.session_state["account_search_done"] = False
        st.session_state["account_search_query"] = ""
        st.session_state["account_search_results"] = []

    if st.button("Search Account"):
        if not acct_search_input.strip():
            st.warning("Enter an account name to search for.")
        else:
            # perform a simple ILIKE search on accounts
            SessionFactory = make_session_factory(engine)
            with SessionFactory() as db_sess:
                try:
                    rows = db_sess.execute(
                        text("SELECT account_id, account_name, current_balance FROM accounts WHERE account_name ILIKE :q LIMIT 10"), 
                        {"q": f"%{acct_search_input}%"}
                    ).fetchall()
                    st.session_state["account_search_done"] = True
                    st.session_state["account_search_query"] = acct_search_input
                    # SQLAlchemy Row objects expose a _mapping for dict-like access
                    st.session_state["account_search_results"] = [dict(r._mapping) for r in rows]
                    
                    if rows:
                        st.success(f"Found {len(rows)} matching account(s).")
                        for r in rows:
                            st.write(f"- {r[1]} (id={r[0]}) — balance: ${r[2]}")
                        # if exactly one match, prefill the account field used by queries
                        if len(rows) == 1:
                            st.info("One account found — pre-filling account for the next query.")
                            st.session_state["selected_account_name"] = rows[0][1]
                    else:
                        st.info("No matching accounts found in PostgreSQL.")
                except Exception as e:
                    st.error(f"Error searching accounts: {e}")

    # Financial Q&A with Cortex-powered Text-to-SQL
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

else:
    st.info("Enable PostgreSQL connection in the sidebar to access real-time financial data search.")

# --- Completion History
st.markdown("---")
st.header("Saved Prompt History (PostgreSQL)")

if use_postgres and engine is not None:
    try:
        SessionFactory = make_session_factory(engine)
        with SessionFactory() as db_sess:
            rows = fetch_history_with_session(db_sess, limit=50)
        if rows:
            for r in rows:
                st.subheader(f"#{r.id} — {r.created_at}")
                st.write(r.prompt)
                # show a collapsed JSON view of result
                with st.expander("Result JSON"):
                    try:
                        st.json(r.result)
                    except Exception:
                        st.write(r.result)
        else:
            st.write("No history found.")
    except Exception as e:
        st.error(f"Failed to load history: {e}")
else:
    st.write("Enable PostgreSQL connection to view saved history.")
