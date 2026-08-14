# Review Report — Reviewer M1 Fix 2 (DetachedInstanceError in intent_router.py)

**Verdict**: APPROVE

---

## 1. Observation

- **Reviewed Code**:
  `modules/voice/intent_router.py` (specifically `_handle_what_to_study()`, `_handle_add_assignment()`, `_handle_show_tasks()`, and `_handle_mark_done()`).
- **Target Issue**:
  `DetachedInstanceError` occurred when accessing SQLAlchemy model properties (e.g. `most_urgent.title`, `most_urgent.due_date`) on objects returned by `get_upcoming()` after the `with get_db_ctx() as db:` context block had closed the database session.
- **Applied Fix in `_handle_what_to_study()` (lines 198-204)**:
  ```python
  from modules.assignments.manager import get_upcoming
  with get_db_ctx() as db:
      upcoming = get_upcoming(db, user_id=self._user_id, days=5)
      if not upcoming:
          msg = "No assignments due soon. Review your weakest subject or get ahead on readings."
      else:
          most_urgent = upcoming[0]
          msg = f"Your most urgent assignment is '{most_urgent.title}', due {most_urgent.due_date}. Start with that."
  ```
- **Integrity Check**:
  - Code inspection confirmed no hardcoded test outputs, dummy facades, or self-certifying shortcuts.
  - Model attribute evaluation is done strictly within active session context blocks across all intent handlers.
- **Independent Test Execution Commands & Results**:
  1. `pytest tests/test_m1_adversarial.py tests/test_cv_voice.py`
     Result: `26 passed in 12.22s`
  2. `pytest` (entire test suite)
     Result: `342 passed in 100.97s`

---

## 2. Logic Chain

1. In `_handle_what_to_study()`, the fallback path executes when `StudyAdvisor.get_next_to_study()` raises an exception.
2. `get_upcoming(db, user_id=self._user_id, days=5)` queries the database and returns SQLAlchemy `Assignment` instances bound to `db`.
3. Prior to the fix, `upcoming = get_upcoming(db, ...)` was called inside `with get_db_ctx() as db:`, but the string formatting `most_urgent.title` and `most_urgent.due_date` occurred outside the `with` block after `db.close()` executed.
4. Accessing un-cached ORM attributes on closed sessions triggers lazy loading / session refresh, throwing `sqlalchemy.orm.exc.DetachedInstanceError`.
5. Moving `if not upcoming:`, `most_urgent = upcoming[0]`, and `msg = f"Your most urgent assignment is '{most_urgent.title}', due {most_urgent.due_date}. Start with that."` inside the `with get_db_ctx() as db:` block guarantees that attribute access occurs while the session is active.
6. The resulting `msg` variable is a primitive Python string, which can safely be passed to `self._speak(msg)` and `self._broadcast(...)` outside the database context.
7. Stress testing with `test_handle_what_to_study_advisor_exception_fallback` and `test_handle_what_to_study_multi_tenant_isolation` in `tests/test_m1_adversarial.py` verifies both error handling and multi-tenant user isolation.

---

## 3. Caveats

- **Minor Suggestion**: In `_handle_eod_report()` (lines 211-215), `run_eod_report(speak_fn=self._speak, broadcast_fn=self._broadcast)` is called without explicitly passing `user_id=self._user_id`. While `run_eod_report` defaults to `user_id=1`, passing `user_id=self._user_id` in future iterations will ensure full multi-tenant accuracy when triggering EOD reports via voice command. This does not cause a crash or `DetachedInstanceError`.

---

## 4. Conclusion

The fix for `DetachedInstanceError` in `modules/voice/intent_router.py` is correct, clean, and robust. All database session context managers safely scope ORM model attribute extractions before session closure. All 342 project tests pass cleanly.

**Final Verdict**: `APPROVE`

---

## 5. Verification Method

To independently verify this report, run the following commands from `c:\Users\samee\projects\Mimo`:

1. Run intent router and adversarial test suite:
   ```powershell
   pytest tests/test_m1_adversarial.py tests/test_cv_voice.py
   ```
   Expected output: `26 passed`

2. Run full project test suite:
   ```powershell
   pytest
   ```
   Expected output: `342 passed`
