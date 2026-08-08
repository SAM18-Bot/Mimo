# Soft Handoff — Orchestrator Generation 1 (orchestrator_r1) to Generation 2 (orchestrator_r2)

## 1. Milestone State
- **Phase 0: Survey & Requirements Mining**: **COMPLETED**. Analyzed Android app structure, FastAPI backend, SQLAlchemy database, and pytest test suite. Created `PROJECT.md` (Feature Inventory, Milestones, Interface Contracts) and `TEST_INFRA.md`.
- **Milestone 1: Android Local Data Layer (Room DB)**: **IN_PROGRESS / REMEDIATION**.
  - Implemented: `AssignmentEntity`, `DailyStatsEntity`, `AssignmentDao`, `DailyStatsDao`, `MimoDatabase` under `com.mimo.app.data`.
  - Refactored: `MimoApplication.kt` (database singleton exposure) and `DashboardViewModel.kt` (reactive Room DB `Flow` collection, `isSynced = false` local writes, dynamic date rollover via `currentDateFlow.flatMapLatest`, `ioDispatcher` constructor parameter).
  - Remediation Note: Gate checks highlighted that `DashboardViewModel.init` executes live Retrofit network calls (`ApiClient.api.getStats()`) which throw `ConnectException` in un-mocked unit test environments. Successor should adjust `DashboardViewModel.init` network error handling or wrap network calls in `DashboardViewModelTest` so unit tests run 100% deterministically.
- **Milestone 2: Mobile Screen Tracking (`MobileTrackerService`)**: **PLANNED**.
- **Milestone 3: Sync Engine (Python `api/routes_sync.py` & Android `SyncWorker`)**: **PLANNED**.
- **Milestone 4: E2E Test Suite & Final Hardening (Tiers 1-5)**: **PLANNED**.

## 2. Active Subagents
- All 23 subagents spawned in Generation 1 have delivered their handoff reports and are complete.

## 3. Pending Decisions & Known Issues
- `DashboardViewModelTest`: `DashboardViewModel.init` makes network calls that throw `ConnectException` during headless unit tests. Successor should instruct Worker to make network fetching fail-safe or conditionally disabled in unit tests (e.g. `try-catch` inside `refresh()` or mock API client).

## 4. Remaining Work for Successor (`orchestrator_r2`)
1. Dispatch Worker to fix `DashboardViewModelTest` unit test isolation so `.\gradlew.bat test` passes with 0 failures.
2. Run M1 Gate Check (Reviewers, Challengers, Forensic Auditor) and mark Milestone 1 **DONE** in `PROJECT.md` and `progress.md`.
3. Execute Milestone 2 (Mobile Screen Tracking: `MobileTrackerService`, `UsageStatsManager`, threshold monitoring, roast notifications).
4. Execute Milestone 3 (Sync Engine: `api/routes_sync.py` for `/sync/push` & `/sync/pull`, Android `SyncWorker` with WorkManager periodic scheduler).
5. Run E2E test suite (Tiers 1-4) & Tier 5 Adversarial Coverage Hardening.
6. Submit final report to Project Sentinel.

## 5. Key Artifacts
- `c:\Users\samee\projects\Mimo\PROJECT.md`
- `c:\Users\samee\projects\Mimo\TEST_INFRA.md`
- `c:\Users\samee\projects\Mimo\ORIGINAL_REQUEST.md`
- `c:\Users\samee\projects\Mimo\.agents\orchestrator_r1\progress.md`
- `c:\Users\samee\projects\Mimo\.agents\orchestrator_r1\GATE_STATUS.md`
- `c:\Users\samee\projects\Mimo\.agents\orchestrator_r1\BRIEFING.md`
