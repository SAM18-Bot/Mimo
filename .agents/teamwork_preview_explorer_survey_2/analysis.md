# FastAPI Backend & WebSocket API Specification for Mimo Android App

## Executive Summary
This document provides the definitive API contract for the Mimo Android application (Kotlin / Jetpack Compose). It covers FastAPI REST endpoint models, WebSocket `/ws` connection handshake and event wire formats, roast event trigger mechanisms, and backend server execution instructions for Android emulator (`http://10.0.2.2:8000`) and physical device connectivity.

---

## 1. REST Endpoints Specification

### 1.1 `GET /reports/stats`
- **Location**: `api/routes_reports.py:22` (handler: `today_stats`)
- **Query Parameters**:
  - `target_date`: Optional ISO date (`YYYY-MM-DD`). Defaults to current date based on active timezone profile or local date.
- **HTTP Response Status**: `200 OK`
- **Response JSON Schema**:
```json
{
  "date": "2026-08-06",
  "productive_s": 10800,
  "productive_min": 180,
  "distracting_s": 2700,
  "distracting_min": 45,
  "neutral_s": 900,
  "neutral_min": 15,
  "desk_time_min": 240,
  "productive_apps": "VS Code (120m), Notion (60m)",
  "distracting_apps": "YouTube (30m), Reddit (15m)",
  "focus_score": 88.5,
  "letter_grade": "A",
  "score_verdict": "Great focus session today!",
  "distraction_count": 3,
  "absent_count": 1,
  "longest_focus_min": 75,
  "peak_hour": 14,
  "due_today": [
    "Math Homework"
  ],
  "submitted_today": [
    "Physics Quiz"
  ],
  "overdue_list": [
    "English Essay (due 2026-08-04)"
  ],
  "upcoming_list": [
    "History Report (due 2026-08-08)"
  ]
}
```

---

### 1.2 `GET /reports/history`
- **Location**: `api/routes_reports.py:29` (handler: `history`)
- **Query Parameters**:
  - `days`: integer (default: `7`). Number of past daily summaries to fetch.
- **HTTP Response Status**: `200 OK`
- **Response JSON Schema** (Array of daily summary objects):
```json
[
  {
    "date": "2026-08-06",
    "focus_score": 88.5,
    "productive_min": 180,
    "distracting_min": 45,
    "assignments_done": 1,
    "assignments_due": 2
  },
  {
    "date": "2026-08-05",
    "focus_score": 75.0,
    "productive_min": 120,
    "distracting_min": 60,
    "assignments_done": 2,
    "assignments_due": 2
  }
]
```

---

### 1.3 `GET /assignments/`
- **Location**: `api/routes_assignments.py:81` (handler: `list_assignments`)
- **Query Parameters**:
  - `status`: Optional string (`pending` | `in_progress` | `done`). Filter by status.
- **HTTP Response Status**: `200 OK`
- **Response JSON Schema** (Array of `AssignmentOut`):
```json
[
  {
    "id": 1,
    "title": "Math Homework",
    "subject": "Math",
    "due_date": "2026-08-10",
    "priority": "high",
    "status": "pending",
    "notes": "Chapter 4 exercises 1-15"
  },
  {
    "id": 2,
    "title": "Physics Lab Report",
    "subject": "Physics",
    "due_date": "2026-08-12",
    "priority": "medium",
    "status": "in_progress",
    "notes": null
  }
]
```

---

### 1.4 `POST /assignments/`
- **Location**: `api/routes_assignments.py:50` (handler: `add_assignment`)
- **HTTP Request Method**: `POST`
- **Headers**: `Content-Type: application/json`
- **Request JSON Schema** (`AssignmentCreate`):
```json
{
  "title": "Chemistry Quiz Prep",
  "subject": "Chemistry",
  "due_date": "2026-08-11",
  "priority": "high",
  "notes": "Review periodic table and reaction balances"
}
```
  - `title`: string (required)
  - `subject`: string (optional, nullable)
  - `due_date`: string ISO date `YYYY-MM-DD` (required)
  - `priority`: string (optional, default `"medium"`, allowed: `"low"`, `"medium"`, `"high"`)
  - `notes`: string (optional, nullable)
- **HTTP Response Status**: `201 Created`
- **Response JSON Schema** (`AssignmentOut`):
```json
{
  "id": 3,
  "title": "Chemistry Quiz Prep",
  "subject": "Chemistry",
  "due_date": "2026-08-11",
  "priority": "high",
  "status": "pending",
  "notes": "Review periodic table and reaction balances"
}
```

---

### 1.5 `POST /assignments/nlp`
- **Location**: `api/routes_assignments.py:67` (handler: `add_assignment_nlp`)
- **HTTP Request Method**: `POST`
- **Headers**: `Content-Type: application/json`
- **Request JSON Schema** (`NLPCreate`):
```json
{
  "text": "Math assignment due Friday priority high"
}
```
  - `text`: string (required, raw natural language or voice command)
- **HTTP Response Status**: `201 Created` (or `422 Unprocessable Entity` if parsing fails)
- **Response JSON Schema** (`AssignmentOut`):
```json
{
  "id": 4,
  "title": "Math assignment",
  "subject": "Math",
  "due_date": "2026-08-08",
  "priority": "high",
  "status": "pending",
  "notes": null
}
```

---

### 1.6 `POST /assignments/{id}/done`
- **Location**: `api/routes_assignments.py:105` (handler: `done`)
- **HTTP Request Method**: `POST`
- **Path Parameter**:
  - `id`: integer (assignment ID)
- **HTTP Response Status**: `200 OK` (or `404 Not Found` if assignment ID does not exist)
- **Response JSON Schema**:
```json
{
  "ok": true,
  "message": "'Math Homework' marked as done."
}
```

---

### 1.7 `GET /screen/breakdown`
- **Location**: `api/routes_screen.py:58` (handler: `daily_breakdown`)
- **Query Parameters**:
  - `target_date`: Optional ISO date (`YYYY-MM-DD`). Defaults to today.
- **HTTP Response Status**: `200 OK`
- **Response JSON Schema** (`DailyBreakdown`):
```json
{
  "productive_min": 180,
  "distracting_min": 45,
  "neutral_min": 15,
  "total_min": 240,
  "top_productive": [
    {
      "app": "VS Code",
      "minutes": 120
    },
    {
      "app": "Notion",
      "minutes": 60
    }
  ],
  "top_distracting": [
    {
      "app": "YouTube",
      "minutes": 30
    },
    {
      "app": "Reddit",
      "minutes": 15
    }
  ]
}
```

---

## 2. WebSocket Protocol & Event Specifications (`/ws`)

### 2.1 Connection URL & Authentication
- **Endpoint**: `/ws`
- **Android Emulator URL**: `ws://10.0.2.2:8000/ws?token=dev_token`
- **Physical Device URL**: `ws://<HOST_IP>:8000/ws?token=dev_token` (or JWT bearer token)
- **Authentication Handshake**:
  - Requires query parameter `token`.
  - Development token: `dev_token` is accepted without validation.
  - Production token: Valid JWT access token issued via `POST /auth/login` or `POST /auth/register`.
  - Disconnect Reasons:
    - Code `1008`: `"Missing token"` (no `token` query param provided)
    - Code `1008`: `"Invalid token"` (failed JWT decoding)
    - Code `1008`: `"Token revoked"` (token is in `TokenBlocklist`)

### 2.2 Connection Initialization Payload
Immediately after a successful WebSocket connection (`manager.connect(ws)` at `main.py:149-157`), the backend automatically broadcasts two initial events:

1. **Initial `stats_update` event**:
```json
{
  "type": "stats_update",
  "stats": {
    "date": "2026-08-06",
    "productive_s": 10800,
    "productive_min": 180,
    "distracting_s": 2700,
    "distracting_min": 45,
    "neutral_s": 900,
    "neutral_min": 15,
    "desk_time_min": 240,
    "productive_apps": "VS Code (120m)",
    "distracting_apps": "YouTube (30m)",
    "focus_score": 88.5,
    "letter_grade": "A",
    "score_verdict": "Great focus!",
    "distraction_count": 3,
    "absent_count": 1,
    "longest_focus_min": 75,
    "peak_hour": 14,
    "due_today": ["Math Homework"],
    "submitted_today": ["Physics Quiz"],
    "overdue_list": [],
    "upcoming_list": ["History Report (due 2026-08-08)"]
  }
}
```

2. **Initial `tasks_list` event**:
```json
{
  "type": "tasks_list",
  "tasks": [
    {
      "id": 1,
      "title": "Math Homework",
      "due_date": "2026-08-10",
      "priority": "high",
      "status": "pending",
      "subject": "Math"
    }
  ]
}
```

---

### 2.3 Live WebSocket Event Wire Specifications

#### 1. `roast` Event (Critical for Background Alert Service)
Emitted by `RoastEngine` (`modules/ai_layer/roast_engine.py:119`) when distraction or absence threshold is exceeded.
```json
{
  "type": "roast",
  "message": "Hey! Watching YouTube videos won't help you finish Math Homework due in 2 days!",
  "trigger": "distraction",
  "app": "YouTube",
  "ts": "2026-08-06T23:23:45.123456"
}
```
- Fields:
  - `type`: `"roast"`
  - `message`: string (the AI-generated roast text to be shown in Android system notification)
  - `trigger`: string (`"distraction"` | `"absent"`)
  - `app`: string (application or context e.g. `"YouTube"`, `"desk"`)
  - `ts`: string ISO timestamp

#### 2. `window_change` Event
Emitted by `ScreenTracker` or `POST /screen/mock`.
```json
{
  "type": "window_change",
  "app": "YouTube",
  "title": "Watching Cat Videos - YouTube",
  "category": "distracting",
  "ts": "2026-08-06T23:23:45.123456"
}
```

#### 3. `cv_event` Event
Emitted by `PresenceMonitor` or `POST /cv/mock`.
```json
{
  "type": "cv_event",
  "event": "absent",
  "ts": "2026-08-06T23:23:45.123456"
}
```

#### 4. `assignment_added` Event
```json
{
  "type": "assignment_added",
  "assignment": {
    "id": 5,
    "title": "Biology Lab",
    "due_date": "2026-08-12",
    "subject": "Biology",
    "priority": "medium",
    "status": "pending"
  }
}
```

#### 5. `assignment_updated` Event
```json
{
  "type": "assignment_updated",
  "id": 5,
  "status": "in_progress",
  "title": "Biology Lab"
}
```

#### 6. `assignment_done` Event
```json
{
  "type": "assignment_done",
  "id": 5,
  "title": "Biology Lab"
}
```

#### 7. `reminder` Event
```json
{
  "type": "reminder",
  "message": "Assignment 'Biology Lab' is due tomorrow!",
  "assignment_id": 5
}
```

---

## 3. Roast Event Triggers & Testing Guide

### How Roast Events Work
1. **Distraction Trigger**: When `on_window_change` receives an app with category `"distracting"`, it tracks elapsed time. If elapsed time >= `config.DISTRACTION_ROAST_AFTER_MINUTES` (and `MIN_ROAST_INTERVAL_SECONDS` cooldown has passed), it calls `generate_roast(...)` and broadcasts the `"roast"` event.
2. **Absence Trigger**: When `on_cv_event` receives `"absent"`, if elapsed absence time >= `config.ABSENCE_ROAST_AFTER_MINUTES`, it calls `generate_roast(...)` and broadcasts the `"roast"` event.

### Methods to Trigger Roast Events for Android Verification
- **Method 1 (HTTP Mock Endpoint - Screen)**:
  Send a POST request to `http://10.0.2.2:8000/screen/mock`:
  ```json
  {
    "app": "YouTube",
    "title": "Watching Gaming Stream",
    "category": "distracting"
  }
  ```
- **Method 2 (HTTP Mock Endpoint - CV)**:
  Send a POST request to `http://10.0.2.2:8000/cv/mock`:
  ```json
  {
    "event": "absent"
  }
  ```
- **Method 3 (Python CLI Mock Scripts)**:
  In the backend workspace, run `python mock_screen.py` or `python mock_cv.py`.
- **Method 4 (Direct Push for Automated Testing)**:
  Call `push_event({"type": "roast", "message": "Test Android Roast Alert!", "trigger": "test", "app": "MockApp", "ts": datetime.now().isoformat()})` from any route or test runner.

---

## 4. Backend Server Status & Startup Guide

### Current Server Status
- **Status**: Not currently running.

### Server Command for Local Development / Android Emulator
To bind to `0.0.0.0:8000` (allowing Android Emulator to connect via `http://10.0.2.2:8000`):

```bash
python run_server.py --host 0.0.0.0 --port 8000 --dev
```
or using Uvicorn directly:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Network Addresses Matrix
| Environment | Base REST URL | WebSocket URL |
|---|---|---|
| Android Emulator | `http://10.0.2.2:8000` | `ws://10.0.2.2:8000/ws?token=dev_token` |
| Local Host PC | `http://localhost:8000` | `ws://localhost:8000/ws?token=dev_token` |
| Physical Android Device | `http://<HOST_LAN_IP>:8000` | `ws://<HOST_LAN_IP>:8000/ws?token=dev_token` |
