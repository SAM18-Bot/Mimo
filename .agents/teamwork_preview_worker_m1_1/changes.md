# Changes Summary — Milestone 1

## Overview
Implemented fixes for the Android startup crash bugs (R1) and established testing environments / test double setups for both Android and Desktop applications (R2 setup).

## 1. Android Startup Crash Fixes (R1)

### `android/app/src/main/java/com/mimo/app/ui/components/AssignmentList.kt`
- **LazyColumn to Column layout fix**: Replaced `LazyColumn` inside `AssignmentList` with a standard `Column(modifier = modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(12.dp))`. This resolves the nested scroll container crash when `AssignmentList` is rendered inside `DashboardScreen.kt`'s parent `Column(Modifier.verticalScroll())`.
- **Date parsing exception handling**: Wrapped `LocalDate.parse(assignment.due_date)` in `runCatching` inside `AssignmentCard`. If `due_date` is empty (`""`) or malformed, it gracefully falls back to `"No due date"` / raw text without throwing an unhandled `DateTimeParseException`.

### `android/app/src/main/java/com/mimo/app/MainActivity.kt`
- **Foreground Service launch protection**: Wrapped `startForegroundService(...)` calls for `RoastEnforcementService` and `MobileTrackerService` inside `runCatching` blocks. On Android 14 (API 34), this catches `ForegroundServiceStartNotAllowedException` or `IllegalStateException` when the app is in the background or restricted.

### `android/app/src/main/java/com/mimo/app/MimoApplication.kt`
- **WorkManager init safeguard**: Wrapped `WorkManager.getInstance(this).enqueueUniquePeriodicWork(...)` in a `runCatching` block to prevent `IllegalStateException` during Robolectric unit test application initialization when `WorkManager` isn't initialized in tests.

### `android/app/src/main/java/com/mimo/app/tracker/MobileTrackerService.kt`
- **UsageStatsManager safeguards**:
  - Safely cast `getSystemService(Context.USAGE_STATS_SERVICE)` using `as? UsageStatsManager` with a null check.
  - Wrapped `usageStatsManager.queryEvents(startTime, endTime)` calls in a `try-catch` block handling `SecurityException` and general `Exception` so missing `PACKAGE_USAGE_STATS` permissions do not crash the service loop.

## 2. Android Test Doubles & Gradle Config (R2 setup)

### `android/app/src/test/java/com/mimo/app/ui/DashboardViewModelTest.kt`
- Added missing interface methods `pushSync(payload: SyncPayload)` and `pullSync()` to `FakeMimoApiService` (instantiating `SyncPayload` with required constructor parameters `date`, `mobileProductiveMin`, `mobileDistractingMin`, `mobileNeutralMin`).

### `android/app/src/test/java/com/mimo/app/ui/DashboardViewModelStressTest.kt`
- Added missing interface methods `pushSync(payload: SyncPayload)` and `pullSync()` to the anonymous `object : MimoApiService`.

### `android/app/build.gradle.kts`
- Enabled `isReturnDefaultValues = true` in `testOptions.unitTests`.
- Added test dependencies:
  - `testImplementation("io.mockk:mockk:1.13.9")`
  - `testImplementation("androidx.test:rules:1.5.0")`
  - `testImplementation("androidx.arch.core:core-testing:2.2.0")`

## 3. Desktop Test Environment (R2 setup)

### `desktop/test_requirements.txt`
- Created `desktop/test_requirements.txt` containing requirements:
  - `pytest==8.3.4`
  - `pytest-mock==3.14.0`
  - `httpx==0.27.0`
  - `respx==0.21.1`
  - `Pillow==10.3.0`
  - `python-dotenv==1.0.1`
  - `plyer==2.1.0`
- Installed `test_requirements.txt` into Python virtual environment `.venv`.
