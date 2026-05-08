from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .core.config import load_settings


class Base(DeclarativeBase):
    pass


_settings = load_settings()

def _normalize_db_url(url: str) -> str:
    # Render provides postgresql:// — SQLAlchemy needs postgresql+psycopg:// for psycopg3.
    if url.startswith("postgresql://") or url.startswith("postgres://"):
        return url.replace("://", "+psycopg://", 1)
    return url

engine = create_engine(_normalize_db_url(_settings.database_url), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, class_=Session)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

