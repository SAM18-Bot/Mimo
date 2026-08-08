# Dispatch Assignment — Reviewer M1 Gate 1

## Mission
Review Milestone 1 (Android Local Data Layer: Room DB, Entities, DAOs, Database, DashboardViewModel offline-first refactoring, and test network isolation).

## Scope & Target Files
- `android/app/src/main/java/com/mimo/app/data/` (AssignmentEntity, DailyStatsEntity, AssignmentDao, DailyStatsDao, MimoDatabase)
- `android/app/src/main/java/com/mimo/app/ui/DashboardViewModel.kt`
- `android/app/src/main/java/com/mimo/app/MimoApplication.kt`
- `android/app/src/test/java/com/mimo/app/ui/DashboardViewModelTest.kt`

## Requirements & Verification
1. Verify Room DB entities and DAOs are correctly implemented with `isSynced` flag defaulting to `false`.
2. Verify `DashboardViewModel` reads and writes to local Room DB via DAOs as single source of truth.
3. Verify network calls in `DashboardViewModel` handle exceptions gracefully and don't fail offline operation.
4. Execute `cmd /c "cd android && gradlew.bat test"` and verify all unit tests pass with 0 failures.
5. Deliver verdict: APPROVE or REQUEST_CHANGES in `handoff.md`.

## Attached Context
- `ORIGINAL_REQUEST.md`
- `PROJECT.md`
- `TEST_INFRA.md`
