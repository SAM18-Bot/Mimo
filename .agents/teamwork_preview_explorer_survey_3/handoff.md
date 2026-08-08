# Handoff Report: Native Android Mobile Dashboard & Background Roast Enforcement Technical Architecture

**Author:** teamwork_preview_explorer_survey_3  
**Date:** 2026-08-06  
**Target Project Location:** `c:\Users\samee\projects\Mimo\android`  

---

## 1. Observation

- **Backend API & WebSocket Contracts**:
  - `GET /reports/stats` (Lines 14-22 in `ORIGINAL_REQUEST.md`): Provides `focus_score`, `productive_minutes`, `distracting_minutes`, `streak_days`, `grade`.
  - `GET /assignments/` & `POST /assignments/` / `POST /assignments/nlp` / `POST /assignments/{id}/done`: Handles assignment state and creation.
  - `GET /screen/breakdown`: Provides usage breakdown by category (`productive`, `distracting`, `neutral`) and top apps list.
  - `WebSocket /ws`: Broadcaster in `api/websocket.py` (lines 43-55) sends JSON payloads over WebSocket.
  - **Roast Payload**: Emitted by `RoastEngine._fire_roast()` (`modules/ai_layer/roast_engine.py:118-125`) with structure:
    ```json
    {
      "type": "roast",
      "message": "...",
      "trigger": "distraction",
      "app": "...",
      "ts": "..."
    }
    ```
- **Android Target Workspace**:
  - `c:\Users\samee\projects\Mimo\android` (currently not created yet; to be generated with Gradle, Kotlin, Jetpack Compose, Material 3, and OkHttp/Retrofit).

---

## 2. Logic Chain

1. **Dashboard UI Requirements**:
   - To adapt the web dashboard to Android, Jetpack Compose provides declarative UI state management using `StateFlow` and MVVM.
   - The Circular Focus Score Gauge can be drawn natively using Compose `Canvas` with `drawArc` and `Brush.sweepGradient`, animated via `animateFloatAsState` for smooth transitions.
   - Key Statistics cards can be laid out using flexible `Row`/`Column` grids with Material 3 `Card` components.
   - Assignments require dynamic urgency calculation (`Overdue`, `Due Today`, `Due Tomorrow`, `Upcoming`) based on `due_date`, with checkable rows triggering `POST /assignments/{id}/done` and quick-add input interfacing with `POST /assignments/nlp`.

2. **Background Enforcement Requirements**:
   - WebSockets disconnected when mobile apps go to background unless managed by a persistent background component.
   - Standard WorkManager polling is limited to 15-minute intervals and cannot deliver real-time roasts (< 1s latency).
   - Therefore, an Android **Foreground Service** (`MimoRoastService`) holding a persistent OkHttp WebSocket listener is required.
   - For Android 13+ (API 33+), runtime `POST_NOTIFICATIONS` permission must be requested on app launch.
   - High importance Notification Channel (`IMPORTANCE_HIGH`) with heads-up display (`PRIORITY_HIGH`) ensures alerts interrupt distractions immediately with sound and vibration even when the app is minimized or closed.

---

## 3. Caveats

- **Battery Optimizations by OEMs**: Aggressive battery saver software on certain devices (e.g., Xiaomi MIUI, Samsung OneUI) may require user approval for `ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS` to keep long-running WebSocket Foreground Services alive across extended idle periods.
- **Network Switching**: Handover between Wi-Fi and Cellular data may briefly sever the WebSocket connection. The OkHttp listener must incorporate exponential backoff auto-reconnection logic.
- **Android 14 Foreground Service Types**: Android 14+ requires explicit `foregroundServiceType` in `AndroidManifest.xml` (`android:foregroundServiceType="dataSync"`).

---

## 4. Conclusion

The technical architecture for the Native Android Mobile Dashboard (Jetpack Compose UI) and Background Roast Enforcement Service (`MimoRoastService`) is complete, fully specified, and documented in `c:\Users\samee\projects\Mimo\.agents\teamwork_preview_explorer_survey_3\analysis.md`. The design guarantees real-time delivery of roast push notifications when the app is in the background or closed, while providing a modern Material 3 Jetpack Compose UI for stats, tasks, score gauge, and usage breakdown.

---

## 5. Verification Method

To independently verify the recommendations and design spec:

1. **Inspect Analysis Document**:
   - View `c:\Users\samee\projects\Mimo\.agents\teamwork_preview_explorer_survey_3\analysis.md` for complete Jetpack Compose code snippets, Notification Channel configuration, and OkHttp WebSocket service code.
2. **Backend Payload Alignment**:
   - Verify WebSocket roast payload structure against `modules/ai_layer/roast_engine.py` (lines 118-125).
3. **Emulator Testing Protocol**:
   - Execute mock roast events by calling `push_event({"type": "roast", "message": "Test Roast", "app": "YouTube"})` in Python while app is in background, then inspect system notification drawer via `adb shell dumpsys notification`.
