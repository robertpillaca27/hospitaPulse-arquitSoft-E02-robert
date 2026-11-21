"""Database engine and request-scoped SQLAlchemy sessions."""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from fastapi import HTTPException, status
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.shared.config import get_settings


@lru_cache
def get_engine() -> Engine | None:
    """Build the PostgreSQL engine when DATABASE_URL is configured."""
    database_url = get_settings().database_url
    if database_url is None:
        return None
    return create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=30,
        max_overflow=20,
        pool_timeout=10,
        pool_recycle=1_800,
    )


def get_db_session() -> Iterator[Session]:
    """Yield a request-scoped session or report missing database configuration."""
    engine = get_engine()
    if engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La base de datos no está configurada. Define DATABASE_URL para usar Encuestas.",
        )
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory() as session:
        yield session
