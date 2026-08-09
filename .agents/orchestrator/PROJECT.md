# Project: Mimo Debugging, Test Environments & Comprehensive Unit Testing

## Architecture
- Target Workspaces: `c:\Users\samee\projects\Mimo\android` and `c:\Users\samee\projects\Mimo\desktop`
- Android Tech Stack: Kotlin, Jetpack Compose, Material 3, Coroutines, Retrofit, Room, Robolectric, JUnit, MockK
- Desktop Tech Stack: Python 3, PyWebview, Pystray, Pytest, Pytest-Mock, HTTPX
- Remote Backend URL: `https://mimo-e8u2.onrender.com` / Local Backend URL: `http://10.0.2.2:8000` / `http://127.0.0.1:8000`

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Android Startup Crash Fix | Replace `LazyColumn` inside `verticalScroll` Column in `AssignmentList.kt` & `DashboardScreen.kt` | M1 | explorer_survey_1 |
| 2 | Safe Date Parsing | Guard `LocalDate.parse` in `AssignmentCard` against empty/invalid `due_date` strings | M1 | explorer_survey_1 |
| 3 | Service & Permission Safeguards | Safeguard `startForegroundService` and `UsageStatsManager` queries in `MainActivity` & `MobileTrackerService` | M1 | explorer_survey_1 |
| 4 | Android Test Doubles & Gradle Config | Fix `pullSync`/`pushSync` in `FakeMimoApiService`; update `android/app/build.gradle.kts` with MockK, core-testing, rules, `isReturnDefaultValues = true` | M1 | explorer_survey_2 |
| 5 | Desktop Isolated Test Env (`.venv`) | Create clean `.venv` and `test_requirements.txt` with `pytest`, `pytest-mock`, `httpx` | M1 | explorer_survey_3 |
| 6 | Desktop Unit Test Suite | Write `desktop/tests/` suite mocking `https://mimo-e8u2.onrender.com` backend APIs | M2 | explorer_survey_3 |
| 7 | Android Local JVM Unit Test Suite | Write `android/app/src/test/` suite using Robolectric & MockK testing `MainActivity`, `DashboardViewModel`, and background services | M2 | explorer_survey_2 |
| 8 | E2E & Forensic Audit Verification | Verify `assembleDebug`, `pytest desktop/tests/`, `testDebugUnitTest` 100% pass & forensic audit CLEAN | M2 | dual_track |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Android Crash Fix & Test Envs Setup | Fix Compose scrolling crash, date parsing crash, update Gradle config & stubs, create `.venv` | none | IN_PROGRESS |
| M2 | Mocked Unit Test Suites & Full Verification | Implement `desktop/tests/` and `android/app/src/test/` test suites; verify all acceptance criteria | M1 | PLANNED |

## Interface Contracts
### Desktop Client ↔ Remote Backend (`https://mimo-e8u2.onrender.com`)
- `GET /health` -> `{"status": "ok"}`
- `GET /reports/stats` -> `{"focus_score": 85, "productive_minutes": 120, "distracting_minutes": 30, "streak_days": 5, "grade": "A"}`
- `GET /assignments/upcoming?days=14` -> `[{"id": "1", "title": "Math HW", "due_date": "2026-08-10", "priority": "high"}]`
- `POST /monitoring/pause` -> `{"status": "paused"}`
- `POST /monitoring/resume` -> `{"status": "resumed"}`

### Android Client ↔ Backend (`MimoApiService`)
- `suspend fun pushSync(payload: SyncPayload): Map<String, Any>`
- `suspend fun pullSync(): SyncPayload`

## Code Layout
`c:\Users\samee\projects\Mimo`
```
c:\Users\samee\projects\Mimo\
├── android/
│   ├── app/
│   │   ├── build.gradle.kts
│   │   └── src/
│   │       ├── main/java/com/mimo/app/
│   │       │   ├── MainActivity.kt
│   │       │   ├── service/RoastEnforcementService.kt
│   │       │   ├── tracker/MobileTrackerService.kt
│   │       │   └── ui/
│   │       │       ├── DashboardScreen.kt
│   │       │       └── components/AssignmentList.kt
│   │       └── test/java/com/mimo/app/
│   │           ├── MainActivityTest.kt
│   │           ├── ui/DashboardViewModelUnitTest.kt
│   │           ├── ui/DashboardViewModelTest.kt
│   │           └── service/ServiceUnitTest.kt
├── desktop/
│   ├── test_requirements.txt
│   └── tests/
│       ├── conftest.py
│       ├── test_backend_api_mock.py
│       ├── test_desktop_app_init.py
│       └── test_desktop_ui_services.py
```
