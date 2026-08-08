## 2026-08-06T03:13:04Z
You are m1_explorer_3 (teamwork_preview_explorer).
Your working directory is: c:\Users\samee\projects\Mimo\.agents\teamwork_preview_explorer_m1_3

MANDATORY SPECIFICATION FILES TO READ FIRST:
- c:\Users\samee\projects\Mimo\.agents\ORIGINAL_REQUEST.md
- c:\Users\samee\projects\Mimo\.agents\orchestrator\PROJECT.md
- c:\Users\samee\projects\Mimo\.agents\teamwork_preview_explorer_survey_1\survey_frontend.md
- c:\Users\samee\projects\Mimo\.agents\teamwork_preview_explorer_survey_2\survey_backend_api.md
- c:\Users\samee\projects\Mimo\.agents\teamwork_preview_explorer_survey_3\survey_design_spec.md

OBJECTIVE:
Formulate the exact HTML structure, CSS rules, and JS rendering code for Milestone 1 Feature 3: App Usage Breakdown Doughnut Chart (showing productive/distracting/neutral screen time distribution from `/screen/breakdown`).

TASKS:
1. Analyze `GET /screen/breakdown` API schema (`productive_min`, `distracting_min`, `neutral_min`, `total_min`, `top_productive`, `top_distracting`).
2. Design a modern Chart.js Doughnut chart component with central total hours readout, interactive legend pills, and top apps list.
3. Provide code to load Chart.js via CDN (`https://cdn.jsdelivr.net/npm/chart.js`) and wire `GET /screen/breakdown` API data.
4. Produce a detailed implementation guide and code snippets in `c:\Users\samee\projects\Mimo\.agents\teamwork_preview_explorer_m1_3\plan_doughnut_chart.md` and standard `handoff.md`.

COMPLETION CRITERIA:
- `plan_doughnut_chart.md` and `handoff.md` written in working directory.
- Send completion message to orchestrator when done.
