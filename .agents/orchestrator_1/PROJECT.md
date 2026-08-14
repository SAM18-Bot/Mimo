# Project: Mimo Bug Fixing, Multi-tenancy, Authentication & Android Refactoring

## Architecture
- Backend: Python FastAPI / SQLite / SQLAlchemy async / Pydantic
- WebSockets: `api/websocket.py` ConnectionManager broadcasting to active clients with user-scoped socket dictionary (`_user_sockets`)
- Schedulers & AI: `schedulers/daily_trigger.py`, `modules/ai_layer/roast_engine.py`, `modules/voice/intent_router.py`, `modules/cv_pipeline/presence.py`
- Android App: Kotlin / Android Jetpack / WebSocketManager / TokenManager / ViewModels

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | RoastEngine user_id | Pass `user_id` when saving `RoastLog` in `_save_roast()` | M1 | R1 |
| 2 | IntentRouter user_id | Pass `user_id` to `StudyAdvisor.get_next_to_study()` and fallback `get_upcoming()` | M1 | R1 |
| 3 | push_sync column names | Fix `DailySummary` column names (`productive_time_s`, `distracted_time_s`, `neutral_time_s`) & pass `user_id` | M1 | R1 |
| 4 | pull_sync user_id | Pass `user_id=current_user.id` to `get_upcoming()` in `pull_sync()` | M1 | R1 |
| 5 | ScheduleManager tenant filtering | Filter by `user_id` in `boost_subject_priority()`, `smart_suggestions()`, `update_block_status()`. Authorize block status updates. | M2 | R2 |
| 6 | RoastEngine context filtering | Filter nearest-due Assignment by `user_id` in `_get_context()` | M2 | R2 |
| 7 | WebSocket multi-tenancy & unicast | Implement unicast/user-scoped WS messaging in `api/websocket.py` and update call sites (`main.py`, `daily_trigger.py`, `reminder.py`, presence, roast) | M2 | R2 |
| 8 | Endpoint Authentication | Enforce `@Depends(current_user)` authentication on `routes_settings.py`, `routes_monitoring.py`, `routes_voice.py` | M3 | R3 |
| 9 | Multi-user EOD Nightly Reports | Iterate over all active users in `_run_eod()` and pass `user_id` to `run_eod_report()` | M4 | R4 |
| 10 | CV Presence User Resolution | Resolve user by `user_id` in `_log_event()` rather than first DB user | M4 | R4 |
| 11 | RoastEngine Per-User Cooldown | Refactor cooldown state from global scalars to `self._user_state: dict[int, dict]` | M4 | R4 |
| 12 | Android WebSocket JWT Auth | Read JWT from `TokenManager` in `WebSocketManager.kt` and pass to WS connection. Update `DashboardViewModel` & `RoastEnforcementService`. | M5 | R5 |
| 13 | Minor Cleanup & Autostart | Verify `.gitignore`; remove unused vars/imports in `pattern_detector.py` & `focus_scorer.py`; use `subprocess.run` in `autostart.py`. | M6 | R6 |
| 14 | Pytest Mocking & Verification | Add OpenAI/Gemini mock fixture in `conftest.py` for <30s test execution; add auth tests for `settings`, `monitoring`, `voice`; verify `./gradlew assembleDebug`. | M7 | Verification |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Fix Confirmed Crashes | R1 crash fixes in roast_engine, intent_router, routes_sync | None | DONE |
| M2 | Cross-Tenant Leaks & WS | R2 multi-tenant schedule filtering, roast context, unicast WS | M1 | PLANNED |
| M3 | Enforce Endpoint Auth | R3 auth on settings, monitoring, voice routes | None | PLANNED |
| M4 | Fix Single-User Assumptions | R4 EOD multi-user loop, CV presence resolution, Roast cooldown | M1, M2 | PLANNED |
| M5 | Android WebSocket Auth | R5 JWT token in WebSocketManager, ViewModel & Service call sites | M3 | PLANNED |
| M6 | Minor Cleanup | R6 unused code cleanup, autostart subprocess | None | PLANNED |
| M7 | Testing & Verification | Pytest fast mocking, auth route unit tests, Android assembleDebug | M1-M6 | PLANNED |

## Code Layout
- Backend: `api/`, `modules/`, `schedulers/`, `desktop/`
- Android: `android/app/src/main/java/com/mimo/app/`
- Tests: `tests/`
