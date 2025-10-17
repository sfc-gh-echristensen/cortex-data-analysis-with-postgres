"""
PostgreSQL utility functions for Budget Tracker 9000
Handles database connections and PostgreSQL-specific operations
"""

import os
import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from src.db import init_db


def make_postgres_engine(user: str, password: str, host: str, port: int, dbname: str, sslmode: str | None = None) -> Engine:
    """
    Build SQLAlchemy connection string for PostgreSQL with psycopg2
    
    Args:
        user: Database username
        password: Database password
        host: Database host
        port: Database port
        dbname: Database name
        sslmode: SSL mode (optional, e.g. 'require')
        
    Returns:
        SQLAlchemy Engine instance
    """
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
    if sslmode:
        url = f"{url}?sslmode={sslmode}"
    return create_engine(url, echo=False)


def ensure_table(engine: Engine):
    """
    Create tables via ORM metadata if they don't exist
    
    Args:
        engine: SQLAlchemy Engine instance
    """
    init_db(engine)


def get_postgres_config():
    """
    Get PostgreSQL configuration from Streamlit secrets or environment variables
    
    Returns:
        Dictionary with PostgreSQL connection configuration
    """
    secrets_pg = st.secrets.get("postgres", {}) if hasattr(st, "secrets") else {}
    
    return {
        "host": secrets_pg.get("host") or os.environ.get("PG_HOST", ""),
        "port": str(secrets_pg.get("port") or os.environ.get("PG_PORT", "5432")),
        "database": secrets_pg.get("database") or os.environ.get("PG_DB", "postgres"),
        "user": secrets_pg.get("user") or os.environ.get("PG_USER", ""),
        "password": secrets_pg.get("password") or os.environ.get("PG_PASSWORD", ""),
        "sslmode": secrets_pg.get("sslmode") or os.environ.get("PG_SSLMODE", "")
    }


def setup_postgres_connection():
    """
    Setup PostgreSQL connection with sidebar configuration
    
    Returns:
        Tuple of (engine: Engine | None, use_postgres: bool)
    """
    # Sidebar: Postgres configuration
    st.sidebar.header("PostgreSQL Configuration")
    config = get_postgres_config()
    
    pg_host = st.sidebar.text_input("Host", value=config["host"])
    pg_port = st.sidebar.text_input("Port", value=config["port"])
    pg_db = st.sidebar.text_input("Database", value=config["database"])
    pg_user = st.sidebar.text_input("User", value=config["user"])
    pg_password = st.sidebar.text_input("Password", value=config["password"], type="password")
    pg_sslmode = st.sidebar.text_input("SSL mode (optional)", value=config["sslmode"])
    
    use_postgres = st.sidebar.checkbox(
        "Enable PostgreSQL", 
        value=bool(config["host"] and config["user"] and config["password"] and config["database"])
    )
    
    engine = None
    if use_postgres:
        if not (pg_host and pg_user and pg_password and pg_db):
            st.sidebar.warning("Enter all PostgreSQL credentials to enable.")
            use_postgres = False
        else:
            try:
                engine = make_postgres_engine(
                    pg_user, pg_password, pg_host, 
                    int(pg_port or 5432), pg_db, 
                    sslmode=pg_sslmode or None
                )
                ensure_table(engine)
                st.sidebar.success("PostgreSQL connection OK")
            except Exception as e:
                st.sidebar.error(f"PostgreSQL connection failed: {e}")
                use_postgres = False
    
    return engine, use_postgres

