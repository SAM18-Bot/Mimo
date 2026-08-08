# Handoff Report: Milestone 1 Remediation Review (Android Local Data Layer)

**Reviewer**: Reviewer 2 (`teamwork_preview_reviewer`)  
**Working Directory**: `c:\Users\samee\projects\Mimo\.agents\teamwork_preview_reviewer_m1_r2_2`  
**Target Milestone**: Milestone 1 Iteration 2 (Android Local Data Layer Remediation)  
**Date**: 2026-08-07  
**Verdict**: **REQUEST_CHANGES**

---

## 1. Observation

Direct code and test execution observations:

1. **Unsynced Data Overwrite Fix in Room DAOs (VERIFIED FIXED)**:
   - `DailyStatsDao.kt` (lines 18-25): Uses `@Transaction suspend fun insertOrUpdate(stats: DailyStatsEntity)` which checks `val existing = getByDate(stats.date)`. If `existing != null && !existing.isSynced && stats.isSynced`, the transaction returns without overwriting unsynced local data.
   - `AssignmentDao.kt` (lines 20-37): Uses `@Transaction suspend fun insert(assignment: AssignmentEntity)` which checks `val existing = getById(assignment.id)`. If `existing != null && !existing.isSynced && assignment.isSynced`, insertion is skipped and local unsynced assignment is preserved.

2. **Dynamic Date Flow in `DashboardViewModel.kt` (VERIFIED FIXED)**:
   - `DashboardViewModel.kt` (lines 25-54): Uses `dateProvider: () -> String` constructor parameter and `currentDateFlow` emitting date string periodically with `distinctUntilChanged()`. `stats` StateFlow uses `flatMapLatest` on `currentDateFlow` to dynamically switch Room observation flow when date changes.

3. **Automated Unit Test Execution Failure (DEFECT FOUND)**:
   - Command executed: `.\gradlew.bat testDebugUnitTest --rerun-tasks --no-daemon` in `android/` directory.
   - Output result:
     ```
     > Task :app:testDebugUnitTest FAILED
     com.mimo.app.ui.DashboardViewModelTest > viewModel_updateStats_savesUnsyncedLocalRecord FAILED
         java.lang.AssertionError at DashboardViewModelTest.kt:59 (assertNotNull(savedStats) failed)

     22 tests completed, 1 failed
     BUILD FAILED in 37s
     ```

4. **Hardcoded `Dispatchers.IO` in `DashboardViewModel.kt`**:
   - `android/app/src/main/java/com/mimo/app/ui/DashboardViewModel.kt`:
     - Line 84: `viewModelScope.launch(Dispatchers.IO)`
     - Line 89: `viewModelScope.launch(Dispatchers.IO)`
     - Line 110: `viewModelScope.launch(Dispatchers.IO)`
     - Line 137: `viewModelScope.launch(Dispatchers.IO)`
     - Line 152: `viewModelScope.launch(Dispatchers.IO)`
     - Line 158: `viewModelScope.launch(Dispatchers.IO)`

---

## 2. Logic Chain

1. **Unsynced Data Protection**:
   - DAO transaction logic in `DailyStatsDao` and `AssignmentDao` successfully prevents remote server payloads (`isSynced = true`) from replacing local rows that have `isSynced = false`.
   - Local offline edits are preserved until `SyncWorker` (Milestone 3) pushes them to the server.

2. **Test Failure & Thread Race Condition**:
   - In `DashboardViewModel.kt`, background operations (`updateStats`, `addAssignment`, `refresh`, `markAssignmentDone`) hardcode `Dispatchers.IO`.
   - In `DashboardViewModelTest.kt`, unit tests initialize `DashboardViewModel` and call `testScheduler.advanceUntilIdle()`.
   - `testScheduler.advanceUntilIdle()` advances coroutines scheduled on `Dispatchers.Main` (replaced via `Dispatchers.setMain(testDispatcher)`), BUT does NOT advance coroutines launched on `Dispatchers.IO`.
   - As a result, when `viewModel.updateStats(...)` launches on `Dispatchers.IO`, the test thread immediately queries `dailyStatsDao.getByDate("2026-08-07")` before the background write to Room finishes executing.
   - `dailyStatsDao.getByDate(...)` returns `null`, causing `assertNotNull(savedStats)` to fail with an `AssertionError`.
   - **Conclusion**: The test suite fails because `DashboardViewModel` hardcodes `Dispatchers.IO` instead of accepting a configurable `CoroutineDispatcher` parameter, creating asynchronous race conditions during unit testing.

---

## 3. Caveats

- All Room DAO tests (`RoomDaoTest.kt`) and Entity tests (`DatabaseEntityTest.kt`) pass cleanly. The failure is isolated to ViewModel dispatcher dependency injection in `DashboardViewModel.kt` / `DashboardViewModelTest.kt`.

---

## 4. Conclusion & Verdict

**Verdict**: **REQUEST_CHANGES**

While the core DAO unsynced data overwrite vulnerability is completely fixed and verified, the build fails because unit test `viewModel_updateStats_savesUnsyncedLocalRecord` fails due to hardcoded `Dispatchers.IO` in `DashboardViewModel`.

---

## 5. Detailed Findings & Actionable Remediation

### [Major] Finding 1: Unit Test Failure in `DashboardViewModelTest` due to Hardcoded `Dispatchers.IO`
- **Where**: `android/app/src/main/java/com/mimo/app/ui/DashboardViewModel.kt` (lines 84, 89, 110, 137, 152, 158) and `android/app/src/test/java/com/mimo/app/ui/DashboardViewModelTest.kt`
- **Why**: Hardcoded `Dispatchers.IO` prevents unit tests from controlling coroutine execution with `TestDispatcher`, causing asynchronous race conditions and test assertions to fail (`assertNotNull(savedStats)` on line 59).
- **Actionable Remediation**:
  1. Add `ioDispatcher: CoroutineDispatcher = Dispatchers.IO` to `DashboardViewModel` constructor:
     ```kotlin
     class DashboardViewModel @JvmOverloads constructor(
         application: Application = MimoApplication.instance,
         private val assignmentDao: AssignmentDao = MimoDatabase.getDatabase(application).assignmentDao(),
         private val dailyStatsDao: DailyStatsDao = MimoDatabase.getDatabase(application).dailyStatsDao(),
         private val ioDispatcher: CoroutineDispatcher = Dispatchers.IO,
         private val dateProvider: () -> String = {
             SimpleDateFormat("yyyy-MM-dd", Locale.getDefault()).format(Date())
         }
     ) : AndroidViewModel(application)
     ```
  2. Replace all hardcoded `Dispatchers.IO` calls in `DashboardViewModel.kt` with `ioDispatcher` (e.g. `viewModelScope.launch(ioDispatcher)`).
  3. In `DashboardViewModelTest.kt`, pass `ioDispatcher = testDispatcher` (or `UnconfinedTestDispatcher()`) when constructing `DashboardViewModel`:
     ```kotlin
     val viewModel = DashboardViewModel(
         application = ApplicationProvider.getApplicationContext(),
         assignmentDao = assignmentDao,
         dailyStatsDao = dailyStatsDao,
         ioDispatcher = testDispatcher,
         dateProvider = { mockDate }
     )
     ```
  4. Run `.\gradlew.bat testDebugUnitTest --no-daemon` to confirm 100% of unit tests pass cleanly.

---

## 6. Verification Method

1. **Run Unit Tests**:
   - Command: `.\gradlew.bat testDebugUnitTest --no-daemon` in `android/` directory.
   - Verification criteria: Build passes cleanly with 0 failing tests (`BUILD SUCCESSFUL`).
