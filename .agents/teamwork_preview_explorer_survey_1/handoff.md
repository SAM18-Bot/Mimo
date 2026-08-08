# Survey Handoff Report — Android Architecture & Requirements Analysis

## 1. Observation

Direct observations from examining the codebase in `c:\Users\samee\projects\Mimo\android`:

1. **Gradle Build Infrastructure**:
   - `build.gradle.kts` (root): Android Application plugin `8.2.2`, Kotlin Android plugin `1.9.22`.
   - `app/build.gradle.kts`:
     - `compileSdk = 34`, `minSdk = 26`, `targetSdk = 34`.
     - Dependencies present:
       - `androidx.core:core-ktx:1.12.0`
       - `androidx.lifecycle:lifecycle-runtime-ktx:2.7.0`, `lifecycle-viewmodel-compose:2.7.0`
       - Compose BOM `2024.02.00` (`ui`, `material3`, `material-icons-extended`)
       - `kotlinx-coroutines-core:1.7.3`, `kotlinx-coroutines-android:1.7.3`
       - `com.squareup.retrofit2:retrofit:2.9.0`, `converter-gson:2.9.0`
       - `com.squareup.okhttp3:okhttp:4.12.0`, `logging-interceptor:4.12.0`
       - `com.google.code.gson:gson:2.10.1`
       - `androidx.work:work-runtime-ktx:2.9.0`
     - **Missing Room Dependencies & Kapt/KSP**: No Room runtime/compiler/ktx dependencies (`androidx.room:room-runtime`, `androidx.room:room-compiler`, `androidx.room:room-ktx`) or annotation processor plugins (`kotlin-kapt` / `ksp`) are defined in `app/build.gradle.kts`.
     - **Missing Test Dependencies**: No test dependencies (JUnit 4, kotlinx-coroutines-test, room-testing, espresso) are present.
   - Command Execution Verification:
     - `cmd /c "cd c:\Users\samee\projects\Mimo\android && gradlew.bat assembleDebug --dry-run"` executed with exit code 0 (`BUILD SUCCESSFUL in 12s`).

2. **AndroidManifest (`android/app/src/main/AndroidManifest.xml`)**:
   - Declares permissions: `INTERNET`, `ACCESS_NETWORK_STATE`, `POST_NOTIFICATIONS`, `FOREGROUND_SERVICE`, `FOREGROUND_SERVICE_DATA_SYNC`, `WAKE_LOCK`.
   - Application class: `com.mimo.app.MimoApplication` (registers notification channel `mimo_roasts`).
   - MainActivity: `com.mimo.app.MainActivity` (handles notification permissions and launches `RoastEnforcementService`).
   - Foreground Service: `com.mimo.app.service.RoastEnforcementService` (handles WebSocket roasts).
   - **Missing Permissions**: `android.permission.PACKAGE_USAGE_STATS` is NOT declared.
   - **Missing Services**: `MobileTrackerService` is NOT declared.

3. **Current Android Source Code (`com/mimo/app/`)**:
   - `network/ApiClient.kt`: Configures Retrofit with base URL `http://10.0.2.2:8000`.
   - `network/ApiModels.kt`: Data models `DailyStats`, `DailyHistoryItem`, `Assignment`, `AssignmentCreate`, `ScreenBreakdown`, `AppMinutes`, `WsEvent`.
   - `network/MimoApiService.kt`: REST interfaces (`getStats`, `getHistory`, `getAssignments`, `createAssignment`, `markAssignmentDone`, `getScreenBreakdown`).
   - `network/WebSocketManager.kt`: OkHttp WebSocket manager listening to `ws://10.0.2.2:8000/ws`.
   - `service/RoastEnforcementService.kt`: Foreground service listening to WebSocket events for real-time roasts from the PC backend.
   - `ui/DashboardViewModel.kt`: Directly fetches data from `ApiClient.api.getStats()`, `getAssignments()`, etc. via Retrofit REST calls.
   - `ui/DashboardScreen.kt`, `ui/components/*`: Jetpack Compose UI showing focus score gauge, stats row, screen time breakdown bar, assignment list.
   - **Missing Data Layer Package (`com/mimo/app/data/`)**: No Room entities, DAOs, or database class exist.
   - **Missing Tracking Service (`MobileTrackerService`)**: No native device usage tracking exists.
   - **Missing Sync Engine (`SyncWorker`)**: No WorkManager worker or sync protocol exists.

---

## 2. Logic Chain

1. **R1 Analysis (Android Local Data Layer)**:
   - Observation: Currently `DashboardViewModel` relies entirely on network calls to `ApiClient.api`. `com/mimo/app/data/` does not exist.
   - Requirement: Offline capabilities require storing data locally using Room DB (`AssignmentEntity` and `DailyStatsEntity`) in `com/mimo/app/data/`.
   - Inference:
     - `app/build.gradle.kts` must add `id("kotlin-kapt")` and Room dependencies (`androidx.room:room-runtime`, `androidx.room:room-ktx`, `androidx.room:room-compiler`).
     - Entity classes `AssignmentEntity` (table `assignments`) and `DailyStatsEntity` (table `daily_stats`) must be created in `com/mimo/app/data/entity/`.
     - DAOs `AssignmentDao` and `DailyStatsDao` must be created with CRUD methods.
     - `MimoDatabase` (`@Database`) and a Repository `MimoRepository` must be created.
     - `DashboardViewModel` must be rewritten to observe Room Flow/LiveData instead of directly executing Retrofit network calls on refresh.

2. **R2 Analysis (Mobile Screen Tracking)**:
   - Observation: `RoastEnforcementService.kt` currently relies on WebSocket events from the PC backend. `PACKAGE_USAGE_STATS` permission and `MobileTrackerService` are missing.
   - Requirement: App must natively track active foreground apps on device via `UsageStatsManager`, categorize them (social media vs productivity), check distraction thresholds, and post local roast notifications independently of PC backend.
   - Inference:
     - Add `<uses-permission android:name="android.permission.PACKAGE_USAGE_STATS" tools:ignore="ProtectedPermissions"/>` to `AndroidManifest.xml`.
     - Implement `MobileTrackerService.kt` extending `Service` (foreground service), using `getSystemService(Context.USAGE_STATS_SERVICE) as UsageStatsManager`.
     - Query app usage events or stats periodically (e.g. 10s ticker loop).
     - Map package names to categories (e.g., `com.instagram.android`, `com.twitter.android`, `com.tiktok` -> Distracting; IDEs/tools -> Productive).
     - Accumulate usage in local Room DB (`DailyStatsEntity`) and trigger local notification using `NotificationManager` when distraction thresholds are exceeded.
     - `MainActivity` must check for `UsageStatsManager` permission and direct the user to `Settings.ACTION_USAGE_ACCESS_SETTINGS` if needed.

3. **R3 Analysis (Sync Engine - PC & Mobile)**:
   - Observation: `androidx.work:work-runtime-ktx:2.9.0` is already declared in `app/build.gradle.kts`, but no `Worker` or sync endpoints are defined.
   - Requirement: Create `SyncWorker` using WorkManager to periodically push local mobile usage stats to PC backend (`/sync/push`) and pull merged data (`/sync/pull`).
   - Inference:
     - Update `MimoApiService.kt` and `ApiModels.kt` with DTOs and endpoints for `/sync/push` (POST) and `/sync/pull` (GET).
     - Implement `SyncWorker` extending `CoroutineWorker`.
     - In `SyncWorker.doWork()`:
       1. Fetch unsynced local mobile stats & assignments from Room DB via `MimoRepository`.
       2. Execute `api.pushMobileStats(...)` to post mobile screen time and usage stats to Python backend.
       3. Execute `api.pullMergedData(...)` to receive merged aggregated stats and assignments.
       4. Save merged stats and assignments back to local Room DB.
     - Schedule `SyncWorker` using `WorkManager.enqueueUniquePeriodicWork` in `MimoApplication` (or when network state changes).

4. **Testing Infrastructure Analysis**:
   - Observation: No test files or test dependencies currently exist in `android/app/src/test`.
   - Inference: Unit tests should be added under `android/app/src/test/java/com/mimo/app/` testing Room DAO operations, `DashboardViewModel` offline behavior, app package categorization logic, and `SyncWorker` logic.

---

## 3. Caveats

1. **Gradle Build Environment**:
   - `gradlew.bat assembleDebug --dry-run` succeeded. Full compilation with Room will require Kapt/KSP code generation during build.
2. **UsageStats Permission on Android Emulator**:
   - `android.permission.PACKAGE_USAGE_STATS` is a special system permission (`appops`). On Android emulators, it cannot be granted via standard runtime dialogs and must be enabled via `Settings -> Usage Access` or `adb shell appops set com.mimo.app GET_USAGE_STATS allow`.
3. **Backend Sync Endpoints**:
   - Synchronization depends on Python backend providing matching `/sync/push` and `/sync/pull` REST endpoints (or `/reports/stats` update).

---

## 4. Conclusion

The Android companion app in `c:\Users\samee\projects\Mimo\android` has a functional Compose UI shell and Retrofit/WebSocket layer, but lacks offline database persistence, local screen usage tracking, and background sync logic.

To fulfill Requirements R1, R2, and R3:
1. **R1 (Local Data Layer)**: Add Room dependencies (`app/build.gradle.kts`), create `com/mimo/app/data/` (`AssignmentEntity`, `DailyStatsEntity`, DAOs, `MimoDatabase`, `MimoRepository`), and update `DashboardViewModel` to operate offline against Room DB.
2. **R2 (Mobile Screen Tracking)**: Add `PACKAGE_USAGE_STATS` permission to `AndroidManifest.xml`, create `MobileTrackerService.kt` utilizing `UsageStatsManager`, implement app categorization & local distraction threshold roast notifications, update `DailyStatsEntity` locally, and register service launch in `MainActivity`.
3. **R3 (Sync Engine)**: Add sync DTOs/endpoints to `MimoApiService`, implement `SyncWorker` using `WorkManager`, schedule periodic background sync jobs, and merge PC + mobile stats into local Room DB.

---

## 5. Verification Method

To verify the implementation once complete:

1. **Gradle Build & Compilation Verification**:
   ```cmd
   cd c:\Users\samee\projects\Mimo\android
   gradlew.bat assembleDebug
   ```
   *Expected result*: Build completes successfully with 0 errors.

2. **Unit Test Suite Verification**:
   ```cmd
   cd c:\Users\samee\projects\Mimo\android
   gradlew.bat test
   ```
   *Expected result*: All unit tests pass for Room database DAOs, ViewModel offline state, and SyncWorker logic.

3. **Offline Mode Functional Verification (R1)**:
   - Launch app without backend connection or with network disabled.
   - Create a task, view task list, and mark task as done.
   - Verify task state is saved in local Room database.

4. **Usage Stats & Local Roast Verification (R2)**:
   - Grant Usage Access permission via ADB:
     ```cmd
     adb shell appops set com.mimo.app GET_USAGE_STATS allow
     ```
   - Launch a distracting package (e.g. `com.instagram.android` or mock foreground package).
   - Verify `MobileTrackerService` detects foreground app, accumulates distracting time in `DailyStatsEntity`, and triggers heads-up notification.

5. **Sync Engine Verification (R3)**:
   - Enable network connection to Python backend (`http://10.0.2.2:8000`).
   - Trigger `SyncWorker` manually or via WorkManager schedule.
   - Verify HTTP POST request hits `/sync/push` endpoint and local mobile screen time is merged with backend data.
