import streamlit as st
import json
import os
from typing import Optional
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from db import init_db, make_engine, make_session_factory, save_completion_with_session, fetch_history_with_session
from snowflake.snowpark.functions import ai_complete
import socket
import urllib.request
import urllib.error


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



# Set the title of the Streamlit app
st.title("Snowflake + Postgres + Cortex Example ❄️ + 🐘")

# Sidebar: Postgres configuration (st.secrets -> env -> UI)
st.sidebar.header("Postgres configuration")
# Try st.secrets first
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

use_postgres = st.sidebar.checkbox("Enable Postgres saving", value=bool(pg_host_default and pg_user_default and pg_password_default and pg_db_default))

# Snowflake configuration
st.sidebar.header("Snowflake / Cortex configuration")
secrets_sf = st.secrets.get("connections", {}) if hasattr(st, "secrets") else {}
sf_conn = secrets_sf.get("snowflake", {}) if isinstance(secrets_sf, dict) else {}

# If st.secrets didn't provide Snowflake creds, try to load .streamlit/secrets.toml directly
if (not sf_conn) and os.path.exists(os.path.join(os.getcwd(), ".streamlit", "secrets.toml")):
    try:
        import tomllib
        secrets_path = os.path.join(os.getcwd(), ".streamlit", "secrets.toml")
        with open(secrets_path, "rb") as f:
            parsed = tomllib.load(f)
        file_connections = parsed.get("connections", {}) if isinstance(parsed, dict) else {}
        file_sf = file_connections.get("snowflake", {}) if isinstance(file_connections, dict) else {}
        if file_sf:
            sf_conn = file_sf
            st.sidebar.info("Loaded Snowflake credentials from .streamlit/secrets.toml")
    except Exception as e:
        # don't crash the app for toml parse errors; show a small warning in sidebar
        st.sidebar.warning(f"Could not parse .streamlit/secrets.toml: {e}")

sf_account_default = sf_conn.get("account") or os.environ.get("SF_ACCOUNT", "")
sf_user_default = sf_conn.get("user") or os.environ.get("SF_USER", "")
sf_password_default = sf_conn.get("password") or os.environ.get("SF_PASSWORD", "")
sf_role_default = sf_conn.get("role") or os.environ.get("SF_ROLE", "")
sf_warehouse_default = sf_conn.get("warehouse") or os.environ.get("SF_WAREHOUSE", "")
sf_database_default = sf_conn.get("database") or os.environ.get("SF_DATABASE", "")
sf_schema_default = sf_conn.get("schema") or os.environ.get("SF_SCHEMA", "")

sf_account = st.sidebar.text_input("Account", value=sf_account_default)
sf_user = st.sidebar.text_input("User", value=sf_user_default)
sf_password = st.sidebar.text_input("Password", value=sf_password_default, type="password")
sf_role = st.sidebar.text_input("Role", value=sf_role_default)
sf_warehouse = st.sidebar.text_input("Warehouse", value=sf_warehouse_default)
sf_database = st.sidebar.text_input("Database", value=sf_database_default)
sf_schema = st.sidebar.text_input("Schema", value=sf_schema_default)

enable_snowflake = st.sidebar.checkbox("Enable Snowflake Cortex", value=bool(sf_account_default and sf_user_default and sf_password_default))

# --- Diagnostics helper (shows public IP, DNS for SF host, and admin SQL snippet)
with st.sidebar.expander("Diagnostics / Network info", expanded=False):
    st.write("Use this panel to gather information for Snowflake network policy troubleshooting.")
    if st.button("Show network diagnostics"):
        # connection method
        conn_method = "Streamlit managed connection (st.connection)" if hasattr(st, "connection") else "Snowpark builder (snowflake.snowpark.Session)"
        st.write(f"Connection method the app will try: **{conn_method}**")

        # public IP
        public_ip = None
        try:
            with urllib.request.urlopen("https://ipinfo.io/ip", timeout=5) as r:
                public_ip = r.read().decode().strip()
        except Exception as e:
            st.warning(f"Could not fetch public IP: {e}")

        if public_ip:
            st.write("Your public IP (outbound):")
            st.code(public_ip)

        # DNS resolution for Snowflake host
        if sf_account:
            sf_host = f"{sf_account}.snowflakecomputing.com"
            st.write(f"DNS resolution for Snowflake host: **{sf_host}**")
            try:
                infos = socket.getaddrinfo(sf_host, 443)
                addrs = sorted({i[4][0] for i in infos})
                for a in addrs:
                    st.write(f"- {a}")
            except Exception as e:
                st.warning(f"DNS resolution failed: {e}")
        else:
            st.info("No Snowflake account configured in the sidebar (Account field is empty).")

        st.markdown("**Admin SQL snippet (copy & paste to Snowflake ACCOUNTADMIN/NETWORKADMIN)**")
        st.code("""-- Replace POLICY_NAME and IP_OR_CIDR below
ALTER NETWORK POLICY POLICY_NAME
  SET ALLOWED_IP_LIST = ('IP_OR_CIDR');
""")
        st.markdown("---")
        if st.button("Check Snowflake demo tables"):
            # Attempt to get a Snowflake session (prefer Streamlit connection)
            sf_sess = None
            try:
                if hasattr(st, "connection"):
                    try:
                        sf_sess = st.connection("snowflake").session()
                    except Exception:
                        sf_sess = None
                if sf_sess is None:
                    try:
                        from snowflake.snowpark import Session as SnowSession
                        sf_cfg = {
                            "account": sf_account,
                            "user": sf_user,
                            "password": sf_password,
                            "role": sf_role,
                            "warehouse": sf_warehouse,
                            "database": sf_database,
                            "schema": sf_schema,
                        }
                        sf_cfg = {k: v for k, v in sf_cfg.items() if v}
                        sf_sess = SnowSession.builder.configs(sf_cfg).create()
                    except Exception as e:
                        st.error(f"Could not create Snowflake session: {e}")
                        sf_sess = None

            except Exception as e:
                st.error(f"Snowflake diagnostics failed to initialize session: {e}")
                sf_sess = None

            if sf_sess is None:
                st.warning("No Snowflake session available. Ensure Snowflake is enabled in the sidebar and credentials are correct.")
            else:
                demo_tables = ["BUDGET_ANALYSIS", "CUSTOM_CATEGORIES", "FINANCIAL_NEWS_SENTIMENT", "TRANSACTIONS"]
                st.write("Checking demo tables (case-insensitive):")
                for t in demo_tables:
                    try:
                        # Use simple count; wrap in try/except to catch missing table errors
                        df = sf_sess.sql(f"SELECT COUNT(*) AS cnt FROM {t}")
                        rows = df.collect()
                        cnt = rows[0][0] if rows else None
                        st.write(f"- {t}: {cnt} rows")
                    except Exception as e:
                        st.error(f"- {t}: error — {e}")
        st.markdown("---")
        st.write("### Run a sample Snowflake SQL (quick test)")
        sample_sql = st.text_area("SQL to run in Snowflake:", value=("SELECT\n  CATEGORY,\n  AVG(SPEND_VS_BUDGET_PCT) AS AVG_BUDGET_PERCENTAGE,\n  SUM(TOTAL_SPEND) AS TOTAL_SPEND,\n  SUM(BUDGET_ALLOCATION) AS TOTAL_BUDGET,\n  COUNT(DISTINCT ANALYSIS_PERIOD) AS NUM_MONTHS\nFROM\n  BUDGET_ANALYSIS\nWHERE\n  PERIOD_TYPE ILIKE '%Monthly%'\n  AND ANALYSIS_PERIOD >= '2025-01-01'\n  AND ANALYSIS_PERIOD < '2025-04-01'\n  AND SPEND_VS_BUDGET_PCT > 100\nGROUP BY\n  CATEGORY\nHAVING\n  COUNT(DISTINCT ANALYSIS_PERIOD) >= 2\nORDER BY\n  AVG_BUDGET_PERCENTAGE DESC;"))
        if st.button("Run sample SQL in Snowflake"):
            sf_sess = None
            try:
                if hasattr(st, "connection"):
                    try:
                        sf_sess = st.connection("snowflake").session()
                    except Exception:
                        sf_sess = None
                if sf_sess is None:
                    try:
                        from snowflake.snowpark import Session as SnowSession
                        sf_cfg = {
                            "account": sf_account,
                            "user": sf_user,
                            "password": sf_password,
                            "role": sf_role,
                            "warehouse": sf_warehouse,
                            "database": sf_database,
                            "schema": sf_schema,
                        }
                        sf_cfg = {k: v for k, v in sf_cfg.items() if v}
                        sf_sess = SnowSession.builder.configs(sf_cfg).create()
                    except Exception as e:
                        st.error(f"Could not create Snowflake session: {e}")
                        sf_sess = None

            except Exception as e:
                st.error(f"Snowflake SQL runner failed to initialize session: {e}")
                sf_sess = None

            if sf_sess is None:
                st.warning("No Snowflake session available. Ensure credentials are set and Snowflake is enabled in the sidebar.")
            else:
                try:
                    df = sf_sess.sql(sample_sql)
                    rows = df.collect()
                    if not rows:
                        st.write("Query ran successfully but returned no rows.")
                    else:
                        # Show column names if present
                        try:
                            cols = [c[0] for c in df.schema.fields]
                        except Exception:
                            # fallback: attempt to infer from first row tuple length
                            cols = [f"col{i}" for i in range(len(rows[0]))]
                        # Limit to first 20 rows for display
                        display_rows = [list(r) for r in rows[:20]]
                        import pandas as pd

                        st.write(f"Showing {len(display_rows)} row(s) (truncated)")
                        st.dataframe(pd.DataFrame(display_rows, columns=cols))
                except Exception as e:
                    st.error(f"Error running sample SQL: {e}")

# Try to obtain a Snowpark session when requested
sf_session = None
if enable_snowflake:
    try:
        # Prefer Streamlit managed Snowflake connection if available
        if hasattr(st, "connection"):
            try:
                sf_session = st.connection("snowflake").session()
            except Exception:
                sf_session = None

        # If not available, try to create a Snowpark session via snowflake.snowpark
        if sf_session is None:
            try:
                from snowflake.snowpark import Session as SnowSession
                sf_cfg = {
                    "account": sf_account,
                    "user": sf_user,
                    "password": sf_password,
                    "role": sf_role,
                    "warehouse": sf_warehouse,
                    "database": sf_database,
                    "schema": sf_schema,
                }
                # Remove empty values
                sf_cfg = {k: v for k, v in sf_cfg.items() if v}
                sf_session = SnowSession.builder.configs(sf_cfg).create()
            except Exception:
                sf_session = None

        if sf_session is not None:
            st.sidebar.success("Snowflake connection OK")
        else:
            st.sidebar.warning("Snowflake connection not available (check credentials or Streamlit connection)")
    except Exception as e:
        st.sidebar.error(f"Snowflake connection failed: {e}")



# Main UI: Prompt input and Generate button
st.subheader("Financial Analysis")
prompt = st.text_area(
    "Enter a prompt:",
    "Summarize last 3 months spending by category and identify the top 3 categories with the largest month-over-month increases or decreases.")

col1, col2 = st.columns([1, 1])
with col1:
    model = st.selectbox("Model", options=["claude-3-5-sonnet", "claude-2.1"], index=0)
with col2:
    show_details = st.checkbox("Show details (raw JSON)", value=True)
# Quick SQL mode: treat the prompt as SQL and run it directly in Snowflake
run_as_sql = st.checkbox("Treat prompt as SQL and run in Snowflake", value=False)

engine: Optional[Engine] = None
if use_postgres:
    if not (pg_host and pg_user and pg_password and pg_db):
        st.sidebar.warning("Enter all Postgres credentials to enable saving.")
        use_postgres = False
    else:
            try:
                engine = make_postgres_engine(pg_user, pg_password, pg_host, int(pg_port or 5432), pg_db, sslmode=pg_sslmode or None)
                ensure_table(engine)
                st.sidebar.success("Postgres connection OK")
            except Exception as e:
                st.sidebar.error(f"Postgres connection failed: {e}")
                use_postgres = False


if st.button("Generate Completion"):
    try:
        # Attempt to obtain a Snowflake session (prefer Streamlit managed connection)
        sf_session_local = None
        try:
            if hasattr(st, "connection"):
                try:
                    sf_session_local = st.connection("snowflake").session()
                except Exception:
                    sf_session_local = None
            if sf_session_local is None:
                try:
                    from snowflake.snowpark import Session as SnowSession
                    sf_cfg = {
                        "account": sf_account,
                        "user": sf_user,
                        "password": sf_password,
                        "role": sf_role,
                        "warehouse": sf_warehouse,
                        "database": sf_database,
                        "schema": sf_schema,
                    }
                    sf_cfg = {k: v for k, v in sf_cfg.items() if v}
                    sf_session_local = SnowSession.builder.configs(sf_cfg).create()
                except Exception:
                    sf_session_local = None
        except Exception:
            sf_session_local = None

        # If Quick SQL mode is enabled, validate and run the prompt as SQL in Snowflake
        performed_sql = False
        if run_as_sql:
            if sf_session_local is None:
                st.error("No Snowflake session available. Enable Snowflake in the sidebar and ensure credentials are correct.")
            else:
                sql_text = prompt.strip()
                # Basic safety checks: require SELECT/WITH and forbid DML/DDL keywords
                low = sql_text.lower()
                forbidden = [
                    "insert ", "update ", "delete ", "merge ", "drop ", "create ", "alter ",
                    "grant ", "revoke ", "call ", "put ", "get ", "copy into",
                ]
                if not (low.startswith("select") or low.startswith("with")):
                    st.error("Quick SQL mode requires the prompt to be a SELECT (or WITH) query.")
                elif any(k in low for k in forbidden):
                    st.error("Detected forbidden statement in SQL. Only read-only SELECT queries are allowed in Quick SQL mode.")
                else:
                    try:
                        with st.spinner("Running SQL in Snowflake..."):
                            df = sf_session_local.sql(sql_text)
                            rows = df.collect()
                        if not rows:
                            st.success("Query ran successfully but returned no rows.")
                        else:
                            # infer column names
                            try:
                                cols = [c.name for c in df.schema.fields]
                            except Exception:
                                cols = [f"col{i}" for i in range(len(rows[0]))]
                            # convert to displayable table
                            try:
                                import pandas as pd
                                display_rows = [list(r) for r in rows[:200]]
                                st.dataframe(pd.DataFrame(display_rows, columns=cols))
                            except Exception:
                                # fallback: simple text table
                                for r in rows[:50]:
                                    st.write(r)
                        # mark that we already handled the SQL execution and should skip ai_complete
                        performed_sql = True
                    except Exception as e:
                        st.error(f"SQL execution error: {e}")
                        performed_sql = False

        # Otherwise, use Cortex ai_complete path as before (only if we did not already run SQL)
        if not performed_sql:
            if sf_session_local is None:
                st.error("Snowflake connection not available for Cortex completion.")
                raise RuntimeError("Snowflake session not available")

            # Display a spinner while waiting for the response
            with st.spinner("Generating response..."):
                # Call the Complete function with the desired model and the user's prompt
                df = sf_session_local.range(1).select(
                    ai_complete(
                        model=model,
                        prompt=prompt,
                        show_details=show_details,
                    ).alias("detailed_response")
                )
                # Extracting result from the generated JSON output
                json_string = df.collect()[0][0]
                data = json.loads(json_string)
                # keep the whole JSON for saving/inspection
                result = data

            # Display the generated text
            st.success("Completion generated!")
            if show_details:
                st.json(result)
            else:
                # Attempt to display a friendly text if available
                try:
                    messages = data['choices'][0]['messages']
                    st.write(messages)
                except Exception:
                    st.write(result)

            # Optionally save the prompt/result to Postgres using ORM
            if use_postgres and engine is not None:
                try:
                    SessionFactory = make_session_factory(engine)
                    with SessionFactory() as db_sess:
                        c = save_completion_with_session(db_sess, prompt, result)
                    st.info(f"Saved completion to Postgres (id={c.id})")
                except Exception as e:
                    st.error(f"Failed to save to Postgres: {e}")

    except Exception as e:
        st.error(f"An error occurred: {e}")


# History viewer (moved to bottom)

# --- Financial Q&A demo
st.markdown("---")
st.header("Real Time Financial Data")

# --- Postgres-first account search
st.write("### Search account in Postgres")
acct_search_input = st.text_input("Account name to search (Postgres):", value="")
if "account_search_done" not in st.session_state:
    st.session_state["account_search_done"] = False
    st.session_state["account_search_query"] = ""
    st.session_state["account_search_results"] = []

if st.button("Search Account"):
    if engine is None:
        st.error("Connect to Postgres in the sidebar to search accounts.")
    elif not acct_search_input.strip():
        st.warning("Enter an account name to search for.")
    else:
        # perform a simple ILIKE search on accounts
        SessionFactory = make_session_factory(engine)
        with SessionFactory() as db_sess:
            rows = db_sess.execute(text("SELECT account_id, account_name, current_balance FROM accounts WHERE account_name ILIKE :q LIMIT 10"), {"q": f"%{acct_search_input}%"}).fetchall()
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
                st.info("No matching accounts found in Postgres.")

user_question = st.text_input("Ask a question about your finances:", "How much did I spend on groceries last week?")



def extract_entities_with_cortex(question: str, sf_session=None) -> dict:
    """Attempt to use Snowflake Cortex EXTRACT_ANSWER path via ai_complete; fall back silently if unavailable."""
    try:
        if sf_session is None:
            sf_session = st.connection("snowflake").session()
        # Use ai_complete to get structured extraction; this is a demo pattern and may need tuning
        df = sf_session.range(1).select(
            ai_complete(model=model, prompt=f"EXTRACT_ANSWER: {question}", show_details=True).alias("d")
        )
        payload = df.collect()[0][0]
        parsed = json.loads(payload)
        # Try to pull out recognized entities (this depends on the model's output format)
        return parsed
    except Exception:
        return {}


def heuristic_extract(question: str) -> dict:
    """Very small heuristic extractor for demo purposes."""
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
    Session = sessionmaker(bind=engine)
    with Session() as s:
        # If asking about balance and account_name provided
        if ("balance" in user_question.lower() or "what's the balance" in user_question.lower()) and account_name:
            row = s.execute(
                text("SELECT account_id, account_name, current_balance FROM accounts WHERE account_name ILIKE :name LIMIT 1"),
                {"name": account_name}
            ).fetchone()
            return {"type": "balance", "result": dict(row) if row else None}

        # Otherwise, attempt sum on transactions
        params = {}
        # start with no extra where clauses; JOIN already ensures t.account_id = accounts.account_id
        where_clauses = []
        sql = "SELECT SUM(t.amount) as total FROM transactions t JOIN accounts ON t.account_id = accounts.account_id"

        if category:
            where_clauses.append("t.category ILIKE :category")
            params["category"] = category
        if start_date and end_date:
            # Use plain named parameters; let the DB cast/interpret the string as needed.
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
    if engine is None:
        st.error("Connect to Postgres in the sidebar to run demo financial queries.")
    elif not st.session_state.get("account_search_done"):
        st.error("Please run the Postgres account search first and select an account before running the Cortex-backed query.")
    else:
        # First try Cortex extraction (if Snowflake connection exists), else heuristic
        entities = heuristic_extract(user_question)
        cortex_out = {}
        try:
            cortex_out = extract_entities_with_cortex(user_question)
        except Exception:
            cortex_out = {}

        # Prefer cortex entities if they look useful
        final_entities = entities
        if isinstance(cortex_out, dict) and cortex_out:
            # naive merge
            final_entities.update({k: v for k, v in cortex_out.items() if v})

        st.write("Detected entities:", final_entities)

        # prefer selected account from Postgres-first search if present
        acct_name = st.session_state.get("selected_account_name") or final_entities.get("account_name")
        qres = query_finances(engine, final_entities.get("start_date"), final_entities.get("end_date"), final_entities.get("category"), acct_name)
        if qres.get("type") == "balance":
            if qres.get("result"):
                st.success(f"Account '{qres['result']['account_name']}' balance: ${qres['result']['current_balance']}")
            else:
                st.write("Account not found.")
        else:
            st.success(f"Total: ${qres.get('total')}")
        # Show the SQL and parameters used (for demo / debugging)
        st.markdown("**SQL sent to Postgres:**")
        st.code(qres.get("sql", ""))
        st.markdown("**Parameters:**")
        st.json(qres.get("params", {}))


    # History viewer (moved to bottom)
    st.markdown("---")
    st.header("Saved prompt history (Postgres)")
    if engine is not None:
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
        st.write("Enable Postgres and connect to view saved history.")

session = st.connection("snowflake")
xyz = session.sql("SHOW CORTEX SEARCH SERVICES;")
st.write(xyz)
