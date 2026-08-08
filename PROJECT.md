# Project: Mimo Standalone Productivity Tracker & Sync Engine

## Architecture
- Workspace: `c:\Users\samee\projects\Mimo\`
- Mobile Application: Android (Kotlin, Jetpack Compose, Room DB, WorkManager, UsageStatsManager)
- Backend Application: Python (FastAPI, SQLAlchemy, SQLite `accountability.db`, Pytest)
- Data Architecture: Local-First Room Database (`com.mimo.app.data`) on Android; periodic/on-demand REST sync via `SyncWorker` to FastAPI `/sync/push` and `/sync/pull` endpoints.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Room Database (`MimoDatabase`) | Abstract Room DB provider with `AssignmentEntity` and `DailyStatsEntity` | M1 | R1 |
| 2 | `AssignmentEntity` Room Entity | SQLite table for offline assignment storage (`id`, `title`, `subject`, `due_date`, `priority`, `status`, `notes`, `isSynced`) | M1 | R1 |
| 3 | `DailyStatsEntity` Room Entity | SQLite table for local focus scores and time tracking (`date`, `productive_min`, `distracting_min`, `neutral_min`, `focus_score`, `isSynced`) | M1 | R1 |
| 4 | `AssignmentDao` & `DailyStatsDao` | Room DAOs exposing CRUD methods and reactive Kotlin `Flow` streams | M1 | R1 |
| 5 | Offline `DashboardViewModel` | Refactored ViewModel reading/writing local Room DB via DAOs instead of direct Retrofit REST calls | M1 | R1 |
| 6 | `MobileTrackerService` | Foreground service using `UsageStatsManager` to poll active foreground app usage | M2 | R2 |
| 7 | Distraction Categorizer & Threshold Monitor | Classifies apps into categories and tracks continuous distracting minutes vs threshold (5m) | M2 | R2 |
| 8 | Autonomous Roast Notifications | High-priority system alert on `mimo_roast_channel` when distraction threshold is breached | M2 | R2 |
| 9 | Backend `POST /sync/push` Endpoint | Python API endpoint receiving mobile usage logs & assignments, inserting into `ScreenSession` and `Assignment` tables | M3 | R3 |
| 10 | Backend `GET /sync/pull` Endpoint | Python API endpoint returning merged daily stats (`desk_time_min`, `focus_score`) and authoritative assignment list | M3 | R3 |
| 11 | Android `SyncWorker` Task | WorkManager `CoroutineWorker` executing background push/pull sync loop | M3 | R3 |
| 12 | WorkManager Sync Scheduler | Enqueues 15-minute periodic schedule & `NetworkType.CONNECTED` constraints for `SyncWorker` | M3 | R3 |
| 13 | End-to-End Test Suite | Opaque-box test suite verifying Room DB, Mobile Tracker logic, and Pytest Sync endpoints | M4 | E2E |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Android Local Data Layer (Room DB) | Room DB entities, DAOs, Database, refactored `DashboardViewModel` for offline-first state | none | IN_PROGRESS |
| M2 | Mobile Screen Tracking & Roast Service | `MobileTrackerService`, `UsageStatsManager` categorizer, distraction threshold, roast notifications | M1 | PLANNED |
| M3 | Sync Engine (Backend REST + Android WorkManager) | `api/routes_sync.py` push/pull endpoints, Android `SyncWorker`, WorkManager scheduler, pytest sync suite | M1, M2 | PLANNED |
| M4 | E2E Testing Suite & Final Hardening | Tiers 1-4 E2E tests, Tier 5 adversarial testing, Forensic Audit verification | M1, M2, M3 | PLANNED |

## Interface Contracts
### Mobile Client ↔ FastAPI Backend Sync API (`http://<host>:8000/sync`)

#### 1. `POST /sync/push`
- Request Headers: `Content-Type: application/json`
- Request Body:
```json
{
  "device_id": "mobile_android_01",
  "screen_sessions": [
    {
      "app_name": "com.instagram.android",
      "category": "distracting",
      "started_at": "2026-08-07T10:00:00Z",
      "ended_at": "2026-08-07T10:15:00Z",
      "duration_s": 900,
      "session_date": "2026-08-07"
    }
  ],
  "assignments": [
    {
      "id": "opt-local-1",
      "title": "Math Homework",
      "subject": "Math",
      "due_date": "2026-08-08",
      "priority": "high",
      "status": "done",
      "notes": "Completed offline"
    }
  ]
}
```
- Response Body (200 OK):
```json
{
  "status": "success",
  "processed_sessions": 1,
  "processed_assignments": 1,
  "daily_summary": {
    "date": "2026-08-07",
    "productive_time_min": 60,
    "distracted_time_min": 15,
    "desk_time_min": 75,
    "focus_score": 82.5
  }
}
```

#### 2. `GET /sync/pull`
- Query Parameters: `device_id` (string), `date` (ISO Date YYYY-MM-DD, optional)
- Response Body (200 OK):
```json
{
  "status": "success",
  "date": "2026-08-07",
  "daily_summary": {
    "focus_score": 82.5,
    "productive_time_min": 60,
    "distracted_time_min": 15,
    "desk_time_min": 75
  },
  "assignments": [
    {
      "id": 1,
      "title": "Math Homework",
      "subject": "Math",
      "due_date": "2026-08-08",
      "priority": "high",
      "status": "done",
      "notes": "Completed offline"
    }
  ]
}
```

## Code Layout
- Android: `android/app/src/main/java/com/mimo/app/`
  - `data/`: `MimoDatabase.kt`, `AssignmentEntity.kt`, `DailyStatsEntity.kt`, `AssignmentDao.kt`, `DailyStatsDao.kt`
  - `service/`: `MobileTrackerService.kt`, `RoastEnforcementService.kt`
  - `sync/`: `SyncWorker.kt`, `SyncScheduler.kt`
  - `ui/`: `DashboardViewModel.kt`, `DashboardScreen.kt`
- Python Backend: `api/` & `db/`
  - `api/routes_sync.py`
  - `main.py`
  - `tests/test_sync.py`
