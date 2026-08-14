## 2026-08-13T03:42:59Z
You are Worker M1 Fix (teamwork_preview_worker).
Your working directory is: c:\Users\samee\projects\Mimo\.agents\worker_m1_fix
Original user request: c:\Users\samee\projects\Mimo\.agents\ORIGINAL_REQUEST.md
Challenger M1_1 Handoff: c:\Users\samee\projects\Mimo\.agents\challenger_m1_1\handoff.md

Your task (Milestone M1 — Iteration 2):
Fix the `DetachedInstanceError` in `modules/voice/intent_router.py::_handle_what_to_study()` fallback path.

Root cause:
In `_handle_what_to_study()`, the fallback path calls `assignments = get_upcoming(db, user_id=self._user_id, days=5)` inside `with get_db_ctx() as db:`. After exiting the `with` block, accessing properties on `assignments` (e.g. `assignment.subject`, `assignment.due_date`, `assignment.title`) causes SQLAlchemy `DetachedInstanceError`.

Fix requirement:
Format the output text or extract all required attribute strings inside the `with get_db_ctx() as db:` block before the session closes, or eagerly load the fields.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Run `pytest` (including `tests/test_m1_adversarial.py`) to verify the fix. Write your report to `c:\Users\samee\projects\Mimo\.agents\worker_m1_fix\handoff.md` and notify orchestrator.
