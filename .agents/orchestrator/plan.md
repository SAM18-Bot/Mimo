# Orchestrator Execution Plan: Mimo Android Crash Fix & Test Environments

## Objectives
1. **R1**: Investigate and fix the Mimo Android app instant startup crash without disabling core functionality.
2. **R2**: Establish isolated test environments: clean Python venv for desktop tests, and Android Gradle project configured for local JVM tests (`testDebugUnitTest`).
3. **R3**: Write and execute comprehensive mocked unit tests for Desktop (`desktop/tests/` mocking `mimo-e8u2.onrender.com`) and Android (`android/app/src/test/` using JUnit, Robolectric/MockK verifying MainActivity, DashboardViewModel, background services).

## Acceptance Criteria
- [ ] Android compiles via `.\gradlew assembleDebug`
- [ ] `pytest desktop/tests/` passes with 100% success
- [ ] `.\gradlew testDebugUnitTest` passes with 100% success

## Milestones & Work Breakdown

### Phase 0: Survey & Technical Investigation (Parallel Explorers)
- **Explorer 1**: Investigate `android/` codebase to pinpoint the root cause of the instant startup crash (1-2s).
- **Explorer 2**: Investigate Android Gradle setup (`build.gradle.kts`), local JVM test dependencies (JUnit 4/5, Robolectric, MockK), and test structures for `MainActivity`, `DashboardViewModel`, and `MimoRoastService`.
- **Explorer 3**: Investigate `desktop/` codebase, Python virtual environment setup (`.venv`), requirements, and `pytest` mocking strategies for backend endpoints (`mimo-e8u2.onrender.com`).

### Phase 1: Android Crash Fix & Test Environment Setup (Milestone 1)
- **Worker**: Apply Kotlin source code fixes for startup crash, configure `android/app/build.gradle.kts` with Robolectric and MockK dependencies, set up clean Python `.venv` with `pytest` & `test_requirements.txt`.
- **Reviewers**: Verify code quality, build success (`.\gradlew assembleDebug`), and test environment isolation.
- **Challenger**: Empirically verify builds and test environment setup.
- **Auditor**: Perform forensic integrity audit.

### Phase 2: Comprehensive Mocked Unit Tests Implementation (Milestone 2)
- **Worker**: Write Desktop unit tests in `desktop/tests/` mocking `mimo-e8u2.onrender.com`. Write Android JVM unit tests in `android/app/src/test/` with JUnit, Robolectric, and MockK testing `MainActivity`, `DashboardViewModel`, and background services. Run `pytest desktop/tests/` and `.\gradlew testDebugUnitTest`.
- **Reviewers**: Review unit test suites for coverage, mocking rigor, and test isolation.
- **Challenger**: Run full test suites (`pytest` and `gradlew testDebugUnitTest`).
- **Auditor**: Verify integrity of tests (no hardcoded/tautological assertions or cheating).

### Phase 3: Final Verification & Sentinel Reporting
- Verify all 3 acceptance criteria are satisfied with 100% passing results.
- Synthesize findings into handoff report.
