"""
Snowflake Cortex AI Queries Module
Handles AI-powered financial queries and text-to-SQL conversion
"""

import streamlit as st
import pandas as pd
import json
import re
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from src.db import make_session_factory, save_completion_with_session, fetch_history_with_session


def render_cortex_queries(engine: Engine, use_postgres: bool, session):
    """
    Render the Cortex AI queries section
    
    Args:
        engine: SQLAlchemy Engine instance
        use_postgres: Boolean indicating if PostgreSQL is enabled
        session: Snowflake session for Cortex API calls
    """
    st.markdown('<div id="ai-queries"></div>', unsafe_allow_html=True)
    st.header("🤖 Snowflake Cortex AI Queries")
    
    if not use_postgres or engine is None:
        st.info("💡 Enable PostgreSQL connection in the sidebar to access Snowflake Cortex AI queries.")
        return
    
    # Account selection
    _render_account_selection(engine)
    
    # AI-powered financial query interface
    _render_query_interface(engine, session)
    
    # Query history
    _render_query_history(engine)


def _render_account_selection(engine: Engine):
    """Render account selection dropdown"""
    st.write("### Select Account")
    
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
                    selected_row = account_rows[selected_index - 1]
                    st.success(f"✅ Selected: **{selected_row[1]}** (ID: {selected_row[0]}) — Balance: **${selected_row[2]:,.2f}**")
                else:
                    if "selected_account_name" in st.session_state:
                        del st.session_state["selected_account_name"]
                    st.session_state["account_search_done"] = False
                    
            else:
                st.warning("No accounts found in the database.")
                
        except Exception as e:
            st.error(f"Error loading accounts: {e}")


def _render_query_interface(engine: Engine, session):
    """Render AI-powered query interface"""
    st.write("### AI-Powered Financial Queries")
    user_question = st.text_input("Ask a question about your finances:", "How much did I spend on groceries last week?")

    if st.button("Run AI-Powered Financial Query"):
        if not st.session_state.get("account_search_done"):
            st.warning("Consider running the PostgreSQL account search first to identify available accounts.")
        
        with st.spinner("Generating SQL with Cortex AI..."):
            # Get schema information
            schema_info = _get_schema_info()
            
            # Add selected account context if available
            context_question = user_question
            if st.session_state.get("selected_account_name"):
                context_question += f" (Focus on account: {st.session_state['selected_account_name']})"
            
            # Generate SQL using Cortex
            cortex_result = _generate_sql_with_cortex(context_question, schema_info, session)
            
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
                query_result = _execute_cortex_query(engine, cortex_result["sql"], cortex_result.get("params", {}))
                
                if query_result["success"]:
                    result_data = query_result["result"]
                    
                    if result_data:
                        # Display results
                        if len(result_data) == 1 and len(result_data[0]) == 1:
                            # Single value result
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
                
                # Show query details
                with st.expander("🔍 Query Details", expanded=False):
                    st.markdown("**Generated SQL:**")
                    st.code(cortex_result["sql"], language="sql")
                    st.markdown("**Parameters:**")
                    st.json(cortex_result.get("params", {}))
                    if not query_result["success"]:
                        st.markdown("**Error Details:**")
                        st.error(query_result["error"])
                
                # Save to PostgreSQL
                try:
                    SessionFactory = make_session_factory(engine)
                    with SessionFactory() as db_sess:
                        result_json = {"response": str(result_data)} if result_data else {}
                        c = save_completion_with_session(db_sess, user_question, result_json)
                    st.success(f"💾 Saved to PostgreSQL (id={c.id})")
                except Exception as e:
                    st.error(f"Failed to save to PostgreSQL: {e}")


def _render_query_history(engine: Engine):
    """Render saved query history"""
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


def _generate_sql_with_cortex(question: str, schema_info: str, session) -> dict:
    """
    Use Snowflake Cortex to generate SQL from natural language
    
    Args:
        question: Natural language question
        schema_info: Database schema information
        session: Snowflake session
        
    Returns:
        Dictionary with sql, params, and explanation
    """
    try:
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
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {"error": "Could not parse SQL generation response", "raw_response": response}
                
    except Exception as e:
        return {"error": f"Failed to generate SQL: {str(e)}"}


def _get_schema_info() -> str:
    """Get schema information for the financial database"""
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


def _execute_cortex_query(engine: Engine, sql: str, params: dict):
    """Execute the Cortex-generated SQL query"""
    SessionFactory = sessionmaker(bind=engine)
    with SessionFactory() as s:
        try:
            result = s.execute(text(sql), params).fetchall()
            return {"success": True, "result": result, "sql": sql, "params": params}
        except Exception as e:
            return {"success": False, "error": str(e), "sql": sql, "params": params}

