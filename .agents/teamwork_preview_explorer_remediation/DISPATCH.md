## 2026-08-06T16:52:28Z
You are remediation_explorer (teamwork_preview_explorer).
Your working directory is: c:\Users\samee\projects\Mimo\.agents\teamwork_preview_explorer_remediation

MANDATORY AUDIT EVIDENCE & SPECIFICATION FILES TO READ FIRST:
- c:\Users\samee\projects\Mimo\.agents\teamwork_preview_auditor_m5_1\handoff.md
- c:\Users\samee\projects\Mimo\.agents\teamwork_preview_challenger_m5_1\handoff.md
- c:\Users\samee\projects\Mimo\.agents\orchestrator\GATE_STATUS.md
- c:\Users\samee\projects\Mimo\.agents\ORIGINAL_REQUEST.md
- c:\Users\samee\projects\Mimo\.agents\orchestrator\PROJECT.md

OBJECTIVE:
Formulate an exact, step-by-step remediation plan (`remediation_plan.md`) to resolve the Forensic Auditor's INTEGRITY VIOLATION (modified Python backend files) and Challenger 1's REQUEST_CHANGES (7 JS engine defects in `static/dashboard.html`).

TASKS:
1. Review the Auditor's evidence report in `teamwork_preview_auditor_m5_1/handoff.md`. Formulate git commands for the worker to execute (`git checkout HEAD -- .`, `git clean -fd db/migrations/` etc.) so that all modified/untracked Python files are reverted and `git status --short` shows ONLY changes in `static/`.
2. Review Challenger 1's evidence report in `teamwork_preview_challenger_m5_1/handoff.md`. Formulate exact code edits for `static/dashboard.html` to fix:
   - Issue 1: Add 25-second WebSocket ping heartbeat loop in `connectWebSocket()`.
   - Issue 2: Fix Top Apps keys in `renderTopApps()` to read `data.top_productive` and `data.top_distracting` returned by `GET /screen/breakdown`.
   - Issue 3: Fix AI Recommendations rendering in `renderStudyRecs()` to check `r.recommendation` (and `r.priority`).
   - Issue 4: Fix Quick-Add NLP submission and fallback `POST /assignments/` payload to include `due_date: new Date().toISOString().split('T')[0]`.
   - Issue 5: Fix `markDone()` single-quote escaping in `renderAssignments()` using `esc(title).replace(/'/g, "\\'")` or data attributes to prevent JS syntax errors on titles containing apostrophes.
   - Issue 6: Fix assignment urgency date string comparison for ISO datetimes (`item.due_date.split('T')[0] === todayStr`).
   - Issue 7: Fix Study Plan field names in `renderStudyPlan()` to read `item.start_time`, `item.end_time`, `item.duration_min`, and `item.reason`.
3. Write `remediation_plan.md` and standard `handoff.md` in your working directory.

COMPLETION CRITERIA:
- `remediation_plan.md` and `handoff.md` written in working directory.
- Send completion message to orchestrator when finished.
