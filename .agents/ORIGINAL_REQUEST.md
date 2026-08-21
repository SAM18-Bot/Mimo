# Original User Request

## 2026-08-13T09:03:32Z

Fix remaining crashes, cross-tenant data leaks, unauthenticated endpoints, and single-user assumptions in the Mimo application, and fix the Android app's WebSocket authentication.

Working directory: c:\Users\samee\projects\Mimo
Integrity mode: development

## Requirements

### R1. Fix Confirmed Crashes
- `modules/ai_layer/roast_engine.py::_save_roast()`: Pass `user_id` when inserting `RoastLog`.
- `modules/voice/intent_router.py::_handle_what_to_study()`: Pass `user_id` to `StudyAdvisor.get_next_to_study()` and the fallback `get_upcoming()`.
- `api/routes_sync.py::push_sync()`: Fix column names in `DailySummary` creation (`productive_time_s`, `distracted_time_s`, `neutral_time_s`).
- `api/routes_sync.py::pull_sync()`: Pass `user_id` to `get_upcoming()`.

### R2. Fix Cross-Tenant Data Leaks
- `modules/schedule/manager.py`: Filter by `user_id` in `boost_subject_priority()`, `smart_suggestions()`, and `update_block_status()`. Ensure users can only modify their own schedule blocks.
- `modules/ai_layer/roast_engine.py::_get_context()`: Filter nearest-due Assignment by `user_id`.
- `api/websocket.py`: Update `ConnectionManager.broadcast()` or create a `unicast()` method to ensure payloads (stats, assignments, roasts) are only sent to the specific user's connected websockets. Apply this to `main.py`, `schedulers/daily_trigger.py`, `modules/assignments/reminder.py`, and CV/roast broadcasts.

### R3. Enforce Authentication on All Routes
- Apply `@Depends(current_user)` or equivalent authentication to `api/routes_settings.py`, `api/routes_monitoring.py`, and `api/routes_voice.py`.

### R4. Fix Single-User Assumptions
- `schedulers/daily_trigger.py::_run_eod()`: Ensure nightly reports iterate over all active users and pass `user_id` to `run_eod_report()`.
- `modules/cv_pipeline/presence.py::_log_event()`: Resolve user by `user_id` rather than grabbing the first user in the DB.
- `RoastEngine`: Refactor cooldown state to be per-user rather than a process-wide singleton.

### R5. Fix Android WebSocket Authentication
- Update `android/app/src/main/java/com/mimo/app/network/WebSocketManager.kt` to read the stored JWT from `TokenManager` (or similar) and pass it to the WebSocket connection instead of using the hardcoded `dev_token`.
- Update call sites (`DashboardViewModel.kt`, `RoastEnforcementService.kt`) to ensure they initiate the connection with the real JWT.

### R6. Minor Cleanup
- Add `.venv-test/` to `.gitignore` and remove it from git tracking.
- Remove unused variables/computations in `modules/behavior_engine/pattern_detector.py` and `modules/cv_pipeline/focus_scorer.py`, and clean up dead imports.
- Change `os.system` to `subprocess.run` in `desktop/autostart.py`.

## Acceptance Criteria

### Verification
- [ ] All Python tests in `pytest tests/` pass successfully in under 30 seconds.
- [ ] Add a mock for OpenAI/Gemini API calls in `conftest.py` or `test_api.py` to prevent real network calls during testing and fix the slow test suite issue.
- [ ] Tests must be added or updated to cover the newly authenticated routes (`settings`, `monitoring`, `voice`).
- [ ] Android project compiles successfully (`./gradlew assembleDebug` or similar).

## 2026-08-20T17:45:38Z

# Teamwork Project Prompt — Draft

> Status: Launched
> Goal: Craft prompt → get user approval → delegate to teamwork_preview
> Requested team: A full agent team

Deep scan the Mimo repository, run all test cases to ensure the system is working perfectly, and build the final release bundles for both the Android and Desktop apps.

Working directory: c:\Users\samee\projects\Mimo
Integrity mode: benchmark

## Requirements

### R1. Deep Scan and Testing
Run the comprehensive test suite (`pytest`) and perform a codebase deep scan. Ensure that no regressions exist after recent AI engine and database changes. All Python backend tests must pass flawlessly.

### R2. Desktop App Bundling
Build a final, distributable bundle or executable for the Mimo Desktop app.

### R3. Android Release Bundling
Compile and build the final Android application. The output must be a signed **Release APK**, which requires configuring or utilizing the existing keystore details.

## Acceptance Criteria

### Verification
- [ ] All Python tests (`pytest tests/`) pass with zero errors.
- [ ] A successfully compiled Desktop app executable/bundle exists in the repository (e.g., in `dist/` or `build/`).
- [ ] A successfully compiled, signed Android Release APK exists in the repository (e.g., in `android/app/build/outputs/apk/release/`).
