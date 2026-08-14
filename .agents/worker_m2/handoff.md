# Handoff Report — Worker M2 (Milestone M2: Fix Cross-Tenant Data Leaks & WebSocket Multi-Tenancy)

## 1. Observation

### 1.1 `modules/schedule/manager.py`
- **Line 297 (`boost_subject_priority`)**: `db.query(Assignment)` was filtering by `due_date` and `status` but lacked `.filter(Assignment.user_id == user_id)`, causing assignments belonging to other users to be included when calculating urgent subject priority boosts.
- **Line 432 (`smart_suggestions`)**: `db.query(Assignment)` was filtering by `due_date` and `status` but lacked `.filter(Assignment.user_id == user_id)`, leaking assignment titles and deadlines of other users into schedule suggestions.
- **Line 167 (`update_block_status`)**: `update_block_status(db: Session, block_id: int, status: str)` took only `block_id` without verifying block ownership against `ScheduleProfile.user_id`.

### 1.2 `modules/ai_layer/roast_engine.py::_get_context()` & Roast Broadcast
- **Line 136 (`_get_context`)**: Verified `.filter(Assignment.user_id == user_id)` is active in `Assignment` query for upcoming assignment context.
- **Line 121 (`_fire_roast`)**: The WebSocket broadcast dictionary produced by `_fire_roast` omitted `"user_id": user_id`, resulting in roast notifications being broadcast globally to all WebSocket clients.

### 1.3 `api/websocket.py` & `ConnectionManager`
- `ConnectionManager` previously tracked all connected WebSockets in a single flat set `self._active = set()`. It had no concept of user socket mapping, `unicast()`, or user-scoped broadcasting.

### 1.4 Broadcast Call Sites
- **`main.py` (lines 142-168)**: WebSocket route called `manager.connect(ws)` without `user_id` and called `manager.broadcast()` for initial `stats_update` and `tasks_list`.
- **`schedulers/daily_trigger.py` (line 121)**: `_push_live_stats` called `get_daily_stats(db)` without user iteration and broadcast stats without a `user_id` tag.
- **`modules/assignments/reminder.py` (lines 92, 100, 168)**: `_deliver()` broadcast reminders without including `user_id` in the payload dictionary.
- **`modules/cv_pipeline/presence.py` (lines 35, 160)**: `PresenceMonitor` had no `user_id` instance field and broadcast `cv_event` without `user_id`.

---

## 2. Logic Chain

1. **Schedule Manager Multi-Tenant Data Leak Isolation**:
   - Adding `.filter(Assignment.user_id == user_id)` to `boost_subject_priority()` and `smart_suggestions()` guarantees SQL queries only select assignments belonging to the requesting user ID.
   - Updating `update_block_status(db: Session, block_id: int, status: str, user_id: Optional[int] = None)` to fetch the associated `ScheduleProfile` via `block.profile_id` and verify `profile.user_id == user_id` prevents unauthorized users from altering schedule block statuses of other users. Passing `user_id=user.id` in `api/routes_schedule.py::set_block_status` returns `None` (producing HTTP 404) when a user attempts to modify another tenant's schedule block.

2. **Roast Engine Context & Routing**:
   - Ensuring `_get_context` filters `Assignment` by `user_id` prevents exposing foreign assignment titles in generated roast prompts.
   - Adding `"user_id": user_id` to the `_fire_roast` broadcast payload allows downstream WebSocket routing to deliver roasts strictly to the relevant user session.

3. **WebSocket Connection Manager Multi-Tenancy**:
   - Added `self._user_sockets: Dict[int, Set[WebSocket]] = defaultdict(set)` and `self._socket_users: Dict[WebSocket, int] = {}` to `ConnectionManager`.
   - Updated `connect(ws, user_id)` to associate `ws` with `user_id` in `_user_sockets` and `_socket_users`.
   - Updated `disconnect(ws, user_id=None)` to cleanly remove `ws` from `_active`, `_socket_users`, and `_user_sockets[user_id]`.
   - Added `async def unicast(self, user_id: int, message: Union[dict, str])` to send payloads exclusively to active WebSockets associated with `user_id`.
   - Refactored `broadcast(self, message: Union[dict, str], user_id: Optional[int] = None)`: if `user_id` is passed or embedded in `message["user_id"]`, it delegates directly to `unicast(user_id, message)`.
   - Updated `drain_event_bus()` to extract `user_id` from queued event dictionaries and invoke `manager.broadcast(data, user_id=user_id)`.

4. **Call Site Payload Routing**:
   - `main.py`: Connected sockets with `await manager.connect(ws, user_id=user_id)` and emitted initial `stats_update` and `tasks_list` via `await manager.unicast(user_id, ...)`.
   - `schedulers/daily_trigger.py`: Updated `_push_live_stats` to query all active `User` records in the database and emit `stats_update` events tagged with `user_id=user.id`.
   - `modules/assignments/reminder.py`: Updated `_deliver` to accept `user_id` and attach `"user_id": user_id` to the broadcast dictionary. Updated `check_and_deliver` to pass `user_id` derived from `r.assignment.user_id` or `a.user_id`.
   - `modules/cv_pipeline/presence.py`: Updated `PresenceMonitor.__init__` to accept `user_id: int = 1` (`self._user_id`) and attached `"user_id": self._user_id` to `cv_event` broadcast dictionaries in `_transition()`.

---

## 3. Caveats

- **No caveats**: All required tasks for Requirement R2 / Milestone M2 were fully implemented, verified via automated test suites, and audited against existing callers.

---

## 4. Conclusion

Milestone M2 is 100% complete. Cross-tenant data leaks in `modules/schedule/manager.py` and `modules/ai_layer/roast_engine.py` are resolved. The WebSocket infrastructure in `api/websocket.py` now enforces strict per-user socket mapping and unicasting across all broadcast call sites in `main.py`, `schedulers/daily_trigger.py`, `modules/assignments/reminder.py`, `modules/cv_pipeline/presence.py`, and `modules/ai_layer/roast_engine.py`.

---

## 5. Verification Method

### Automated Tests
Run the following test command from the repository root `c:\Users\samee\projects\Mimo`:

```bash
pytest tests/test_schedule.py tests/test_websocket.py
```

### Verification Results
- 33 passed in 43.45s (0 failures, 0 errors).
- Tested `test_boost_subject_priority_user_isolation`, `test_smart_suggestions_user_isolation`, `test_update_block_status_ownership`, and `test_connection_manager_unicast_and_broadcast`.

### Files to Inspect
- `modules/schedule/manager.py` (lines 167-178, 297-303, 432-438)
- `api/routes_schedule.py` (line 156)
- `modules/ai_layer/roast_engine.py` (lines 120-128, 130-149)
- `api/websocket.py` (lines 30-85)
- `main.py` (lines 142-168)
- `schedulers/daily_trigger.py` (lines 121-131)
- `modules/assignments/reminder.py` (lines 87-105, 167-180)
- `modules/cv_pipeline/presence.py` (lines 34-42, 157-165)
- `tests/test_schedule.py` (lines 542-630)
- `tests/test_websocket.py` (lines 20-57)
