# Handoff Report — Challenger M1_1 (Adversarial Verification of Milestone M1)

## Verdict: REJECT

---

## 1. Observation

Adversarial testing was executed using `tests/test_m1_adversarial.py` (12 comprehensive edge-case and isolation tests).

### Key Empirical Findings:

1. **`modules/voice/intent_router.py::_handle_what_to_study()` — CRASH IN FALLBACK PATH**:
   - When `StudyAdvisor.get_next_to_study()` raises an exception or fails, control passes to the `except Exception:` fallback block:
     ```python
     # modules/voice/intent_router.py:196-203
     with get_db_ctx() as db:
         upcoming = get_upcoming(db, user_id=self._user_id, days=5)
     if not upcoming:
         msg = "No assignments due soon. Review your weakest subject or get ahead on readings."
     else:
         most_urgent = upcoming[0]
         msg = f"Your most urgent assignment is '{most_urgent.title}', due {most_urgent.due_date}. Start with that."
     ```
   - Running `pytest tests/test_m1_adversarial.py -k "test_handle_what_to_study_advisor_exception_fallback"` produces the following verbatim error trace:
     ```
     E   sqlalchemy.orm.exc.DetachedInstanceError: Instance <Assignment at 0x1d3de4f2490> is not bound to a Session; attribute refresh operation cannot proceed
     ```

2. **`modules/ai_layer/roast_engine.py::_save_roast()` — VERIFIED SAFE**:
   - Verified that `_save_roast(trigger, message, user_id)` persists `RoastLog` records with the given `user_id`.
   - Missing `user_id` parameter correctly defaults to `user_id=1`.
   - Passing `user_id=None` or non-existent `user_id` triggers DB exceptions, which are safely caught by `_save_roast`'s `try...except Exception` block and logged as `Roast save error`, preventing python process crashes.
   - Calling interfaces `trigger_roast()`, `on_window_change()`, and `on_cv_event()` accurately pass `user_id` down to `_get_context()` and `_save_roast()`.

3. **`api/routes_sync.py::push_sync()` and `pull_sync()` — VERIFIED SAFE**:
   - `push_sync()` and `pull_sync()` both enforce authentication (return `401 Unauthorized` without bearer JWT).
   - `push_sync()` uses correct column names (`productive_time_s`, `distracted_time_s`, `neutral_time_s`, `desk_time_s`), accumulates mobile usage cleanly, and falls back gracefully to `date.today()` if passed an unparseable date string.
   - Multi-tenant isolation verified: `push_sync()` and `pull_sync()` strictly scope queries and mutations to `user.id`.

---

## 2. Logic Chain

1. In `intent_router.py`, the fallback block inside `_handle_what_to_study()` executes `with get_db_ctx() as db: upcoming = get_upcoming(...)`.
2. The context manager `get_db_ctx()` yields the session `db` and calls `db.close()` when exiting the `with` block.
3. `upcoming[0]` is an ORM `Assignment` instance whose session reference is invalidated when `db.close()` executes.
4. Outside the `with` block, the code attempts to read `most_urgent.title` and `most_urgent.due_date`. Because the session is closed and attributes are expired, SQLAlchemy attempts an automatic attribute reload, which throws `sqlalchemy.orm.exc.DetachedInstanceError`.
5. Consequently, any operational failure of `StudyAdvisor` results in an unhandled exception crash rather than delivering fallback study guidance.

---

## 3. Caveats

- `_save_roast()` silently swallows DB insert failures via `try...except Exception: log.error(...)`. While this prevents crashes when invalid user IDs are supplied, roast logs are silently lost.
- `push_sync()` falls back to `date.today()` on malformed date strings, which avoids HTTP 500 errors but may log usage on the wrong day if a client sends invalid date formats.

---

## 4. Conclusion

Explicit Verdict: **REJECT**

While `_save_roast()`, `push_sync()`, and `pull_sync()` meet safety and data integrity criteria, `modules/voice/intent_router.py::_handle_what_to_study()` contains an unhandled `DetachedInstanceError` crash in its fallback path. Worker M1 must fix this by extracting primitive attribute values (title, due_date) inside the session context block before session closure.

---

## 5. Verification Method

Run the adversarial test suite from workspace root `c:\Users\samee\projects\Mimo`:

```powershell
pytest tests/test_m1_adversarial.py
```

To isolate the specific fallback crash bug:

```powershell
pytest tests/test_m1_adversarial.py -k "test_handle_what_to_study_advisor_exception_fallback" -v
```

Expected result: 1 test failure (`DetachedInstanceError` in `_handle_what_to_study`).
