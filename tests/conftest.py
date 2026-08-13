"""
Shared pytest fixtures.

Key design:
  - db_engine: per-test SQLAlchemy engine bound to a temp SQLite file
  - db_session: session on that engine, used by pure unit tests
  - client: FastAPI TestClient that patches the global DB module to use
            the same engine — so both route handlers AND internal get_db_ctx()
            calls all hit the same tables.
"""

import os
import tempfile

# Force test env before any project imports
os.environ["OPENAI_API_KEY"] = "sk-test-fake"
os.environ["NO_HARDWARE"]    = "1"
os.environ["NO_VOICE"]       = "1"
# Override DATABASE_URL — individual fixtures will patch the engine further

import pytest
from datetime import datetime, date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.database import Base, get_db
import db.models  # noqa: F401 — register models


# ── per-test SQLite file engine ───────────────────────────────────────────

@pytest.fixture(scope="function")
def db_engine():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    engine = create_engine(
        f"sqlite:///{path}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    try:
        os.unlink(path)
    except OSError:
        pass


@pytest.fixture(scope="function")
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


# ── FastAPI TestClient with DB patch ─────────────────────────────────────

@pytest.fixture(scope="function")
def client(db_engine):
    """
    FastAPI TestClient that redirects ALL DB access — both route-layer
    (via get_db dependency) and service-layer (via get_db_ctx context manager)
    — to the same per-test SQLite file engine.
    """
    import db.database as db_mod
    from sqlalchemy.orm import sessionmaker as SM
    from fastapi.testclient import TestClient

    # Patch the global engine + SessionLocal so get_db_ctx() uses our engine
    original_engine      = db_mod.engine
    original_SessionLocal = db_mod.SessionLocal

    db_mod.engine      = db_engine
    db_mod.SessionLocal = SM(autocommit=False, autoflush=False, bind=db_engine)

    # Also override the FastAPI dependency
    from main import app

    def override_get_db():
        Session = SM(autocommit=False, autoflush=False, bind=db_engine)
        session = Session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c

    # Restore originals
    app.dependency_overrides.clear()
    db_mod.engine       = original_engine
    db_mod.SessionLocal = original_SessionLocal


# ── seed helpers ──────────────────────────────────────────────────────────

@pytest.fixture
def seed_sessions(db_session):
    from db.models import ScreenSession

    def _seed(rows):
        objs = []
        now  = datetime.now()
        for i, r in enumerate(rows):
            start = r.get("started", now - timedelta(hours=2 - i * 0.1))
            end   = r.get("ended",   start + timedelta(seconds=r.get("duration", 600)))
            obj   = ScreenSession(
                user_id      = r.get("user_id", 1),
                app_name     = r.get("app",      "unknown"),
                window_title = r.get("title",    ""),
                category     = r.get("category", "neutral"),
                started_at   = start,
                ended_at     = end,
                duration_s   = r.get("duration", 600),
                session_date = r.get("date",     date.today()),
            )
            db_session.add(obj)
            objs.append(obj)
        db_session.commit()
        return objs

    return _seed


@pytest.fixture
def seed_cv(db_session):
    from db.models import CVEvent

    def _seed(events):
        objs = []
        now  = datetime.now()
        for i, ev in enumerate(events):
            obj = CVEvent(
                user_id      = 1,
                event_type   = ev,
                timestamp    = now - timedelta(minutes=len(events) - i),
                session_date = date.today(),
            )
            db_session.add(obj)
            objs.append(obj)
        db_session.commit()
        return objs

    return _seed


@pytest.fixture
def seed_assignments(db_session):
    from db.models import Assignment

    def _seed(rows):
        objs = []
        for r in rows:
            obj = Assignment(
                user_id  = r.get("user_id", 1),
                title    = r["title"],
                subject  = r.get("subject"),
                due_date = r.get("due_date", date.today() + timedelta(days=3)),
                priority = r.get("priority", "medium"),
                status   = r.get("status",   "pending"),
            )
            db_session.add(obj)
            objs.append(obj)
        db_session.commit()
        return objs

    return _seed


# ── auth helper ──────────────────────────────────────────────────────────

@pytest.fixture
def auth_headers(client, db_engine):
    """Create a test user and return auth headers with a valid JWT."""
    from db.models import User
    from modules.auth.security import create_access_token
    from sqlalchemy.orm import sessionmaker as SM

    Session = SM(autocommit=False, autoflush=False, bind=db_engine)
    session = Session()

    user = User(
        id=1,
        email="test@mimo.dev",
        password_hash="fakehash",
        role="student",
        display_name="Test Student",
    )
    session.merge(user)
    session.commit()
    session.close()

    token = create_access_token(user_id=1, role="student")
    return {"Authorization": f"Bearer {token}"}
