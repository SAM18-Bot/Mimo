## 2026-08-06T22:17:13Z
You are recovery_explorer (teamwork_preview_explorer).
Your working directory is: c:\Users\samee\projects\Mimo\.agents\teamwork_preview_explorer_recovery

MANDATORY SPECIFICATION FILES TO READ FIRST:
- c:\Users\samee\projects\Mimo\.agents\ORIGINAL_REQUEST.md
- c:\Users\samee\projects\Mimo\.agents\orchestrator\PROJECT.md
- c:\Users\samee\projects\Mimo\.agents\teamwork_preview_explorer_survey_1\survey_frontend.md
- c:\Users\samee\projects\Mimo\.agents\teamwork_preview_explorer_survey_2\survey_backend_api.md
- c:\Users\samee\projects\Mimo\.agents\teamwork_preview_explorer_survey_3\survey_design_spec.md
- c:\Users\samee\projects\Mimo\.agents\teamwork_preview_explorer_m1_1\plan_gauge.md
- c:\Users\samee\projects\Mimo\.agents\teamwork_preview_explorer_m1_2\plan_weekly_chart.md
- c:\Users\samee\projects\Mimo\.agents\teamwork_preview_explorer_m1_3\plan_doughnut_chart.md

OBJECTIVE:
Inspect `static/dashboard.html` line-by-line to assess the current truncation state, and produce a complete, unified, production-ready reconstruction blueprint document (`blueprint.md`) covering all HTML, CSS, and JS logic needed to deliver the entire Mimo Dashboard Redesign (Milestones 1 to 4).

TASKS:
1. Read `static/dashboard.html` to catalog what CSS, HTML elements, and scripts currently exist and where truncation occurred.
2. Write a comprehensive single-file blueprint in `c:\Users\samee\projects\Mimo\.agents\teamwork_preview_explorer_recovery\blueprint.md` containing:
   - Full `<head>` with CDN imports (Tailwind CDN, Plus Jakarta Sans & JetBrains Mono, Lucide Icons, Chart.js).
   - Complete CSS design tokens (Dark mode default, Light mode `html[data-theme="light"]`, responsive breakpoints for 1920px, 1200px, 768px, 375px).
   - Full HTML layout:
     - Sidebar navigation (Dashboard `/`, Schedule `/schedule`, Settings `/settings`, active indicators, theme toggle, mobile toggle).
     - Header bar with Live WS indicator (pulse green/yellow/red), Focus timer quick status, Breadcrumbs.
     - Left column: Focus Score SVG Gauge (0-100 count-up + grade badge), Weekly 7-day bar chart + streak pill + tooltip, App usage doughnut chart + top apps list.
     - Center column: Currently active app hero card + category badge, Presence monitor, Activity timeline feed.
     - Right column: Assignments list with urgency badges (Overdue, Due Today, Due Soon) + mark-done, Quick-add NLP input, Focus Session Timer widget (Start, Pause, Reset, MM:SS), AI Study recommendations.
     - Full-width Roast Zone card feed.
     - Morning Q&A modal overlay (`#qa-overlay`).
     - Toast notification element (`#toast`).
   - Complete ES6 JavaScript logic:
     - Global state `S`, REST API fetch functions (`/reports/stats`, `/reports/history`, `/assignments/`, `/screen/breakdown`, `/study/recommendations`), WebSocket `/ws` connection manager with exponential backoff auto-reconnect, DOM renderers, Focus Timer countdown/countup controller, Quick-add NLP form handler, Mark-done API caller, Morning Q&A handler, and Dark/Light theme toggle switcher with `localStorage` persistence.
3. Write standard `handoff.md` in your working directory.

COMPLETION CRITERIA:
- `blueprint.md` and `handoff.md` created in `c:\Users\samee\projects\Mimo\.agents\teamwork_preview_explorer_recovery\`.
- Send completion message to orchestrator when finished.
