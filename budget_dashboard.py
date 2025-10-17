"""
Budget Dashboard Module
Renders the budget tracking and spending analytics dashboard
"""

import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
import calendar
from sqlalchemy import text
from sqlalchemy.engine import Engine
from db_utils import get_db_connection


# Budget configuration constants
DAILY_BUDGET = 75.00
WEEKLY_BUDGET = 400.00
MONTHLY_BUDGET = 1500.00

CATEGORY_BUDGETS = {
    'Food & Dining': 400,
    'Shopping': 300,
    'Entertainment': 200,
    'Transportation': 150,
    'Utilities': 250,
    'Other': 200
}


def render_budget_dashboard(engine: Engine, use_postgres: bool):
    """
    Render the complete budget dashboard with spending analytics
    
    Args:
        engine: SQLAlchemy Engine instance
        use_postgres: Boolean indicating if PostgreSQL is enabled
    """
    st.markdown('<div id="budget-dashboard"></div>', unsafe_allow_html=True)
    st.header("💰 Budget Dashboard")
    
    if not use_postgres or engine is None:
        st.info("💡 Enable PostgreSQL connection in the sidebar to access your budget dashboard.")
        return
    
    try:
        # Get spending data
        spending_data = _fetch_spending_data()
        
        # Render dashboard sections
        _render_daily_budget_status(spending_data)
        _render_weekly_comparison(spending_data)
        _render_monthly_tracking(spending_data)
        _render_category_breakdown(spending_data)
        _render_insights(spending_data)
        
    except Exception as e:
        st.error(f"Error loading budget dashboard: {e}")
        st.info("Make sure you have transaction data in your PostgreSQL database.")


def _fetch_spending_data():
    """Fetch all spending data from database"""
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
        
    return {
        'daily_spending': float(today_result.daily_spending),
        'current_week': float(weekly_result.current_week),
        'last_week': float(weekly_result.last_week),
        'current_month': float(monthly_result.current_month),
        'last_month': float(monthly_result.last_month),
        'category_data': [(row.category, float(row.spending)) for row in category_result]
    }


def _render_daily_budget_status(data):
    """Render today's budget status section"""
    st.subheader("📅 Today's Budget Status")
    
    daily_spending = data['daily_spending']
    daily_percent = (daily_spending / DAILY_BUDGET) * 100 if DAILY_BUDGET > 0 else 0
    daily_remaining = DAILY_BUDGET - daily_spending
    
    # Color coding for budget status
    if daily_percent <= 50:
        daily_color, daily_status, daily_style = "🟢", "Great! You're on budget", "color: green;"
    elif daily_percent <= 80:
        daily_color, daily_status, daily_style = "🟡", "Good progress, watch spending", "color: orange;"
    elif daily_percent <= 100:
        daily_color, daily_status, daily_style = "🟠", "Close to budget limit", "color: #ff8c00;"
    else:
        daily_color, daily_status, daily_style = "🔴", "Over budget!", "color: red;"
    
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


def _render_weekly_comparison(data):
    """Render weekly spending comparison section"""
    st.subheader("📈 Weekly Spending Comparison")
    
    current_week = data['current_week']
    last_week = data['last_week']
    weekly_change = current_week - last_week
    weekly_percent_change = (weekly_change / last_week * 100) if last_week > 0 else 0
    
    # Weekly status
    if weekly_percent_change <= -10:
        weekly_status = "📉 Spending down significantly"
    elif weekly_percent_change <= -5:
        weekly_status = "📉 Spending decreased"
    elif weekly_percent_change <= 5:
        weekly_status = "➡️ Spending similar to last week"
    elif weekly_percent_change <= 15:
        weekly_status = "📈 Spending increased"
    else:
        weekly_status = "📈 Spending up significantly"
    
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


def _render_monthly_tracking(data):
    """Render monthly budget tracking with chart"""
    st.subheader("📊 Monthly Budget Tracking")
    
    today = datetime.now()
    current_month = data['current_month']
    
    # Calculate monthly metrics
    monthly_percent = (current_month / MONTHLY_BUDGET) * 100 if MONTHLY_BUDGET > 0 else 0
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    days_elapsed = today.day
    expected_spending = (MONTHLY_BUDGET / days_in_month) * days_elapsed
    spending_vs_expected = current_month - expected_spending
    
    # Monthly status
    if current_month > MONTHLY_BUDGET:
        monthly_status = "🚨 Over monthly budget!"
    elif monthly_percent > 90:
        monthly_status = "⚠️ Close to monthly limit"
    elif current_month < expected_spending * 0.8:
        monthly_status = "✅ Well under budget"
    else:
        monthly_status = "👍 On track with budget"
    
    # Create budget tracking chart
    budget_data = pd.DataFrame({
        'Category': ['Spent', 'Expected by Now', 'Remaining Budget', 'Over Budget'],
        'Amount': [
            current_month,
            expected_spending,
            max(0, MONTHLY_BUDGET - current_month) if current_month <= MONTHLY_BUDGET else 0,
            max(0, current_month - MONTHLY_BUDGET) if current_month > MONTHLY_BUDGET else 0
        ],
        'Type': ['actual', 'expected', 'remaining', 'over'],
        'Color': ['#ff6b6b', '#4ecdc4', '#95e1d3', '#ffa8a8']
    })
    
    # Remove zero amounts for cleaner chart
    budget_data = budget_data[budget_data['Amount'] > 0]
    
    # Create horizontal bar chart
    chart = alt.Chart(budget_data).mark_bar().encode(
        x=alt.X('Amount:Q', title='Amount ($)', scale=alt.Scale(domain=[0, max(MONTHLY_BUDGET * 1.2, current_month * 1.1)])),
        y=alt.Y('Category:N', title='', sort=['Spent', 'Expected by Now', 'Remaining Budget', 'Over Budget']),
        color=alt.Color('Color:N', scale=None, legend=None),
        tooltip=['Category:N', alt.Tooltip('Amount:Q', format='.2f')]
    ).properties(
        width=600,
        height=200,
        title=f"Monthly Budget Progress: {monthly_percent:.1f}% Used"
    )
    
    # Add budget line
    budget_line = alt.Chart(pd.DataFrame({'budget': [MONTHLY_BUDGET]})).mark_rule(
        color='red',
        strokeDash=[5, 5],
        strokeWidth=2
    ).encode(x='budget:Q')
    
    combined_chart = (chart + budget_line).resolve_scale(color='independent')
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.altair_chart(combined_chart, use_container_width=True)
    
    with col2:
        st.metric("This Month", f"${current_month:.2f}")
        st.metric("Monthly Budget", f"${MONTHLY_BUDGET:.2f}")
        st.metric("Days Elapsed", f"{days_elapsed}/{days_in_month}")
        
        if current_month > MONTHLY_BUDGET:
            st.error(f"Over by ${current_month - MONTHLY_BUDGET:.2f}")
        else:
            remaining = MONTHLY_BUDGET - current_month
            st.success(f"${remaining:.2f} remaining")
    
    st.markdown(f"**{monthly_status}**")
    if spending_vs_expected > 50:
        st.warning(f"⚡ You're spending ${spending_vs_expected:.2f} above expected pace")
    elif spending_vs_expected < -50:
        st.success(f"💰 You're ${abs(spending_vs_expected):.2f} under expected spending")


def _render_category_breakdown(data):
    """Render category budget breakdown"""
    st.subheader("🏷️ Category Budget Breakdown")
    
    category_data = data['category_data']
    
    if not category_data:
        st.info("No spending data available for this month")
        return
    
    for category, spending in category_data:
        budget = CATEGORY_BUDGETS.get(category, 200)
        category_percent = (spending / budget) * 100 if budget > 0 else 0
        
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


def _render_insights(data):
    """Render budget insights and recommendations"""
    st.subheader("💡 Budget Insights & Tips")
    
    insights = []
    daily_spending = data['daily_spending']
    current_week = data['current_week']
    last_week = data['last_week']
    current_month = data['current_month']
    category_data = data['category_data']
    
    # Calculate metrics
    today = datetime.now()
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    days_elapsed = today.day
    expected_spending = (MONTHLY_BUDGET / days_in_month) * days_elapsed
    weekly_percent_change = ((current_week - last_week) / last_week * 100) if last_week > 0 else 0
    
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
    for category, spending in category_data[:3]:
        budget = CATEGORY_BUDGETS.get(category, 200)
        if spending > budget * 1.1:
            insights.append(f"🏷️ **{category}**: Over budget by ${spending - budget:.2f}")
    
    if insights:
        for insight in insights:
            st.info(insight)
    else:
        st.success("🎉 Your spending looks healthy across all categories!")

