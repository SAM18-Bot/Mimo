# Android Project Survey & Feasibility Analysis

**Target Workspace**: `c:\Users\samee\projects\Mimo\android`  
**Date**: 2026-08-06  
**Investigator**: `teamwork_preview_explorer_survey_1`  

---

## Executive Summary

A comprehensive survey of `c:\Users\samee\projects\Mimo\android` was performed. The directory **does not exist** yet in the workspace root. No Android Gradle configuration, Kotlin source code, Jetpack Compose components, or background service implementations currently exist in the repository.

To meet requirements **R1 (Native Android Mobile Dashboard)** and **R2 (Background Enforcement / Roast-Plus-Alert)**, a brand new Android Gradle project must be bootstrapped from scratch under `c:\Users\samee\projects\Mimo\android`.

---

## Detailed Survey Findings

### 1. Project Directory & Gradle Configuration
- **Status**: Directory `c:\Users\samee\projects\Mimo\android` is missing.
- **Root `settings.gradle.kts`**: Missing.
- **Root `build.gradle.kts`**: Missing.
- **`app/build.gradle.kts`**: Missing.
- **Gradle Wrapper (`gradlew`, `gradlew.bat`, `gradle/wrapper/`)**: Missing.
- **Versions Status**:
  - Android Gradle Plugin (AGP): Unconfigured (Recommended: `8.2.2` or `8.4.0`)
  - Kotlin Version: Unconfigured (Recommended: `1.9.22` or `2.0.0`)
  - Min SDK: Unconfigured (Recommended: `26` for Android 8.0+)
  - Target/Compile SDK: Unconfigured (Recommended: `34` for Android 14)
  - Compose BOM Version: Unconfigured (Recommended: `2024.02.02` / Compose Compiler `1.5.8`)

### 2. Source Files (`android/app/src/main`)
- **Status**: Missing directory tree `android/app/src/main`.
- **`AndroidManifest.xml`**: Missing.
- **Kotlin Classes / MainActivity**: Missing.
- **Theme & Composables**: Missing.
- **Background Service & Notification Channels**: Missing.

### 3. Dependencies Checklist

| Category | Recommended Library | Present vs Missing | Purpose |
|---|---|---|---|
| **UI Framework** | Jetpack Compose UI + Material 3 | ❌ Missing | Modern declarative mobile UI |
| **HTTP Client** | Retrofit 2 + OkHttp 4 | ❌ Missing | Backend REST API integration (`/reports/stats`, `/assignments/`, etc.) |
| **JSON Parser** | Gson or kotlinx.serialization | ❌ Missing | Deserializing API responses & WebSocket JSON payloads |
| **WebSockets** | OkHttp WebSocket / Ktor Client | ❌ Missing | Real-time connection to `ws://10.0.2.2:8000/ws` for `roast` events |
| **Async / Threading** | Kotlin Coroutines + Flow | ❌ Missing | Asynchronous API calls and state management |
| **ViewModel / Lifecycle** | AndroidX Lifecycle & ViewModel | ❌ Missing | UI state retention across lifecycle events |
| **Background Execution** | Foreground Service / WorkManager | ❌ Missing | Keeping WebSocket active in background for background alerts |
| **System Notifications** | AndroidX Core Notifications | ❌ Missing | Displaying roast alerts via NotificationManager |

### 4. Build Test Execution
- Command executed check: Gradle wrapper unavailable because `./gradlew` does not exist.
- Build status: **CANNOT COMPILE** until project files are generated.

---

## Technical Blueprint for Bootstrap & Implementation

### A. Recommended Directory Structure
```
c:\Users\samee\projects\Mimo\android/
├── build.gradle.kts
├── settings.gradle.kts
├── gradle.properties
├── gradlew
├── gradlew.bat
├── gradle/
│   └── wrapper/
│       ├── gradle-wrapper.jar
│       └── gradle-wrapper.properties
└── app/
    ├── build.gradle.kts
    ├── proguard-rules.pro
    └── src/
        ├── main/
        │   ├── AndroidManifest.xml
        │   └── java/com/mimo/app/
        │       ├── MainActivity.kt
        │       ├── MimoApplication.kt
        │       ├── data/
        │       │   ├── model/
        │       │   │   ├── Models.kt (StatsResponse, TaskItem, RoastEvent, etc.)
        │       │   └── api/
        │       │       ├── MimoApiService.kt
        │       │       └── MimoWebSocketManager.kt
        │       ├── service/
        │       │   └── RoastBackgroundService.kt
        │       ├── ui/
        │       │   ├── theme/
        │       │   │   ├── Color.kt
        │       │   │   ├── Theme.kt
        │       │   │   └── Type.kt
        │       │   ├── components/
        │       │   │   ├── FocusScoreGauge.kt
        │       │   │   ├── WeeklyBarChart.kt
        │       │   │   ├── AppBreakdownCard.kt
        │       │   │   └── TaskListCard.kt
        │       │   └── dashboard/
        │       │       ├── DashboardScreen.kt
        │       │       └── DashboardViewModel.kt
        │       └── util/
        │           └── NotificationHelper.kt
```

### B. Required Android Permissions in Manifest
```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
<uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_DATA_SYNC" />
```

### C. Backend API Integration Mapping
- **Emulator Host IP**: `http://10.0.2.2:8000` (or configurable base URL)
- **Endpoints to integrate**:
  1. `GET /reports/stats` -> Focus score (0-100), streak, grade, productive/distracting mins.
  2. `GET /assignments/` -> List of assignments with title, subject, due_date, priority.
  3. `POST /assignments/` & `POST /assignments/nlp` -> Quick add tasks.
  4. `POST /assignments/{id}/done` -> Complete task.
  5. `GET /screen/breakdown` -> App usage categories.
  6. `WebSocket ws://10.0.2.2:8000/ws` -> Listen for `"type": "roast"` messages to fire notifications.

---

## Action Plan for Implementation Stage

1. **Bootstrap Project Shell**:
   - Create directory `c:\Users\samee\projects\Mimo\android`.
   - Write root `build.gradle.kts`, `settings.gradle.kts`, `gradle.properties`, wrapper files, and `app/build.gradle.kts`.
2. **Build Manifest & Permissions**:
   - Create `AndroidManifest.xml` with required services, permissions, and `MimoApplication`.
3. **Data Layer**:
   - Implement Retrofit interface `MimoApiService` and OkHttp WebSocket listener `MimoWebSocketManager`.
4. **Background Enforcement Service**:
   - Implement `RoastBackgroundService` (Foreground service with ongoing status notification).
   - Implement `NotificationHelper` creating notification channel `mimo_roasts` with high priority.
5. **Jetpack Compose UI**:
   - Build custom Canvas `FocusScoreGauge` (animated arc, grade badge, color gradients).
   - Build `WeeklyBarChart` and `TaskListCard` with quick-add dialog and complete button.
   - Assemble `DashboardScreen` with ViewModel lifecycle data fetching.
6. **Build & Verify**:
   - Execute `./gradlew assembleDebug` to verify compilation.
