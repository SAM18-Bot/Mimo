from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from contextlib import contextmanager
import config

engine = create_engine(
    config.DATABASE_URL,
    connect_args={"check_same_thread": False},  # needed for SQLite + FastAPI
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def init_db():
    """Create all tables. Call once at startup."""
    from db import models  # noqa: F401 - import so models register with Base
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db_ctx():
    """Context manager for use outside FastAPI (schedulers, background threads)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db():
    """FastAPI dependency injection."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
