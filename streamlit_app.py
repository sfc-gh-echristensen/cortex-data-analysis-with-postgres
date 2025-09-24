import streamlit as st
import pandas as pd
import json
import re

# Initialize connection to Snowflake using the connection from secrets
conn = st.connection("snowflake")
session = conn.session()

st.title(":material/network_intel_node: Cortex Data Analysis")

# Retrieve data

data = session.sql("SELECT * FROM BUILD25_POSTGRES_CORTEX.PUBLIC.BUDGET_ANALYSIS")
df = data.to_pandas()

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

with st.expander(":material/database: See Data", expanded=True):
    df
