# Handoff Report — Worker M1 Fix (Milestone M1 — Iteration 2)

## 1. Observation

- **Root Cause & Error Trace**:
  When running `pytest tests/test_m1_adversarial.py -k "test_handle_what_to_study_advisor_exception_fallback"`, the fallback path in `modules/voice/intent_router.py::_handle_what_to_study()` previously failed with:
  ```
  sqlalchemy.orm.exc.DetachedInstanceError: Instance <Assignment at 0x1e604780610> is not bound to a Session; attribute refresh operation cannot proceed
  ```
  This occurred because `most_urgent.title` and `most_urgent.due_date` were accessed outside the `with get_db_ctx() as db:` context block after `db.close()` had executed.

- **File Modified**:
  - `modules/voice/intent_router.py`:
    Lines 196-202 were updated so that checking `if not upcoming:` and accessing `most_urgent.title` and `most_urgent.due_date` occur inside `with get_db_ctx() as db:`, binding the computed message string `msg` before session closure.
    In addition, `_handle_show_tasks()` and `_handle_mark_done()` were updated to extract primitive values inside their respective `with get_db_ctx() as db:` blocks.

- **Test Execution Commands & Results**:
  1. `pytest tests/test_m1_adversarial.py`
     Result: `12 passed in 29.83s`
  2. `pytest` (full test suite)
     Result: `61 passed in 26.69s`

---

## 2. Logic Chain

1. In `_handle_what_to_study()`, `get_upcoming(db, user_id=self._user_id, days=5)` queries the database and returns a list of ORM `Assignment` models.
2. The context manager `get_db_ctx()` yields a SQLAlchemy session `db` and automatically closes the session upon exiting the `with` block.
3. Evaluating ORM attributes `most_urgent.title` and `most_urgent.due_date` after session exit triggers SQLAlchemy's attribute refresh mechanism, which raises `DetachedInstanceError` on closed sessions.
4. Moving the conditional check `if not upcoming:` and message string interpolation inside the `with get_db_ctx() as db:` block evaluates `most_urgent.title` and `most_urgent.due_date` while the session is active.
5. The constructed `msg` object is a plain Python string. Subsequent operations outside the `with` block (`self._speak(msg)` and `self._broadcast(...)`) process primitive strings safely without referencing ORM model instances.

---

## 3. Caveats

No caveats.

---

## 4. Conclusion

`DetachedInstanceError` in `modules/voice/intent_router.py::_handle_what_to_study()` fallback path is fully fixed and verified. All 61 tests across the entire test suite pass cleanly.

---

## 5. Verification Method

Run the following commands from workspace root `c:\Users\samee\projects\Mimo`:

1. Verify adversarial test suite:
   ```powershell
   pytest tests/test_m1_adversarial.py
   ```
   Expected result: 12 passed.

2. Verify full test suite:
   ```powershell
   pytest
   ```
   Expected result: 61 passed in under 30 seconds.
