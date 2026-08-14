# Technical Findings & Handoff Report: Explorer 2 (API Routes, WebSockets, Route Auth, Schedulers)

## 1. Observation

### 1.1 `api/routes_sync.py`
- **`push_sync()` (lines 38-60)**:
  - Query: `stats_record = db.query(DailySummary).filter(DailySummary.date == payload.date).first()` does not filter by `user_id`.
  - Creation:
    ```python
    stats_record = DailySummary(
        date=payload.date,
        productive_s=payload.mobileProductiveMin * 60,
        distracting_s=payload.mobileDistractingMin * 60,
        neutral_s=payload.mobileNeutralMin * 60,
        desk_time_s=(payload.mobileProductiveMin + payload.mobileDistractingMin + payload.mobileNeutralMin) * 60,
    )
    ```
  - Column Mismatch: `db/models.py` (lines 74-77) defines `DailySummary` columns as `productive_time_s`, `distracted_time_s`, `neutral_time_s`, and requires `user_id` (`nullable=False`). `push_sync()` attempts to write `productive_s`, `distracting_s`, `neutral_s` without `user_id`.
- **`pull_sync()` (lines 62-98)**:
  - Line 78 calls `tasks = get_upcoming(db, days=7)`.
  - `modules/assignments/manager.py` (line 53) defines `get_upcoming(db: Session, user_id: int, days: int = 7)`. Calling `get_upcoming(db, days=7)` passes `days=7` as positional `user_id`, fetching assignments for `user_id=7`.
  - Neither `push_sync` nor `pull_sync` enforces authentication via `current_user = Depends(current_user)`.

### 1.2 `api/websocket.py` & Connection Management Architecture
- **`ConnectionManager` (`api/websocket.py`, lines 30-61)**:
  ```python
  class ConnectionManager:
      def __init__(self):
          self._active: Set[WebSocket] = set()
  ```
  - Tracks all clients in a single flat set `self._active`. No association exists between WebSocket connections and `user_id`.
- **Call Sites & Cross-Tenant Data Leaks**:
  - `main.py` (lines 142-160): Decodes JWT to get `user_id`, but then calls `manager.broadcast({"type": "stats_update", "stats": stats})` and `manager.broadcast({"type": "tasks_list", ...})`, sending user A's private data to ALL connected WebSockets.
  - `schedulers/daily_trigger.py` (lines 121-129): `_push_live_stats` calls `get_daily_stats(db)` (default `user_id=1`) and broadcasts stats to all connections.
  - `modules/assignments/reminder.py` (lines 174-180): `_deliver` broadcasts reminders to all connections without `user_id` routing.
  - `modules/cv_pipeline/presence.py` (lines 159-164): Broadcasts `cv_event` without `user_id` routing.
  - `modules/ai_layer/roast_engine.py` (lines 118-125): Broadcasts `roast` without `user_id` routing.

### 1.3 API Route Authentication (R3)
- **`api/routes_settings.py` (lines 30-113)**: Endpoints (`/settings`, `/settings/data`, `/settings/save`, `/settings/save-all`, `/settings/restart`, `/settings/openai-test`) lack authentication dependencies. Unauthenticated users can read/modify configuration and restart background services.
- **`api/routes_monitoring.py` (lines 17-95)**: Endpoints (`/monitoring/pause`, `/monitoring/resume`, `/monitoring/status`) lack authentication dependencies. Unauthenticated users can pause/resume system tracking.
- **`api/routes_voice.py` (lines 35-167)**: Endpoints (`/voice/command`, `/voice/speak`, `/voice/status`, `/voice/intents`) lack authentication dependencies. Unauthenticated users can trigger system voice commands and TTS messages.
- **Project Standard Auth**: `from api.routes_auth import current_user` (returns `User` model, raises HTTP 401 if token is missing or invalid).

### 1.4 `schedulers/daily_trigger.py`
- **`_run_eod()` (lines 98-105)**:
  ```python
  def _run_eod(speak_fn=None, broadcast_fn=None):
      log.info("Running scheduled EOD report...")
      try:
          from modules.ai_layer.daily_report import run_eod_report
          run_eod_report(speak_fn=speak_fn, broadcast_fn=broadcast_fn)
  ```
- **`run_eod_report()` (`modules/ai_layer/daily_report.py`, line 19)**:
  `def run_eod_report(user_id: int = 1, speak_fn: Optional[Callable] = None, broadcast_fn: Optional[Callable] = None)`
- Default parameter `user_id=1` is used because `_run_eod()` does not pass `user_id` or iterate over active users.

---

## 2. Logic Chain

1. **`api/routes_sync.py` Fixes**:
   - `push_sync` crashes with `TypeError` when creating `DailySummary` because `productive_s`, `distracting_s`, and `neutral_s` do not match `DailySummary` model fields (`productive_time_s`, `distracted_time_s`, `neutral_time_s`). Also, `user_id` is required by the `DailySummary` schema. Adding `current_user: User = Depends(current_user)` permits retrieving `current_user.id`, filtering `DailySummary` by `user_id` + `date`, and saving with correct field names.
   - `pull_sync` calling `get_upcoming(db, days=7)` maps `days=7` to `user_id`, executing SQL filter `WHERE user_id = 7`. Adding `current_user: User = Depends(current_user)` allows calling `get_daily_stats(db, user_id=current_user.id)` and `get_upcoming(db, user_id=current_user.id, days=7)`.

2. **`api/websocket.py` & Connection Management Architecture**:
   - `ConnectionManager` must maintain dual tracking:
     - `self._user_sockets: Dict[int, Set[WebSocket]] = defaultdict(set)`
     - `self._socket_users: Dict[WebSocket, int] = {}`
   - Method signatures:
     - `async def connect(self, ws: WebSocket, user_id: int)`: store `ws` in `self._active`, `self._user_sockets[user_id]`, and `self._socket_users[ws]`.
     - `def disconnect(self, ws: WebSocket)`: remove `ws` from `self._active`, lookup `user_id = self._socket_users.pop(ws, None)`, and remove `ws` from `self._user_sockets[user_id]`.
     - `async def unicast(self, user_id: int, data: dict)`: serialize `data` and send only to `self._user_sockets.get(user_id, set())`.
     - `async def broadcast(self, data: dict, user_id: Optional[int] = None)`: if `user_id` is supplied (or present in `data.get("user_id")`), delegate to `unicast(user_id, data)`; otherwise broadcast globally if no user context exists.
   - Call sites update plan:
     - `main.py`: `await manager.connect(ws, user_id)` on connection, and use `await manager.unicast(user_id, ...)` for initial `stats_update` and `tasks_list`.
     - `schedulers/daily_trigger.py`: `_push_live_stats` queries all active users and broadcasts user-scoped stats (`{"user_id": user.id, ...}`).
     - `modules/assignments/reminder.py`: `_deliver` includes `"user_id": assignment.user_id` in the broadcast payload.
     - `modules/cv_pipeline/presence.py`: `_transition` includes `"user_id": self._user_id` in the broadcast payload.
     - `modules/ai_layer/roast_engine.py`: `_fire_roast` includes `"user_id": self._user_id` in the broadcast payload.

3. **API Route Authentication (R3)**:
   - All endpoints in `routes_settings.py`, `routes_monitoring.py`, and `routes_voice.py` must enforce authentication using `user: User = Depends(current_user)`.
   - In `routes_voice.py::send_command`, update the `IntentRouter` initialization to pass `user_id=user.id`:
     `IntentRouter(speak_fn=..., broadcast_fn=..., user_id=user.id)`.

4. **`schedulers/daily_trigger.py` Nightly Reports (R4)**:
   - In `_run_eod()`: Open DB session, query all active users (`db.query(User).all()`), and loop:
     ```python
     for user in users:
         try:
             run_eod_report(user_id=user.id, speak_fn=speak_fn, broadcast_fn=broadcast_fn)
         except Exception as e:
             log.error(f"EOD report failed for user {user.id}: {e}")
     ```

---

## 3. Caveats

- **Static Page HTML Routes**: `GET /settings` returns `static/settings.html`. If the frontend serves static page templates unauthenticated before JavaScript fetches authenticated API endpoints, auth dependencies should be attached to individual data/action endpoints (`/settings/data`, `/settings/save`, `/settings/save-all`, `/settings/restart`, `/settings/openai-test`) or applied to static routes appropriately based on frontend flow.
- **Background Engine Singletons**: `PresenceMonitor` and `RoastEngine` in `schedulers/background_tasks.py` must store and use `user_id` per instance when monitoring specific user sessions.

---

## 4. Conclusion

All requirements for R1 (sync crash fixes), R2 (WebSocket user isolation), R3 (route authentication), and R4 (EOD report multi-user iteration) are precisely analyzed with exact file locations and code fixes identified:
- Fix `push_sync` & `pull_sync` parameters and `DailySummary` column names in `api/routes_sync.py`.
- Refactor `ConnectionManager` in `api/websocket.py` to support `unicast(user_id, data)` and user-scoped `broadcast`, updating all event broadcast sites (`main.py`, `daily_trigger.py`, `reminder.py`, `presence.py`, `roast_engine.py`).
- Enforce `Depends(current_user)` across `api/routes_settings.py`, `api/routes_monitoring.py`, and `api/routes_voice.py`.
- Refactor `_run_eod()` in `schedulers/daily_trigger.py` to iterate over all active users in the database and pass `user_id` to `run_eod_report()`.

---

## 5. Verification Method

1. **Automated Test Suite**:
   - Run `pytest tests/` to verify test execution under 30 seconds.
2. **Specific Route Auth Verification**:
   - Issue unauthenticated requests to `/settings/data`, `/monitoring/status`, and `/voice/command` and confirm `HTTP 401 Unauthorized`.
3. **Sync Endpoint Verification**:
   - Test `POST /sync/push` with mobile screen time payload using valid auth token and verify correct insertion in `DailySummary` table with column names `productive_time_s`, `distracted_time_s`, `neutral_time_s`.
   - Test `GET /sync/pull` with valid auth token and verify assignments returned correspond only to the authenticated user.
4. **WebSocket Isolation Verification**:
   - Connect two distinct WebSocket clients with different user JWT tokens; verify `stats_update` and `tasks_list` emitted to user A are not received by user B.
5. **Nightly EOD Verification**:
   - Execute `_run_eod()` with multiple users in DB and verify `DailySummary` records and reports are generated for every user ID.
