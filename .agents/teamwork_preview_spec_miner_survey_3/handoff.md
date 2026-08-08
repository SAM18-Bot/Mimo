# Specification Mining Handoff Report — R1, R2, R3

## 1. Observation
- **Source Specification**: `c:\Users\samee\projects\Mimo\ORIGINAL_REQUEST.md` lines 13-34.
- **Codebase Audited**:
  - `c:\Users\samee\projects\Mimo\PROJECT.md` (Android Kotlin architecture & existing contracts)
  - `c:\Users\samee\projects\Mimo\SETUP_AND_TEST.md` (Testing, FastAPI setup, and mock scripts)
  - `c:\Users\samee\projects\Mimo\android\app\src\main\java\com\mimo\app\` (`DashboardViewModel.kt`, `ApiModels.kt`, `MimoApiService.kt`, `RoastEnforcementService.kt`)
  - `c:\Users\samee\projects\Mimo\db\models.py` (SQLAlchemy models: `ScreenSession`, `DailySummary`, `Assignment`)
  - `c:\Users\samee\projects\Mimo\api\` (`routes_reports.py`, `routes_assignments.py`, `routes_screen.py`, `main.py`)
  - `c:\Users\samee\projects\Mimo\modules\behavior_engine\aggregator.py` (`get_daily_stats`, focus score calculation, `desk_time_min` logic)
- **Key Findings**:
  - The Android companion app currently relies directly on Retrofit network calls (`ApiClient.api`) to fetch stats/assignments and update statuses, failing when offline.
  - The backend lacks `api/routes_sync.py` for syncing mobile app data (`/sync/push` and `/sync/pull`).
  - Android WorkManager dependency (`androidx.work:work-runtime-ktx:2.9.0`) is present in `android/app/build.gradle.kts`, but Room Database entities and DAOs in `com.mimo.app.data` are missing and must be added along with Room Gradle dependencies (`androidx.room:room-runtime`, `androidx.room:room-ktx`, `androidx.room:room-compiler`).
  - `MobileTrackerService` using Android's `UsageStatsManager` and local threshold/roast logic is required for standalone mobile screen tracking.

---

## 2. Logic Chain
1. **Requirements Mapping**:
   - `ORIGINAL_REQUEST.md` requires converting Mimo into a standalone app functioning offline with a local Room Database (R1), native screen tracking service (R2), and Python/Android sync engine (R3).
2. **Data Layer Architecture (R1)**:
   - To function offline, `DashboardViewModel` must read and write to local Room Database entities (`AssignmentEntity`, `DailyStatsEntity`) via reactive Kotlin `Flow`s from `AssignmentDao` and `DailyStatsDao`. UI operations (`markAssignmentDone`, quick-add assignment) must be written locally first with an `isSynced = false` flag.
3. **Screen Tracking & Distraction Engine (R2)**:
   - `MobileTrackerService` must run as a foreground service using `UsageStatsManager` to record active foreground apps. It compares package names against distraction rules, updates local screen usage stats, and triggers high-priority local notifications (`mimo_roast_channel`) when distraction exceeds thresholds (e.g. 5 minutes).
4. **Sync Engine Protocol (R3)**:
   - Backend `api/routes_sync.py` must provide `POST /sync/push` to receive mobile usage logs and new/modified assignments, merge them into `ScreenSession` and `Assignment` tables, recalculate `desk_time_min` and `focus_score` in `DailySummary`, and return status.
   - Endpoint `GET /sync/pull` (or `POST /sync/pull`) returns merged daily stats and the authoritative assignment list to the device.
   - Android `SyncWorker` (WorkManager `CoroutineWorker`) executes when network connectivity is available (`NetworkType.CONNECTED`), pushing unsynced local data and pulling server updates into Room DB.

---

## 3. Caveats
- Android `UsageStatsManager` requires the special permission `android.permission.PACKAGE_USAGE_STATS`, which cannot be granted via standard runtime prompt dialogs; it requires guiding the user to system settings (`Settings.ACTION_USAGE_ACCESS_SETTINGS`) or auto-granting via `adb shell appops set <pkg> GET_USAGE_STATS allow` in emulator testing.
- Android Room Database implementation requires enabling `ksp` or `kapt` plugin in `android/app/build.gradle.kts` to process `@Dao` and `@Database` annotations properly during Gradle build.
- `desk_time_min` recalculation on the server must ensure duplicate screen session intervals from PC and mobile are either summed or aggregated cleanly without double counting overlapping timestamps.

---

## 4. Conclusion
The specification for Mimo Standalone & Sync Engine (R1, R2, R3) is complete and fully enumerated below.

### Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | R1: Local Data | Room Database Init (`MimoDatabase`) | Abstract Room DB provider holding `assignments` and `daily_stats` tables | Application Context | Instantiated `MimoDatabase` instance & DAOs | Fallback to destructive migration or throw schema error | ORIGINAL_REQUEST.md line 15 & Gradle inspect |
| 2 | R1: Local Data | `AssignmentEntity` Room Entity | Local SQLite table for offline assignment storage | Title, due date, priority, status, notes, `isSynced` flag | Local database record | Constraint validation error handling | ORIGINAL_REQUEST.md line 15 & `ApiModels.kt` |
| 3 | R1: Local Data | `DailyStatsEntity` Room Entity | Local SQLite table for daily focus scores and time tracking | Date (PK), productive/distracting/neutral min, focus score | Local database record | Primary key conflict updates row via REPLACE | ORIGINAL_REQUEST.md line 15 & `ApiModels.kt` |
| 4 | R1: Local Data | `AssignmentDao` & `DailyStatsDao` | Room DAOs exposing CRUD & Reactive `Flow` streams for UI and SyncWorker | Queries, Entities, Status flags | Kotlin `Flow<List<T>>`, ID lists, suspend return values | Empty result returns null/empty list | ORIGINAL_REQUEST.md line 15 |
| 5 | R1: Local Data | Offline `DashboardViewModel` | Refactored ViewModel observing Room DB instead of direct REST API calls | UI actions (add task, complete task, refresh) | `StateFlow<List<Assignment>>`, `StateFlow<DailyStats>` | Network errors ignored offline; local DB state rendered | ORIGINAL_REQUEST.md line 15 & `DashboardViewModel.kt` |
| 6 | R2: Mobile Tracker | `MobileTrackerService` | Foreground service running screen tracking loop on Android | System usage events, timer triggers | Screen usage logs & category duration updates | Graceful degradation if permission missing | ORIGINAL_REQUEST.md line 19 & `AndroidManifest.xml` |
| 7 | R2: Mobile Tracker | `UsageStatsManager` Categorizer | Interrogates foreground app package name and categorizes (productive/distracting/neutral) | `UsageEvents.Event.MOVE_TO_FOREGROUND` | Category minutes & package logs | Unknown apps default to NEUTRAL category | ORIGINAL_REQUEST.md line 19 |
| 8 | R2: Mobile Tracker | Local Distraction Monitor | Tracks continuous minutes spent on distracting apps vs threshold (e.g. 5m) | Elapsed distracting seconds | Trigger signal for roast alert | Resets on app switch to productive | ORIGINAL_REQUEST.md line 19 |
| 9 | R2: Mobile Tracker | Autonomous Roast Notifications | Posts local high-priority heads-up notification with witty roast text | Threshold trigger signal | System notification on `mimo_roast_channel` | Degrades to toast/log if notification perm denied | ORIGINAL_REQUEST.md line 19 & `RoastEnforcementService.kt` |
| 10 | R3: Sync Engine | `POST /sync/push` Endpoint | Python API endpoint receiving mobile logs & assignments, updating backend DB | `SyncPushRequest` JSON body | `SyncPushResponse` (status, processed count, ID mapping) | 422 for invalid schema, 500 on DB error | ORIGINAL_REQUEST.md line 23 & `api/routes_sync.py` |
| 11 | R3: Sync Engine | `GET /sync/pull` Endpoint | Python API endpoint returning merged focus stats and authoritative assignment list | Device ID, optional `since` ISO timestamp | `SyncPullResponse` JSON (merged stats & assignments) | 400/422 on invalid parameters | ORIGINAL_REQUEST.md line 23 & `api/routes_sync.py` |
| 12 | R3: Sync Engine | Android `SyncWorker` Task | WorkManager `CoroutineWorker` executing background push/pull sync loop | Unsynced local data (`isSynced = false`) | Sync HTTP requests & Room DB update (`isSynced = true`) | Network error returns `Result.retry()` with backoff | ORIGINAL_REQUEST.md line 23 & `build.gradle.kts` |
| 13 | R3: Sync Engine | WorkManager Sync Trigger Manager | Manages 15-minute periodic schedule & `NetworkType.CONNECTED` constraints | System boot, connectivity restore, UI manual sync | Enqueued WorkRequests in WorkManager | Retains pending work in queue when offline | ORIGINAL_REQUEST.md line 23 & 32 |

---

### Edge Cases

| # | Feature | Input | Observed Behavior / Expected Requirement |
|---|---------|-------|-----------------------------------------|
| 1 | R1: Offline Assignment | User creates assignment with network disabled | Inserted into `AssignmentEntity` with local ID and `isSynced = false`. App UI updates instantly via `Flow`. |
| 2 | R1: Offline Mark Done | User marks task done with network disabled | Room DB record updated to `status = 'done'`, `isSynced = false`. UI updates task state to completed locally. |
| 3 | R2: Usage Access Denied | User opens app without granting Usage Access permission | `MobileTrackerService` detects missing permission, logs warning, displays prompt/dialog to grant permission in Settings without crashing. |
| 4 | R2: Continuous Distraction | User stays on Instagram for 20 continuous minutes | Roast notification fires at 5-minute threshold. Cooldown logic prevents spamming every second; subsequent roasts fire per cooldown policy. |
| 5 | R3: Push Sync Offline Retry | `SyncWorker` fires `POST /sync/push` while network drops mid-request | `IOException` caught, `SyncWorker` returns `Result.retry()`. WorkManager reschedules request using exponential backoff. |
| 6 | R3: Merged Stats Calculation | Mobile logs 30m Instagram + PC logs 60m VS Code for today | Server merges records: total `desk_time_min` becomes 90m, focus score recalculated based on combined 60m productive / 30m distracting. |

---

## 5. Verification Method

To independently verify the extracted specifications:

1. **Verify R1 (Android Local Data Layer)**:
   - Check `android/app/src/main/java/com/mimo/app/data/` for `MimoDatabase.kt`, `AssignmentEntity.kt`, `DailyStatsEntity.kt`, `AssignmentDao.kt`, `DailyStatsDao.kt`.
   - Inspect `DashboardViewModel.kt` to ensure UI state reads from DAOs via `Flow`.
   - Run Android emulator with airplane mode / network disabled. Add an assignment and mark an assignment done. Verify data persists and reflects in UI.

2. **Verify R2 (Mobile Screen Tracking)**:
   - Verify `MobileTrackerService` in `android/app/src/main/java/com/mimo/app/service/`.
   - Ensure `<uses-permission android:name="android.permission.PACKAGE_USAGE_STATS" />` is in `AndroidManifest.xml`.
   - Launch distracting app on emulator (e.g. YouTube / Browser with distracting site) for threshold duration and confirm local roast notification appears.

3. **Verify R3 (Sync Engine)**:
   - Check Python backend `api/routes_sync.py` for `POST /sync/push` and `GET /sync/pull`.
   - Check Android `SyncWorker.kt` in `com/mimo/app/sync/` for `CoroutineWorker` push/pull implementation.
   - Restore network on emulator, trigger sync, and query Python endpoint `GET /reports/stats` to verify mobile screen time is added to `desk_time_min` and focus score calculations.
