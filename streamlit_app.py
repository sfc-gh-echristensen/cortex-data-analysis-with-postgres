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

# Agent configuration
DATABASE = "BUILD25_POSTGRES_CORTEX"
SCHEMA = "AGENTS"
AGENT = "POSTGRES_AGENT"

# Build full URL
HOST = st.secrets.get("agent", {}).get("SNOWFLAKE_HOST")
print("Using Snowflake host:", HOST)
API_ENDPOINT = f"https://{HOST}/api/v2/databases/{DATABASE}/schemas/{SCHEMA}/agents/{AGENT}:run"
API_TIMEOUT = 60  # timeout in seconds for requests library

st.header("Search Snowflake with Cortex Agent")

# Initialize session state for messages
if "messages" not in st.session_state:
    st.session_state.messages = []

# Predefined user queries
user_queries = [
    "Provide a summary of my spending for Bills & Utilities.",
    "What's my biggest spending category in the last year, and how has it changed over time?"
]

# UI for question selection/input
questions_list = st.selectbox("What would you like to know?", user_queries)
question = st.text_area("Enter a question:", value=questions_list)

# Add a reset button
if st.button("Reset Conversation"):
    st.session_state.messages = []
    st.success("Conversation reset!")

if st.button("Submit"):
    # Add user message to conversation
    user_message = {
        "role": "user",
        "content": [{"type": "text", "text": question}]
    }
    
    # Create a clean messages list for this request
    messages_to_send = [user_message]
    
    # Prepare agent request payload with correct structure
    payload = {
        "messages": messages_to_send
    }
    
    # Placeholders for streaming display
    status_placeholder = st.empty()
    output_container = st.container()
    text_placeholder = output_container.empty()
    
    try:
        # Get authentication token from session
        token = HOST = st.secrets.get("agent", {}).get("SNOWFLAKE_PAT")
        
        # Make API call using requests with streaming
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        status_placeholder.info("Connecting to agent...")
        
        response = requests.post(
            API_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=API_TIMEOUT,
            verify=False,  # Disable SSL verification for hostname with underscore
            stream=True  # Enable streaming
        )
        
        # Check response status
        if response.status_code != 200:
            status_placeholder.error(f"Error: Status {response.status_code}")
            st.text(response.text)
        else:
            # Process SSE stream
            text_buffer = ""
            final_message = None
            buffer = ""
            
            # Stream the response line by line
            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue
                
                line = line.strip()
                
                # Parse SSE format
                if line.startswith('event:'):
                    event_type = line.split('event:', 1)[1].strip()
                    buffer = event_type
                    
                elif line.startswith('data:'):
                    data_line = line.split('data:', 1)[1].strip()
                    
                    try:
                        data = json.loads(data_line)
                        
                        # Show status updates
                        if buffer == 'response.status':
                            status_placeholder.info(f"Status: {data.get('message', '')}")
                        
                        # Stream text deltas in real-time
                        elif buffer == 'response.text.delta':
                            text_buffer += data.get('text', '')
                            text_placeholder.markdown(text_buffer)
                        
                        # Parse the final response event
                        elif buffer == 'response':
                            final_message = data
                            
                    except json.JSONDecodeError:
                        pass
            
            status_placeholder.empty()  # Clear status
            
            if final_message:
                # Add messages to session state
                st.session_state.messages.append(user_message)
                st.session_state.messages.append(final_message)
                
                # Clear the streaming text and show final formatted output
                text_placeholder.empty()
                
                # Display final response
                with output_container.expander(":material/output: Generated Output", expanded=True):
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
                            with st.expander("Thinking"):
                                st.write(item.get("thinking", {}).get("text", ""))
                        
                        elif item_type == "tool_use":
                            with st.expander(f"Tool Use: {item.get('tool_use', {}).get('name', 'Unknown')}"):
                                st.json(item.get("tool_use"))
                        
                        elif item_type == "tool_result":
                            with st.expander("Tool Result"):
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
                    
                    # Optionally save the prompt/result to PostgreSQL using ORM
                    if use_postgres and engine is not None:
                        try:
                            SessionFactory = make_session_factory(engine)
                            with SessionFactory() as db_sess:
                                # Convert response to JSON if it's a string
                                result_json = {"response": response_text} if isinstance(response_text, str) else response_text
                                c = save_completion_with_session(db_sess, question, result_json)
                            st.info(f"Saved completion to PostgreSQL (id={c.id})")
                        except Exception as e:
                            st.error(f"Failed to save to PostgreSQL: {e}")
            else:
                st.warning("No final response found in events")
                
    except Exception as e:
        st.error(f"Agent request failed: {str(e)}")
        import traceback
        st.code(traceback.format_exc())

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