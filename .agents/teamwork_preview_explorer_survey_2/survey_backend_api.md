# Survey Report: Mimo Backend REST & WebSocket Specifications

**Author**: survey_explorer_2 (teamwork_preview_explorer)  
**Date**: 2026-08-06  
**Target Codebase**: `c:\Users\samee\projects\Mimo\`  
**Target Output**: `survey_backend_api.md`  
**Inspection Mode**: Read-only  

---

## Executive Summary

The Mimo Python FastAPI backend (version `2.0.0`) is a behavior-aware AI productivity coach for students. It combines REST endpoints for data retrieval and actions with a unified WebSocket (`/ws`) for real-time event broadcasts (app focus changes, CV presence states, AI roasts, task updates, reminders, and daily reports).

This document cataloging the exact REST endpoints, request/response JSON schemas, field types, status codes, WebSocket event formats, and background event generators serves as the definitive reference for the frontend dashboard redesign.

---

## 1. Primary REST Endpoints Catalog

Below are the 10 core endpoints requested for the dashboard redesign, followed by additional backend endpoints found in the codebase.

### 1.1 `GET /reports/stats`
- **Description**: Fetches live aggregated productivity and focus statistics for a given target date (defaults to today). Called on dashboard load and periodically.
- **Query Parameters**:
  - `target_date` (`Optional[date]`): ISO date string `YYYY-MM-DD` (e.g. `2026-08-06`). Default: today.
- **Status Code**: `200 OK`
- **JSON Response Schema & Field Types**:
```json
{
  "date": "2026-08-06",
  "productive_s": 7200,
  "productive_min": 120,
  "distracting_s": 1800,
  "distracting_min": 30,
  "neutral_s": 600,
  "neutral_min": 10,
  "desk_time_min": 160,
  "productive_apps": "code (90m), notion (30m)",
  "distracting_apps": "chrome (30m)",
  "focus_score": 85.5,
  "letter_grade": "A",
  "score_verdict": "Great focus today!",
  "distraction_count": 3,
  "absent_count": 1,
  "longest_focus_min": 45,
  "peak_hour": 14,
  "due_today": ["Math Homework"],
  "submitted_today": ["Physics Quiz"],
  "overdue_list": ["Chemistry Lab (due 2026-08-04)"],
  "upcoming_list": ["AI Project (due 2026-08-08)"]
}
```
- **Field Details**:
  - `date` (`str`): ISO formatted date (`YYYY-MM-DD`).
  - `productive_s` (`int`): Total seconds spent in productive applications.
  - `productive_min` (`int`): Total minutes spent in productive applications.
  - `distracting_s` (`int`): Total seconds spent in distracting applications.
  - `distracting_min` (`int`): Total minutes spent in distracting applications.
  - `neutral_s` (`int`): Total seconds spent in neutral applications.
  - `neutral_min` (`int`): Total minutes spent in neutral applications.
  - `desk_time_min` (`int`): Total desk screen time in minutes (`(productive_s + distracting_s + neutral_s) // 60`).
  - `productive_apps` (`str`): Formatted string listing top productive apps with minutes e.g., `"code (90m), notion (30m)"` or `"none"`.
  - `distracting_apps` (`str`): Formatted string listing top distracting apps with minutes e.g., `"chrome (30m)"` or `"none"`.
  - `focus_score` (`float`): Calculated productivity score from `0.0` to `100.0`.
  - `letter_grade` (`str`): Academic grade representation: `"A+"`, `"A"`, `"B"`, `"C"`, `"D"`, `"F"`.
  - `score_verdict` (`str`): Short qualitative summary sentence.
  - `distraction_count` (`int`): Number of CV distraction events detected.
  - `absent_count` (`int`): Number of CV absence events detected.
  - `longest_focus_min` (`int`): Longest uninterrupted productive app session in minutes.
  - `peak_hour` (`int | null`): Hour of day (0-23) with highest productive screen time.
  - `due_today` (`List[str]`): List of assignment titles due on target date.
  - `submitted_today` (`List[str]`): List of assignment titles completed on target date.
  - `overdue_list` (`List[str]`): Formatted string list: `["{title} (due {date})"]`.
  - `upcoming_list` (`List[str]`): Formatted string list for assignments due in next 3 days: `["{title} (due {date})"]`.

---

### 1.2 `GET /reports/history`
- **Description**: Fetches daily summaries for the last N days for focus score trends and weekly bar charts.
- **Query Parameters**:
  - `days` (`int`): Number of historical days to fetch (default: `7`).
- **Status Code**: `200 OK`
- **JSON Response Schema & Field Types**: Array of objects ordered by date descending (`DailySummary`).
```json
[
  {
    "date": "2026-08-06",
    "focus_score": 85.5,
    "productive_min": 120,
    "distracting_min": 30,
    "assignments_done": 2,
    "assignments_due": 3
  },
  {
    "date": "2026-08-05",
    "focus_score": 72.0,
    "productive_min": 90,
    "distracting_min": 45,
    "assignments_done": 1,
    "assignments_due": 2
  }
]
```
- **Field Details**:
  - `date` (`str`): Date string `YYYY-MM-DD`.
  - `focus_score` (`float | null`): Focus score for that day.
  - `productive_min` (`int`): Productive screen time in minutes (`(productive_time_s or 0) // 60`).
  - `distracting_min` (`int`): Distracting screen time in minutes (`(distracted_time_s or 0) // 60`).
  - `assignments_done` (`int | null`): Number of assignments completed on that day.
  - `assignments_due` (`int | null`): Number of assignments due on that day.

---

### 1.3 `GET /assignments/`
- **Description**: Fetches list of all assignments, optionally filtered by status.
- **Query Parameters**:
  - `status` (`Optional[str]`): Filter by `"pending"`, `"in_progress"`, or `"done"`.
- **Status Code**: `200 OK`
- **JSON Response Schema & Field Types**: List of `AssignmentOut` models.
```json
[
  {
    "id": 1,
    "title": "Math Assignment 3",
    "subject": "Math",
    "due_date": "2026-08-10",
    "priority": "high",
    "status": "pending",
    "notes": "Chapter 4 problems 1-10"
  }
]
```
- **Field Details**:
  - `id` (`int`): Primary key ID.
  - `title` (`str`): Assignment title.
  - `subject` (`str | null`): Associated subject string.
  - `due_date` (`str`): Due date formatted as `YYYY-MM-DD`.
  - `priority` (`str`): Priority level (`"low"`, `"medium"`, `"high"`). Default: `"medium"`.
  - `status` (`str`): Current status (`"pending"`, `"in_progress"`, `"done"`).
  - `notes` (`str | null`): Free-form notes or description.

---

### 1.4 `POST /assignments/`
- **Description**: Creates a new assignment.
- **Status Code**: `201 Created`
- **Request Body** (`AssignmentCreate`):
```json
{
  "title": "Physics Lab Report",
  "subject": "Physics",
  "due_date": "2026-08-12",
  "priority": "high",
  "notes": "Include error analysis"
}
```
  - `title` (`str`, required): Title of assignment.
  - `subject` (`str | null`, optional): Subject name.
  - `due_date` (`str` ISO Date `YYYY-MM-DD`, required): Due date.
  - `priority` (`str | null`, optional): `"low"`, `"medium"`, `"high"`. Default: `"medium"`.
  - `notes` (`str | null`, optional): Optional notes.
- **JSON Response Schema**: `AssignmentOut` object (same structure as GET item).
- **Side Effect**: Emits WebSocket event `assignment_added`.

---

### 1.5 `POST /assignments/nlp`
- **Description**: Parses natural language text (e.g. "Math assignment due Friday priority high") and creates an assignment.
- **Status Code**: `201 Created` (returns `422 Unprocessable Entity` if parsing fails).
- **Request Body** (`NLPCreate`):
```json
{
  "text": "Math assignment due Friday priority high"
}
```
- **JSON Response Schema**: `AssignmentOut` object.
- **Side Effect**: Emits WebSocket event `assignment_added`.

---

### 1.6 `POST /assignments/{id}/done`
- **Description**: Marks an assignment as completed.
- **Path Parameters**: `id` (`int`): Assignment ID.
- **Status Code**: `200 OK` (returns `404 Not Found` if assignment ID non-existent).
- **Request Body**: None (empty body).
- **JSON Response Schema**:
```json
{
  "ok": true,
  "message": "'Physics Lab Report' marked as done."
}
```
- **Side Effect**: Emits WebSocket event `assignment_done`.

---

### 1.7 `GET /screen/breakdown`
- **Description**: Fetches app screen usage breakdown for today (or specified date), including category totals and top productive/distracting apps.
- **Query Parameters**:
  - `target_date` (`Optional[date]`): Target date `YYYY-MM-DD`. Default: today.
- **Status Code**: `200 OK`
- **JSON Response Schema & Field Types** (`DailyBreakdown`):
```json
{
  "productive_min": 120,
  "distracting_min": 30,
  "neutral_min": 15,
  "total_min": 165,
  "top_productive": [
    { "app": "code", "minutes": 90 },
    { "app": "notion", "minutes": 30 }
  ],
  "top_distracting": [
    { "app": "chrome", "minutes": 30 }
  ]
}
```
- **Field Details**:
  - `productive_min` (`int`): Productive minutes.
  - `distracting_min` (`int`): Distracting minutes.
  - `neutral_min` (`int`): Neutral minutes.
  - `total_min` (`int`): Sum of productive, distracting, and neutral minutes.
  - `top_productive` (`List[dict]`): Top up to 5 productive apps `[{"app": str, "minutes": int}]`.
  - `top_distracting` (`List[dict]`): Top up to 5 distracting apps `[{"app": str, "minutes": int}]`.

---

### 1.8 `GET /study/recommendations`
- **Description**: Runs full subject study analysis, ranking weak subjects, creating daily time slots, and generating AI advice.
- **Query Parameters**:
  - `days` (`int`): Analysis lookback period (default: `7`).
- **Status Code**: `200 OK`
- **JSON Response Schema & Field Types**:
```json
{
  "analysis_date": "2026-08-06",
  "days_analysed": 7,
  "subjects": ["math", "physics", "computer science"],
  "weak_subjects": ["math"],
  "strong_subjects": ["computer science"],
  "time_per_subject": {
    "math": 15,
    "physics": 45,
    "computer science": 120
  },
  "completion_rates": {
    "math": 33.3,
    "physics": 80.0
  },
  "last_studied": {
    "math": "2026-08-04",
    "physics": "2026-08-05"
  },
  "priority_ranking": [
    { "subject": "math", "need_score": 82.5 },
    { "subject": "physics", "need_score": 45.0 }
  ],
  "daily_study_plan": [
    {
      "subject": "math",
      "start_time": "14:00",
      "end_time": "16:00",
      "duration_min": 120,
      "reason": "Lowest study time this week among your subjects."
    }
  ],
  "recommendations": [
    {
      "recommendation": "Prioritise math — it has the lowest study time this week. Aim for at least 90 minutes on it tomorrow.",
      "priority": "high"
    }
  ],
  "peak_hour": 14,
  "weekly_patterns": []
}
```
- **Field Details**:
  - `analysis_date` (`str`): `YYYY-MM-DD`.
  - `days_analysed` (`int`): Lookback days.
  - `subjects` (`List[str]`): List of detected subjects.
  - `weak_subjects` (`List[str]`): Top 3 highest need-score subjects.
  - `strong_subjects` (`List[str]`): Subjects with need score < 30.
  - `time_per_subject` (`Dict[str, int]`): Minutes per subject over past N days.
  - `completion_rates` (`Dict[str, float]`): % assignment completion rate (0-100).
  - `last_studied` (`Dict[str, str]`): Date ISO string when subject was last detected.
  - `priority_ranking` (`List[dict]`): Sorted `[{"subject": str, "need_score": float}]`.
  - `daily_study_plan` (`List[dict]`): Array of time slots `[{"subject": str, "start_time": str, "end_time": str, "duration_min": int, "reason": str}]`.
  - `recommendations` (`List[dict]`): Array of advice items `[{"recommendation": str, "priority": "high" | "medium" | "low"}]`.
  - `peak_hour` (`int | null`): Peak focus hour.
  - `weekly_patterns` (`List[str]`): Textual pattern insights.

---

### 1.9 `POST /reports/accountability`
- **Description**: Submits morning Q&A accountability log entry.
- **Status Code**: `201 Created`
- **Request Body** (`AccountabilityAnswer`):
```json
{
  "question": "What is your main goal for today?",
  "answer": "Finish Chapter 4 Math exercises and submit physics lab report."
}
```
  - `question` (`str`): Question string.
  - `answer` (`str`): Answer text.
- **JSON Response Schema**:
```json
{
  "ok": true
}
```

---

### 1.10 Additional Supporting Endpoints

#### Assignment Endpoints
- `GET /assignments/upcoming?days=7` — List upcoming assignments for next N days (`AssignmentOut[]`).
- `GET /assignments/overdue` — List overdue pending assignments (`AssignmentOut[]`).
- `PATCH /assignments/{id}/status` — Body `{"status": "pending" | "in_progress" | "done"}`. Updates status, emits `assignment_updated` WS event.
- `DELETE /assignments/{id}` — Deletes assignment (Status `204 No Content`).

#### Screen Tracker Endpoints
- `GET /screen/sessions?target_date=YYYY-MM-DD&category=productive` — Raw screen sessions (limit 200).
- `GET /screen/live` — Returns active foreground window: `{"app": str, "title": str, "category": str}`.
- `POST /screen/mock` — Body `{"app": str, "title": str, "category": str}`. Injects fake window event for testing. Emits `window_change` WS event.

#### CV / Presence Endpoints
- `GET /cv/events?target_date=YYYY-MM-DD` — Recent CV events: `[{"event": str, "ts": str}]`.
- `GET /cv/presence` — REST status summary fallback.
- `GET /cv/focus/today` — Today's focus score and distraction/absence counts.
- `POST /cv/mock` — Body `{"event": "present" | "absent" | "distracted" | "returned"}`. Injects fake CV event. Emits `cv_event` WS event.

#### Study & Report Detail Endpoints
- `GET /study/next` — Returns single immediate action string: `{"recommendation": "Study Math..."}`.
- `GET /study/subjects` — Returns raw minutes per subject dictionary.
- `POST /reports/eod` — Triggers background EOD report generation.
- `GET /reports/eod/latest` — Fetches latest EOD report text and summary.
- `GET /reports/accountability/today` — Returns today's Q&A logs: `[{"question": str, "answer": str}]`.
- `GET /reports/roasts` — Returns today's roast log: `[{"trigger": str, "message": str, "ts": str}]`.
- `GET /reports/patterns` — 7-day pattern detector analysis.
- `GET /reports/score/breakdown` — Granular breakdown of focus score factors (productive_pts, presence_pts, penalties, bonuses).

#### Control & Auxiliary Endpoints
- `GET /health` — System status, background component status (`screen_tracker`, `esp32_connected`, `roast_engine`, `ws_clients`, hardware flags).
- `POST /monitoring/pause` & `POST /monitoring/resume` & `GET /monitoring/status` — Control/check background tracking state. Emits `monitoring_paused` / `monitoring_resumed` WS events.
- `POST /voice/command` — Body `{"text": str, "speak_response": bool}`. Routes voice/text commands. Emits `voice_response`, `tasks_list`, `assignment_added`, or `study_advice`.

---

## 2. WebSocket `/ws` Specification

### 2.1 Connection Behavior
- **URL**: `ws://localhost:8000/ws` (or `ws://<host>:8000/ws`).
- **Connection Handshake**:
  1. Server accepts WebSocket connection and registers client in `ConnectionManager`.
  2. Server immediately sends **`stats_update`** payload with today's live stats.
  3. Server immediately sends **`tasks_list`** payload with upcoming 7-day tasks.
  4. Connection enters receive loop. Any client text sent to WS is received (server does not require incoming text unless testing ping).
- **Disconnection**: Client removal from active set on disconnect or socket drop.

---

### 2.2 Complete Catalog of WebSocket Event Messages

All WebSocket messages sent by the server are JSON objects containing a top-level `"type"` property.

#### 1. `stats_update`
- **Trigger**: Sent on connection connect, every 60 seconds via `APScheduler`, or after batch stats recomputations.
- **Payload Format**:
```json
{
  "type": "stats_update",
  "stats": {
    "date": "2026-08-06",
    "productive_s": 7200,
    "productive_min": 120,
    "distracting_s": 1800,
    "distracting_min": 30,
    "neutral_s": 600,
    "neutral_min": 10,
    "desk_time_min": 160,
    "productive_apps": "code (90m), notion (30m)",
    "distracting_apps": "chrome (30m)",
    "focus_score": 85.5,
    "letter_grade": "A",
    "score_verdict": "Great focus today!",
    "distraction_count": 3,
    "absent_count": 1,
    "longest_focus_min": 45,
    "peak_hour": 14,
    "due_today": ["Math Homework"],
    "submitted_today": ["Physics Quiz"],
    "overdue_list": ["Chemistry Lab (due 2026-08-04)"],
    "upcoming_list": ["AI Project (due 2026-08-08)"]
  }
}
```

#### 2. `tasks_list`
- **Trigger**: Sent on WebSocket connect or when user requests tasks via voice/command.
- **Payload Format**:
```json
{
  "type": "tasks_list",
  "tasks": [
    {
      "id": 1,
      "title": "Math Homework",
      "due_date": "2026-08-06",
      "priority": "high",
      "status": "pending",
      "subject": "Math"
    }
  ]
}
```

#### 3. `window_change`
- **Trigger**: Sent by `ScreenTracker` whenever active OS window changes or polled (every 2s by default), or injected via `POST /screen/mock`.
- **Payload Format**:
```json
{
  "type": "window_change",
  "app": "code",
  "title": "main.py — Mimo",
  "category": "productive",
  "ts": "2026-08-06T08:40:00.123456"
}
```
- **Category values**: `"productive"`, `"distracting"`, `"neutral"`.

#### 4. `cv_event`
- **Trigger**: Sent by `PresenceMonitor` on presence state change, or injected via `POST /cv/mock`.
- **Payload Format**:
```json
{
  "type": "cv_event",
  "event": "present",
  "ts": "2026-08-06T08:40:05.654321"
}
```
- **Event values**: `"present"`, `"absent"`, `"distracted"`, `"returned"`.

#### 5. `roast`
- **Trigger**: Sent by `RoastEngine` when user remains on distracting app or absent past threshold.
- **Payload Format**:
```json
{
  "type": "roast",
  "message": "You've been staring at Instagram for 10 minutes while Math is due today!",
  "trigger": "distraction",
  "app": "chrome",
  "ts": "2026-08-06T08:41:00.000000"
}
```
- **Trigger values**: `"distraction"`, `"absent"`.

#### 6. `morning_qa`
- **Trigger**: Sent by `APScheduler` daily at 08:00 AM.
- **Payload Format**:
```json
{
  "type": "morning_qa",
  "questions": [
    "What are your top 3 priorities for today?",
    "When do you plan to finish your highest-priority task?",
    "What potential distractions will you face and how will you handle them?"
  ]
}
```

#### 7. `assignment_added`
- **Trigger**: Sent when a new assignment is created via REST (`POST /assignments/`, `POST /assignments/nlp`) or voice.
- **Payload Format**:
```json
{
  "type": "assignment_added",
  "assignment": {
    "id": 5,
    "title": "Physics Lab",
    "due_date": "2026-08-10",
    "subject": "Physics",
    "priority": "high",
    "status": "pending"
  }
}
```

#### 8. `assignment_updated`
- **Trigger**: Sent when assignment status is modified via `PATCH /assignments/{id}/status`.
- **Payload Format**:
```json
{
  "type": "assignment_updated",
  "id": 5,
  "status": "in_progress",
  "title": "Physics Lab"
}
```

#### 9. `assignment_done`
- **Trigger**: Sent when assignment is marked done via `POST /assignments/{id}/done`.
- **Payload Format**:
```json
{
  "type": "assignment_done",
  "id": 5,
  "title": "Physics Lab"
}
```

#### 10. `reminder`
- **Trigger**: Sent by `ReminderLoop` every 15 minutes when pending or overdue assignment reminders are due.
- **Payload Format**:
```json
{
  "type": "reminder",
  "message": "'Physics Lab' is due TOMORROW. If you haven't started, start RIGHT NOW.",
  "assignment_id": 5,
  "ts": "2026-08-06T08:45:00.000000"
}
```

#### 11. `eod_report`
- **Trigger**: Sent by `APScheduler` daily at 22:00 PM (or manually via `POST /reports/eod`).
- **Payload Format**:
```json
{
  "type": "eod_report",
  "report": {
    "summary": "You studied for 3 hours. Grade: B.",
    "focus_score_comment": "Focus score: 75/100.",
    "biggest_win": "Completed Physics Quiz.",
    "biggest_fail": "45 minutes on Reddit.",
    "tomorrow_priority": "Finish Math assignment.",
    "study_recommendation": "Study Math first.",
    "roast_or_praise": "Decent day."
  },
  "stats": { ... }
}
```

#### 12. `voice_response`
- **Trigger**: Sent when voice interaction generates a spoken text feedback message.
- **Payload Format**:
```json
{
  "type": "voice_response",
  "message": "Added Math assignment due Friday."
}
```

#### 13. `study_advice`
- **Trigger**: Sent when user requests study advice via voice command.
- **Payload Format**:
```json
{
  "type": "study_advice",
  "message": "Study Math — you've only spent 15min on it this week."
}
```

#### 14. `monitoring_paused` & `monitoring_resumed`
- **Trigger**: Sent when background monitoring is paused or resumed via `/monitoring/pause` or `/monitoring/resume`.
- **Payload Format**: `{"type": "monitoring_paused"}` or `{"type": "monitoring_resumed"}`.

#### 15. `schedule_updated` & `schedule_block_updated`
- **Trigger**: Sent when user updates onboarding schedule profile or block status in `/schedule`.
- **Payload Format**: `{"type": "schedule_updated", "profile_id": 1, "blocks": 14}` or `{"type": "schedule_block_updated", "id": 3, "status": "done"}`.

---

## 3. Background Data Streams, Generators & Frequencies

The Mimo backend uses background threads and schedulers to continuously track user state and emit events.

| Component | Source File | Frequency / Interval | Generated WebSocket Events & Actions |
|---|---|---|---|
| **ScreenTracker** | `modules/screen_tracker/tracker.py` | Every 2.0s (`SCREEN_POLL_INTERVAL`) | Emits `window_change` event.<br>Triggers `RoastEngine.on_window_change()`. Stitches screen sessions to DB. |
| **PresenceMonitor** | `modules/cv_pipeline/presence.py` | Frame loop (~0.1s poll) | Emits `cv_event` on state changes (`present`, `absent`, `distracted`, `returned`).<br>Triggers `RoastEngine.on_cv_event()`. |
| **RoastEngine** | `modules/ai_layer/roast_engine.py` | State-triggered | Evaluates distraction/absence duration. Respects `MIN_ROAST_INTERVAL_SECONDS` (default: 300s). Emits `roast` event and fires TTS / OS notification. |
| **Live Stats Pusher** | `schedulers/daily_trigger.py` | Every 60s | Fetches latest DB aggregations and broadcasts `stats_update` event to all dashboard clients. |
| **ReminderLoop** | `modules/assignments/reminder.py` | Every 15 minutes (`REMINDER_CHECK_INTERVAL_MINUTES`) | Checks pending reminders and overdue tasks. Emits `reminder` event for due items. |
| **Morning Q&A Job** | `schedulers/daily_trigger.py` | Daily at 08:00 AM | Emits `morning_qa` event with accountability questions. |
| **EOD Report Job** | `schedulers/daily_trigger.py` | Daily at 22:00 PM (`EOD_REPORT_HOUR`) | Runs AI EOD report pipeline, saves summary to DB, emits `eod_report` event. |
| **Mock Screen Generator** | `mock_screen.py` & `POST /screen/mock` | On demand / demo loop | Simulates window changes for testing without OS hooks. Emits `window_change`. |
| **Mock CV Generator** | `mock_cv.py` & `POST /cv/mock` | On demand / demo loop | Simulates camera presence states without ESP32 hardware. Emits `cv_event`. |

---

## 4. Dashboard Redesign Mapping Matrix

This matrix maps each of the 10 required UI features to its corresponding backend API/WS resources:

| UI Feature | Primary REST Endpoint | WebSocket Event(s) | Fallback / Data Fields |
|---|---|---|---|
| **1. Animated Focus Score Gauge** | `GET /reports/stats` | `stats_update` | `stats.focus_score` (0-100), `stats.letter_grade` ("A+", "A", etc.), `stats.score_verdict` |
| **2. Weekly Focus Score Bar Chart** | `GET /reports/history?days=7` | `stats_update` (re-fetch) | Array of `{ date, focus_score, productive_min, distracting_min, assignments_done }` |
| **3. App Usage Breakdown** | `GET /screen/breakdown` | `stats_update` / `window_change` | `productive_min`, `distracting_min`, `neutral_min`, `top_productive`, `top_distracting` |
| **4. Real-time Activity Timeline** | `GET /screen/sessions` | `window_change`, `cv_event`, `roast` | Event stream of app switches, presence changes, and roasts with ISO timestamp `ts` |
| **5. Assignment Urgency List** | `GET /assignments/` | `tasks_list`, `assignment_added`, `assignment_updated`, `assignment_done` | Color code by `due_date` vs today (`overdue`, `due_today`, `upcoming_3d`), `priority` |
| **6. Quick-add Assignment Input** | `POST /assignments/` or `POST /assignments/nlp` | `assignment_added` | Payload: `{ title, subject, due_date, priority }` or `{ text }` |
| **7. Live WebSocket Connection Indicator** | `ws://localhost:8000/ws` | Connection lifecycle (`onopen`, `onclose`, `onerror`, `onmessage`) | Green: connected; Yellow: reconnecting; Red: disconnected |
| **8. Responsive Mobile Layout** | N/A (Frontend CSS/JS) | N/A | Breakpoints: Desktop (>=1200px), Tablet (>=768px), Mobile (>=375px) |
| **9. Sidebar Navigation** | Static pages | N/A | Links to Dashboard (`/`), Schedule (`/schedule`), Settings (`/settings`) |
| **10. Focus Session Timer** | Local state / `POST /screen/mock` | `window_change` | Client-side timer (start/stop/elapsed time) |

---

## 5. Verification & Testing Instructions

To independently verify all REST endpoints and WebSocket events:
1. **Start Backend Server**:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```
2. **Access Swagger Interactive OpenAPI Docs**:
   - `http://localhost:8000/docs`
3. **Run Mock Screen Injector**:
   ```bash
   python mock_screen.py --demo
   ```
4. **Run Mock CV Injector**:
   ```bash
   python mock_cv.py --demo
   ```
5. **WebSocket Verification**:
   - Connect via Browser Console or Postman to `ws://localhost:8000/ws` and inspect initial `stats_update` and `tasks_list` messages as well as live `window_change` events.
