# Original User Request

## Initial Request — 2026-08-07T09:10:53Z

<USER_REQUEST>
Convert the existing Mimo Android companion app into a fully standalone productivity tracking application with offline capabilities and a sync engine.

Working directory: c:\Users\samee\projects\Mimo
Integrity mode: benchmark

## Requirements

### R1. Android Local Data Layer
The Android app must store data locally so it can function entirely offline.
Implement an Android Room Database in `com/mimo/app/data/` with tables for `AssignmentEntity` and `DailyStatsEntity`. Update the `DashboardViewModel` to read from and write to this local Room database instead of fetching live data from the Retrofit API.

### R2. Mobile Screen Tracking
The Android app must track screen time natively on the device.
Implement a background service (`MobileTrackerService`) utilizing Android's `UsageStatsManager` to track time spent on mobile applications (e.g., social media vs productivity apps). This service should periodically check distraction thresholds and fire local "roast" notifications independently of the PC backend.

### R3. Sync Engine (PC & Mobile)
The system must support merging mobile and PC data when the devices connect.
In the Python backend, create a new `api/routes_sync.py` with endpoints to push mobile data and pull merged data. In the Android app, create a `SyncWorker` using Android `WorkManager` to periodically upload local mobile usage stats to the PC backend and download the aggregated focus score and assignments.

## Acceptance Criteria

### Standalone Functionality
- [ ] An agent-as-judge can run the Android app on an emulator with network access disabled and successfully create, view, and mark assignments as done locally.
- [ ] The Android app successfully tracks the active foreground app on the emulator using `UsageStatsManager` and logs it to the local Room database.

### Sync Verification
- [ ] When network access is restored, the Android `SyncWorker` successfully hits the Python backend's `/sync/push` endpoint.
- [ ] After a sync, a programmatic test can hit `GET /reports/stats` on the Python backend and verify that the mobile screen time has been successfully added to the total `desk_time_min` and focus score calculations.
</USER_REQUEST>
