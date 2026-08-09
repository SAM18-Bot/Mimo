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
