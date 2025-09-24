"""
Connect to Postgres and print table names and columns for quick verification.

Usage:
PG_HOST=... PG_USER=... PG_PASSWORD=... PG_DB=... python verify_tables.py
"""
import os
from sqlalchemy import create_engine, text
import urllib.parse


def main():
    host = os.environ.get("PG_HOST")
    port = os.environ.get("PG_PORT", "5432")
    db = os.environ.get("PG_DB")
    user = os.environ.get("PG_USER")
    password = os.environ.get("PG_PASSWORD")

    if not (host and db and user and password):
        print("Please set PG_HOST, PG_DB, PG_USER and PG_PASSWORD environment variables.")
        return

    # URL-encode credentials in case they contain special characters
    user_enc = urllib.parse.quote_plus(user)
    password_enc = urllib.parse.quote_plus(password)

    url = f"postgresql+psycopg2://{user_enc}:{password_enc}@{host}:{port}/{db}"

    # Append sslmode if provided via PG_SSLMODE
    sslmode = os.environ.get("PG_SSLMODE")
    if sslmode:
        url = f"{url}?sslmode={sslmode}"

    engine = create_engine(url)

    with engine.connect() as conn:
        print("Tables in database:")
        rows = conn.execute(text("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public';")).fetchall()
        for r in rows:
            print(" -", r[0])
            cols = conn.execute(text(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{r[0]}' ORDER BY ordinal_position;"
                                     )).fetchall()
            for c in cols:
                print("    ", c[0], c[1])


if __name__ == "__main__":
    main()
