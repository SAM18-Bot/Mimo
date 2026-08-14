# Adversarial Verification Report — Challenger M1_2

## Verdict: REJECT

---

## 1. Observation

### Codebase and Fix Inspection
- **`modules/ai_layer/roast_engine.py`**:
  - Line 82: `def _fire_roast(self, trigger: str, app: str, minutes: int, user_id: int = 1):`
  - Line 154: `def _save_roast(self, trigger: str, message: str, user_id: int = 1):`
  - Line 157: `RoastLog(user_id=user_id, trigger=trigger, message=message, session_date=date.today())`
  - Observation: `RoastLog` model (`db/models.py:164`) requires non-nullable `user_id`. `_save_roast` accepts `user_id` and persists it cleanly.

- **`api/routes_sync.py::push_sync()`**:
  - Line 39: `@router.post("/push")`
  - Line 62: `DailySummary(user_id=user.id, date=summary_date, productive_time_s=..., distracted_time_s=..., neutral_time_s=..., desk_time_s=...)`
  - Observation: All column names match `DailySummary` model fields in `db/models.py:75-78`. `user.id` is explicitly assigned, date string is validated/coerced to `date` instance.

- **`api/routes_sync.py::pull_sync()`**:
  - Line 81: `@router.get("/pull", response_model=SyncPayload)`
  - Line 99: `tasks = get_upcoming(db, user_id=user.id, days=7)`
  - Observation: Authentication dependency `@Depends(current_user)` is present. `user_id=user.id` is passed.

- **`modules/voice/intent_router.py::_handle_what_to_study()` (CRITICAL FAILURE FOUND)**:
  - Lines 198–204:
    ```python
    with get_db_ctx() as db:
        upcoming = get_upcoming(db, user_id=self._user_id, days=5)
    if not upcoming:
        msg = "No assignments due soon. Review your weakest subject or get ahead on readings."
    else:
        most_urgent = upcoming[0]
        msg = f"Your most urgent assignment is '{most_urgent.title}', due {most_urgent.due_date}. Start with that."
    ```
  - Observation: When `StudyAdvisor` raises an exception (e.g. LLM failure or DB issue), execution enters the `except Exception:` fallback block. Inside the fallback block, `get_upcoming()` returns a list of ORM `Assignment` objects within `with get_db_ctx() as db:`. When the `with` block exits, `db.close()` is called. On line 204, accessing `most_urgent.title` and `most_urgent.due_date` on the detached ORM instance triggers a runtime crash: `sqlalchemy.orm.exc.DetachedInstanceError: Instance <Assignment> is not bound to a Session; attribute refresh operation cannot proceed`.

### Full Test Suite Execution Result
Command executed: `pytest`
Output verbatim:
```
FAILED tests/test_m1_adversarial.py::test_handle_what_to_study_advisor_exception_fallback
====== 1 failed, 336 passed, 5 skipped, 2 warnings in 354.99s (0:05:54) =======
```

Traceback:
```python
modules\voice\intent_router.py:192: in _handle_what_to_study
    with get_db_ctx() as db:
...
RuntimeError: Advisor error

During handling of the above exception, another exception occurred:
tests\test_m1_adversarial.py:156: in test_handle_what_to_study_advisor_exception_fallback
    router._handle_what_to_study()
modules\voice\intent_router.py:202: in _handle_what_to_study
    else:
..\..\AppData\Local\Programs\Python\Python311\Lib\site-packages\sqlalchemy\orm\attributes.py:566: in __get__
    return self.impl.get(state, dict_)
...
sqlalchemy.orm.exc.DetachedInstanceError: Instance <Assignment at 0x21b61987210> is not bound to a Session; attribute refresh operation cannot proceed
```

---

## 2. Logic Chain

1. **`RoastLog` and `push_sync`/`pull_sync` fixes**: Validated and working as claimed. Column mapping in `DailySummary` and parameter passing in `pull_sync` and `RoastEngine` execute correctly.
2. **`_handle_what_to_study` Fallback Defect**: In `modules/voice/intent_router.py`, the fallback path queries `get_upcoming()` inside `with get_db_ctx() as db:`. When `get_db_ctx()` exits, the SQLAlchemy session closes. Lines 203-204 read `most_urgent.title` and `most_urgent.due_date` outside of the session context.
3. **Runtime Crash**: Accessing attributes on the detached `Assignment` instance after session closure triggers `sqlalchemy.orm.exc.DetachedInstanceError`, crashing the intent handler whenever `StudyAdvisor` fails or raises an exception.
4. **Acceptance Criteria Failure**: Requirement R1 requires fixing crash scenarios in `_handle_what_to_study()`, and Acceptance Criteria mandates all test items pass in `pytest`. The test suite failed due to `DetachedInstanceError`.

---

## 3. Caveats

- `push_sync()`, `pull_sync()`, and `RoastEngine` fixes are structurally sound and verified.
- The single remaining issue in M1 is the session scoping in `modules/voice/intent_router.py::_handle_what_to_study()`, where attributes must be extracted inside the `with get_db_ctx() as db:` block before the session closes (matching the pattern used in `_handle_add_assignment`).

---

## 4. Conclusion

Milestone M1 cannot be approved because `_handle_what_to_study()` retains a confirmed runtime crash (`DetachedInstanceError`) on its exception fallback path, causing `pytest` test failures.

**Explicit Verdict**: **`REJECT`**

---

## 5. Verification Method & Required Remediation

### Remediation in `modules/voice/intent_router.py`
Extract `most_urgent.title` and `most_urgent.due_date` inside the `with get_db_ctx() as db:` block:
```python
        except Exception:
            # Fallback to simple assignment-based advice
            from modules.assignments.manager import get_upcoming
            with get_db_ctx() as db:
                upcoming = get_upcoming(db, user_id=self._user_id, days=5)
                if not upcoming:
                    msg = "No assignments due soon. Review your weakest subject or get ahead on readings."
                else:
                    most_urgent = upcoming[0]
                    urgent_title, urgent_due = most_urgent.title, most_urgent.due_date
                    msg = f"Your most urgent assignment is '{urgent_title}', due {urgent_due}. Start with that."
```

### Verification Command
Run the full test suite:
```powershell
pytest
```
Pass condition: 100% pass rate with 0 failures.
