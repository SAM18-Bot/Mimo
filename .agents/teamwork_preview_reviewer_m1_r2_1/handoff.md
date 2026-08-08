# Review Handoff Report: Milestone 1 Iteration 2 (Android Local Data Layer)

**Reviewer**: Reviewer 1 (`teamwork_preview_reviewer`)  
**Working Directory**: `c:\Users\samee\projects\Mimo\.agents\teamwork_preview_reviewer_m1_r2_1`  
**Target Milestone**: Milestone 1 Iteration 2 (Android Local Data Layer)  
**Date**: 2026-08-07  
**Verdict**: **REQUEST_CHANGES**

---

## Review Summary

**Verdict**: **REQUEST_CHANGES**

### Findings

#### [Critical] Finding 1: Unit Test Failure in `DashboardViewModelTest` (`viewModel_updateStats_savesUnsyncedLocalRecord`)

- **What**: Unit test `viewModel_updateStats_savesUnsyncedLocalRecord` in `DashboardViewModelTest.kt` failed during `gradlew test` execution:
  ```
  com.mimo.app.ui.DashboardViewModelTest > viewModel_updateStats_savesUnsyncedLocalRecord FAILED
      java.lang.AssertionError at DashboardViewModelTest.kt:46
  22 tests completed, 1 failed
  > Task :app:testReleaseUnitTest FAILED
  ```
- **Where**: `android/app/src/main/java/com/mimo/app/ui/DashboardViewModel.kt` (line 158) and `android/app/src/test/java/com/mimo/app/ui/DashboardViewModelTest.kt` (lines 46-64).
- **Why**: `DashboardViewModel.kt` hardcodes `viewModelScope.launch(Dispatchers.IO)` inside `updateStats()`. In unit tests using `kotlinx.coroutines.test.runTest` and `testScheduler.advanceUntilIdle()`, coroutines launched on `Dispatchers.IO` execute asynchronously on the global thread pool rather than the test dispatcher. As a result, `testScheduler.advanceUntilIdle()` returns before `dailyStatsDao.insertOrUpdate` finishes, causing `dailyStatsDao.getByDate(...)` to return `null` and fail the assertion `assertNotNull(savedStats)`.
- **Suggestion**: Inject a `CoroutineDispatcher` parameter (e.g. `ioDispatcher: CoroutineDispatcher = Dispatchers.IO`) into `DashboardViewModel` constructor (or provide dispatcher injection) so tests can pass `UnconfinedTestDispatcher()` or `StandardTestDispatcher()`. Update `DashboardViewModelTest` to inject `testDispatcher`.

---

## 1. Observation

Direct code observations from the reviewed implementation:

1. **Unsynced Data Overwrite Protection in DAOs**:
   - `android/app/src/main/java/com/mimo/app/data/DailyStatsDao.kt` (lines 17-25):
     ```kotlin
     @Transaction
     suspend fun insertOrUpdate(stats: DailyStatsEntity) {
         val existing = getByDate(stats.date)
         if (existing != null && !existing.isSynced && stats.isSynced) {
             // Unsynced local modification exists; do not overwrite with remote synced stats.
             return
         }
         insertRaw(stats)
     }
     ```
   - `android/app/src/main/java/com/mimo/app/data/AssignmentDao.kt` (lines 20-37):
     ```kotlin
     @Transaction
     suspend fun insert(assignment: AssignmentEntity): Long {
         if (assignment.id != 0) {
             val existing = getById(assignment.id)
             if (existing != null && !existing.isSynced && assignment.isSynced) {
                 // Local assignment has unsynced changes; preserve it.
                 return existing.id.toLong()
             }
         }
         return insertRaw(assignment)
     }

     @Transaction
     suspend fun insertAll(assignments: List<AssignmentEntity>) {
         for (assignment in assignments) {
             insert(assignment)
         }
     }
     ```

2. **Dynamic Date Flow Observation in `DashboardViewModel.kt`**:
   - `android/app/src/main/java/com/mimo/app/ui/DashboardViewModel.kt` (lines 37-54):
     ```kotlin
     private val currentDateFlow: Flow<String> = flow {
         while (true) {
             emit(getTodayDateString())
             delay(60_000)
         }
     }.distinctUntilChanged()

     val stats: StateFlow<DailyStats> = currentDateFlow
         .flatMapLatest { dateStr ->
             dailyStatsDao.getByDateFlow(dateStr).map { entity ->
                 entity?.toDomain() ?: DailyStats(date = dateStr)
             }
         }
         .stateIn(...)
     ```

3. **Test Suite Results**:
   - Ran `gradlew.bat test` in `android/` directory:
     - 22 tests executed: 21 PASSED, 1 FAILED (`viewModel_updateStats_savesUnsyncedLocalRecord`).

---

## 2. Logic Chain

1. **Unsynced Data Preservation Logic**:
   - DAO implementation logic correctly handles `isSynced == false` preservation via `@Transaction` checks in `DailyStatsDao` and `AssignmentDao`.
   - Dynamic date observation in `DashboardViewModel` correctly uses `currentDateFlow` and `flatMapLatest`.

2. **Test Failure Reasoning**:
   - Hardcoding `Dispatchers.IO` in `DashboardViewModel.updateStats()` causes non-deterministic execution in coroutine unit tests.
   - When running `gradlew test`, `viewModel_updateStats_savesUnsyncedLocalRecord` fails assertion `assertNotNull(savedStats)` because the `Dispatchers.IO` task has not completed by the time `testScheduler.advanceUntilIdle()` returns.
   - `gradlew test` fails with exit code 1. A milestone cannot be approved when unit tests in the target codebase fail.

---

## 3. Caveats

- The Room DAO implementation logic for `isSynced == false` protection is sound and passed all `RoomDaoTest` cases (8/8 passed).
- The entity mapper logic in `DatabaseEntityTest` passed (5/5 passed).
- Only the dispatcher synchronization in `DashboardViewModel` and its corresponding unit test `DashboardViewModelTest` require fixing.

---

## 4. Conclusion

While the Room DAO logic and dynamic date flow implementation satisfy the functional requirements, the unit test suite fails due to hardcoded `Dispatchers.IO` in `DashboardViewModel.kt`.

**Verdict**: **REQUEST_CHANGES**

---

## 5. Verification Method

1. **Reproduce Test Failure**:
   - Run `cmd /c "cd c:\Users\samee\projects\Mimo\android && gradlew.bat test"`
   - Observe test failure output:
     `com.mimo.app.ui.DashboardViewModelTest > viewModel_updateStats_savesUnsyncedLocalRecord FAILED`
2. **Verify Fix**:
   - Inject `ioDispatcher: CoroutineDispatcher = Dispatchers.IO` into `DashboardViewModel` constructor.
   - Use `ioDispatcher` in `viewModelScope.launch(ioDispatcher)`.
   - Pass `testDispatcher` or `UnconfinedTestDispatcher()` in `DashboardViewModelTest`.
   - Re-run `gradlew.bat test` and verify 100% pass rate.
