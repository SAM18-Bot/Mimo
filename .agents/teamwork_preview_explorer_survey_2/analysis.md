# R2 & R3 Android Local JVM Testing Architecture Analysis

## 1. Executive Summary
This report presents a thorough investigation of requirements **R2** (Isolated Test Environments) and **R3** (Comprehensive Mocked Unit Testing) for the Mimo Android application. 
During initial execution of `.\gradlew testDebugUnitTest`, the build failed at `:app:compileDebugUnitTestKotlin` due to outdated manual interface mocks (`FakeMimoApiService` missing `pushSync` and `pullSync` methods added to `MimoApiService`). Additionally, `android/app/build.gradle.kts` lacks standard Kotlin mocking dependencies (`io.mockk:mockk`), component testing rules (`androidx.test:rules`), and unit tests for `MainActivity` and background services (`RoastEnforcementService`, `MobileTrackerService`).

This report provides exact Gradle configurations, dependency declarations, and complete test implementation specifications to achieve 100% test pass rate for `.\gradlew testDebugUnitTest`.

---

## 2. Root Cause & Build Environment Analysis

### 2.1 Current Test Failure Observation
- **Command Executed**: `.\gradlew testDebugUnitTest`
- **Failure Point**: `:app:compileDebugUnitTestKotlin`
- **Verbatim Error**:
  ```
  e: file:///C:/Users/samee/projects/Mimo/android/app/src/test/java/com/mimo/app/ui/DashboardViewModelTest.kt:21:1 Class 'FakeMimoApiService' is not abstract and does not implement abstract member public abstract suspend fun pullSync(): SyncPayload defined in com.mimo.app.network.MimoApiService
  ```
- **Affected Files**:
  - `android/app/src/test/java/com/mimo/app/ui/DashboardViewModelTest.kt` (lines 21–65)
  - `android/app/src/test/java/com/mimo/app/ui/DashboardViewModelStressTest.kt` (lines 171–195)

### 2.2 Brittle Test Architecture
The existing unit tests rely on manual stub implementations (`FakeMimoApiService` and anonymous `object : MimoApiService`). When `MimoApiService.kt` was expanded with sync endpoints (`pushSync` and `pullSync`), the manual stubs became out of sync, breaking compilation. 
Transitioning to dynamic mocking with **MockK** (`io.mockk:mockk`) decouples unit tests from interface growth, preventing future build breakage.

---

## 3. Required Gradle Dependencies & Configurations (`build.gradle.kts`)

### 3.1 `android/app/build.gradle.kts` Dependency Updates
To support local JVM testing with JUnit 4, Robolectric, and MockK, update the `dependencies` block:

```kotlin
dependencies {
    // Standard Testing Libraries (Already present)
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.7.3")
    testImplementation("org.robolectric:robolectric:4.11.1")
    testImplementation("androidx.test:core-ktx:1.5.0")
    testImplementation("androidx.test.ext:junit:1.1.5")
    testImplementation("androidx.room:room-testing:2.6.1")

    // NEW: Mocking & Testing Rules (R2 & R3 Requirements)
    testImplementation("io.mockk:mockk:1.13.9")
    testImplementation("androidx.test:rules:1.5.0")
    testImplementation("androidx.arch.core:core-testing:2.2.0")
}
```

### 3.2 `testOptions` Configuration for Seamless Robolectric Execution
Robolectric requires Android resource processing and default stub values for un-mocked Android SDK calls. Configure `android/app/build.gradle.kts`:

```kotlin
android {
    ...
    testOptions {
        unitTests {
            isIncludeAndroidResources = true
            isReturnDefaultValues = true
        }
    }
}
```

---

## 4. Test Suite Architecture & File Structure (R3)

The unit test suite will be located in `android/app/src/test/java/com/mimo/app/`:

| Test Component | Target Source Class | Test File Path | Key Responsibilities |
|---|---|---|---|
| **UI Startup & Lifecycle** | `MainActivity` | `android/app/src/test/java/com/mimo/app/MainActivityTest.kt` | UI startup, Compose setContent, notification permission check, service launching & stopping |
| **ViewModel & Network** | `DashboardViewModel` | `android/app/src/test/java/com/mimo/app/ui/DashboardViewModelUnitTest.kt` | StateFlow emissions (`stats`, `assignments`, `history`, `screenBreakdown`, `isLoading`), REST API calls, network exception fallback |
| **Background Services** | `RoastEnforcementService`, `MobileTrackerService` | `android/app/src/test/java/com/mimo/app/service/ServiceUnitTest.kt` | Service lifecycle, foreground notification channel creation, WebSocket roast notification firing, app usage categorization & local stats update |

---

## 5. Detailed Unit Test Implementation Specifications

### 5.1 `MainActivityTest.kt`
Tests that `MainActivity` can initialize, set Compose UI content, request permissions, and manage foreground services without throwing exceptions.

```kotlin
package com.mimo.app

import android.content.Intent
import android.os.Build
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.mimo.app.service.RoastEnforcementService
import com.mimo.app.tracker.MobileTrackerService
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.Shadows
import org.robolectric.annotation.Config

@RunWith(AndroidJUnit4::class)
@Config(sdk = [Build.VERSION_CODES.R])
class MainActivityTest {

    @Test
    fun mainActivity_onCreate_launchesWithoutCrashing() {
        val controller = Robolectric.buildActivity(MainActivity::class.java)
        val activity = controller.create().start().resume().get()

        assertNotNull(activity)
        assertFalse(activity.isFinishing)
        controller.destroy()
    }

    @Test
    fun mainActivity_startsForegroundServicesOnLaunch() {
        val controller = Robolectric.buildActivity(MainActivity::class.java)
        controller.create().start().resume()

        val shadowApp = Shadows.shadowOf(ApplicationProvider.getApplicationContext<android.app.Application>())
        val startedServices = shadowApp.startedServices

        // Verify RoastEnforcementService and MobileTrackerService intents were sent
        val serviceClasses = startedServices.map { it.intentClass.name }
        assertTrue(serviceClasses.contains(RoastEnforcementService::class.java.name))
        assertTrue(serviceClasses.contains(MobileTrackerService::class.java.name))

        controller.destroy()
    }

    @Test
    fun mainActivity_onDestroy_stopsServices() {
        val controller = Robolectric.buildActivity(MainActivity::class.java)
        val activity = controller.create().start().resume().get()

        controller.destroy()

        val shadowApp = Shadows.shadowOf(ApplicationProvider.getApplicationContext<android.app.Application>())
        val stoppedServices = shadowApp.stoppedServices
        val serviceClasses = stoppedServices.map { it.intentClass.name }

        assertTrue(serviceClasses.contains(RoastEnforcementService::class.java.name))
        assertTrue(serviceClasses.contains(MobileTrackerService::class.java.name))
    }
}
```

---

### 5.2 `DashboardViewModelUnitTest.kt`
Refactored ViewModel test using MockK dynamic mocks, replacing the broken `FakeMimoApiService`.

```kotlin
package com.mimo.app.ui

import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.mimo.app.data.AssignmentDao
import com.mimo.app.data.DailyStatsDao
import com.mimo.app.data.MimoDatabase
import com.mimo.app.network.*
import io.mockk.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.asExecutor
import kotlinx.coroutines.test.*
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import java.io.IOException

@OptIn(ExperimentalCoroutinesApi::class)
@RunWith(AndroidJUnit4::class)
class DashboardViewModelUnitTest {

    private lateinit var database: MimoDatabase
    private lateinit var assignmentDao: AssignmentDao
    private lateinit var dailyStatsDao: DailyStatsDao
    private val testDispatcher = StandardTestDispatcher()
    private val apiService: MimoApiService = mockk(relaxed = true)
    private val webSocketManager: WebSocketManager = mockk(relaxed = true)

    @Before
    fun setUp() {
        Dispatchers.setMain(testDispatcher)
        database = Room.inMemoryDatabaseBuilder(
            ApplicationProvider.getApplicationContext(),
            MimoDatabase::class.java
        )
            .allowMainThreadQueries()
            .setQueryExecutor(testDispatcher.asExecutor())
            .setTransactionExecutor(testDispatcher.asExecutor())
            .build()

        assignmentDao = database.assignmentDao()
        dailyStatsDao = database.dailyStatsDao()
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
        database.close()
    }

    @Test
    fun viewModel_initialization_fetchesRemoteDataAndUpdateRoom() = runTest {
        coEvery { apiService.getStats(any()) } returns DailyStats(date = "2026-08-08", productive_min = 60, distracting_min = 15)
        coEvery { apiService.getAssignments(any()) } returns listOf(
            Assignment(id = 1, title = "Mock Assignment", due_date = "2026-08-10", priority = "high")
        )

        val viewModel = DashboardViewModel(
            application = ApplicationProvider.getApplicationContext(),
            assignmentDao = assignmentDao,
            dailyStatsDao = dailyStatsDao,
            ioDispatcher = StandardTestDispatcher(testScheduler),
            dateProvider = { "2026-08-08" },
            webSocketManager = webSocketManager,
            apiService = apiService
        )

        testScheduler.advanceUntilIdle()

        assertFalse(viewModel.isLoading.value)
        assertNull(viewModel.error.value)
        coVerify { apiService.getStats("2026-08-08") }
        coVerify { apiService.getAssignments() }
    }

    @Test
    fun viewModel_refresh_handlesNetworkExceptionGracefully_offlineMode() = runTest {
        coEvery { apiService.getStats(any()) } throws IOException("Network Offline")
        coEvery { apiService.getAssignments(any()) } throws IOException("Network Offline")

        val viewModel = DashboardViewModel(
            application = ApplicationProvider.getApplicationContext(),
            assignmentDao = assignmentDao,
            dailyStatsDao = dailyStatsDao,
            ioDispatcher = StandardTestDispatcher(testScheduler),
            dateProvider = { "2026-08-08" },
            webSocketManager = null,
            apiService = apiService
        )

        viewModel.refresh()
        testScheduler.advanceUntilIdle()

        assertFalse(viewModel.isLoading.value)
        assertNull(viewModel.error.value)
    }

    @Test
    fun viewModel_updateStats_calculatesFocusScoreAndSavesUnsyncedRecord() = runTest {
        val viewModel = DashboardViewModel(
            application = ApplicationProvider.getApplicationContext(),
            assignmentDao = assignmentDao,
            dailyStatsDao = dailyStatsDao,
            ioDispatcher = StandardTestDispatcher(testScheduler),
            dateProvider = { "2026-08-08" },
            webSocketManager = null,
            apiService = apiService
        )

        viewModel.updateStats(productiveDelta = 60, distractingDelta = 20, neutralDelta = 10)
        testScheduler.advanceUntilIdle()

        val saved = dailyStatsDao.getByDate("2026-08-08")
        assertNotNull(saved)
        assertEquals(60, saved?.productiveMin)
        assertEquals(20, saved?.distractingMin)
        assertEquals(75.0, saved?.focusScore ?: 0.0, 0.1)
        assertFalse(saved?.isSynced ?: true)
    }
}
```

---

### 5.3 `ServiceUnitTest.kt`
Tests lifecycle, notification manager interaction, and foreground startup for `RoastEnforcementService` and `MobileTrackerService`.

```kotlin
package com.mimo.app.service

import android.app.NotificationManager
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.mimo.app.tracker.MobileTrackerService
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.Shadows
import org.robolectric.annotation.Config

@RunWith(AndroidJUnit4::class)
@Config(sdk = [Build.VERSION_CODES.R])
class ServiceUnitTest {

    @Test
    fun roastEnforcementService_onStartCommand_createsForegroundNotification() {
        val controller = Robolectric.buildService(RoastEnforcementService::class.java)
        val service = controller.create().startCommand(0, 0).get()

        assertNotNull(service)

        val notificationManager = ApplicationProvider.getApplicationContext<Context>()
            .getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val shadowNM = Shadows.shadowOf(notificationManager)

        // Verify notification channel was created
        val channel = shadowNM.getNotificationChannel("mimo_fg_service")
        assertNotNull(channel)

        controller.destroy()
    }

    @Test
    fun mobileTrackerService_onStartCommand_createsForegroundNotification() {
        val controller = Robolectric.buildService(MobileTrackerService::class.java)
        val service = controller.create().startCommand(0, 0).get()

        assertNotNull(service)

        val notificationManager = ApplicationProvider.getApplicationContext<Context>()
            .getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val shadowNM = Shadows.shadowOf(notificationManager)

        // Verify notification channel was created
        val channel = shadowNM.getNotificationChannel("mimo_tracker_fg_service")
        assertNotNull(channel)

        controller.destroy()
    }
}
```

---

## 6. Actionable Implementation Steps for Implementer

1. **Update `android/app/build.gradle.kts`**:
   - Add `testImplementation("io.mockk:mockk:1.13.9")`, `testImplementation("androidx.test:rules:1.5.0")`, `testImplementation("androidx.arch.core:core-testing:2.2.0")`.
   - Ensure `testOptions.unitTests` has `isIncludeAndroidResources = true` and `isReturnDefaultValues = true`.

2. **Fix Existing Tests**:
   - Update `DashboardViewModelTest.kt` and `DashboardViewModelStressTest.kt` to use `MockK` or add `pushSync` and `pullSync` stubs to `FakeMimoApiService`.

3. **Add New Test Files**:
   - Create `android/app/src/test/java/com/mimo/app/MainActivityTest.kt`.
   - Create `android/app/src/test/java/com/mimo/app/service/ServiceUnitTest.kt`.

4. **Verify Execution**:
   - Execute `.\gradlew testDebugUnitTest` and confirm 100% test success.
