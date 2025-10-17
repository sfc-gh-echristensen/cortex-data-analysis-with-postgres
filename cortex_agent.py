"""
Snowflake Cortex Agent Module
Handles the Cortex AI agent chat interface and subscription management demo
"""

import streamlit as st
import pandas as pd
import json
import requests
from sqlalchemy.engine import Engine
from db import make_session_factory, save_completion_with_session


# Agent configuration
DATABASE = "BUILD25_POSTGRES_CORTEX"
SCHEMA = "AGENTS"
AGENT = "POSTGRES_AGENT"
API_TIMEOUT = 60


def render_cortex_agent(engine: Engine, use_postgres: bool):
    """
    Render the Snowflake Cortex agent chat interface
    
    Args:
        engine: SQLAlchemy Engine instance
        use_postgres: Boolean indicating if PostgreSQL is enabled
    """
    st.markdown('<div id="snowflake-analytics"></div>', unsafe_allow_html=True)
    st.title("❄️ Snowflake Financial Analytics")
    
    # Spending overview chart
    _render_spending_overview()
    
    st.markdown("---")
    st.header("❄️ Chat with Snowflake Cortex Agent")
    
    # Subscription management demo
    _render_subscription_panel()
    
    # Chat interface
    _render_chat_interface(engine, use_postgres)


def _render_spending_overview():
    """Render spending overview chart from Snowflake data"""
    st.subheader("📊 Monthly Spending Overview")
    
    try:
        # Get Snowflake connection from Streamlit
        conn = st.connection("snowflake")
        session = conn.session()
        
        # Get sample data
        sample_df = session.sql("SELECT * FROM TRANSACTIONS LIMIT 5").to_pandas()
        
        # Detect columns
        date_columns = [col for col in sample_df.columns if any(keyword in col.upper() for keyword in ['DATE', 'TIME'])]
        amount_columns = [col for col in sample_df.columns if any(keyword in col.upper() for keyword in ['AMOUNT', 'SPENDING'])]
        category_columns = [col for col in sample_df.columns if any(keyword in col.upper() for keyword in ['CATEGORY', 'TYPE'])]
        
        if date_columns and amount_columns:
            date_col = date_columns[0]
            amount_col = amount_columns[0]
            
            # Create query
            if category_columns:
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
                chart_query = f"""
                SELECT 
                    DATE_TRUNC('month', {date_col}) as month,
                    SUM(ABS({amount_col})) as total_amount
                FROM TRANSACTIONS 
                WHERE {date_col} >= DATEADD('month', -12, CURRENT_DATE())
                GROUP BY DATE_TRUNC('month', {date_col})
                ORDER BY month DESC
                """
            
            chart_df = session.sql(chart_query).to_pandas()
            
            if not chart_df.empty:
                chart_df['MONTH'] = pd.to_datetime(chart_df['MONTH'])
                
                if 'CATEGORY' in chart_df.columns:
                    import altair as alt
                    chart = alt.Chart(chart_df).mark_area().encode(
                        x=alt.X('MONTH:T', title='Month'),
                        y=alt.Y('TOTAL_AMOUNT:Q', title='Total Amount ($)'),
                        color=alt.Color('CATEGORY:N', title='Category'),
                        tooltip=['MONTH:T', 'CATEGORY:N', 'TOTAL_AMOUNT:Q']
                    ).properties(width=700, height=400, title="Monthly Spending by Category").interactive()
                    st.altair_chart(chart, use_container_width=True)
                else:
                    st.line_chart(chart_df.set_index('MONTH')['TOTAL_AMOUNT'])
                
                # Show metrics
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
            else:
                st.warning("No spending data found")
    except Exception as e:
        st.error(f"Error loading Snowflake data: {e}")
        st.info("Showing sample chart due to connection issues")


def _render_subscription_panel():
    """Render subscription management demo panel"""
    # Initialize subscription demo data
    if "demo_subscriptions" not in st.session_state:
        st.session_state.demo_subscriptions = {
            "netflix": {"name": "Netflix", "cost": 15.99, "last_used": "2024-09-15", "status": "active"},
            "spotify": {"name": "Spotify Premium", "cost": 9.99, "last_used": "2024-10-07", "status": "active"},
            "adobe": {"name": "Adobe Creative Cloud", "cost": 52.99, "last_used": "2024-08-12", "status": "active"},
            "gym": {"name": "Planet Fitness", "cost": 24.99, "last_used": "2024-07-20", "status": "active"},
            "hulu": {"name": "Hulu + Live TV", "cost": 76.99, "last_used": "2024-10-05", "status": "active"},
            "microsoft": {"name": "Microsoft 365", "cost": 6.99, "last_used": "2024-10-08", "status": "active"}
        }
    
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
                total_savings = sum(sub['cost'] for sub in cancelled_subs.values())
                for sub_data in cancelled_subs.values():
                    st.write(f"- ~~{sub_data['name']}~~: ${sub_data['cost']}/month")
                st.metric("Monthly Savings", f"${total_savings:.2f}")
            else:
                st.info("No subscriptions cancelled yet. Try asking: 'Tell me about subscriptions I don't use'")
    
    st.write("💡 **Try asking:** 'Tell me about subscriptions I don't use' or 'Which subscriptions should I cancel?'")


def _render_chat_interface(engine: Engine, use_postgres: bool):
    """Render the chat interface with Cortex agent"""
    # Initialize chat messages
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    
    # Display chat history
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            if message["role"] == "user":
                st.markdown(message["content"])
            else:
                _display_assistant_message(message)
    
    # Chat input
    if prompt := st.chat_input("Ask me about your financial data or subscriptions..."):
        # Enhance prompt with subscription context if relevant
        enhanced_prompt = _add_subscription_context(prompt)
        
        # Add to chat history
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get agent response
        with st.chat_message("assistant"):
            _process_agent_response(enhanced_prompt, engine, use_postgres)
    
    # Clear chat button
    if st.button("🗑️ Clear Chat History"):
        st.session_state.chat_messages = []
        st.rerun()


def _add_subscription_context(prompt: str) -> str:
    """Add subscription context to prompts about subscriptions"""
    subscription_keywords = ["subscription", "cancel", "unused", "recurring", "monthly", "netflix", "spotify", "adobe", "gym", "hulu"]
    
    if any(keyword in prompt.lower() for keyword in subscription_keywords):
        active_subs = {k: v for k, v in st.session_state.demo_subscriptions.items() if v["status"] == "active"}
        
        context = f"""
SUBSCRIPTION CONTEXT:
The user has the following active subscriptions:

"""
        for sub_id, sub_data in active_subs.items():
            context += f"- {sub_data['name']}: ${sub_data['cost']}/month (last used: {sub_data['last_used']})\n"
        
        context += f"""
Current date: {pd.Timestamp.now().strftime('%Y-%m-%d')}

User's question: {prompt}
"""
        return context
    
    return prompt


def _display_assistant_message(message):
    """Display assistant message with all content types"""
    content_items = message.get("content", [])
    
    for item in content_items:
        item_type = item.get("type")
        
        if item_type == "text":
            st.markdown(item.get("text", ""))
        elif item_type == "thinking":
            with st.expander("🤔 Thinking"):
                st.write(item.get("thinking", {}).get("text", ""))
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


def _process_agent_response(prompt: str, engine: Engine, use_postgres: bool):
    """Process agent response and display results"""
    # Build API endpoint
    HOST = st.secrets.get("agent", {}).get("SNOWFLAKE_HOST")
    API_ENDPOINT = f"https://{HOST}/api/v2/databases/{DATABASE}/schemas/{SCHEMA}/agents/{AGENT}:run"
    
    user_message = {"role": "user", "content": [{"type": "text", "text": prompt}]}
    payload = {"messages": [user_message]}
    
    with st.status("Thinking...", expanded=True) as status:
        try:
            token = st.secrets.get("agent", {}).get("SNOWFLAKE_PAT")
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            
            status.update(label="Connecting to agent...", state="running")
            
            response = requests.post(API_ENDPOINT, json=payload, headers=headers, timeout=API_TIMEOUT, verify=False, stream=True)
            
            if response.status_code != 200:
                st.error(f"Error: Status {response.status_code}")
                st.text(response.text)
            else:
                # Process streaming response
                _handle_streaming_response(response, status, engine, use_postgres, prompt)
                
        except Exception as e:
            st.error(f"Agent request failed: {str(e)}")
            import traceback
            st.code(traceback.format_exc())


def _handle_streaming_response(response, status, engine, use_postgres, prompt):
    """Handle streaming response from agent"""
    text_buffer = ""
    final_message = None
    buffer = ""
    response_placeholder = st.empty()
    
    for line in response.iter_lines(decode_unicode=True):
        if not line:
            continue
        
        line = line.strip()
        
        if line.startswith('event:'):
            buffer = line.split('event:', 1)[1].strip()
        elif line.startswith('data:'):
            data_line = line.split('data:', 1)[1].strip()
            
            try:
                data = json.loads(data_line)
                
                if buffer == 'response.status':
                    status.update(label=f"Status: {data.get('message', '')}", state="running")
                elif buffer == 'response.text.delta':
                    text_buffer += data.get('text', '')
                    response_placeholder.markdown(text_buffer)
                elif buffer == 'response':
                    final_message = data
            except json.JSONDecodeError:
                pass
    
    status.update(label="Complete!", state="complete")
    
    if final_message:
        response_placeholder.empty()
        content_items = final_message.get("content", [])
        response_text = ""
        
        for item in content_items:
            if item.get("type") == "text":
                text_content = item.get("text", "")
                st.markdown(text_content)
                response_text += text_content
        
        # Add to chat history
        st.session_state.chat_messages.append({"role": "assistant", "content": final_message.get("content", [])})
        
        # Save to PostgreSQL if enabled
        if use_postgres and engine:
            try:
                SessionFactory = make_session_factory(engine)
                with SessionFactory() as db_sess:
                    result_json = {"response": response_text}
                    c = save_completion_with_session(db_sess, prompt, result_json)
                st.success(f"💾 Saved to PostgreSQL (id={c.id})")
            except Exception as e:
                st.error(f"Failed to save: {e}")

