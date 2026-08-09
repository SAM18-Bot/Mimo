# Orchestrator Context: Mimo Project

## Project Overview
Mimo consists of a Kotlin Android App (`android/`), a Python Desktop App (`desktop/`), and a FastAPI backend.
The primary objectives are:
1. Fix instant crash on startup in the Android app without disabling core functions (background tracking, networking, notifications).
2. Create isolated test environments for Desktop (`.venv` with `pytest` / `test_requirements.txt`) and Android (`android/app/build.gradle.kts` configured for `testDebugUnitTest` with Robolectric & MockK).
3. Write unit tests for Desktop (`desktop/tests/` mocking `mimo-e8u2.onrender.com`) and Android (`android/app/src/test/` verifying `MainActivity`, `DashboardViewModel`, and background services).

## Workspace Paths
- Project Root: `c:\Users\samee\projects\Mimo`
- Android App: `c:\Users\samee\projects\Mimo\android`
- Desktop App: `c:\Users\samee\projects\Mimo\desktop`
- Orchestrator Workspace: `c:\Users\samee\projects\Mimo\.agents\orchestrator`
- Original Request: `c:\Users\samee\projects\Mimo\.agents\ORIGINAL_REQUEST.md`

## Key Files to Monitor
- `android/app/src/main/java/com/mimo/app/MainActivity.kt`
- `android/app/src/main/java/com/mimo/app/MimoApplication.kt`
- `android/app/src/main/java/com/mimo/app/ui/dashboard/DashboardViewModel.kt`
- `android/app/src/main/java/com/mimo/app/service/MimoRoastService.kt`
- `android/app/build.gradle.kts`
- `desktop/`
