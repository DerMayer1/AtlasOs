from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker


def normalize_database_url(database_url: str) -> str:
    """Pin bare Postgres URLs to the psycopg3 driver this project ships.

    Managed hosts (Render, Railway, Heroku) hand out ``postgres://`` or
    ``postgresql://`` DSNs, which SQLAlchemy maps to the psycopg2 dialect — a
    driver we do not install. Rewrite those to ``postgresql+psycopg`` so the
    connection works out of the box, while leaving any URL that already names a
    driver (``postgresql+asyncpg``, ``postgresql+psycopg``) untouched.
    """
    url = make_url(database_url)
    if url.drivername in ("postgres", "postgresql"):
        url = url.set(drivername="postgresql+psycopg")
    return url.render_as_string(hide_password=False)


def make_engine(database_url: str) -> Engine:
    database_url = normalize_database_url(database_url)
    connect_args = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        db_path = make_url(database_url).database
        if db_path and db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return create_engine(database_url, connect_args=connect_args, pool_pre_ping=True)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)
