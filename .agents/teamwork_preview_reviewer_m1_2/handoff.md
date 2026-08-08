# Handoff & Quality Review Report: Milestone 1 (Android Local Data Layer - Room DB)

**Reviewer**: Reviewer 2 (`teamwork_preview_reviewer`)  
**Working Directory**: `c:\Users\samee\projects\Mimo\.agents\teamwork_preview_reviewer_m1_2`  
**Target Milestone**: Milestone 1 - Android Local Data Layer (Room DB)  
**Date**: 2026-08-07  
**Verdict**: **REQUEST_CHANGES**

---

## Executive Summary

Worker 1 successfully set up the foundational Room Database infrastructure (`AssignmentEntity`, `DailyStatsEntity`, `AssignmentDao`, `DailyStatsDao`, `MimoDatabase`), application lazy singleton (`MimoApplication`), Gradle `kapt` / Room dependencies, and refactored `DashboardViewModel` to stream state from Room DAOs using Kotlin `Flow` and `StateFlow`.

However, during adversarial review and edge-case stress testing, a **Critical Defect** was identified in `DashboardViewModel.kt`: when network calls in `refresh()` or WebSocket listeners succeed, remote data forcibly overwrites unsynced local database records (`isSynced = false`) using `OnConflictStrategy.REPLACE`. This causes **silent loss of offline user modifications** (e.g. offline assignment status updates or offline daily screen stats) the moment the app regains network connectivity.

Additionally, a **Major Defect** exists where `stats` `StateFlow` statically captures the date string at initialization time, causing stale observations past midnight (date rollover).

---

## 1. Observation

Direct code observations from inspection:

1. **Unsynced Data Overwrite in `DashboardViewModel.kt`**:
   - `android/app/src/main/java/com/mimo/app/ui/DashboardViewModel.kt` (lines 98-104):
     ```kotlin
     val remoteStats = ApiClient.api.getStats()
     dailyStatsDao.insertOrUpdate(remoteStats.toEntity(isSynced = true))

     val remoteAssignments = ApiClient.api.getAssignments()
     assignmentDao.insertAll(remoteAssignments.map { it.toEntity(isSynced = true) })
     ```
   - `android/app/src/main/java/com/mimo/app/data/DailyStatsDao.kt` (line 14-15):
     ```kotlin
     @Insert(onConflict = OnConflictStrategy.REPLACE)
     suspend fun insertOrUpdate(stats: DailyStatsEntity)
     ```
   - `android/app/src/main/java/com/mimo/app/data/AssignmentDao.kt` (line 17-21):
     ```kotlin
     @Insert(onConflict = OnConflictStrategy.REPLACE)
     suspend fun insertAll(assignments: List<AssignmentEntity>)
     ```

2. **Stale Date Flow Observation in `DashboardViewModel.kt`**:
   - `android/app/src/main/java/com/mimo/app/ui/DashboardViewModel.kt` (lines 28-39):
     ```kotlin
     private fun getTodayDateString(): String {
         val sdf = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault())
         return sdf.format(Date())
     }

     val stats: StateFlow<DailyStats> = dailyStatsDao.getByDateFlow(getTodayDateString())
     ```
   - `getTodayDateString()` is evaluated only once when `DashboardViewModel` is instantiated.

3. **Room Schema & Entity Definitions**:
   - `android/app/src/main/java/com/mimo/app/data/AssignmentEntity.kt` (lines 8-34): Defined with auto-generated primary key `id: Int = 0`, `isSynced: Boolean = false`, and mapping extension functions `toDomain()` / `toEntity()`.
   - `android/app/src/main/java/com/mimo/app/data/DailyStatsEntity.kt` (lines 8-28): Defined with primary key `date: String`, `isSynced: Boolean = false`, and mapping extension functions `toDomain()` / `toEntity()`.
   - `android/app/src/main/java/com/mimo/app/data/MimoDatabase.kt` (lines 8-12): Annotated `@Database(entities = [AssignmentEntity::class, DailyStatsEntity::class], version = 1, exportSchema = false)`.

4. **Unit Test Scope**:
   - `android/app/src/test/java/com/mimo/app/data/DatabaseEntityTest.kt`: Contains 4 unit tests verifying extension mapping methods (`toDomain()` and `toEntity()`). No tests exist for DAOs, Room database queries, or ViewModel state management.

---

## 2. Logic Chain

1. **Data Loss Scenario (Offline Edits Overwritten)**:
   - When a user performs offline actions (e.g. marking an assignment done via `markAssignmentDone(id)` or tracking offline screen stats via `updateStats(...)`), Room writes `isSynced = false` to the local SQLite table.
   - When network connectivity is restored or `refresh()` triggers, `ApiClient.api.getStats()` and `ApiClient.api.getAssignments()` fetch server state.
   - `remoteStats.toEntity(isSynced = true)` and `remoteAssignments.map { it.toEntity(isSynced = true) }` create entity objects with `isSynced = true`.
   - `dailyStatsDao.insertOrUpdate` and `assignmentDao.insertAll` use `OnConflictStrategy.REPLACE`.
   - SQLite replaces existing rows matching primary keys (`date` or `id`).
   - **Conclusion**: Local offline modifications (`isSynced = false`) are overwritten and erased before `SyncWorker` (Milestone 3) ever gets a chance to push them to the server.

2. **Stale Date Observation**:
   - `stats` `StateFlow` calls `dailyStatsDao.getByDateFlow(getTodayDateString())` at initialization time.
   - If `DashboardViewModel` remains alive across midnight (e.g., app in foreground/background), `stats` continues to query yesterday's date string.
   - **Conclusion**: The UI will display yesterday's stats even after local `updateStats` writes new records for today's date.

3. **Integrity Assessment**:
   - Source code was checked for hardcoded outputs, fake DAOs, or bypassed implementations. Real Room implementation is in place. No integrity violations were found.

---

## 3. Caveats

- Hardware emulator execution could not be verified directly via `run_command` due to environment permission prompt limits. Static analysis and logic tracing were used.
- SyncWorker integration is scheduled for Milestone 3; however, the local data layer MUST support unsynced record preservation to avoid race conditions when Milestone 3 is introduced.

---

## 4. Conclusion & Verdict

**Verdict**: **REQUEST_CHANGES**

While the core Room Database structure and reactive ViewModel bindings are well-implemented, the local-first integrity requirement (R1) is violated by `refresh()` overwriting unsynced local modifications.

---

## 5. Detailed Findings & Actionable Remediation

### [Critical] Finding 1: Unsynced Local Data Overwritten by Remote `refresh()`
- **Where**: `android/app/src/main/java/com/mimo/app/ui/DashboardViewModel.kt` (lines 98-104) and `AssignmentDao.kt` / `DailyStatsDao.kt`
- **Why**: `insertOrUpdate()` and `insertAll()` use `OnConflictStrategy.REPLACE`, overwriting local rows regardless of their `isSynced` flag. If a user edits an assignment or updates stats while offline, fetching remote data wipes out local unsynced edits.
- **Remediation**:
  1. In `DailyStatsDao`, modify insert logic or add a helper that checks if existing record is unsynced (`isSynced == false`). If local record is unsynced, do NOT overwrite it with stale remote data until local data has been synced.
  2. In `AssignmentDao`, preserve unsynced local assignments (`is_synced = 0`) when merging remote assignments, or update only records where `is_synced = 1`.

### [Major] Finding 2: Static Date Evaluation in `stats` StateFlow
- **Where**: `android/app/src/main/java/com/mimo/app/ui/DashboardViewModel.kt` (lines 33-39)
- **Why**: `getTodayDateString()` is evaluated only once when `stats` is declared. Across date rollover (midnight), `stats` continues observing the old date.
- **Remediation**:
  Transform `stats` into a dynamic flow using `flatMapLatest` or a date ticker flow that re-evaluates `dailyStatsDao.getByDateFlow(today)` whenever the calendar day changes.

### [Minor] Finding 3: Missing DAO & ViewModel Unit Tests
- **Where**: `android/app/src/test/java/com/mimo/app/`
- **Why**: `DatabaseEntityTest.kt` only tests extension mapping methods. DAOs and ViewModel offline fallback logic are un-tested.
- **Remediation**:
  Add Robolectric or in-memory Room unit tests (`Room.inMemoryDatabaseBuilder`) verifying `AssignmentDao` and `DailyStatsDao` CRUD, `getUnsynced()`, and `markSynced()`.

---

## 6. Verification Method

1. **Verify Unsynced Data Safety**:
   - Inspect `DashboardViewModel.kt` and DAOs to verify that remote upsert calls do not overwrite records with `isSynced == false`.
2. **Verify Entity & DAO Mapping**:
   - Inspect `AssignmentEntity.kt`, `DailyStatsEntity.kt`, `AssignmentDao.kt`, `DailyStatsDao.kt`, and `MimoDatabase.kt`.
3. **Run Unit Tests**:
   - Execute in `android/`: `./gradlew test` or `.\gradlew.bat test`.
