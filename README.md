# 💰 Budget Tracker 9000

AI-Powered Financial Analytics & Real-Time Data Insights using PostgreSQL and Snowflake Cortex

## 🌟 Features

- **📊 Budget Dashboard** - Track daily, weekly, and monthly spending with visual charts
- **🤖 AI-Powered SQL Queries** - Natural language to SQL conversion using Snowflake Cortex
- **🔧 Transaction Management** - Approve, decline, or cancel pending transactions with AI analysis
- **❄️ Cortex Agent Chat** - Interactive financial assistant powered by Snowflake AI
- **🔍 Search Demo** - Three-tier search: ILIKE, pg_trgm fuzzy search, and pgvector semantic search
- **💬 Subscription Management** - Track and manage recurring subscriptions

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL database
- Snowflake account (for AI features)
- OpenAI API key (optional, for semantic search)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd cortex-data-analysis-with-postgres
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure secrets**
   ```bash
   # Copy the template
   cp .streamlit/secrets_template.toml .streamlit/secrets.toml
   
   # Edit with your credentials
   nano .streamlit/secrets.toml
   ```

4. **Run the application**
   ```bash
   streamlit run streamlit_app.py
   ```

5. **Open in browser**
   - Navigate to `http://localhost:8501`

## ⚙️ Configuration

### Required Secrets

Create `.streamlit/secrets.toml` from the template and configure:

#### PostgreSQL (Required for core features)
```toml
[postgres]
host = "your-host"
port = 5432
database = "your_database"
user = "your_username"
password = "your_password"
sslmode = "require"
```

#### Snowflake (Required for AI features)
```toml
[connections.snowflake]
account = "YOUR_ACCOUNT"
user = "YOUR_USERNAME"
password = "YOUR_PASSWORD"
role = "ACCOUNTADMIN"
warehouse = "YOUR_WAREHOUSE"
database = "YOUR_DATABASE"
schema = "PUBLIC"

[agent]
SNOWFLAKE_PAT = "your-personal-access-token"
SNOWFLAKE_HOST = "YOUR_ACCOUNT.snowflakecomputing.com"
```

#### OpenAI (Optional, for semantic search)
```toml
[openai]
api_key = "sk-proj-your-key-here"
```

See `.streamlit/secrets_template.toml` for complete configuration with detailed comments.

## 📁 Project Structure

```
cortex-data-analysis-with-postgres/
├── streamlit_app.py              # Main application (170 lines, refactored!)
├── postgres_utils.py              # PostgreSQL utilities
├── budget_dashboard.py            # Budget tracking interface
├── cortex_queries.py              # AI-powered queries
├── transaction_manager_ui.py      # Transaction management
├── cortex_agent.py                # Snowflake agent chat
├── db_utils.py                    # Database operations
├── db.py                          # Database models
├── models_finance.py              # Financial data models
├── pages/
│   └── search.py                  # Search demo page
├── .streamlit/
│   ├── secrets_template.toml      # Configuration template
│   └── secrets.toml               # Your credentials (git-ignored)
└── requirements.txt               # Python dependencies
```

## 🎯 Usage

### Budget Dashboard
1. Enable PostgreSQL in the sidebar
2. View daily, weekly, and monthly spending
3. Track budget progress with visual charts
4. Get AI-powered spending insights

### AI Queries
1. Select an account from the dropdown
2. Ask natural language questions like:
   - "How much did I spend on groceries last week?"
   - "Show me all transactions over $100"
   - "What's my spending by category this month?"
3. View generated SQL and results

### Transaction Manager
1. View pending transactions
2. Use AI analysis to identify suspicious transactions
3. Approve or cancel transactions with one click
4. Review cancellation history

### Search Demo
Navigate to Search Demo page to explore:
- **ILIKE**: Basic pattern matching
- **pg_trgm**: Fuzzy search with typo tolerance
- **pgvector**: AI semantic search (requires embeddings setup)

## 🔧 Database Setup

### Create Tables

```bash
# Run the setup scripts
python3 setup_transaction_management.py
```

### Load Sample Data

```bash
# Load sample transactions
python3 load_sample_data.py

# Or load expanded data
python3 bulk_insert_expanded_data.py
```

### Setup Semantic Search (Optional)

```bash
# Install OpenAI library
pip install openai

# Configure OpenAI API key in secrets.toml

# Generate embeddings
python3 setup_embeddings.py
```

## 📊 Data Models

### Accounts Table
- `account_id` - Primary key
- `account_name` - Account name (unique)
- `current_balance` - Current balance

### Transactions Table
- `transaction_id` - Primary key
- `date` - Transaction date
- `amount` - Transaction amount
- `merchant` - Merchant name
- `category` - Transaction category
- `notes` - Additional notes
- `status` - Transaction status (pending, approved, completed, declined, cancelled)
- `account_id` - Foreign key to accounts
- `embedding` - Vector embedding (optional, for semantic search)

## 🛠️ Development

### Code Refactoring

The codebase has been refactored into modular components:
- Main app reduced from **1500+ lines to ~170 lines**
- Each feature in separate module
- Clear separation of concerns
- Easy to test and maintain

See `REFACTORING_SUMMARY.md` for details.

### Adding New Features

1. Create new module in project root
2. Export render function
3. Import and call in `streamlit_app.py`
4. Follow existing module patterns

## 🔒 Security

- ✅ `secrets.toml` is git-ignored
- ✅ Use environment variables for CI/CD
- ✅ Rotate credentials regularly
- ✅ Use PostgreSQL SSL mode
- ✅ Never commit credentials to version control

## 📝 Documentation

- `REFACTORING_SUMMARY.md` - Code refactoring details
- `DATA_LOADING.md` - Data loading instructions
- `EMBEDDINGS_SETUP.md` - Semantic search setup
- `TRANSACTION_MANAGEMENT.md` - Transaction management guide

## 🐛 Troubleshooting

### PostgreSQL Connection Issues
- Verify credentials in `secrets.toml`
- Check SSL mode setting
- Ensure PostgreSQL server is running
- Check firewall/network settings

### Snowflake Connection Issues
- Verify account name and credentials
- Check Personal Access Token validity
- Ensure warehouse is running
- Verify database/schema permissions

### Semantic Search Not Working
- Install OpenAI library: `pip install openai`
- Add OpenAI API key to `secrets.toml`
- Run embeddings setup: `python3 setup_embeddings.py`
- Check embedding column exists in database

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

[Your License Here]

## 🙏 Acknowledgments

- Built with [Streamlit](https://streamlit.io/)
- Powered by [Snowflake Cortex](https://www.snowflake.com/en/data-cloud/cortex/)
- Uses [PostgreSQL](https://www.postgresql.org/)
- Embeddings by [OpenAI](https://openai.com/)

---

**Made with ❤️ using Streamlit, PostgreSQL, and Snowflake Cortex**
