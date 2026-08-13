# Backend Codebase Survey & Analysis Report (Requirement R1)

## Executive Summary
This report provides a detailed survey of the FastAPI backend application in the Mimo codebase for Requirement R1 (Thorough Verification of Core Flows). It details the location of backend application files, database initialization/migrations/schema setup, entry points, exact request/response formats for Authentication, Onboarding, and Assignments endpoints, local server execution steps, and an inventory of existing tests and verification utilities.

---

## 1. Backend Architecture & Entry Points

### 1.1 Application Structure & Key Files
- **Root Entry Point (`main.py`)**: Defines the main FastAPI application `app = FastAPI(title="Mimo — AI Accountability System", version="2.0.0", lifespan=lifespan)`.
- **Server Launcher (`run_server.py`)**: CLI script that configures Uvicorn server options (`--port`, `--host`, `--dev`, `--no-browser`) and executes `uvicorn.run("main:app", ...)`. Default port: **8000**, default host: **0.0.0.0**.
- **Desktop Launcher (`run_desktop.py`)**: Runs Uvicorn in a background thread while launching a PySide6 GUI / system tray application.
- **Global Configuration (`config.py`)**: Loads environment variables from `.env` via `python-dotenv`. Configures `DATABASE_URL`, `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_EXPIRE_MINUTES`, `OPENAI_API_KEY`, app categorization keywords, and schedule timings.
- **API Router Directory (`api/`)**: Contains modular route handlers registered in `main.py`:
  - `routes_auth.py`: Authentication, JWT tokens, device registration, parent portal, database reset.
  - `routes_onboarding.py`: Student onboarding completion & initial schedule generation.
  - `routes_assignments.py`: Assignment CRUD operations, natural language parsing, and completion.
  - `routes_screen.py`: Screen tracking breakdowns and mock session injection.
  - `routes_cv.py`: Computer vision event logging and focus scores.
  - `routes_reports.py`: Productivity stats, history, and accountability Q&A logs.
  - `routes_schedule.py`: Schedule profiles, blocks, and auto-generated daily schedules.
  - `routes_settings.py`: Desktop settings CRUD and environment variable updates.
  - `routes_monitoring.py`: Background tracking pause/resume state.
  - `routes_sync.py`: Device data sync routes.
  - `routes_voice.py`: Voice intent handling and text-to-speech triggers.
  - `websocket.py`: WebSocket connection manager on `/ws` endpoint.

### 1.2 Startup Sequence & Lifespan Handler
In `main.py`:
1. Database initialization is invoked at module level via `from db.database import init_db; init_db()`.
2. Static assets are mounted at `/static`.
3. 12 API routers are included into `app`.
4. Lifespan context manager (`lifespan(app)`) starts:
   - Event bus drain loop (`asyncio.create_task(drain_event_bus())`).
   - Background tasks (`schedulers.background_tasks.start_all(...)`).
   - APScheduler (`schedulers.daily_trigger.start_scheduler(...)`).

---

## 2. Database Initialization, Schema & Migrations

### 2.1 Database Configuration (`db/database.py`)
- Uses SQLAlchemy SQLAlchemy 2.0 with engine bound to `config.DATABASE_URL`.
- Default SQLite URL: `sqlite:///./mimo.db` (or `sqlite:///./accountability.db` in `.env.example`).
- Connect args for SQLite: `{"check_same_thread": False}`.
- Provides:
  - `init_db()`: Calls `Base.metadata.create_all(bind=engine)`.
  - `get_db()`: FastAPI dependency yielding a `Session`.
  - `get_db_ctx()`: Context manager for non-FastAPI modules (schedulers, background tasks).

### 2.2 Schema Models (`db/models.py`)
- **`User`** (`users` table): `id`, `email` (unique), `password_hash`, `role` (`student` | `parent`), `display_name`, `ai_engine`, `api_key`, `course`, `age`, `education_level`, `onboarding_completed` (Boolean), `auth_provider` (`local` | `google`), `google_id`, `created_at`.
- **`Device`** (`devices` table): `id`, `user_id` (FK `users.id`), `device_name`, `device_type` (`desktop` | `android` | `hardware` | `other`), `platform`, `status`, `linked_at`, `last_seen_at`, `created_at`.
- **`Assignment`** (`assignments` table): `id`, `user_id` (FK `users.id`), `title`, `subject`, `due_date` (Date), `priority` (`low` | `medium` | `high`), `status` (`pending` | `in_progress` | `done`), `notes`, `created_at`, `reminded_at`.
- **`ScheduleProfile`** (`schedule_profiles` table): `id`, `user_id` (FK `users.id`), `timezone`, `wake_time`, `sleep_time`, `school_start`, `school_end`, `study_goal_minutes`, `session_minutes`, `break_minutes`, `active`, `notes`, `created_at`, `updated_at`.
- **`ScheduleBlock`** (`schedule_blocks` table): `id`, `profile_id` (FK `schedule_profiles.id`), `day_of_week`, `block_date`, `start_time`, `end_time`, `kind` (`school` | `study` | `fixed` | `break`), `title`, `subject`, `flexibility`, `source`, `priority`, `status`, `created_at`.
- **`ParentInvite`** (`parent_invites` table): `id`, `student_id` (FK `users.id`), `code` (6-digit unique code), `expires_at`, `consumed_at`, `created_at`.
- **`ParentStudentLink`** (`parent_student_links` table): `id`, `parent_id` (FK `users.id`), `student_id` (FK `users.id`), `created_at`.
- **`TokenBlocklist`** (`token_blocklist` table): `id`, `token` (String 500, unique), `expires_at`, `created_at`.
- Additional tables: `ScreenSession`, `CVEvent`, `AccountabilityLog`, `DailySummary`, `StudySession`, `Reminder`, `RoastLog`.

### 2.3 Schema Migrations & Reset
- Migrations managed via Alembic (`alembic.ini`, `db/migrations/env.py`).
- Revision history in `db/migrations/versions/`:
  - `001_initial_schema.py`: Initial setup of core monitoring and assignment tables.
  - `002_schedule_module.py`: Schedules, reminders, roast logs.
  - `003_auth_device_parent.py`: Users, devices, parent link, token blocklist, foreign key additions.
- **Database Reset Endpoint**: `GET /reset-db` drops all tables (`Base.metadata.drop_all`) and calls `init_db()`, returning `{"message": "Database reset and schema recreated"}`.

---

## 3. Core Flow Endpoint Inventory & Request Formats

### 3.1 Authentication Flow (`api/routes_auth.py`)

#### 1. User Registration
- **HTTP Method & Path**: `POST /auth/register` (Status 201 Created)
- **Authentication**: None required.
- **Request Headers**: `Content-Type: application/json`
- **Request Body Format**:
  ```json
  {
    "email": "student@example.com",
    "password": "strongpassword123",
    "role": "student",
    "display_name": "Student Name"
  }
  ```
  *Validation Rules*: `email` valid EmailStr; `password` min 8 chars; `role` must be `"student"` or `"parent"`.
- **Response Format (201 Created)**:
  ```json
  {
    "access_token": "<jwt_access_token_string>",
    "token_type": "bearer",
    "user": {
      "id": 1,
      "email": "student@example.com",
      "role": "student",
      "display_name": "Student Name",
      "onboarding_completed": false
    }
  }
  ```
- **Error Responses**: `422 Unprocessable Entity` if email exists, password is too short, or input validation fails.

#### 2. User Login
- **HTTP Method & Path**: `POST /auth/login` (Status 200 OK)
- **Authentication**: None required.
- **Request Body Format**:
  ```json
  {
    "email": "student@example.com",
    "password": "strongpassword123"
  }
  ```
- **Response Format (200 OK)**: Same `AuthOut` schema as registration.
- **Error Responses**: `401 Unauthorized` (`{"detail": "invalid email or password"}`).

#### 3. User Profile (`/auth/me`)
- **HTTP Method & Path**: `GET /auth/me` (Status 200 OK)
- **Request Headers**: `Authorization: Bearer <access_token>`
- **Response Format (200 OK)**:
  ```json
  {
    "id": 1,
    "email": "student@example.com",
    "role": "student",
    "display_name": "Student Name",
    "onboarding_completed": false
  }
  ```
- **Error Responses**: `401 Unauthorized` if token is missing, invalid, or present in `TokenBlocklist`.

#### 4. Logout (`/auth/logout`)
- **HTTP Method & Path**: `POST /auth/logout` (Status 200 OK)
- **Request Headers**: `Authorization: Bearer <access_token>`
- **Response Format (200 OK)**: `{"status": "logged_out"}` (Adds token to `TokenBlocklist`).

---

### 3.2 Onboarding Flow (`api/routes_onboarding.py`)

#### Complete Onboarding
- **HTTP Method & Path**: `POST /onboarding/complete` (Status 200 OK)
- **Request Headers**: `Authorization: Bearer <access_token>` (Required)
- **Request Body Format**:
  ```json
  {
    "course": "Computer Science",
    "age": 20,
    "education_level": "Undergraduate",
    "ai_engine": "openai",
    "api_key": "sk-optional-key",
    "wake_time": "07:00",
    "sleep_time": "23:00",
    "study_goal_minutes": 120
  }
  ```
  *Validation Rules*: `course`, `age`, `education_level`, `ai_engine` are required. `api_key` optional. `wake_time` (default `"07:00"`), `sleep_time` (default `"23:00"`), `study_goal_minutes` (default `120`).
- **Backend Execution Logic**:
  1. Checks `user.onboarding_completed`. If `True`, returns `{"status": "success", "message": "Onboarding already completed."}`.
  2. Updates `user` object in database with `course`, `age`, `education_level`, `ai_engine`, `api_key`, and sets `onboarding_completed = True`.
  3. Creates an active `ScheduleProfile` row linked to `user.id`.
  4. Creates an initial default `ScheduleBlock` row for study sessions.
- **Response Format (200 OK)**:
  ```json
  {
    "status": "success",
    "message": "Onboarding completed successfully."
  }
  ```
- **Error Responses**: `401 Unauthorized` if token is missing or invalid.

---

### 3.3 Assignments Flow (`api/routes_assignments.py`)

#### 1. Create Assignment
- **HTTP Method & Path**: `POST /assignments/` (Status 201 Created)
- **Request Headers**: `Authorization: Bearer <access_token>` (Required)
- **Request Body Format**:
  ```json
  {
    "title": "Algorithms Problem Set 1",
    "subject": "Computer Science",
    "due_date": "2026-08-20",
    "priority": "high",
    "notes": "Exercises from Chapter 3"
  }
  ```
  *Fields*: `title` (required), `subject` (optional), `due_date` (ISO Date YYYY-MM-DD, required), `priority` (`"low"` | `"medium"` | `"high"`, default `"medium"`), `notes` (optional).
- **Backend Execution Logic**:
  1. Inserts `Assignment` record bound to `user.id`.
  2. Automatically schedules `Reminder` records for future trigger dates (3 days prior, 1 day prior, day of).
  3. Emits WebSocket broadcast `assignment_added`.
- **Response Format (201 Created)**:
  ```json
  {
    "id": 1,
    "title": "Algorithms Problem Set 1",
    "subject": "Computer Science",
    "due_date": "2026-08-20",
    "priority": "high",
    "status": "pending",
    "notes": "Exercises from Chapter 3"
  }
  ```

#### 2. Create Assignment via Natural Language (NLP)
- **HTTP Method & Path**: `POST /assignments/nlp` (Status 201 Created)
- **Request Headers**: `Authorization: Bearer <access_token>` (Required)
- **Request Body Format**:
  ```json
  {
    "text": "Math assignment due Friday"
  }
  ```
- **Response Format (201 Created)**: Returns created `AssignmentOut`.
- **Error Responses**: `422 Unprocessable Entity` if parsing fails.

#### 3. List All Assignments
- **HTTP Method & Path**: `GET /assignments/` (Status 200 OK)
- **Request Headers**: `Authorization: Bearer <access_token>` (Required)
- **Query Parameters**: `status` (optional: `?status=pending`, `?status=in_progress`, `?status=done`)
- **Response Format (200 OK)**: JSON Array of `AssignmentOut` objects.

#### 4. List Upcoming Assignments
- **HTTP Method & Path**: `GET /assignments/upcoming` (Status 200 OK)
- **Request Headers**: `Authorization: Bearer <access_token>` (Required)
- **Query Parameters**: `days` (optional, default 7, e.g. `?days=7`)
- **Response Format (200 OK)**: JSON Array of pending/in_progress `AssignmentOut` objects due within N days.

#### 5. List Overdue Assignments
- **HTTP Method & Path**: `GET /assignments/overdue` (Status 200 OK)
- **Request Headers**: `Authorization: Bearer <access_token>` (Required)
- **Response Format (200 OK)**: JSON Array of pending/in_progress `AssignmentOut` objects with due dates before today.

#### 6. Mark Assignment Status
- **HTTP Method & Path**: `PATCH /assignments/{assignment_id}/status` (Status 200 OK)
- **Request Headers**: `Authorization: Bearer <access_token>` (Required)
- **Request Body Format**: `{"status": "in_progress"}` (`"pending"` | `"in_progress"` | `"done"`)
- **Response Format (200 OK)**: `{"ok": true, "id": 1, "status": "in_progress"}`
- **Error Responses**: `404 Not Found`.

#### 7. Mark Assignment Done
- **HTTP Method & Path**: `POST /assignments/{assignment_id}/done` (Status 200 OK)
- **Request Headers**: `Authorization: Bearer <access_token>` (Required)
- **Response Format (200 OK)**: `{"ok": true, "message": "'Algorithms Problem Set 1' marked as done."}`
- **Error Responses**: `404 Not Found`.

#### 8. Delete Assignment
- **HTTP Method & Path**: `DELETE /assignments/{assignment_id}` (Status 204 No Content)
- **Request Headers**: `Authorization: Bearer <access_token>` (Required)
- **Response Format**: Empty body (204 No Content).

---

## 4. Local Execution & Verification Procedures

### 4.1 Environment Setup
Create or ensure `.env` file exists with test-safe variables:
```ini
OPENAI_API_KEY=sk-test-key
DATABASE_URL=sqlite:///./mimo.db
JWT_SECRET_KEY=dev-only-change-me
NO_HARDWARE=1
NO_VOICE=1
```

### 4.2 Local Server Execution Commands
To start the FastAPI backend server on port 8000:
```bash
# Option A: Using run_server.py script
python run_server.py --port 8000 --dev --no-browser

# Option B: Direct Uvicorn execution
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 4.3 Database Synchronization & Reset Commands
- Initial database creation on startup: automatically handled by `main.py` calling `init_db()`.
- Manual DB init via python snippet:
  ```bash
  python -c "from db.database import init_db; init_db()"
  ```
- Reset database via HTTP request:
  ```bash
  curl http://localhost:8000/reset-db
  ```

### 4.4 End-to-End Core Flow Verification (Network Requests)
Verification of Requirement R1 can be executed using three methods:

#### Method 1: Python Automated Network Verification Script (Against Live Server `http://127.0.0.1:8000`)
```python
import httpx

BASE_URL = "http://127.0.0.1:8000"

def verify_core_flows():
    client = httpx.Client(base_url=BASE_URL)
    
    # 1. Health check
    r = client.get("/health")
    assert r.status_code == 200, f"Health check failed: {r.text}"
    print("✓ Health check passed")

    # 2. Auth: Register
    reg_payload = {
        "email": "test_verification_user@example.com",
        "password": "Password123!",
        "role": "student",
        "display_name": "Verification User"
    }
    r = client.post("/auth/register", json=reg_payload)
    if r.status_code == 422: # If already registered, login
        r = client.post("/auth/login", json={"email": reg_payload["email"], "password": reg_payload["password"]})
    assert r.status_code in (200, 201), f"Auth failed: {r.text}"
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✓ Auth (Register/Login) passed")

    # 3. Auth: Verify /auth/me
    r = client.get("/auth/me", headers=headers)
    assert r.status_code == 200, f"/auth/me failed: {r.text}"
    print("✓ /auth/me passed")

    # 4. Onboarding: Complete
    onboard_payload = {
        "course": "Software Engineering",
        "age": 22,
        "education_level": "Undergraduate",
        "ai_engine": "openai",
        "wake_time": "07:00",
        "sleep_time": "23:00",
        "study_goal_minutes": 180
    }
    r = client.post("/onboarding/complete", json=onboard_payload, headers=headers)
    assert r.status_code == 200, f"Onboarding failed: {r.text}"
    print("✓ Onboarding complete passed")

    # 5. Assignments: Create
    assign_payload = {
        "title": "System Verification Assignment",
        "subject": "Testing",
        "due_date": "2026-08-25",
        "priority": "high",
        "notes": "Automated verification test"
    }
    r = client.post("/assignments/", json=assign_payload, headers=headers)
    assert r.status_code == 201, f"Assignment creation failed: {r.text}"
    assignment_id = r.json()["id"]
    print(f"✓ Assignment created (ID: {assignment_id})")

    # 6. Assignments: List & Upcoming
    r = client.get("/assignments/", headers=headers)
    assert r.status_code == 200 and len(r.json()) > 0, f"List assignments failed: {r.text}"
    
    r = client.get("/assignments/upcoming?days=30", headers=headers)
    assert r.status_code == 200, f"Upcoming assignments failed: {r.text}"
    print("✓ Assignments list and upcoming query passed")

    # 7. Assignments: Mark Done
    r = client.post(f"/assignments/{assignment_id}/done", headers=headers)
    assert r.status_code == 200, f"Mark assignment done failed: {r.text}"
    print("✓ Assignment marked done passed")

    print("\n🎉 ALL R1 CORE FLOW VERIFICATIONS PASSED WITH 200/201 OK!")

if __name__ == "__main__":
    verify_core_flows()
```

#### Method 2: cURL Commands
```bash
# 1. Register User
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"curluser@example.com","password":"password123","role":"student"}'

# (Save access_token from response as $TOKEN)

# 2. Complete Onboarding
curl -X POST http://localhost:8000/onboarding/complete \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"course":"Computer Science","age":21,"education_level":"College","ai_engine":"openai"}'

# 3. Create Assignment
curl -X POST http://localhost:8000/assignments/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Curl Assignment","due_date":"2026-08-25","priority":"high"}'
```

---

## 5. Existing Tests & Verification Utilities

### 5.1 Test Suite Breakdown (`tests/`)
- `tests/conftest.py`: Provides pytest fixtures. Creates a temporary SQLite database per test and monkeypatches FastAPI `TestClient` so that route dependency injection (`get_db`) and background context manager (`get_db_ctx`) point to the temporary engine. Sets `NO_HARDWARE=1` and `NO_VOICE=1`.
- `tests/test_auth_device_parent.py`: Coverage for authentication flows:
  - `test_register_login_and_me`
  - `test_duplicate_registration_rejected`
  - `test_device_registration_and_heartbeat`
  - `test_device_access_is_owner_only`
  - `test_student_creates_parent_invite_and_parent_links`
  - `test_parent_summary_requires_link`
  - `test_parent_summary_allowed_after_link`
- `tests/test_assignments.py`: Coverage for assignment business logic and auto-reminder generation (`TestAssignmentCRUD`, `TestUpcomingAndOverdue`, `TestReminders`).
- `tests/test_api.py`: Coverage for HTTP API endpoints (`TestHealth`, `TestAssignmentsAPI`, `TestScreenAPI`, `TestCVAPI`, `TestReportsAPI`, `TestVoiceAPI`, `TestStudyAPI`, `TestFullWorkflow`).
- `tests/test_api_desktop.py`: Coverage for settings page and monitoring status pause/resume (`TestSettingsPage`, `TestSettingsData`, `TestSettingsSave`, `TestSettingsSaveAll`, `TestMonitoringStatus`, `TestMonitoringPauseResume`).

### 5.2 Test Execution Command
To run all existing Python backend tests:
```bash
pytest tests/ -v
```

### 5.3 Key Gaps Identified in Existing Test Suite
1. **Onboarding Endpoint**: `POST /onboarding/complete` exists in `api/routes_onboarding.py`, but has **no unit test in `tests/`**.
2. **Auth Header Requirements**: Endpoints in `routes_assignments.py` depend on `current_user` (`Authorization: Bearer <token>`). Any manual test script or new test MUST pass valid Bearer tokens obtained via `/auth/register` or `/auth/login`.

---

## 6. Summary of Findings for R1 Verification Implementation
- The FastAPI application is fully equipped with database tables, Alembic migrations, and modular routers for Authentication (`routes_auth.py`), Onboarding (`routes_onboarding.py`), and Assignments (`routes_assignments.py`).
- All three target flows (Auth, Onboarding, Assignments) return well-defined JSON responses and manage database persistence automatically upon startup.
- Local server execution is straightforward using `python run_server.py --port 8000 --dev --no-browser`.
- An end-to-end Python network verification script (provided in Section 4.4) can be executed to verify all endpoints return 200/201 OK without 500 internal server errors.
