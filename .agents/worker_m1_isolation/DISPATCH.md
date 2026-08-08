# Dispatch Assignment — Worker M1 Isolation

## Mission
Fix network isolation in `DashboardViewModel` and `DashboardViewModelTest` so unit tests run 100% deterministically without network access.

## Scope
- Files: `android/app/src/main/java/com/mimo/app/ui/DashboardViewModel.kt`, `android/app/src/test/java/com/mimo/app/DashboardViewModelTest.kt`
- Objective: Ensure network failures in `DashboardViewModel` (e.g., when calling `ApiClient.api.getStats()`) are safely caught without interrupting offline operations or causing test exceptions, and ensure `DashboardViewModelTest.kt` mocks network dependencies or tests local Room DB behaviors safely.
- Verification command: Run `.\gradlew.bat test` from `c:\Users\samee\projects\Mimo\android\` (or workspace root if configured) and confirm 0 test failures.

## Instructions & Guidance
- Read `ORIGINAL_REQUEST.md`, `PROJECT.md`, and `TEST_INFRA.md`.
- Ensure offline functionality is preserved (Room DB remains source of truth).
- Wrap network API calls in `try-catch` inside `refresh()` or network fetching coroutine in `DashboardViewModel.kt` so `ConnectException` / network errors are swallowed or logged gracefully without blowing up local Flow subscriptions.
- Run `gradlew test` (or `.\gradlew.bat testDebugUnitTest`) to verify all unit tests pass.

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
