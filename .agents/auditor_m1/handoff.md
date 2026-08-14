# Forensic Audit Report — Milestone M1

**Work Product**: Milestone M1 (Fix Confirmed Crashes)
**Profile**: General Project
**Integrity Mode**: Development
**Verdict**: INTEGRITY VIOLATION

---

## 1. Observation

Empirical execution of the full test suite (`pytest`) on Milestone M1 code resulted in **exit code 1** with 5 test failures:

```
=========================== short test summary info ===========================
FAILED tests/test_empirical_m1_stress.py::test_roast_engine_creation_and_multiuser
FAILED tests/test_m1_adversarial.py::test_save_roast_valid_user_id - assert None is not None
FAILED tests/test_m1_adversarial.py::test_save_roast_missing_user_id_defaults - assert None is not None
FAILED tests/test_m1_adversarial.py::test_roast_engine_fire_roast_user_id_propagation - assert None is not None
FAILED tests/test_m1_adversarial.py::test_handle_what_to_study_advisor_exception_fallback - AssertionError: assert 'Fallback Urgent Task' in 'No assignments due soon...'
====== 5 failed, 332 passed, 5 skipped, 2 warnings in 332.02s (0:05:32) =======
```

### Forensic Root Cause Analysis:

1. **`RoastEngine._save_roast()` Silent Database Error Swallowing**:
   - `_save_roast` in `modules/ai_layer/roast_engine.py` (line 154) wraps database insertion in a broad `try...except Exception as e:` block:
     ```python
     def _save_roast(self, trigger: str, message: str, user_id: int = 1):
         try:
             with get_db_ctx() as db:
                 db.add(RoastLog(user_id=user_id, trigger=trigger, message=message, session_date=date.today()))
         except Exception as e:
             log.error(f"Roast save error: {e}")
     ```
   - When executed in multi-threaded runtime environments or under database session context management, `get_db_ctx()` encounters an exception:
     `Roast save error: SQLite objects created in a thread can only be used in that same thread...`
   - Because `_save_roast` catches `Exception` blindly, the failure is logged and silently swallowed without persisting the record to the database or alerting the caller.
   - Consequently, `RoastLog` records are not saved, causing `test_save_roast_valid_user_id`, `test_save_roast_missing_user_id_defaults`, `test_roast_engine_fire_roast_user_id_propagation`, and `test_roast_engine_creation_and_multiuser` to fail with `assert None is not None`.

2. **`IntentRouter._handle_what_to_study()` Fallback Task Retrieval Failure**:
   - In `modules/voice/intent_router.py` (line 193), when `StudyAdvisor` raises an exception, the fallback handler attempts `with get_db_ctx() as db: upcoming = get_upcoming(db, user_id=self._user_id, days=5)`.
   - Due to database thread/session context isolation issues, the fallback query fails to retrieve the user's pending assignments, returning `"No assignments due soon..."` instead of the user's urgent task. This causes `test_handle_what_to_study_advisor_exception_fallback` to fail.

---

## 2. Logic Chain

1. **Rule of Verification**: Per the Forensic Auditor protocol, all claims must be verified empirically, and a project whose test suite fails or does not execute cleanly is an automatic failure.
2. **Observation**: Executing `pytest` across the project results in 5 failing tests and exit code 1.
3. **Traceability**:
   - `RoastEngine._save_roast` catches all exceptions, turning runtime database persistence failures into silent log messages while returning success to callers.
   - Database operations fail to persist `RoastLog` entries under multi-threaded execution patterns.
   - `IntentRouter._handle_what_to_study` fails to return upcoming assignments during fallback execution.
4. **Conclusion**: The implementation suffers from silent error swallowing and multi-threaded database transaction failures, violating acceptance criterion R1 and test suite compliance.

---

## 3. Caveats

No caveats. Test failures and error logs were reproduced directly from the test runner.

---

## 4. Conclusion

The Milestone M1 work product receives a verdict of **INTEGRITY VIOLATION**. The test suite fails with 5 test failures (exit code 1) due to silent exception swallowing and broken database persistence in `RoastEngine` and `IntentRouter`.

---

## 5. Verification Method

To re-verify independently, run the full test suite from the workspace root:

```powershell
pytest
```

Expected result:
- Execution completes with 5 failures (`test_empirical_m1_stress.py`, `test_m1_adversarial.py`).
- Exit code 1.
