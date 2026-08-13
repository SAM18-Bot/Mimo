## 2026-08-12T21:40:19Z
You are worker_m4_gen2 (Android Unit Test Remediation Worker - Replacement).
Your working directory is: c:\Users\samee\projects\Mimo\.agents\work_m4_gen2
Read `c:\Users\samee\projects\Mimo\.agents\ORIGINAL_REQUEST.md` and `c:\Users\samee\projects\Mimo\.agents\orchestrator_r3\PROJECT.md`.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Background & Audit Feedback:
The Victory Auditor rejected the previous claim because `MimoApiService.kt` interface added `authenticateGoogle(body: Map<String, String>): Map<String, Any>`, but fake implementations of `MimoApiService` in test files (`DashboardViewModelTest.kt`, `DashboardViewModelStressTest.kt`, etc.) were missing an implementation of `authenticateGoogle`, causing `.\gradlew.bat testDebugUnitTest` compilation to fail.

Your Tasks:
1. Inspect `MimoApiService` interface definition in `android/app/src/main/java/com/mimo/app/network/MimoApiService.kt`.
2. Find all test files under `android/app/src/test/` that implement `MimoApiService` (specifically `DashboardViewModelTest.kt`, `DashboardViewModelStressTest.kt`, and any other test classes).
3. Implement `override suspend fun authenticateGoogle(body: Map<String, String>): Map<String, Any>` in all `FakeMimoApiService` classes (e.g. returning `mapOf("token" to "fake_token", "user" to mapOf("id" to "1"))`).
4. Execute `.\gradlew.bat testDebugUnitTest` in `android/` directory and ensure 100% passing tests with 0 compilation errors.
5. Execute `.\gradlew.bat assembleDebug` in `android/` directory and verify `android/app/build/outputs/apk/debug/app-debug.apk` is generated.
6. Write execution and test output logs to `c:\Users\samee\projects\Mimo\.agents\work_m4_gen2\test_log.txt`.
7. Write a detailed handoff report to `c:\Users\samee\projects\Mimo\.agents\work_m4_gen2\handoff.md`.
8. Send a message to parent when finished.
