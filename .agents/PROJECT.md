# Project: Mimo Dashboard UI Redesign

## Architecture
- Target File: `static/dashboard.html`
- Aesthetic: Linear / Vercel / Raycast Level — Dark & Light Theme System
- Tech Stack: Pure Static HTML5 / Modern CSS3 (CSS Custom Properties) / ES6+ JavaScript.
- Libraries loaded via CDN: Tailwind CSS CDN, Plus Jakarta Sans & JetBrains Mono Fonts, Lucide Icons, Chart.js.
- Backend APIs: FastAPI REST Endpoints & WebSocket `/ws`.

## Feature Inventory
| # | Feature | Description | Milestone | Status |
|---|---------|-------------|-----------|--------|
| 1 | Animated Focus Score Gauge | Circular SVG gauge with 0-100 score, letter grade, and breakdown bars | M1 | DONE |
| 2 | Weekly Focus Score Bar Chart | 7-day focus score bar chart with hover tooltips and streak indicator | M1 | DONE |
| 3 | App Usage Breakdown Chart | Doughnut chart showing Productive/Distracting/Neutral minutes from `/screen/breakdown` | M1 | DONE |
| 4 | Real-time Activity Timeline | Chronological app usage event stream with status badges | M3 | DONE |
| 5 | Assignment Urgency List | Assignment list with due date urgency indicators and mark-done functionality | M2 | DONE |
| 6 | Quick-Add Assignment Input | Input field posting NLP or structured data to `/assignments/nlp` or `/assignments/` | M2 | DONE |
| 7 | Live WS Status Indicator | Connection status dot and text with auto-reconnect backoff | M3 | DONE |
| 8 | Responsive Mobile Layout | Seamless grid layouts across 1920px desktop, 768px tablet, 375px mobile | M4 | DONE |
| 9 | Sidebar Navigation | Fixed sidebar with links to Dashboard (`/`), Schedule (`/schedule`), Settings (`/settings`) | M4 | DONE |
| 10 | Focus Session Timer | Interactive timer widget (Start, Pause, Reset, elapsed time display) | M3 | DONE |
| 11 | Dark/Light Theme System | Theme toggle switch with CSS variables and localStorage persistence | M4 | DONE |
| 12 | AI Accountability Roast Feed | Real-time AI roast notifications and Morning Q&A modal | M3 | DONE |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Core Visual Analytics & Charts | Focus score gauge, 7-day weekly bar chart, app breakdown doughnut chart | none | DONE |
| M2 | Assignment & Task Management | Assignment list with urgency badges, quick-add input, mark-done, study advice | M1 | DONE |
| M3 | Live Event Stream & Interactive Widgets | Activity timeline, WS status indicator, Focus session timer, Roast feed & Morning Q&A | M1, M2 | DONE |
| M4 | Theme Engine, Sidebar & Responsive Hardening | CSS custom property dark/light theme toggle, Sidebar navigation, 1920px/768px/375px responsive grids | M1, M2, M3 | DONE |
| M5 | E2E Integration & Audit Gate | Comprehensive verification of all 10 features, visual quality, and audit pass | M1-M4 | DONE |

## Interface Contracts
### Frontend JS State (`S`) ↔ Backend REST / WS
- `S.score` updated via `GET /reports/stats` & WS `stats_update`
- `S.assignments` updated via `GET /assignments/` & WS `tasks_list` / `assignment_added` / `assignment_done`
- `S.history` updated via `GET /reports/history`
- `S.breakdown` updated via `GET /screen/breakdown`
- WebSocket status updated via `ws.onopen`, `ws.onclose`, `ws.onerror`

## Code Layout
- Main Dashboard: `static/dashboard.html` (Completed, 1,914 lines, 78KB, 0 truncation)
- Linked Pages: `static/schedule.html`, `static/settings.html`
- Static Assets: `static/`
