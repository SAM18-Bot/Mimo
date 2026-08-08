# Backend Exploration Handoff Report — Python Backend & Sync Architecture

## 1. Observation

### File & Directory Map
- Entry Points & Scripts:
  - `main.py`: FastAPI app instance (`app = FastAPI(...)`), lifespan startup/shutdown, router registration, WebSocket `/ws` endpoint handler.
  - `run_server.py`: Uvicorn CLI runner script (`python run_server.py --port 8000 --dev`).
  - `run_desktop.py`: PyQt desktop GUI launcher with system tray integration.
- Database & Schemas:
  - `config.py`: Defines `DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./accountability.db")`, thresholds, and keyword categories.
  - `db/database.py`: Sets up SQLAlchemy engine (`sqlite:///./accountability.db`), `SessionLocal`, `Base`, `init_db()`, and context manager `get_db_ctx()`.
  - `db/models.py`: Defines 15 ORM models including `ScreenSession`, `Assignment`, `DailySummary`, `CVEvent`, `User`, `Device`, `RoastLog`, `ScheduleProfile`, `ScheduleBlock`, etc.
  - `db/migrations/`: Alembic migrations (`001_initial_schema.py`, `002_schedule_module.py`, `003_auth_device_parent.py`).
- API Layer (`api/`):
  - `api/routes_assignments.py`: Router for `/assignments/` (POST add, POST `/nlp`, GET list, GET `/upcoming`, GET `/overdue`, PATCH `/{id}/status`, POST `/{id}/done`, DELETE `/{id}`).
  - `api/routes_reports.py`: Router for `/reports/` (GET `/stats`, GET `/history`, POST `/eod`, GET `/eod/latest`, POST `/accountability`, GET `/roasts`, GET `/patterns`, GET `/score/breakdown`).
  - `api/routes_screen.py`: Router for `/screen/` (GET `/sessions`, GET `/breakdown`, GET `/live`, POST `/mock`).
  - `api/routes_auth.py`: Router for `/auth`, `/devices`, `/parent`.
  - `api/routes_cv.py`, `routes_voice.py`, `routes_monitoring.py`, `routes_schedule.py`, `routes_settings.py`, `websocket.py`.
  - **MISSING FILE**: `api/routes_sync.py` does NOT exist yet.
- Aggregation & Scoring (`modules/behavior_engine/`):
  - `aggregator.py`: `get_daily_stats(db, target_date)` aggregates `ScreenSession` records by `session_date`. Calculates `productive_s`, `distracting_s`, `neutral_s`, `desk_time_min = total_s // 60`, calls `ProductivityScorer.compute(...)` for `focus_score`, and fetches `due_today`, `submitted_today`, `overdue_list`, `upcoming_list`.
  - `scorer.py`: `ProductivityScorer` class computing weighted score (0–100), letter grade (A+ to F), and score breakdown.
- Testing Suite (`tests/`):
  - `pytest.ini`: Root pytest config specifying `testpaths = tests`, `addopts = -v --tb=short -q`.
  - `tests/conftest.py`: Fixtures `db_engine` (per-test temporary SQLite DB), `db_session`, and `client` (FastAPI `TestClient` overriding `get_db` and patching `db.database.engine`).
  - 15 test modules with 321 total test cases (`test_api.py`, `test_aggregator.py`, `test_assignments.py`, `test_auth_device_parent.py`, `test_scorer.py`, etc.).

### Database Schemas (Key Tables for Sync)
1. `ScreenSession` (`db/models.py:10-21`):
   ```python
   class ScreenSession(Base):
       __tablename__ = "screen_sessions"
       id           = Column(Integer, primary_key=True, index=True)
       app_name     = Column(String(200), nullable=False)
       window_title = Column(String(500))
       category     = Column(String(20))          # productive | neutral | distracting
       started_at   = Column(DateTime, nullable=False)
       ended_at     = Column(DateTime)
       duration_s   = Column(Integer, default=0)
       session_date = Column(Date)
   ```
2. `Assignment` (`db/models.py:32-46`):
   ```python
   class Assignment(Base):
       __tablename__ = "assignments"
       id         = Column(Integer, primary_key=True, index=True)
       title      = Column(String(300), nullable=False)
       subject    = Column(String(100))
       due_date   = Column(Date, nullable=False)
       priority   = Column(String(20), default="medium")   # low | medium | high
       status     = Column(String(20), default="pending")  # pending | in_progress | done
       notes      = Column(Text)
       created_at = Column(DateTime, default=func.now())
       reminded_at = Column(DateTime)
   ```
3. `DailySummary` (`db/models.py:58-75`):
   ```python
   class DailySummary(Base):
       __tablename__ = "daily_summaries"
       id                = Column(Integer, primary_key=True, index=True)
       date              = Column(Date, unique=True, nullable=False)
       productive_time_s = Column(Integer, default=0)
       distracted_time_s = Column(Integer, default=0)
       neutral_time_s    = Column(Integer, default=0)
       desk_time_s       = Column(Integer, default=0)
       focus_score       = Column(Float, default=0.0)
       ...
   ```

## 2. Logic Chain

1. **Observation 1**: `ORIGINAL_REQUEST.md` (R3) requires creating `api/routes_sync.py` with push/pull endpoints for PC and Mobile sync, such that after a mobile push sync, `GET /reports/stats` returns mobile screen time added to total `desk_time_min` and updated focus score.
2. **Observation 2**: Direct inspection of `api/` confirms `routes_sync.py` is absent. `main.py:92-113` includes 10 routers (`assignments`, `screen`, `reports`, `cv`, `voice`, `study`, `settings`, `monitoring`, `schedule`, `auth`), but not a `sync` router.
3. **Observation 3**: `aggregator.py:38-47` computes `get_daily_stats()` by executing `db.query(ScreenSession).filter(ScreenSession.session_date == target_date).all()`, summing `duration_s` across categories (`productive`, `distracting`, `neutral`), and computing `desk_time_min = total_s // 60`.
4. **Logic Step**: To merge mobile screen time so `GET /reports/stats` incorporates it:
   - The push endpoint (`POST /sync/push`) in `api/routes_sync.py` should accept mobile sessions or daily mobile stats payload.
   - Inserting pushed mobile sessions as `ScreenSession` records (with app name, category, duration, date) directly feeds `aggregator.py:get_daily_stats()`, updating `desk_time_min`, category minutes, and `focus_score`.
   - `POST /sync/push` or `GET /sync/pull` should return the updated `get_daily_stats()` (or focus score) alongside active assignments from `get_all_assignments(db)` for the mobile client.
5. **Observation 4**: The test infrastructure in `tests/conftest.py` uses FastAPI `TestClient` with SQLite engine patching. Adding new test cases in a test file (e.g., `tests/test_sync.py` or within `test_api.py`) will automatically test the sync endpoints using in-memory/isolated SQLite DB.

## 3. Caveats

- `routes_sync.py` must be registered in `main.py` (`app.include_router(sync_router)`).
- When inserting mobile screen sessions into `ScreenSession`, ensure `category` is properly assigned (either passed from mobile Room DB or categorized using `modules.screen_tracker.categorizer.categorize_app`).
- Default date filtering should use `session_date` / `date.today()` or target date provided in payload.

## 4. Conclusion

The Python backend codebase is cleanly structured using FastAPI and SQLAlchemy.
To fulfill R3 of `ORIGINAL_REQUEST.md`:
1. Create `api/routes_sync.py` implementing:
   - `POST /sync/push`: Accepts mobile usage stats / sessions, inserts them into `ScreenSession` DB table, and returns merged daily stats (`focus_score`, `desk_time_min`, etc.) and assignment list.
   - `GET /sync/pull`: Returns merged stats and assignments list.
2. Register `sync_router` in `main.py`.
3. Add pytest test cases to verify `/sync/push` updates `GET /reports/stats` as required by acceptance criteria.

## 5. Verification Method

- Run pytest test suite:
  ```powershell
  pytest
  ```
  Execution verified: 316 passed, 5 skipped across 321 items (exit code 0).
- Code inspection of `api/routes_sync.py` and `main.py` router registration.
- Verify `GET /reports/stats` returns updated `desk_time_min` after pushing mock mobile screen time to `POST /sync/push`.

