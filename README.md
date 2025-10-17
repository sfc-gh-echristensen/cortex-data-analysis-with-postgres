## Snowflake Cortex + PostgreSQL Financial Analytics Demo

A full-stack demo app for financial analytics demonstrating the integration of **Snowflake Cortex AI**, **PostgreSQL with pgvector**, and **Streamlit** for intelligent data analysis and natural language interactions.

---

## 🌟 Features

This demo application showcases powerful integrations between modern data technologies:

### 📊 **PostgreSQL Integration**
- **Real-time Budget Dashboard** - Track daily, weekly, and monthly spending with interactive visualizations
- **Transaction Management** - Approve, decline, or cancel pending transactions with full audit trail
- **Financial Data Storage** - Robust PostgreSQL backend with comprehensive data models
- **Live Data Queries** - Dynamic queries with SQLAlchemy ORM

### 🤖 **Snowflake Cortex AI**
- **Natural Language to SQL** - Convert plain English questions into PostgreSQL queries using Cortex Complete
- **AI-Powered Financial Insights** - Get intelligent spending recommendations and budget analysis
- **Cortex Analyst Integration** - Enterprise-grade natural language query interface
- **Snowflake Data Visualization** - Display and analyze data from Snowflake tables

### 💬 **Intelligent Agent**
- **Cortex AI Agent** - Interactive chat interface for financial queries
- **Context-Aware Responses** - Agent remembers conversation history and context
- **Data Retrieval & Updates** - Agent can both read and write to PostgreSQL
- **Subscription Management Demo** - Intelligent subscription analysis and cancellation recommendations

### 🔍 **Advanced Search Demo**
Showcase three progressively sophisticated search techniques:
1. **ILIKE Pattern Matching** - Basic SQL substring search
2. **pg_trgm Fuzzy Search** - Typo-tolerant trigram matching
3. **pgvector Semantic Search** - AI-powered contextual search with embeddings

### 🔗 **OpenAI Integration**
- **Embedding Generation** - Create vector embeddings for semantic search
- **pgvector Storage** - Store and query embeddings in PostgreSQL
- **Intelligent Search** - Find transactions by meaning, not just keywords

---

## 🎯 Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   Streamlit UI  │ ◄─────► │  Python Backend  │ ◄─────► │   PostgreSQL    │
│   (Frontend)    │         │   (Application)  │         │   (Database)    │
└─────────────────┘         └──────────────────┘         └─────────────────┘
         │                           │                            │
         │                           ▼                            │
         │                  ┌──────────────────┐                 │
         └─────────────────►│ Snowflake Cortex │                 │
                            │   AI Services    │                 │
                            └──────────────────┘                 │
                                     │                            │
                                     ▼                            ▼
                            ┌──────────────────┐         ┌─────────────────┐
                            │  Cortex Analyst  │         │    pgvector     │
                            │  Cortex Agent    │         │   (Embeddings)  │
                            │  Cortex Complete │         └─────────────────┘
                            └──────────────────┘                 ▲
                                                                 │
                                                         ┌───────┴────────┐
                                                         │  OpenAI API    │
                                                         │  (Embeddings)  │
                                                         └────────────────┘
```

---

## 📋 Requirements

### **Snowflake Account**
- Active Snowflake account with appropriate permissions
- **Cortex Analyst** enabled on your account
- **Cortex AI Agent** configured and deployed
- **Personal Access Token (PAT)** for API authentication
- Warehouse with sufficient compute resources

### **PostgreSQL Database**
- PostgreSQL 16+ (cloud or self-hosted)
- **pgvector extension** installed (for semantic search)
- **pg_trgm extension** installed (for fuzzy search)
- SSL/TLS connection support recommended

### **Python Environment**
- Python 3.11 or higher
- pip package manager
- Virtual environment (recommended)

### **API Keys**
- **OpenAI API Key** (optional, for semantic search with embeddings)
- Get from: https://platform.openai.com/api-keys

### **Development Tools**
- Git for version control
- Text editor or IDE
- Terminal/command line access

---

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd cortex-data-analysis-with-postgres
```

### 2. Set Up Python Environment

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure PostgreSQL

#### Install Required Extensions

```sql
-- Connect to your PostgreSQL database
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

#### Create Database Tables

```bash
# Run the setup script
python3 setup_transaction_management.py
```

### 4. Configure Secrets

```bash
# Copy the template
cp .streamlit/secrets_template.toml .streamlit/secrets.toml

# Edit with your credentials
nano .streamlit/secrets.toml
```

**Required Configuration:**

```toml
# PostgreSQL Connection
[postgres]
host = "your-postgres-host.com"
port = 5432
database = "your_database"
user = "your_username"
password = "your_password"
sslmode = "require"

# Snowflake Connection
[connections.snowflake]
account = "YOUR_ACCOUNT"
user = "YOUR_USERNAME"
password = "YOUR_PASSWORD"
role = "ACCOUNTADMIN"
warehouse = "YOUR_WAREHOUSE"
database = "YOUR_DATABASE"
schema = "PUBLIC"

# Snowflake Cortex Agent
[agent]
SNOWFLAKE_PAT = "your-personal-access-token"
SNOWFLAKE_HOST = "YOUR_ACCOUNT.snowflakecomputing.com"

# OpenAI (Optional - for semantic search)
[openai]
api_key = "sk-proj-your-key-here"
```

### 5. Load Sample Data

Choose one of the following options:

```bash
# Option 1: Load sample transaction data
python3 load_sample_data.py

# Option 2: Load expanded dataset
python3 bulk_insert_expanded_data.py

# Option 3: Load from SQL backup (see Sample Data section below)
psql -h your-host -U your-user -d your-database -f sample_data_backup.sql
```

### 6. Setup Semantic Search (Optional)

If you want to use the pgvector semantic search feature:

```bash
# Generate embeddings for existing transactions
python3 setup_embeddings.py
```

### 7. Run the Application

```bash
streamlit run streamlit_app.py
```

The app will open in your browser at **http://localhost:8501**

---

## 📦 Sample Data

### PostgreSQL Sample Data

Load sample financial data into your PostgreSQL database:

#### **Option 1: Python Script**
```bash
python3 load_sample_data.py
```

#### **Option 2: SQL Backup File**
Download and restore the sample data backup:

```bash
# Download the SQL backup file
# [Link to postgres_sample_data.sql will be added here]

# Restore to your database
psql -h your-host -U your-user -d your-database -f postgres_sample_data.sql
```

**Included Data:**
- 500+ sample transactions
- 5 account profiles (Checking, Savings, Credit Card, Investment, Emergency Fund)
- Categories: Groceries, Dining, Shopping, Transportation, Utilities, Entertainment, etc.
- Date range: Last 6 months
- Various transaction statuses: pending, approved, completed, declined

### Snowflake Sample Data

Load sample data into your Snowflake account:

#### **SQL Scripts**
```sql
-- Download the Snowflake setup script
-- [Link to snowflake_sample_data.sql will be added here]

-- Run in Snowflake worksheet
USE DATABASE YOUR_DATABASE;
USE SCHEMA PUBLIC;

-- Create and populate transactions table
SOURCE @~/snowflake_sample_data.sql;
```

**Included Data:**
- Transactions table with 1000+ records
- Monthly aggregations
- Category breakdowns
- Spending trends over time

#### **Alternative: Python Loader**
```bash
python3 snowflake_loader_final.py
```

---

## 🎨 Application Features

### **Budget Dashboard**

<img src="docs/screenshots/budget_dashboard.png" alt="Budget Dashboard" width="800"/>

- **Today's Budget Status** - Real-time spending vs daily budget
- **Weekly Comparison** - Current week vs previous week trends
- **Monthly Tracking** - Visual chart showing budget progress
- **Category Breakdown** - Spending by category with progress bars
- **Smart Insights** - AI-powered recommendations based on spending patterns

### **Cortex AI Queries**

<img src="docs/screenshots/cortex_queries.png" alt="Cortex Queries" width="800"/>

- **Natural Language Interface** - Ask questions in plain English
- **SQL Generation** - Automatic conversion to PostgreSQL queries
- **Account Selection** - Filter queries by specific accounts
- **Query History** - Review past queries and results
- **Result Visualization** - Tables, metrics, and charts

**Example Queries:**
```
"How much did I spend on groceries last week?"
"Show me all transactions over $100 this month"
"What's my average daily spending?"
"Which category did I spend the most on?"
```

### **Transaction Manager**

<img src="docs/screenshots/transaction_manager.png" alt="Transaction Manager" width="800"/>

- **Pending Transactions View** - See all transactions awaiting approval
- **AI Analysis** - Automatic detection of unusual or high-amount transactions
- **One-Click Actions** - Approve or cancel transactions
- **Cancellation Audit Trail** - Full history with reasons
- **Manual Management** - Override AI suggestions when needed

### **Cortex AI Agent Chat**

<img src="docs/screenshots/agent_chat.png" alt="Agent Chat" width="800"/>

- **Interactive Conversation** - Natural dialogue with AI agent
- **Context Awareness** - Agent remembers previous messages
- **Data Retrieval** - Query PostgreSQL and Snowflake data
- **Subscription Management** - Identify and cancel unused subscriptions
- **Spending Analytics** - Get insights from Snowflake aggregations

### **Search Demo**

<img src="docs/screenshots/search_demo.png" alt="Search Demo" width="800"/>

Three search methods to compare:

1. **ILIKE** - Traditional SQL pattern matching
   - Fast and simple
   - Exact substring matches
   - Case-insensitive

2. **pg_trgm** - Fuzzy text search
   - Typo-tolerant
   - Similarity scoring
   - Handles misspellings

3. **pgvector** - Semantic search
   - AI-powered understanding
   - Finds conceptually similar results
   - Language-agnostic

---

## 📁 Project Structure

```
cortex-data-analysis-with-postgres/
├── streamlit_app.py              # Main application entry point (170 lines)
├── postgres_utils.py              # PostgreSQL connection utilities
├── budget_dashboard.py            # Budget tracking interface
├── cortex_queries.py              # Cortex AI query functionality
├── transaction_manager_ui.py      # Transaction management UI
├── cortex_agent.py                # Snowflake agent chat interface
├── db_utils.py                    # Database utility functions
├── db.py                          # Database session management
├── models.py                      # SQLAlchemy data models
├── models_finance.py              # Financial domain models
│
├── pages/
│   └── search.py                  # Search demo page
│
├── .streamlit/
│   ├── secrets_template.toml      # Configuration template
│   └── secrets.toml               # Your credentials (git-ignored)
│
├── setup_embeddings.py            # Generate pgvector embeddings
├── setup_transaction_management.py # Initialize database tables
├── load_sample_data.py            # Load sample transactions
├── bulk_insert_expanded_data.py   # Load expanded dataset
├── snowflake_loader_final.py      # Load Snowflake sample data
│
├── requirements.txt               # Python dependencies
├── README.md                      # This file
├── REFACTORING_SUMMARY.md         # Code refactoring documentation
├── .gitignore                     # Git ignore rules
│
└── docs/
    └── screenshots/               # Application screenshots
```

---

## 🔧 Configuration Guide

### Environment Variables

Alternatively to `secrets.toml`, you can use environment variables:

```bash
# PostgreSQL
export PG_HOST="your-host"
export PG_PORT="5432"
export PG_DB="your-database"
export PG_USER="your-username"
export PG_PASSWORD="your-password"
export PG_SSLMODE="require"

# OpenAI (optional)
export OPENAI_API_KEY="sk-proj-your-key"
```

### Snowflake Cortex Agent Setup

1. **Create Agent in Snowflake:**
```sql
CREATE OR REPLACE CORTEX AGENT POSTGRES_AGENT
  WAREHOUSE = YOUR_WAREHOUSE
  DATABASE = YOUR_DATABASE
  SCHEMA = AGENTS
  PROMPT = 'You are a financial analysis assistant...';
```

2. **Generate Personal Access Token:**
   - Go to Snowflake UI → Profile → Personal Access Tokens
   - Click "Generate New Token"
   - Copy token to `secrets.toml`

3. **Configure in secrets.toml:**
```toml
[agent]
SNOWFLAKE_PAT = "your-token-here"
SNOWFLAKE_HOST = "YOUR_ACCOUNT.snowflakecomputing.com"
```

### PostgreSQL Extensions

```sql
-- Install required extensions
CREATE EXTENSION IF NOT EXISTS vector;      -- For semantic search
CREATE EXTENSION IF NOT EXISTS pg_trgm;     -- For fuzzy search

-- Verify installation
SELECT * FROM pg_extension WHERE extname IN ('vector', 'pg_trgm');
```

---

## 💡 Usage Examples

### Budget Tracking

1. **Enable PostgreSQL** in the sidebar
2. Navigate to **Budget Dashboard** section
3. View real-time spending metrics
4. Check category breakdowns
5. Review AI insights and recommendations

### Natural Language Queries

1. Go to **AI Queries** section
2. Select an account (optional)
3. Type your question: *"How much did I spend on dining last month?"*
4. Click **Run Query**
5. View SQL generation and results

### Transaction Management

1. Go to **Transaction Manager**
2. Click **Analyze Pending Transactions**
3. Review AI-flagged suspicious transactions
4. Click cancel button for unwanted transactions
5. View confirmation and audit trail

### Semantic Search

1. Navigate to **Search Demo** page
2. Select **pgvector Semantic Search**
3. Enter search term: *"morning coffee"*
4. View contextually similar results
5. Compare with ILIKE and pg_trgm results

---
## 📚 Additional Resources

### Documentation
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Snowflake Cortex Documentation](https://docs.snowflake.com/en/user-guide/snowflake-cortex)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [pgvector GitHub](https://github.com/pgvector/pgvector)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)

### Tutorials
- [Cortex Analyst Quickstart](https://quickstarts.snowflake.com/guide/getting-started-with-cortex-analyst/)
- [pgvector Setup Guide](https://github.com/pgvector/pgvector#installation)
- [Streamlit Multipage Apps](https://docs.streamlit.io/library/get-started/multipage-apps)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**Built with ❤️ using Streamlit, PostgreSQL, Snowflake Cortex, and AI**

*Last updated: October 2025*
