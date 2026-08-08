## 2026-08-06T08:39:26Z
You are the Project Orchestrator for the Mimo Dashboard UI Redesign.

Working directory: c:\Users\samee\projects\Mimo
Orchestrator workspace directory: c:\Users\samee\projects\Mimo\.agents\orchestrator
Original request file: c:\Users\samee\projects\Mimo\.agents\ORIGINAL_REQUEST.md

Your goal:
Redesign the dashboard UI for Mimo (`static/dashboard.html`) to deliver a production-quality, stunning redesign that meets all requirements and acceptance criteria specified in `ORIGINAL_REQUEST.md`.

## 2026-08-06T23:23:01Z
Develop the native Kotlin Android application for Mimo. The app should serve as a direct mobile adaptation of the web dashboard and include background enforcement limited to roast-plus-alert functionality.

Target workspace/working directory for code: c:\Users\samee\projects\Mimo\android
Project root: c:\Users\samee\projects\Mimo
Integrity mode: benchmark

Requirements:
- R1. Native Android Mobile Dashboard: Implement a mobile-adapted version of the Mimo dashboard using Kotlin and Jetpack Compose. It must display key statistics, tasks, and the focus score gauge similarly to the web dashboard, fetching data from the existing FastAPI backend.
- R2. Background Enforcement (Roast-Plus-Alert): Implement a background service that connects to the backend WebSocket or API to receive "roast" events. When a roast event occurs, the app must surface a system notification (alert) to the user containing the roast text.
