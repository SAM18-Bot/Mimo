# Handoff Report — Requirement R1 Survey (Backend Core Flows)

## 1. Observation
Direct observations from codebase inspection of Mimo project:

- **Entry Points & Launchers**:
  - `main.py` lines 83–88: `app = FastAPI(title="Mimo — AI Accountability System", version="2.0.0", lifespan=lifespan)`
  - `main.py` line 34: `init_db()` called at module import.
  - `main.py` lines 106–117: Routers included: `assignments_router`, `screen_router`, `reports_router`, `cv_router`, `voice_router`, `study_router`, `settings_router`, `monitoring_router`, `schedule_router`, `auth_router`, `sync_router`, `onboarding_router`.
  - `run_server.py` lines 58–64: `uvicorn.run("main:app", host=args.host, port=args.port, reload=args.dev, log_level="info")` with default port 8000 and host `0.0.0.0`.

- **Database Initialization & Models**:
  - `db/database.py` lines 6–12: `engine = create_engine(config.DATABASE_URL, connect_args=connect_args)`. Default `DATABASE_URL` is `sqlite:///./mimo.db` (or `sqlite:///./accountability.db`).
  - `db/database.py` lines 21–24: `init_db()` invokes `Base.metadata.create_all(bind=engine)`.
  - `db/models.py`: Defines tables `users`, `devices`, `assignments`, `schedule_profiles`, `schedule_blocks`, `parent_invites`, `parent_student_links`, `token_blocklist`, `screen_sessions`, `cv_events`, `accountability_logs`, `daily_summaries`, `study_sessions`, `reminders`, `roast_logs`.
  - `db/migrations/versions/`: Contains Alembic migration revisions `001_initial_schema.py`, `002_schedule_module.py`, `003_auth_device_parent.py`.

- **Authentication Endpoints (`api/routes_auth.py`)**:
  - `POST /auth/register` (line 119): Registers user (`email`, `password`, `role`, `display_name`), returns status 201 with `access_token` and `user` object.
  - `POST /auth/login` (line 152): Authenticates user (`email`, `password`), returns `access_token` and `user` object.
  - `GET /auth/me` (line 169): Requires `Authorization: Bearer <token>`, returns `UserOut`.
  - `POST /auth/logout` (line 128): Adds Bearer token to `TokenBlocklist`.
  - `GET /reset-db` (line 25): Drops all metadata tables and re-invokes `init_db()`.

- **Onboarding Endpoints (`api/routes_onboarding.py`)**:
  - `POST /onboarding/complete` (line 22): Requires `Authorization: Bearer <token>`. Expects JSON body with `course`, `age`, `education_level`, `ai_engine`, `api_key`, `wake_time`, `sleep_time`, `study_goal_minutes`. Updates user fields, sets `onboarding_completed = True`, creates `ScheduleProfile` and default `ScheduleBlock`.

- **Assignments Endpoints (`api/routes_assignments.py`)**:
  - `POST /assignments/` (line 52): Requires Bearer token. Expects `title`, `subject`, `due_date`, `priority`, `notes`. Returns status 201 `AssignmentOut`.
  - `POST /assignments/nlp` (line 70): Requires Bearer token. Expects `text`, parses natural language into assignment.
  - `GET /assignments/` (line 84): Lists user assignments (optional query `status`).
  - `GET /assignments/upcoming` (line 89): Lists upcoming assignments for next `days` (default 7).
  - `GET /assignments/overdue` (line 94): Lists overdue assignments.
  - `PATCH /assignments/{assignment_id}/status` (line 99): Updates status (`pending`, `in_progress`, `done`).
  - `POST /assignments/{assignment_id}/done` (line 108): Marks assignment as done.
  - `DELETE /assignments/{assignment_id}` (line 117): Deletes assignment (204 No Content).

- **Existing Test Suite (`tests/`)**:
  - `tests/conftest.py`: Mocks database with isolated temporary SQLite file for pytest runs. Sets `NO_HARDWARE=1` and `NO_VOICE=1`.
  - `tests/test_auth_device_parent.py`: Unit tests for registration, login, `/auth/me`, device heartbeat, parent linking.
  - `tests/test_assignments.py`: Unit tests for assignment manager & reminders.
  - `tests/test_api.py`: Integration tests for assignments, screen, CV, reports, voice, study, health.
  - `tests/test_api_desktop.py`: Integration tests for settings and monitoring.

---

## 2. Logic Chain
1. **Observation**: `main.py` imports and registers `auth_router`, `onboarding_router`, and `assignments_router` while calling `init_db()` on startup.
2. **Logic Step**: The FastAPI application automatically ensures database tables exist when launched via `python run_server.py --port 8000 --dev --no-browser` or `uvicorn main:app`.
3. **Observation**: Routes in `routes_auth.py`, `routes_onboarding.py`, and `routes_assignments.py` rely on `get_db` for SQLAlchemy sessions and `current_user` for Bearer token authorization.
4. **Logic Step**: To verify Requirement R1 without 500 errors, network requests must follow a strict order:
   - First, register or log in via `POST /auth/register` or `POST /auth/login` to obtain an `access_token`.
   - Second, pass `Authorization: Bearer <access_token>` in all subsequent requests to `/auth/me`, `/onboarding/complete`, `/assignments/`, `/assignments/upcoming`, and `/assignments/{id}/done`.
5. **Observation**: Existing test file `tests/test_auth_device_parent.py` tests Auth endpoints, but there is no existing unit test in `tests/` targeting `/onboarding/complete`.
6. **Logic Step**: An automated Python network verification script (provided in `analysis.md` section 4.4) executing against `http://127.0.0.1:8000` will validate all R1 core flows in real runtime environment without modifying source code.

---

## 3. Caveats
- **No Source Modification**: As per read-only explorer constraints, no project source code was modified.
- **Test Server Launch**: The backend server was not launched in this exploration phase to strictly respect the constraint "Do NOT launch long-running servers or run tests yourself."
- **Database File Choice**: SQLite is used locally by default (`mimo.db`). Ensure `.env` is set with `NO_HARDWARE=1` and `NO_VOICE=1` when running the server locally to prevent missing hardware driver exceptions (e.g. OpenCV camera streams or PyAudio microphones).

---

## 4. Conclusion
The backend codebase is fully structured and prepared for Requirement R1 core flow verification.
- **Entry point**: `main.py` / `run_server.py`.
- **Port**: Default `8000`.
- **Database sync**: Handled by `init_db()` in `db/database.py` and Alembic migrations.
- **Target core endpoints**:
  1. `POST /auth/register` & `POST /auth/login` -> Bearer token generation.
  2. `POST /onboarding/complete` -> User onboarding & schedule profile creation.
  3. `POST /assignments/`, `GET /assignments/`, `GET /assignments/upcoming`, `POST /assignments/{id}/done` -> Assignment lifecycle.
- Detailed technical report has been compiled in `analysis.md`.

---

## 5. Verification Method
To independently verify these findings:
1. Inspect `c:\Users\samee\projects\Mimo\main.py` lines 34 and 93–117 for router registrations and DB init.
2. Inspect `c:\Users\samee\projects\Mimo\api\routes_auth.py`, `routes_onboarding.py`, and `routes_assignments.py` for exact request/response Pydantic models.
3. Inspect `c:\Users\samee\projects\Mimo\.agents\teamwork_preview_explorer_survey_1\analysis.md` for the complete end-to-end Python network verification script.
4. Execute `python run_server.py --port 8000 --dev --no-browser` and run the verification script in section 4.4 of `analysis.md` to confirm all endpoints respond with 200/201 OK.
