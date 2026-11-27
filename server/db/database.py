from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from server import config

connect_args = {"check_same_thread": False} if config.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    config.DATABASE_URL,
    connect_args=connect_args,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def init_db():
    """Upgrade an empty, versioned, or recognized create_all database on startup."""
    from pathlib import Path
    from alembic import command
    from alembic.autogenerate import compare_metadata
    from alembic.config import Config
    from alembic.migration import MigrationContext
    from sqlalchemy import inspect, text
    from server.db import models  # noqa: F401

    cfg = Config()
    cfg.set_main_option("script_location", str(Path(__file__).parent / "migrations"))
    with engine.begin() as conn:
        if conn.dialect.name == "postgresql":
            conn.execute(text("SELECT pg_advisory_xact_lock(182910035)"))
        cfg.attributes["connection"] = conn
        schema = inspect(conn)
        if schema.get_table_names() and not schema.has_table("alembic_version"):
            # Old installations used the ORM's create_all, including account ownership
            # and sync receipts. Reject unknown shapes before recording a baseline.
            def legacy_object(obj, name, kind, reflected, compare_to):
                if kind in {"column", "index"} and obj.table.name == "assignments" and name in {
                    "request_id", "ix_assignments_user_request"
                } and compare_to is None and not reflected:
                    return False
                if kind == "column" and obj.table.name == "screen_sessions" and name == "device":
                    return False
                if kind == "table" and name == "chat_messages" and not reflected and compare_to is None:
                    return False
                return True

            context = MigrationContext.configure(conn, opts={"include_object": legacy_object})
            if compare_metadata(context, Base.metadata):
                raise RuntimeError("Unrecognized unversioned schema. Compare a backup with revision 005 before upgrading.")
            command.stamp(cfg, "005")
        command.upgrade(cfg, "head")


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
