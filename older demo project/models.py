from sqlalchemy import Column, Integer, Text, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

# Prefer the Postgres JSONB type when available, otherwise fall back to generic JSON
try:
    from sqlalchemy.dialects.postgresql import JSONB as SA_JSON
except Exception:
    from sqlalchemy import JSON as SA_JSON

Base = declarative_base()


class Completion(Base):
    __tablename__ = "completions"
    id = Column(Integer, primary_key=True, index=True)
    prompt = Column(Text, nullable=False)
    result = Column(SA_JSON)
    created_at = Column(TIMESTAMP, server_default=func.now())
