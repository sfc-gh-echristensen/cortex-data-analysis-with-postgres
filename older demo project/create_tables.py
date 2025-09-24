"""
Simple script to create ORM tables in a Postgres database.

Usage (env vars):
PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASSWORD

Example:
PG_HOST=yourhost PG_USER=you PG_PASSWORD=secret PG_DB=dbname python create_tables.py
"""
import os
from sqlalchemy import create_engine
from db import init_db


def main():
    host = os.environ.get("PG_HOST")
    port = os.environ.get("PG_PORT", "5432")
    db = os.environ.get("PG_DB")
    user = os.environ.get("PG_USER")
    password = os.environ.get("PG_PASSWORD")

    if not (host and db and user and password):
        print("Please set PG_HOST, PG_DB, PG_USER and PG_PASSWORD environment variables.")
        return

    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
    engine = create_engine(url)
    init_db(engine)
    print("Tables created (if not existing) with ORM metadata")


if __name__ == "__main__":
    main()
