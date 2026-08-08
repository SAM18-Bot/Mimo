# Dispatch Assignment — Forensic Auditor M1 Gate 1

## Mission
Perform forensic integrity audit for Milestone 1 (Android Local Data Layer: Room DB, Entities, DAOs, Database, DashboardViewModel offline-first refactoring, and test network isolation).

## Scope & Target Files
- `android/app/src/main/java/com/mimo/app/data/`
- `android/app/src/main/java/com/mimo/app/ui/DashboardViewModel.kt`
- `android/app/src/test/java/com/mimo/app/ui/DashboardViewModelTest.kt`

## Checks
1. Perform static code analysis to verify Room DB entities and DAOs are genuine implementations, not mocked facades or hardcoded stubs.
2. Verify `DashboardViewModel` legitimately queries/writes Room DB DAOs and uses genuine coroutine Flows.
3. Verify `DashboardViewModelTest` uses valid `FakeMimoApiService` without hardcoding outputs into source files or bypassing Room DB state.
4. Run `cmd /c "cd android && gradlew.bat test"` to verify clean test execution.
5. Deliver verdict: CLEAN or INTEGRITY VIOLATION in `handoff.md`.

## Attached Context
- `ORIGINAL_REQUEST.md`
- `PROJECT.md`
- `TEST_INFRA.md`
