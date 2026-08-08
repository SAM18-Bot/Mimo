## 2026-08-06T16:53:26Z
You are worker_remediation (teamwork_preview_worker).
Your working directory is: c:\Users\samee\projects\Mimo\.agents\teamwork_preview_worker_remediation

MANDATORY SPECIFICATION FILES TO READ FIRST:
- c:\Users\samee\projects\Mimo\.agents\ORIGINAL_REQUEST.md
- c:\Users\samee\projects\Mimo\.agents\orchestrator\PROJECT.md
- c:\Users\samee\projects\Mimo\.agents\teamwork_preview_explorer_remediation\remediation_plan.md
- c:\Users\samee\projects\Mimo\.agents\teamwork_preview_auditor_m5_1\handoff.md
- c:\Users\samee\projects\Mimo\.agents\teamwork_preview_challenger_m5_1\handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

WRITE OWNERSHIP BOUNDARY:
You exclusively modify: `static/dashboard.html`.
Revert all backend Python files via git so `git status --short` shows ONLY `static/dashboard.html` modified.

TASKS:
1. Revert all modified Python backend files and untracked Alembic migration script by running:
   `git checkout HEAD -- api/routes_auth.py api/routes_screen.py api/routes_settings.py db/models.py modules/ai_layer/daily_report.py modules/assignments/parser.py requirements.txt`
   `git clean -f db/migrations/versions/004_add_user_id_columns.py`
   Run `git status --short` to confirm ONLY `static/dashboard.html` is modified.
2. Modify `static/dashboard.html` to apply all 7 JS engine fixes specified in `remediation_plan.md`:
   - Fix 1: 25-second WebSocket ping heartbeat loop in `connectWebSocket()`.
   - Fix 2: Top Apps keys in `renderTopApps()` reading `data.top_productive` and `data.top_distracting`.
   - Fix 3: AI Recommendations rendering in `renderStudyRecs()` reading `r.recommendation`.
   - Fix 4: Quick-Add fallback `POST /assignments/` payload including `due_date`.
   - Fix 5: `markDone()` single-quote escaping in `renderAssignments()`.
   - Fix 6: Assignment urgency date comparison handling ISO datetime strings (`item.due_date.split('T')[0] === todayStr`).
   - Fix 7: Study Plan field mappings in `renderStudyPlan()` reading `start_time`/`end_time`/`duration_min`/`reason`.
3. Validate HTML syntax balancing, run Node.js JS syntax check (`node --check`), and run `pytest` to confirm all backend tests pass.
4. Write standard 5-component `handoff.md` in your working directory and report completion.

COMPLETION CRITERIA:
- `git status --short` shows zero Python modifications.
- All 7 JS engine fixes implemented in `static/dashboard.html`.
- `handoff.md` written in working directory.
- Send completion message to orchestrator when finished.
