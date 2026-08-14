# Handoff Report — Reviewer M2_2

## 1. Observation

### 1.1 Reviewed Source Code & Call Sites
- **`modules/schedule/manager.py`**:
  - `boost_subject_priority` (lines 299-305): Filters `Assignment` with `.filter(Assignment.user_id == user_id)`.
  - `smart_suggestions` (lines 434-440): Filters `Assignment` with `.filter(Assignment.user_id == user_id)`.
  - `update_block_status` (lines 167-183): Signature accepts `user_id: Optional[int] = None`. When provided, fetches `ScheduleProfile` via `db.get(ScheduleProfile, block.profile_id)` and verifies `profile.user_id == user_id`, returning `None` if ownership validation fails.
- **`modules/ai_layer/roast_engine.py`**:
  - `_get_context` (lines 135-143): Filters `Assignment` with `.filter(Assignment.user_id == user_id)`.
  - `_fire_roast` (line 128): Payload passed to `self._broadcast` includes `"user_id": user_id`.
  - `_save_roast` (line 158): Passes `user_id=user_id` when persisting `RoastLog`.
  - **State tracking** (lines 45-48): `_last_roast_time`, `_distraction_start`, `_absence_start`, `_current_distracting_app` remain single-instance scalar attributes on `RoastEngine`.
- **`api/websocket.py` & `ConnectionManager`**:
  - `ConnectionManager` (lines 31-96): Maintains `_user_sockets: Dict[int, Set[WebSocket]]` and `_socket_users: Dict[WebSocket, int]`.
  - `unicast(user_id, message)` (lines 59-71): Delivers payload strictly to sockets registered under `user_id`.
  - `broadcast(message, user_id=None)` (lines 73-92): Checks `user_id` parameter or `message.get("user_id")`. If present, calls `unicast(target_user, message)`. If omitted, broadcasts globally to all `_active` connections.
  - `drain_event_bus` (lines 105-118): Drains `event_bus` queue and invokes `manager.broadcast(data, user_id=data.get("user_id"))`.
- **`api/routes_assignments.py`**:
  - Line 63 (`add_assignment`): `push_event({"type": "assignment_added", "assignment": {...}})` — **omits `"user_id": user.id`**.
  - Line 77 (`add_assignment_nlp`): `push_event({"type": "assignment_added", "assignment": {...}})` — **omits `"user_id": user.id`**.
  - Line 104 (`set_status`): `push_event({"type": "assignment_updated", "id": a.id, "status": a.status, "title": a.title})` — **omits `"user_id": user.id`**.
  - Line 113 (`done`): `push_event({"type": "assignment_done", "id": a.id, "title": a.title})` — **omits `"user_id": user.id`**.
- **`api/routes_schedule.py`**:
  - Line 127 (`create_from_onboarding`): `push_event({"type": "schedule_updated", ...})` — **omits `"user_id": user.id`**.
  - Line 161 (`set_block_status`): `push_event({"type": "schedule_block_updated", ...})` — **omits `"user_id": user.id`**.
  - Line 170 (`reschedule`): `push_event({"type": "schedule_rescheduled", ...})` — **omits `"user_id": user.id`**.
  - Line 190 (`boost`): `push_event({"type": "schedule_boosted", ...})` — **omits `"user_id": user.id`**.
- **`modules/cv_pipeline/presence.py`**:
  - Line 173 (`_log_event`): `user = db.query(User).first()` hardcodes lookup to the first user in the DB instead of using `self._user_id`.

### 1.2 Automated Test Execution
- Executed `pytest tests/test_schedule.py tests/test_websocket.py`.
- Result: 33 items collected and passed.

---

## 2. Logic Chain

1. **Schedule Manager Multi-Tenant DB Isolation**:
   - `boost_subject_priority()` and `smart_suggestions()` include `.filter(Assignment.user_id == user_id)`. Unrelated users' assignment deadlines cannot affect another user's subject priority or schedule suggestions.
   - `update_block_status()` checks `profile.user_id == user_id`. If user A requests modification of user B's schedule block, the method returns `None`, causing `api/routes_schedule.py` to return HTTP 404.

2. **WebSocket Routing Logic & Global Broadcast Leaks**:
   - `ConnectionManager.broadcast()` routes by `user_id` if present; if `user_id` is `None`, it falls back to sending the message to all `self._active` sockets.
   - In `api/routes_assignments.py` (lines 63, 77, 104, 113), events for newly created, updated, or completed assignments are pushed to `event_bus` without `"user_id": user.id`.
   - In `api/routes_schedule.py` (lines 127, 161, 170, 190), schedule events are pushed without `"user_id": user.id`.
   - When `drain_event_bus()` processes these queue items, `data.get("user_id")` evaluates to `None`. Consequently, `broadcast` emits assignment titles, deadlines, statuses, and schedule updates to ALL connected WebSocket clients across tenants.
   - Requirement R2 explicitly requires: *"ensure payloads (stats, assignments, roasts) are only sent to the specific user's connected websockets."*
   - Therefore, the omitted `user_id` tags in `routes_assignments.py` and `routes_schedule.py` represent an active cross-tenant data leak over WebSockets.

3. **CV Pipeline Hardcoded User Lookup**:
   - `PresenceMonitor._log_event()` fetches `db.query(User).first()` rather than using `self._user_id`. In multi-user deployments, presence events recorded by secondary users are attributed to user ID 1 in the database.

---

## 3. Caveats

- **Test Suite Execution**: Full `pytest` run across all 346 tests was launched in the background; targeted execution of `tests/test_schedule.py` and `tests/test_websocket.py` completed with 100% pass rate.
- **RoastEngine Cooldown Scope**: While `RoastEngine._get_context()` and `_fire_roast()` now isolate DB context and WebSocket delivery per `user_id`, distraction timers and roast cooldown timestamps remain singletons. Under simultaneous multi-user activity, one user's roast will set the global cooldown timer for all users.

---

## 4. Conclusion

**Verdict**: **`REQUEST_CHANGES`**

### Summary of Rationale
While database-level multi-tenant isolation in `modules/schedule/manager.py` and `modules/ai_layer/roast_engine.py` is correctly implemented and verified, WebSocket event dispatches in `api/routes_assignments.py` and `api/routes_schedule.py` omit the `user_id` tag. This causes assignment additions, status changes, completion events, and schedule updates to be broadcast globally to all connected tenants via `ConnectionManager.broadcast()`, violating Requirement R2.

---

## 5. Review Findings & Actionable Remediation

### [MAJOR] Finding 1: Cross-Tenant Assignment Data Leak via WebSocket Broadcasts
- **Where**: `api/routes_assignments.py` (lines 63, 77, 104, 113)
- **Why**: `push_event` payloads for `assignment_added`, `assignment_updated`, and `assignment_done` omit `"user_id": user.id`. `ConnectionManager` falls back to global broadcast.
- **Remediation**: Include `"user_id": user.id` in all `push_event` calls in `api/routes_assignments.py`:
  ```python
  push_event({
      "type": "assignment_added",
      "user_id": user.id,
      "assignment": {...}
  })
  ```

### [MAJOR] Finding 2: Cross-Tenant Schedule Event Broadcast Leak
- **Where**: `api/routes_schedule.py` (lines 127, 161, 170, 190)
- **Why**: `push_event` calls for `schedule_updated`, `schedule_block_updated`, `schedule_rescheduled`, and `schedule_boosted` omit `"user_id": user.id`.
- **Remediation**: Attach `"user_id": user.id` to every `push_event` dictionary in `api/routes_schedule.py`.

### [MINOR] Finding 3: Hardcoded First User Query in `PresenceMonitor._log_event`
- **Where**: `modules/cv_pipeline/presence.py` (line 173)
- **Why**: `db.query(User).first()` attaches `CVEvent` records to user 1 regardless of `self._user_id`.
- **Remediation**: Replace `user = db.query(User).first()` with `self._user_id`.

### [MINOR] Finding 4: Process-Wide Singleton Tracking in `RoastEngine`
- **Where**: `modules/ai_layer/roast_engine.py` (lines 45-48)
- **Why**: `_last_roast_time` and distraction start timestamps are single scalar floats instead of per-user maps.
- **Remediation**: Refactor tracking state to a per-user dictionary `Dict[int, float]` to prevent cross-user cooldown interference.

---

## 6. Verified Claims & Integrity Check

- **`modules/schedule/manager.py` SQL Isolation**: Verified line-by-line that `boost_subject_priority`, `smart_suggestions`, and `update_block_status` filter by `user_id`. No hardcoded test stubs or facades detected.
- **`api/websocket.py` Socket Mapping**: Verified `_user_sockets` and `_socket_users` correctly track connections and clean up on disconnect.
- **`tests/test_schedule.py` & `tests/test_websocket.py`**: Verified tests perform actual DB inserts and socket assertions without self-certifying shortcuts.

---

## 7. Verification Method

To re-verify after remediation:
1. **Automated Tests**:
   ```bash
   pytest tests/test_schedule.py tests/test_websocket.py tests/test_api.py
   ```
2. **WebSocket Isolation Check**:
   Inspect `push_event` calls across `api/routes_assignments.py`, `api/routes_schedule.py`, `api/routes_screen.py`, and `api/routes_voice.py` to confirm every user-specific event dictionary includes `"user_id": user.id`.
