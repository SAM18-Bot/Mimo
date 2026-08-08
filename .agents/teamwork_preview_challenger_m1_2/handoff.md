# Handoff Report: Challenger 2 - Milestone 1 (`isSynced` Flag Adversarial Validation)

**Author**: Challenger 2 (`teamwork_preview_challenger`)  
**Working Directory**: `c:\Users\samee\projects\Mimo\.agents\teamwork_preview_challenger_m1_2`  
**Date**: 2026-08-07  
**Verdict**: **REJECT**

---

## 1. Observation

Direct observations from source inspection of Room DB DAOs, entities, and ViewModel layer in Mimo Android App:

- **Local Writes & Queries**:
  - `AssignmentDao.kt` (lines 29-33):
    ```kotlin
    @Query("UPDATE assignments SET status = 'done', is_synced = 0 WHERE id = :id")
    suspend fun markDone(id: Int)

    @Query("SELECT * FROM assignments WHERE is_synced = 0")
    suspend fun getUnsynced(): List<AssignmentEntity>

    @Query("UPDATE assignments SET is_synced = 1 WHERE id IN (:ids)")
    suspend fun markSynced(ids: List<Int>)
    ```
    - Note: `markDone` correctly sets `is_synced = 0` (`isSynced = false`).
  - `DailyStatsDao.kt` (lines 17-21):
    ```kotlin
    @Query("SELECT * FROM daily_stats WHERE is_synced = 0")
    suspend fun getUnsynced(): List<DailyStatsEntity>

    @Query("UPDATE daily_stats SET is_synced = 1 WHERE date IN (:dates)")
    suspend fun markSynced(dates: List<String>)
    ```
  - `DashboardViewModel.kt` (lines 122-133, 142-165):
    - `addAssignment()` initializes `AssignmentEntity(..., isSynced = false)`.
    - `updateStats()` creates `DailyStatsEntity(..., isSynced = false)`.

- **CRITICAL FAILURE OBSERVATION - Remote Refresh Data Overwrite**:
  - `DashboardViewModel.kt` (lines 94-113):
    ```kotlin
    fun refresh() {
        viewModelScope.launch(Dispatchers.IO) {
            _isLoading.value = true
            _error.value = null
            try {
                val remoteStats = ApiClient.api.getStats()
                dailyStatsDao.insertOrUpdate(remoteStats.toEntity(isSynced = true))

                val remoteAssignments = ApiClient.api.getAssignments()
                assignmentDao.insertAll(remoteAssignments.map { it.toEntity(isSynced = true) })

                _history.value = ApiClient.api.getHistory()
                _screenBreakdown.value = ApiClient.api.getScreenBreakdown()
            } catch (e: Exception) {
                // Ignore network errors gracefully to operate 100% offline
            } finally {
                _isLoading.value = false
            }
        }
    }
    ```
  - `AssignmentDao.kt` (lines 17-21) and `DailyStatsDao.kt` (line 14):
    ```kotlin
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(assignments: List<AssignmentEntity>)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertOrUpdate(stats: DailyStatsEntity)
    ```
  - `DashboardViewModel.kt` (lines 77-83):
    ```kotlin
    "stats_update" -> event.stats?.let { remoteStats ->
        dailyStatsDao.insertOrUpdate(remoteStats.toEntity(isSynced = true))
    }
    "tasks_list" -> event.tasks?.let { remoteTasks ->
        assignmentDao.insertAll(remoteTasks.map { it.toEntity(isSynced = true) })
    }
    ```

- **Adversarial Test File Created**:
  - `android/app/src/test/java/com/mimo/app/data/SyncedFlagAdversarialTest.kt`: Contains unit test cases proving premature `isSynced = true` overwrite and offline data loss during remote refreshes.

---

## 2. Logic Chain

1. **Local State Setting**: When a user marks an assignment done offline (`markAssignmentDone`) or updates daily stats offline (`updateStats`), `AssignmentDao` / `DailyStatsDao` set `isSynced = false` (`is_synced = 0`).
2. **Pending Sync State**: Before `SyncWorker` executes its `POST /sync/push` request to sync these unsynced records to the Python backend, the server database still holds stale/outdated records (e.g. `status = "pending"` for tasks, or `productiveMin = 0` for mobile usage stats).
3. **Triggering Remote Fetch**: When network connectivity is established or the app launches / refreshes (`DashboardViewModel.refresh()` or WebSocket `tasks_list`/`stats_update` events), `DashboardViewModel` fetches remote assignments and daily stats from Retrofit REST API / WebSocket.
4. **Blind Local Overwrite**: `DashboardViewModel` maps remote items using `.toEntity(isSynced = true)` and immediately invokes `assignmentDao.insertAll(...)` and `dailyStatsDao.insertOrUpdate(...)`.
5. **SQLite Replace Conflict Execution**: Because `AssignmentDao` and `DailyStatsDao` use `@Insert(onConflict = OnConflictStrategy.REPLACE)`, Room executes SQLite `DELETE` + `INSERT` on matching primary keys (`id` for assignments, `date` for stats).
6. **Data Loss & Requirement Violation**:
   - The local unsynced record (`isSynced = false`, `status = "done"`) is deleted and replaced with the incoming remote record (`isSynced = true`, `status = "pending"`).
   - The user's offline task completion and offline screen time tracking are **PERMANENTLY LOST** before sync could push them to the server.
   - Requirement 5 ("Verify that offline task completion, quick-add, and stats updates never lose `isSynced = false` state before sync") is **VIOLATED**.

---

## 3. Caveats

- **DAO Query Definitions**: `AssignmentDao.markDone()` and `DailyStatsDao.getUnsynced()` are correctly written SQL queries in isolation. The flaw is not in SQL syntax, but in the ViewModel / DAO synchronization strategy (`onConflict = REPLACE` on remote fetch).
- **Fix Recommendation**: In `DashboardViewModel.refresh()` and WebSocket event handlers, remote entities must not overwrite local entities if `localEntity.isSynced == false` (or DAOs must perform selective updates / ignore replacement for unsynced local rows until `SyncWorker` completes push sync).

---

## 4. Conclusion

**Verdict: REJECT**

The current Milestone 1 implementation fails to guarantee that offline task completions, quick-adds, and stats updates maintain their `isSynced = false` state. Calling `DashboardViewModel.refresh()` or receiving WebSocket events before `SyncWorker` pushes unsynced data unconditionally overwrites local unsynced records (`isSynced = false`) with remote server records (`isSynced = true`), causing silent offline data loss.

---

## 5. Verification Method

To verify these failure modes independently:

1. **Inspect Code Files**:
   - `android/app/src/main/java/com/mimo/app/ui/DashboardViewModel.kt` (lines 77-83, 99-103)
   - `android/app/src/main/java/com/mimo/app/data/AssignmentDao.kt` (lines 17-21)
   - `android/app/src/main/java/com/mimo/app/data/DailyStatsDao.kt` (line 14)
   - `android/app/src/test/java/com/mimo/app/data/SyncedFlagAdversarialTest.kt`

2. **Execute Unit Tests**:
   - Run in `android/` directory:
     `.\gradlew.bat test` or `./gradlew test`
   - Observe that `SyncedFlagAdversarialTest` asserts failure when `toEntity(isSynced = true)` from remote refresh replaces local unsynced entities.
