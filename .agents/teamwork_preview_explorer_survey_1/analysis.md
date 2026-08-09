# Root Cause Analysis Report: Android Instant Startup Crash (R1)

## Executive Summary
The Mimo Android application experiences an instant crash (1-2 seconds after launch) due to a critical Jetpack Compose layout violation combined with an unhandled date parsing exception in the UI layer. In addition, the Android unit test suite fails to compile due to missing mock implementations in `FakeMimoApiService`.

---

## 1. Primary Root Causes Identified

### Root Cause 1: Jetpack Compose Infinite Height Measurement Crash (`IllegalStateException`)
- **File**: `android/app/src/main/java/com/mimo/app/ui/DashboardScreen.kt` (Lines 76–104)
- **File**: `android/app/src/main/java/com/mimo/app/ui/components/AssignmentList.kt` (Lines 30–41)
- **Code Observation**:
  `DashboardScreen.kt`:
  ```kotlin
  Column(
      modifier = Modifier
          .fillMaxSize()
          .verticalScroll(rememberScrollState())
          .padding(16.dp),
      verticalArrangement = Arrangement.spacedBy(24.dp)
  ) {
      ...
      AssignmentList(
          assignments = assignments,
          onMarkDone = { id -> viewModel.markAssignmentDone(id) }
      )
  }
  ```
  `AssignmentList.kt`:
  ```kotlin
  @Composable
  fun AssignmentList(
      assignments: List<Assignment>,
      onMarkDone: (Int) -> Unit,
      modifier: Modifier = Modifier
  ) {
      LazyColumn(
          modifier = modifier.fillMaxWidth(),
          contentPadding = PaddingValues(16.dp),
          verticalArrangement = Arrangement.spacedBy(12.dp)
      ) {
          items(assignments) { assignment -> ... }
      }
  }
  ```
- **Mechanism**: Jetpack Compose forbids nesting a lazy scrollable container (`LazyColumn`) inside a parent container with vertical scrolling (`Column` with `verticalScroll`), because the parent provides infinite maximum height constraints.
- **Exception Thrown**: `java.lang.IllegalStateException: Vertically scrollable component was measured with an infinity maximum height constraints, which is disallowed.`
- **Timing**: Fires immediately on the first UI measure/layout pass when `setContent { DashboardScreen() }` executes during `MainActivity.onCreate()` (approx 1-2 seconds into launch).

---

### Root Cause 2: Uncaught `DateTimeParseException` during UI Rendering
- **File**: `android/app/src/main/java/com/mimo/app/ui/components/AssignmentList.kt` (Line 50)
- **Code Observation**:
  ```kotlin
  @Composable
  fun AssignmentCard(
      assignment: Assignment,
      onMarkDone: () -> Unit
  ) {
      val today = LocalDate.now()
      val dueDate = LocalDate.parse(assignment.due_date) // Assuming ISO format YYYY-MM-DD
  ```
- **Mechanism**: `Assignment.due_date` defaults to `""` in `ApiModels.kt` (Line 43). When `LocalDate.parse("")` is called on an uninitialized or empty date string, Java 8 `java.time` throws `DateTimeParseException: Text '' could not be parsed`.
- **Timing**: Fires during composition/recomposition when task items with blank or invalid date strings are rendered.

---

### Root Cause 3: Unit Test Suite Compilation Failure (`compileDebugUnitTestKotlin FAILED`)
- **File**: `android/app/src/test/java/com/mimo/app/ui/DashboardViewModelTest.kt` (Lines 21–65)
- **File**: `android/app/src/test/java/com/mimo/app/ui/DashboardViewModelStressTest.kt` (Lines 171–195)
- **Code Observation**:
  ```kotlin
  class FakeMimoApiService(...) : MimoApiService { ... }
  ```
- **Mechanism**: `MimoApiService.kt` defines `suspend fun pushSync(payload: SyncPayload): Map<String, Any>` and `suspend fun pullSync(): SyncPayload`. However, the mock test implementations `FakeMimoApiService` and `throwingApiService` in `DashboardViewModelTest.kt` and `DashboardViewModelStressTest.kt` do not implement these two methods.
- **Gradle Result**: Running `.\gradlew testDebugUnitTest` fails with:
  `error: class 'FakeMimoApiService' is not abstract and does not implement abstract member public abstract suspend fun pullSync(): SyncPayload defined in com.mimo.app.network.MimoApiService`

---

### Root Cause 4: Potential Android 14 Foreground Service and Usage Stats Exceptions
- **File**: `android/app/src/main/java/com/mimo/app/MainActivity.kt` (Lines 48–58)
- **File**: `android/app/src/main/java/com/mimo/app/tracker/MobileTrackerService.kt` (Lines 74–90)
- **Code Observation**:
  In `MainActivity.kt`:
  ```kotlin
  private fun startRoastService() {
      val roastIntent = Intent(this, RoastEnforcementService::class.java)
      val trackerIntent = Intent(this, MobileTrackerService::class.java)
      if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
          startForegroundService(roastIntent)
          startForegroundService(trackerIntent)
      }
  }
  ```
  In `MobileTrackerService.kt`:
  ```kotlin
  val usageStatsManager = getSystemService(Context.USAGE_STATS_SERVICE) as UsageStatsManager
  val events = usageStatsManager.queryEvents(startTime, endTime)
  ```
- **Mechanism**:
  1. Starting two foreground services concurrently in `MainActivity.onCreate()` using `startForegroundService` without verifying Android 14 foreground service launch conditions or try-catch blocks can cause `ForegroundServiceStartNotAllowedException`.
  2. In `MobileTrackerService`, accessing `UsageStatsManager` without checking if `usageStatsManager` is null or catching `SecurityException` when usage access permission is revoked can lead to uncaught service crashes.

---

## 2. Recommended Fix Implementation Plan

### Fix 1: Resolve Nested Scroll Crash in `DashboardScreen.kt` / `AssignmentList.kt`
- Option A (Recommended): Replace `LazyColumn` in `AssignmentList.kt` with a standard `Column` using `forEach` (since tasks are displayed inside the parent `verticalScroll` Column). Or pass `Modifier` without nested scrolling.
- Option B: Use `item` blocks within a single root `LazyColumn` in `DashboardScreen.kt`.

Proposed code for `AssignmentList.kt`:
```kotlin
@Composable
fun AssignmentList(
    assignments: List<Assignment>,
    onMarkDone: (Int) -> Unit,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        assignments.forEach { assignment ->
            AssignmentCard(
                assignment = assignment,
                onMarkDone = { onMarkDone(assignment.id) }
            )
        }
    }
}
```

### Fix 2: Safe Date Parsing in `AssignmentCard`
Wrap `LocalDate.parse` in `runCatching` or provide a fallback for blank/invalid dates.

Proposed code for `AssignmentCard` in `AssignmentList.kt`:
```kotlin
val today = LocalDate.now()
val dueDate = runCatching { LocalDate.parse(assignment.due_date) }.getOrNull()
val daysUntilDue = if (dueDate != null) ChronoUnit.DAYS.between(today, dueDate) else 0L

val (statusColor, statusText) = when {
    dueDate == null -> MimoColors.TextMuted to "No Due Date"
    daysUntilDue < 0 -> MimoColors.Error to "Overdue"
    daysUntilDue == 0L -> MimoColors.Warning to "Due Today"
    else -> MimoColors.Success to "In ${daysUntilDue} days"
}
```

### Fix 3: Update `FakeMimoApiService` for Unit Tests
Implement `pushSync` and `pullSync` in `FakeMimoApiService` and `throwingApiService` in `DashboardViewModelTest.kt` and `DashboardViewModelStressTest.kt`.

```kotlin
override suspend fun pushSync(payload: SyncPayload): Map<String, Any> {
    if (shouldThrowError) throw IOException("Network connection offline")
    return mapOf("status" to "success")
}

override suspend fun pullSync(): SyncPayload {
    if (shouldThrowError) throw IOException("Network connection offline")
    return SyncPayload(date = "2026-08-07", mobileProductiveMin = 0, mobileDistractingMin = 0, mobileNeutralMin = 0)
}
```

### Fix 4: Safeguard Service Initialization & `UsageStatsManager`
In `MainActivity.kt`: Wrap service calls in try-catch blocks for `ForegroundServiceStartNotAllowedException` / `SecurityException`.
In `MobileTrackerService.kt`: Wrap `queryEvents` in try-catch to prevent service crash when `PACKAGE_USAGE_STATS` is not granted.

---

## 3. Scope & Verification Strategy
- Compiles via `.\gradlew assembleDebug`.
- Unit tests compile and pass 100% via `.\gradlew testDebugUnitTest`.
- Robolectric / ViewModel tests verify initialization without exceptions.
