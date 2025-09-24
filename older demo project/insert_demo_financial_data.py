"""
Insert demo accounts and transactions for the financial Q&A demo.

Usage:
PG_HOST=... PG_USER=... PG_PASSWORD=... PG_DB=... python insert_demo_financial_data.py
"""
import os
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models_finance import Account, Transaction, Base


def make_engine_from_env():
    host = os.environ.get("PG_HOST")
    port = os.environ.get("PG_PORT", "5432")
    db = os.environ.get("PG_DB")
    user = os.environ.get("PG_USER")
    password = os.environ.get("PG_PASSWORD")
    sslmode = os.environ.get("PG_SSLMODE")

    if not (host and db and user and password):
        raise RuntimeError("Set PG_HOST, PG_DB, PG_USER, PG_PASSWORD environment variables")

    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
    if sslmode:
        url = f"{url}?sslmode={sslmode}"
    return create_engine(url)


def main():
    engine = make_engine_from_env()
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    with Session() as s:
        # Create accounts
        checking = Account(account_name="Checking", current_balance=Decimal("1500.00"))
        savings = Account(account_name="Savings", current_balance=Decimal("5000.00"))
        s.add_all([checking, savings])
        s.commit()

        # Insert transactions (some in last week)
        today = datetime.utcnow().date()
        last_week_start = datetime.combine(today - timedelta(days=today.weekday()+7), datetime.min.time())
        # Add a few transactions across dates
        samples = [
            # last week groceries
            {"date": last_week_start + timedelta(days=2), "amount": Decimal("45.23"), "merchant": "Local Grocery", "category": "Groceries", "notes": "Weekly groceries", "account_id": checking.account_id},
            {"date": last_week_start + timedelta(days=4), "amount": Decimal("82.10"), "merchant": "Supermart", "category": "Groceries", "notes": "Extra supplies", "account_id": checking.account_id},
            # dining
            {"date": last_week_start + timedelta(days=1), "amount": Decimal("15.00"), "merchant": "Cafe Corner", "category": "Dining", "notes": "Coffee and sandwich", "account_id": checking.account_id},
            # other prior transactions
            {"date": datetime.utcnow() - timedelta(days=40), "amount": Decimal("120.00"), "merchant": "Electric Co", "category": "Utilities", "notes": "Monthly bill", "account_id": checking.account_id},
            {"date": datetime.utcnow() - timedelta(days=10), "amount": Decimal("350.00"), "merchant": "Gadget Store", "category": "Shopping", "notes": "New headphones", "account_id": checking.account_id},
            # savings transfer
            {"date": datetime.utcnow() - timedelta(days=3), "amount": Decimal("200.00"), "merchant": "Internal Transfer", "category": "Transfer", "notes": "Transfer to savings", "account_id": checking.account_id},
        ]

        for t in samples:
            tx = Transaction(
                date=t["date"],
                amount=t["amount"],
                merchant=t.get("merchant"),
                category=t.get("category"),
                notes=t.get("notes"),
                account_id=t.get("account_id"),
            )
            s.add(tx)

        s.commit()
        print("Inserted demo accounts and transactions.")


if __name__ == "__main__":
    main()
