# Handoff Report — Explorer 1 (Investigation of R1, R2, R4, R6)

## 1. Observation

### 1.1 `modules/ai_layer/roast_engine.py`
- **Line 150-158 (`_save_roast`)**:
  ```python
  def _save_roast(self, trigger: str, message: str):
      try:
          with get_db_ctx() as db:
              db.add(RoastLog(
                  trigger      = trigger,
                  message      = message,
                  session_date = date.today(),
              ))
  ```
  `RoastLog.user_id` in `db/models.py:164` is defined as `Column(Integer, ForeignKey("users.id"), nullable=False, index=True)`. `_save_roast` fails to pass `user_id`, causing a database NOT NULL constraint violation crash.
- **Line 127-145 (`_get_context`)**:
  ```python
  upcoming = (
      db.query(Assignment)
      .filter(Assignment.status != "done")
      .filter(Assignment.due_date >= date.today())
      .order_by(Assignment.due_date)
      .limit(3)
      .all()
  )
  ```
  `Assignment` query does not filter by `user_id`, causing assignment context from other users to be included in roasts.
- **Line 44-48, 80-87 (`Cooldown & state tracking`)**:
  ```python
  self._last_roast_time: float = 0.0
  self._distraction_start: Optional[float] = None
  self._absence_start: Optional[float] = None
  self._current_distracting_app: str = ""
  ```
  Tracking state is stored as process-wide instance attributes rather than per-user mappings (`dict[int, dict]`).

### 1.2 `modules/voice/intent_router.py`
- **Line 186-203 (`_handle_what_to_study`)**:
  ```python
  with get_db_ctx() as db:
      advisor = StudyAdvisor(db)
      msg     = advisor.get_next_to_study() # MISSING positional arg user_id!
  ```
  `StudyAdvisor.get_next_to_study(self, user_id: int)` in `modules/ai_layer/study_advisor.py:82` requires `user_id: int`. Calling without `user_id` raises `TypeError`.
  In the `except Exception:` fallback block:
  ```python
  with get_db_ctx() as db:
      upcoming = get_upcoming(db, days=5) # MISSING user_id!
  ```
  `get_upcoming` in `modules/assignments/manager.py:53` has signature `(db: Session, user_id: int, days: int = 7)`. Passing `days=5` as the 2nd positional parameter sets `user_id = 5` and `days = 7` (default).

### 1.3 `modules/schedule/manager.py`
- **Line 292-298 (`boost_subject_priority`)**:
  ```python
  urgent_assignments = (
      db.query(Assignment)
      .filter(Assignment.due_date >= target)
      .filter(Assignment.due_date <= deadline)
      .filter(Assignment.status != "done")
      .all()
  )
  ```
  Missing `.filter(Assignment.user_id == user_id)`.
- **Line 426-432 (`smart_suggestions`)**:
  ```python
  urgent = (
      db.query(Assignment)
      .filter(Assignment.due_date >= target)
      .filter(Assignment.due_date <= deadline)
      .filter(Assignment.status != "done")
      .all()
  )
  ```
  Missing `.filter(Assignment.user_id == user_id)`.
- **Line 167-176 (`update_block_status`)**:
  ```python
  def update_block_status(db: Session, block_id: int, status: str) -> Optional[ScheduleBlock]:
      if status not in VALID_STATUSES:
          raise ValueError(...)
      block = db.get(ScheduleBlock, block_id)
      if not block:
          return None
      block.status = status
      ...
  ```
  No `user_id` parameter or ownership verification; permits arbitrary users to mutate blocks belonging to other users.

### 1.4 `modules/cv_pipeline/presence.py`
- **Line 166-175 (`_log_event`)**:
  ```python
  def _log_event(self, event_type: str, ts: datetime):
      try:
          with get_db_ctx() as db:
              from db.models import User
              user = db.query(User).first()
              if not user:
                  return
              db.add(CVEvent(user_id=user.id, ...))
  ```
  Indiscriminately queries the first user in the DB (`db.query(User).first()`) instead of logging events for a specific `user_id`.

### 1.5 `modules/behavior_engine/pattern_detector.py` & `modules/cv_pipeline/focus_scorer.py`
- **`pattern_detector.py:15`**: Dead import `from typing import List, Optional` (`Optional` is unused).
- **`pattern_detector.py:68`**: Unused variable/computation: `worst_hour = min(hourly, key=hourly.get) if hourly else None`.
- **`focus_scorer.py:37`**: Unused variable/computation: `absent_count = sum(1 for e in events if e.event_type == "absent")`.

### 1.6 `desktop/autostart.py`
- **Line 184 (`_enable_macos`)**:
  `os.system(f"launchctl load -w '{_PLIST_PATH}' 2>/dev/null")`
- **Line 191 (`_disable_macos`)**:
  `os.system(f"launchctl unload '{_PLIST_PATH}' 2>/dev/null")`
  Uses shell string execution `os.system` instead of `subprocess.run`.

---

## 2. Logic Chain

1. **Roast Log Crash & Context Leak**:
   - `RoastLog.user_id` is defined as `nullable=False` in `db/models.py`. Omitting `user_id` when constructing `RoastLog` in `_save_roast` triggers a database integrity exception.
   - `_get_context` omits `Assignment.user_id == user_id`, causing roasts generated for User A to disclose pending assignment titles of User B.
   - `RoastEngine` maintains process-wide scalar attributes for cooldowns (`_last_roast_time`, `_distraction_start`, `_absence_start`), causing state pollution between concurrent users. Storing per-user state dictionaries (keyed by `user_id`) isolates multi-user tracking.

2. **Voice Intent Router Crashes**:
   - `StudyAdvisor.get_next_to_study(user_id: int)` expects `user_id`. `_handle_what_to_study` calls `advisor.get_next_to_study()` without arguments, throwing a `TypeError`.
   - In `_handle_what_to_study` exception fallback, `get_upcoming(db, days=5)` is invoked. Since `get_upcoming` expects `(db, user_id, days=7)`, positional argument 2 (`days=5`) binds to `user_id`, causing `user_id=5` to be queried instead of `self._user_id`.

3. **Schedule Cross-Tenant Leaks**:
   - `boost_subject_priority` and `smart_suggestions` query `Assignment` filtered by deadline and status, but omit `Assignment.user_id == user_id`. This leaks assignments of all users into target user's schedule boost logic and suggestion feed.
   - `update_block_status` fetches `ScheduleBlock` by `block_id` without filtering or verifying `ScheduleProfile.user_id == user_id`.

4. **CV Presence Single-User Assumption**:
   - `PresenceMonitor._log_event` fetches `db.query(User).first()`, assigning all computer vision events to user 1 regardless of who is using the app. Receiving or initializing `PresenceMonitor` with `user_id` allows inserting `CVEvent` under `self._user_id`.

5. **Behavior Engine & CV Pipeline Cleanup**:
   - `pattern_detector.py` imports `Optional` which is never used in type annotations, and computes `worst_hour` which is never referenced or returned.
   - `focus_scorer.py` computes `absent_count` on line 37 which is never referenced or returned.

6. **Desktop Autostart Subprocess Safety**:
   - `os.system` runs commands through the system shell with unescaped string formatting. Replacing `os.system` with `subprocess.run(["launchctl", ...], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)` guarantees safe, non-shell execution.

---

## 3. Caveats

- **API/Route Authentication**: Explorer 1 investigated backend modules and desktop scripts assigned under R1, R2, R4, R6. API route auth decorator additions (`routes_settings.py`, `routes_monitoring.py`, `routes_voice.py`) and WebSocket unicasting (`api/websocket.py`) belong to Explorer 2's domain as per task division.
- **Default `user_id=1`**: When functions like `on_window_change` or `on_cv_event` are called without explicit `user_id` from legacy single-user callers, defaulting `user_id=1` maintains full backwards compatibility.

---

## 4. Conclusion

All designated backend items under R1, R2, R4, and R6 contain clear, reproducible bugs with precise solutions:
1. `modules/ai_layer/roast_engine.py`: Pass `user_id` in `_save_roast`, add `user_id` filter in `_get_context`, and convert single-user tracking attributes into per-user dict structure.
2. `modules/voice/intent_router.py`: Pass `self._user_id` to `advisor.get_next_to_study(self._user_id)` and `get_upcoming(db, user_id=self._user_id, days=5)`.
3. `modules/schedule/manager.py`: Add `.filter(Assignment.user_id == user_id)` in `boost_subject_priority()` and `smart_suggestions()`, and add `user_id` checking to `update_block_status()`.
4. `modules/cv_pipeline/presence.py`: Store `self._user_id` in `PresenceMonitor` and use it in `_log_event()` instead of `db.query(User).first()`.
5. `modules/behavior_engine/pattern_detector.py` & `modules/cv_pipeline/focus_scorer.py`: Remove dead import `Optional`, unused `worst_hour` variable, and unused `absent_count` variable.
6. `desktop/autostart.py`: Replace `os.system` calls in `_enable_macos` and `_disable_macos` with `subprocess.run`.

---

## 5. Verification Method

- **Automated Tests**:
  Run `pytest tests/` in the project environment to verify no existing tests break.
- **Manual Verification Commands**:
  - `pytest tests/test_roast.py` (or corresponding roast engine test) to verify `_save_roast` and `_get_context` logic.
  - `pytest tests/test_voice.py` or test `IntentRouter.route("what should I study")` to verify `user_id` parameter passing.
  - `pytest tests/test_schedule.py` to verify schedule block ownership and filtering.
- **Files to Inspect**:
  - `modules/ai_layer/roast_engine.py`
  - `modules/voice/intent_router.py`
  - `modules/schedule/manager.py`
  - `modules/cv_pipeline/presence.py`
  - `modules/behavior_engine/pattern_detector.py`
  - `modules/cv_pipeline/focus_scorer.py`
  - `desktop/autostart.py`
