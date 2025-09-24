# 📦 Streamlit App Starter Kit 
```
⬆️ (Replace above with your app's name)
```

Description of the app ...

## Demo App

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://app-starter-kit.streamlit.app/)

## GitHub Codespaces

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/streamlit/app-starter-kit?quickstart=1)

## Section 2: Search Snowflake Warehouse (Analytical Queries)

This search is for answering strategic questions that require analyzing large volumes of historical data and unstructured information. This is where the true power of Snowflake and Cortex AI shines.

Example user queries:
- "What's my biggest spending category in the last year, and how has it changed over time?"
- "Provide a summary of my spending trends for Q2 compared to Q1."

Back-End Process:

- The app sends the user's query to a Snowflake stored procedure that uses Cortex AI functions like CORTEX.SUMMARIZE or CORTEX.ANALYST. This query runs directly on a large historical table and can perform complex aggregations, trend analysis, and even generate a natural-language summary from the data itself. The AI can process vast numbers of transactions to provide a concise, high-level answer.

Demo Data for Snowflake:

- `historical_transactions` table: A complete archive of all transactions, potentially with millions of rows. This table would be a direct copy from the PostgreSQL `transactions` table but on a much larger scale.

- `custom_categories` table: A mapping of `merchant_name` to a more refined category, created from user input or machine learning models.

- `budget_analysis` table: A pre-calculated summary of monthly or quarterly spending, ideal for quick queries and visualizations.

- `financial_news_sentiment` table: Unstructured data from news headlines and articles related to finance, with a sentiment score. This can be used to add context, for example, "Why did my investments drop in Q3 2024?" could be linked to a negative sentiment trend in this data.

I have added some sample/demo data to these Snowflake tables for the purposes of the demo.

## Further Reading

This is filler text, please replace this with a explanatory text about further relevant resources for this repo
- Resource 1
- Resource 2
- Resource 3

## Quickstart — Run locally with Postgres secrets

1. Create and activate a virtual environment (macOS):

```bash
python3 -m venv ~/.venvs/cortex-demo
source ~/.venvs/cortex-demo/bin/activate
```

2. Install requirements:

```bash
pip install -r requirements.txt
```

3. Add your credentials to `.streamlit/secrets.toml` (do NOT commit this file). Example:

```toml
[connections.snowflake]
account = "SFDEVREL_ENTERPRISE"
user = "ELIZABETHC"
password = "<your_snowflake_token>"
role = "ACCOUNTADMIN"
warehouse = "ELIZABETH_XS"
database = "BUILD25_POSTGRES_CORTEX"
schema = "PUBLIC"

[postgres]
host = "your-postgres-host.example.com"
port = 5432
database = "your_db"
user = "your_user"
password = "your_password"
```

4. Run the app:

```bash
streamlit run streamlit_app.py
```

5. Open the URL shown by Streamlit (usually http://localhost:8501). Use the sidebar to enable Postgres saving if you didn't put credentials in `secrets.toml`.

Security notes:
- Add `.streamlit/secrets.toml` to `.gitignore`.
- Prefer environment variables or secrets when deploying to cloud services.

## Create the Postgres tables

If you want to create the tables directly in your Postgres database (so you can inspect them), run:

```bash
# set required environment variables and run
PG_HOST=your.host PG_PORT=5432 PG_DB=your_db PG_USER=your_user PG_PASSWORD='your_password' \
	python create_tables.py
```

This will connect to your Postgres instance and run the ORM metadata create_all to ensure the `completions` table exists.

## Snowflake helper scripts (create demo tables, views and read-only role)

Two helper SQL files are included under the `sql/` folder to make it easy to prepare a Snowflake schema for the demo and to ensure a read-only role has access:

- `sql/create_demo_tables_and_views.sql` — creates `transactions` and `accounts` tables (with a quoted `"DATE"` column), inserts sample rows if the tables are empty, creates a `transactions_view` that aliases `"DATE"` to `transaction_date`, and creates two summary views (`category_totals_90d` and `top_merchants_90d`).
- `sql/grant_readonly_role.sql` — example script to create a read-only role and grant SELECT/USAGE on the current database/schema and existing objects. Optionally contains commented-out statements to create a demo user and assign the role.

How to run:

1. Open Snowflake Worksheets or SnowSQL connected to the target database and schema:

```sql
USE DATABASE <your_database>;
USE SCHEMA <your_schema>;
-- then run the contents of sql/create_demo_tables_and_views.sql
-- and sql/grant_readonly_role.sql (if you want to create the demo role)
```

2. After creating the view `transactions_view` you can query it without quoting the `DATE` identifier; e.g.:

```sql
SELECT transaction_id, transaction_date, account_name, amount FROM transactions_view LIMIT 10;
```

3. Grant the read-only role to the user or generate credentials to use in the app's `secrets.toml`. Ensure the app uses that user's role/credentials so Cortex or the Snowpark session can access the tables.

If you'd like I can also add code in the app to prefer `transactions_view` when available (so you don't need to change queries). Say "yes, add view fallback" and I'll implement that change.

