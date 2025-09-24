"""
Create financial tables (accounts, transactions) in Postgres.

Usage:
PG_HOST=... PG_PORT=... PG_USER=... PG_PASSWORD=... PG_DB=... python create_financial_tables.py
"""
import os
from sqlalchemy import create_engine

from models_finance import Base


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
    print("Creating tables...")
    Base.metadata.create_all(engine)
    print("Done creating financial tables.")


if __name__ == "__main__":
    main()
