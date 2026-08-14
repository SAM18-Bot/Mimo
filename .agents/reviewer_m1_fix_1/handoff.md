# Review Handoff Report — Reviewer M1 Fix 1

## Review Summary

**Verdict**: `APPROVE`

---

## 1. Observation

- **Target File**: `modules/voice/intent_router.py`
- **Prior Error**:
  Running `pytest tests/test_m1_adversarial.py -k "test_handle_what_to_study_advisor_exception_fallback"` previously failed with:
  ```
  sqlalchemy.orm.exc.DetachedInstanceError: Instance <Assignment at ...> is not bound to a Session; attribute refresh operation cannot proceed
  ```
- **Code Inspection of Fix**:
  In `modules/voice/intent_router.py::_handle_what_to_study()` (lines 198-204):
  ```python
  with get_db_ctx() as db:
      upcoming = get_upcoming(db, user_id=self._user_id, days=5)
      if not upcoming:
          msg = "No assignments due soon. Review your weakest subject or get ahead on readings."
      else:
          most_urgent = upcoming[0]
          msg = f"Your most urgent assignment is '{most_urgent.title}', due {most_urgent.due_date}. Start with that."
  ```
  Attributes `most_urgent.title` and `most_urgent.due_date` are evaluated inside `with get_db_ctx() as db:` before the SQLAlchemy session is closed.
- **Related Handlers Checked**:
  - `_handle_add_assignment()`: Captures `a_id, a_title, a_subject, a_due, a_priority, a_status` within `with get_db_ctx() as db:` (lines 93-95).
  - `_handle_show_tasks()`: Builds `task_list` dictionary list within `with get_db_ctx() as db:` (lines 115-119).
  - `_handle_mark_done()`: Extracts `a_title = a.title` within `with get_db_ctx() as db:` (line 158).
- **Test Executions**:
  1. `pytest tests/test_m1_adversarial.py` -> **12 passed in 37.16s**
  2. `pytest` (full test suite) -> **337 passed, 5 skipped in 356.60s (0:05:56)**

---

## 2. Logic Chain

1. In SQLAlchemy ORM, accessing model attributes after `db.close()` or outside session context attempts to refresh detached model state, which raises `sqlalchemy.orm.exc.DetachedInstanceError`.
2. In `_handle_what_to_study()`, the fallback block handles `StudyAdvisor` exceptions by calling `get_upcoming()`.
3. By scoping both `upcoming = get_upcoming(...)` and `msg = f"Your most urgent assignment is '{most_urgent.title}', due {most_urgent.due_date}..."` inside `with get_db_ctx() as db:`, attribute access for `title` and `due_date` occurs while the session is alive.
4. Once constructed, `msg` is a plain string. Subsequent calls `self._speak(msg)` and `self._broadcast(...)` receive string primitives and do not touch ORM objects after session closure.
5. All related voice intent handlers follow the same pattern of extracting primitive strings/ints/dicts inside their respective DB session blocks before session closure.

---

## 3. Caveats

No caveats.

---

## 4. Conclusion

**Verdict**: `APPROVE`

The fix in `modules/voice/intent_router.py::_handle_what_to_study()` and related handlers correctly extracts model attributes within active database session contexts, eliminating `DetachedInstanceError`. All unit and adversarial tests pass without regression.

---

## 5. Verification Method

To independently verify:

1. Run adversarial test suite:
   ```powershell
   pytest tests/test_m1_adversarial.py
   ```
   Expected result: 12 passed.

2. Run full test suite:
   ```powershell
   pytest
   ```
   Expected result: 337 passed, 5 skipped in ~6 minutes.

3. Inspect `modules/voice/intent_router.py`:
   Confirm that all ORM attribute accesses in `_handle_what_to_study()`, `_handle_add_assignment()`, `_handle_show_tasks()`, and `_handle_mark_done()` occur inside `with get_db_ctx() as db:` context blocks.

---

## Verified Claims

- `_handle_what_to_study()` fallback path attribute extraction within DB session context prevents `DetachedInstanceError` → verified via code inspection and `pytest tests/test_m1_adversarial.py` → **PASS**
- Related handlers (`_handle_add_assignment`, `_handle_show_tasks`, `_handle_mark_done`) extract primitive values within DB session context → verified via code inspection → **PASS**
- Adversarial test suite runs and passes cleanly → verified via `pytest tests/test_m1_adversarial.py` (12 passed) → **PASS**
- Full test suite runs and passes cleanly → verified via `pytest` (337 passed, 5 skipped) → **PASS**

---

## Integrity Assessment

- Hardcoded test outputs in source code: **None**
- Facade implementations / shortcuts: **None**
- Bypassed logic or self-certifying violations: **None**
