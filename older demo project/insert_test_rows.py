"""
Insert a few test rows into the completions table for verification.

Usage: set PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASSWORD then run:
  python insert_test_rows.py
"""
import os
import json
from sqlalchemy import create_engine
from db import init_db, make_session_factory
from models import Completion


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
    Session = make_session_factory(engine)

    samples = [
        ("Test prompt 1", {"text": "sample result 1"}),
        ("Test prompt 2", {"text": "sample result 2", "meta": {"n": 2}}),
        ("Test prompt 3", {"text": "sample result 3", "meta": {"n": 3}}),
    ]

    with Session() as s:
        inserted = []
        for p, r in samples:
            c = Completion(prompt=p, result=r)
            s.add(c)
            s.flush()
            inserted.append((c.id, c.prompt))
        s.commit()

        print("Inserted rows:")
        for iid, prompt in inserted:
            print(f" - id={iid} prompt={prompt}")

        print("Last 5 rows in table:")
        rows = s.query(Completion).order_by(Completion.created_at.desc()).limit(5).all()
        for r in rows:
            print(r.id, r.prompt, json.dumps(r.result))


if __name__ == "__main__":
    main()
