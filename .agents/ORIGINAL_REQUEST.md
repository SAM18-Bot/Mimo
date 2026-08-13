# Original User Request

## Initial Request — 2026-08-08T13:14:58+05:30

<USER_REQUEST>
The goal is to thoroughly debug the instant crash on the Mimo Android app, create isolated testing environments for both the Python Desktop App and the Android App, and write and run a comprehensive unit test suite to ensure neither app crashes on startup.

Working directory: c:\Users\samee\projects\Mimo
Integrity mode: development

## Requirements

### R1. Resolve the Android Instant Crash
Investigate and completely fix the bug causing the Mimo Android app to instantly crash (close within 1-2 seconds) upon opening. The fix must be applied to the Kotlin source code without disabling core functionality (such as background tracking or networking).

### R2. Establish Isolated Test Environments
Set up a clean Python `venv` specifically for running desktop tests, and ensure the Android Gradle project is configured to run isolated local JVM tests (`testDebugUnitTest`). 

### R3. Comprehensive Mocked Unit Testing
Write and execute comprehensive unit tests for both the Desktop app (using `pytest` or `unittest`) and the Android app (using `JUnit` and `Robolectric`/`MockK`). These tests must mock the backend API and verify that every major component (e.g., UI initialization, network clients, background services) can initialize successfully without exceptions.

## Acceptance Criteria

### Crash Resolution
- [ ] The Android app compiles via `.\gradlew assembleDebug` successfully.
- [ ] No `Exception` or `Crash` logs are thrown in `logcat` when simulating the app startup via Robolectric tests.

### Desktop Testing
- [ ] A dedicated `test_requirements.txt` or equivalent is created to install `pytest` and mocking libraries in an isolated `.venv`.
- [ ] A test suite exists in `desktop/tests/` that mocks the `mimo-e8u2.onrender.com` backend.
- [ ] Running `pytest desktop/tests/` passes with 100% success and covers app initialization.

### Android Testing
- [ ] A test suite exists in `android/app/src/test/` using Robolectric or equivalent mocking frameworks.
- [ ] Running `.\gradlew testDebugUnitTest` passes with 100% success.
- [ ] The Android test suite explicitly verifies `MainActivity`, `DashboardViewModel`, and background services can initialize without crashing.
</USER_REQUEST>

## Follow-up — 2026-08-11T08:27:08+05:30

<USER_REQUEST>
# Teamwork Project Prompt — Draft

> Status: Launched.
> Goal: Craft prompt → get user approval → delegate to teamwork_preview

Verify the Mimo cross-platform application (Desktop and Android), ensure all recently implemented features function correctly through thorough runtime testing, and compile the final release artifacts.

Working directory: c:\Users\samee\projects\Mimo
Integrity mode: benchmark

## Requirements

### R1. Thorough Verification of Core Flows
Run the FastAPI backend locally and execute network requests (e.g., via `curl` or a Python test script) against the critical endpoints: Authentication, Onboarding, and Assignments. Ensure no 500 errors occur and that the database schema is fully synchronized.

### R2. Compile Final Desktop App
Using PyInstaller, compile the final `Mimo.exe` Desktop app. Verify that the build correctly bundles the `static/` directory and successfully launches without background zombie process hanging.

### R3. Compile Final Android App
Run the Gradle build (`gradlew assembleDebug`) in the `android/` directory. Verify that the `app-debug.apk` is generated successfully without compilation errors.

## Acceptance Criteria

### Verification & Build Success
- [ ] A test script or manual request verification log is produced showing successful 200 OK responses for Login, Onboarding, and Assignment creation.
- [ ] The Desktop executable (`dist/Mimo/Mimo.exe`) is generated and its binary exists.
- [ ] The Android APK (`android/app/build/outputs/apk/debug/app-debug.apk`) is generated and its binary exists.

---
*Next: when approved → delegate via invoke_subagent (see Delegation Protocol)*
</USER_REQUEST>

## Follow-up — 2026-08-11T15:42:50Z

The server restarted and all tasks were halted. Sweeping security fixes were made to the backend architecture (including changing `api_key` to an encrypted property, modifying WebSocket token auth in `main.py`, and fixing `user_id` scoping in `get_daily_stats`). Re-verify the codebase against these changes and fix any broken tests before re-triggering the final audit and compiling the Desktop/Android apps.

## Follow-up — 2026-08-12T15:37:14Z

The server restarted again, pausing all tasks. Resume verification and compilation work where left off. Review previous state and ensure new security fixes (api_key encryption, WS token scoping, etc.) are fully tested and desktop/Android apps are compiled.
