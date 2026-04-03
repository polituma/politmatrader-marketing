"""
Database engine and session factory.

Key fixes over original:
- SQLite gets check_same_thread=False (required for multi-thread/scheduler use)
- Session dependency for FastAPI injection instead of manual SessionLocal() usage
- Engine connect_args only applied when using SQLite
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


def _build_engine():
    connect_args: dict[str, Any] = {}
    kwargs: dict[str, Any] = {"future": True}

    if settings.is_sqlite:
        connect_args["check_same_thread"] = False
        kwargs["pool_pre_ping"] = True
    else:
        # PostgreSQL / other production DBs
        kwargs["pool_size"] = 10
        kwargs["max_overflow"] = 20
        kwargs["pool_pre_ping"] = True

    eng = create_engine(settings.database_url, connect_args=connect_args, **kwargs)

    # Enable WAL mode for SQLite — much better concurrent read performance.
    if settings.is_sqlite:
        @event.listens_for(eng, "connect")
        def _set_sqlite_pragma(dbapi_conn, _connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return eng


engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a DB session and ensures cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
