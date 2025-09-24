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

    # Financial Q&A
    user_question = st.text_input("Ask a question about your finances:", "How much did I spend on groceries last week?")

    def heuristic_extract(question: str) -> dict:
        """Very simple heuristic extractor for demo purposes."""
        import re
        from datetime import datetime, timedelta

        q = question.lower()
        entities = {}

        # timeframe: last week / this week / last month
        if "last week" in q:
            today = datetime.utcnow().date()
            # last calendar week (Mon-Sun) ending last Sunday
            last_sunday = today - timedelta(days=today.weekday() + 1)
            start = last_sunday - timedelta(days=6)
            end = last_sunday
            entities["start_date"] = start.isoformat()
            entities["end_date"] = end.isoformat()
        elif "this week" in q:
            today = datetime.utcnow().date()
            start = datetime.combine(today - timedelta(days=today.weekday()), datetime.min.time()).date()
            end = today
            entities["start_date"] = start.isoformat()
            entities["end_date"] = end.isoformat()

        # category
        m = re.search(r"grocer|grocery|groceries", q)
        if m:
            entities["category"] = "Groceries"

        # account
        if "checking" in q:
            entities["account_name"] = "Checking"

        return entities

    def query_finances(engine: Engine, start_date: str | None, end_date: str | None, category: str | None, account_name: str | None):
        """Run parameterized queries against the demo financial schema."""
        from datetime import datetime
        SessionFactory = sessionmaker(bind=engine)
        with SessionFactory() as s:
            # If asking about balance and account_name provided
            if ("balance" in user_question.lower() or "what's the balance" in user_question.lower()) and account_name:
                row = s.execute(
                    text("SELECT account_id, account_name, current_balance FROM accounts WHERE account_name ILIKE :name LIMIT 1"),
                    {"name": account_name}
                ).fetchone()
                return {"type": "balance", "result": dict(row._mapping) if row else None}

            # Otherwise, attempt sum on transactions
            params = {}
            where_clauses = []
            sql = "SELECT SUM(t.amount) as total FROM transactions t JOIN accounts ON t.account_id = accounts.account_id"

            if category:
                where_clauses.append("t.category ILIKE :category")
                params["category"] = category
            if start_date and end_date:
                where_clauses.append("t.date BETWEEN :start_date AND :end_date")
                params["start_date"] = start_date
                params["end_date"] = end_date
            if account_name:
                where_clauses.append("accounts.account_name ILIKE :acct")
                params["acct"] = account_name

            if where_clauses:
                sql = sql + " WHERE " + " AND ".join(where_clauses)

            row = s.execute(text(sql), params).fetchone()
            total = row[0] if row is not None else None
            return {"type": "sum", "total": float(total) if total is not None else 0.0, "sql": sql, "params": params}

    if st.button("Run Financial Query"):
        if not st.session_state.get("account_search_done"):
            st.error("Please run the PostgreSQL account search first and select an account before running the query.")
        else:
            # Extract entities from the question
            entities = heuristic_extract(user_question)

            # prefer selected account from PostgreSQL-first search if present
            acct_name = st.session_state.get("selected_account_name") or entities.get("account_name")
            
            try:
                qres = query_finances(engine, entities.get("start_date"), entities.get("end_date"), entities.get("category"), acct_name)
                if qres.get("type") == "balance":
                    if qres.get("result"):
                        st.success(f"Account '{qres['result']['account_name']}' balance: ${qres['result']['current_balance']}")
                    else:
                        st.write("Account not found.")
                else:
                    st.success(f"Total: ${qres.get('total')}")
                
                # Show the SQL and parameters used (for demo / debugging) - in a collapsible section
                with st.expander("Query Details", expanded=False):
                    st.write("Detected entities:", entities)
                    st.markdown("**SQL sent to PostgreSQL:**")
                    st.code(qres.get("sql", ""))
                    st.markdown("**Parameters:**")
                    st.json(qres.get("params", {}))
            except Exception as e:
                st.error(f"Error running financial query: {e}")

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
