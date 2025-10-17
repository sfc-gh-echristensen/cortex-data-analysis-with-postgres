import json
from typing import Iterator, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from src.models import Base, Completion


def make_engine(url: str):
    return create_engine(url)


def make_session_factory(engine):
    return sessionmaker(bind=engine)


def init_db(engine):
    Base.metadata.create_all(engine)


def save_completion_with_session(session: Session, prompt: str, result_json: dict):
    c = Completion(prompt=prompt, result=result_json)
    session.add(c)
    session.commit()
    session.refresh(c)
    return c


def fetch_history_with_session(session: Session, limit: int = 50):
    return session.query(Completion).order_by(Completion.created_at.desc()).limit(limit).all()
