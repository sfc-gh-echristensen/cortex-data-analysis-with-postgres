"""
Budget Tracker 9000 - Main Application
Refactored version using modular components
"""

import streamlit as st
import urllib3

# Import modular components
from postgres_utils import setup_postgres_connection
from budget_dashboard import render_budget_dashboard
from cortex_queries import render_cortex_queries
from transaction_manager_ui import render_transaction_manager
from cortex_agent import render_cortex_agent
from pages.search import show_search_page

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Initialize Snowflake connection
conn = st.connection("snowflake")
session = conn.session()

# =============================================================================
# APP HEADER / BANNER
# =============================================================================

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

# =============================================================================
# POSTGRESQL CONNECTION SETUP
# =============================================================================

engine, use_postgres = setup_postgres_connection()

# =============================================================================
# RENDER DASHBOARD SECTIONS
# =============================================================================

# Budget Dashboard
render_budget_dashboard(engine, use_postgres)

# Cortex AI Queries
render_cortex_queries(engine, use_postgres, session)

# Transaction Manager
render_transaction_manager(engine, use_postgres)

# Cortex Agent & Snowflake Analytics
render_cortex_agent(engine, use_postgres)

