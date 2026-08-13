# Project: Mimo — Verification and Final Release Compilation

## Architecture
- **Backend Service (FastAPI)**: Python server running `main:app` via `run_server.py`. Handles SQLite database (`mimo.db`) with Alembic migrations, SQLAlchemy models, and REST API for Auth, Onboarding, Assignments, etc.
- **Desktop Application (PyInstaller + PyWebView)**: Windows desktop GUI wrapping FastAPI backend and pywebview frontend. Entry point `desktop/main_desktop.py`, configured via `desktop/mimo.spec`.
- **Android Application (Kotlin + Compose + Gradle)**: Native Android app in `android/` directory using AGP 8.2.2, compileSdk 34, built via Gradle wrapper `gradlew assembleDebug`.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Backend DB Sync & Server Startup | FastAPI `init_db()` and Alembic schema synchronization, headless launch on local port | Milestone 1 | ORIGINAL_REQUEST R1 |
| 2 | Core Flows Verification (Auth, Onboarding, Assignments) | End-to-end network requests against `/auth/register`, `/auth/login`, `/auth/me`, `/onboarding/complete`, `/assignments/` returning 200/201 OK | Milestone 1 | ORIGINAL_REQUEST R1 |
| 3 | PyInstaller Spec & Lifecycle Hardening | Fix `numpy` exclusion in `desktop/mimo.spec` and resolve zombie process hazards in `main_desktop.py` & `tray.py` | Milestone 2 | Survey Explorer 2 |
| 4 | Desktop Executable Build (`dist/Mimo/Mimo.exe`) | Run `pyinstaller desktop/mimo.spec`, verify static/ bundling and clean process launch/exit | Milestone 2 | ORIGINAL_REQUEST R2 |
| 5 | Android SDK Config & Local Properties | Ensure `android/local.properties` specifies SDK directory `C:\Users\samee\AppData\Local\Android\Sdk` | Milestone 3 | Survey Explorer 3 |
| 6 | Android APK Compilation (`app-debug.apk`) | Execute `gradlew assembleDebug` in `android/`, verify `android/app/build/outputs/apk/debug/app-debug.apk` binary | Milestone 3 | ORIGINAL_REQUEST R3 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | FastAPI Backend Core Flows Verification | Launch local server, run e2e network request verification for Auth, Onboarding, Assignments, generate verification log | none | DONE |
| M2 | PyInstaller Desktop App Compilation | Apply spec & zombie fixes, execute PyInstaller build for `dist/Mimo/Mimo.exe`, verify static bundling & launch | none | DONE |
| M3 | Android App Compilation | Ensure SDK properties, execute `gradlew assembleDebug`, verify `app-debug.apk` output binary | none | DONE |
| M4 | Android Unit Tests Remediation | Implement missing `authenticateGoogle` in `FakeMimoApiService` across Android test files, execute `.\gradlew testDebugUnitTest` and verify 100% pass | M3 | PLANNED |

## Interface Contracts
### Backend REST API Contracts
- `POST /auth/register`: Payload `{"email": "...", "password": "...", "display_name": "...", "role": "student"}` -> Response 201 `{"access_token": "...", "token_type": "bearer", "user": {...}}`
- `POST /auth/login`: Payload `{"email": "...", "password": "..."}` -> Response 200 `{"access_token": "...", "user": {...}}`
- `GET /auth/me`: Headers `Authorization: Bearer <token>` -> Response 200 `UserOut`
- `POST /onboarding/complete`: Headers `Authorization: Bearer <token>`, Payload `{"course": "Computer Science", "age": 20, "education_level": "Undergraduate", "ai_engine": "gemini", "api_key": "test_key", "wake_time": "08:00", "sleep_time": "23:00", "study_goal_minutes": 120}` -> Response 200 `{"status": "success", "message": "Onboarding completed successfully"}`
- `POST /assignments/`: Headers `Authorization: Bearer <token>`, Payload `{"title": "Math Homework", "subject": "Math", "due_date": "2026-08-15T18:00:00", "priority": "high", "notes": "Chapter 5"}` -> Response 201 `AssignmentOut`
- `GET /assignments/`: Headers `Authorization: Bearer <token>` -> Response 200 `List[AssignmentOut]`
- `GET /assignments/upcoming`: Headers `Authorization: Bearer <token>` -> Response 200 `List[AssignmentOut]`
- `POST /assignments/{assignment_id}/done`: Headers `Authorization: Bearer <token>` -> Response 200 `AssignmentOut`

## Code Layout
- Backend: `main.py`, `run_server.py`, `db/`, `api/`, `modules/`
- Desktop: `desktop/main_desktop.py`, `desktop/mimo.spec`, `desktop/tray.py`, `static/`
- Android: `android/app/build.gradle.kts`, `android/local.properties`, `android/gradlew.bat`
- Metadata & Reports: `.agents/orchestrator_r3/`, `.agents/work_m1/`, `.agents/work_m2/`, `.agents/work_m3/`
