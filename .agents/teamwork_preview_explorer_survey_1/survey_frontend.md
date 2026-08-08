# Mimo Frontend Comprehensive Survey & Architectural Catalog

**Date**: 2026-08-06  
**Investigator**: survey_explorer_1 (teamwork_preview_explorer)  
**Target Files**:  
- `c:/Users/samee/projects/Mimo/static/dashboard.html` (42,337 bytes, 837 lines)  
- `c:/Users/samee/projects/Mimo/static/schedule.html` (11,840 bytes, 76 lines)  
- `c:/Users/samee/projects/Mimo/static/settings.html` (10,467 bytes, 309 lines)  
- `c:/Users/samee/projects/Mimo/static/file_tree.html` (20,590 bytes, 411 lines)  

---

## 1. Executive Summary & Overview

The current Mimo frontend is a single-page HTML/CSS/JavaScript dashboard application served statically by a FastAPI backend at `http://localhost:8000/`.

- **CSS & Fonts**: All styling is embedded directly in `<style>` blocks within the HTML `<head>`. No external CSS stylesheets (`<link rel="stylesheet">`) or web font services (e.g. Google Fonts) are imported. System fonts (`Segoe UI`, `Cascadia Code`, `Fira Code`) are used.
- **JavaScript & Assets**: All JavaScript is written in plain ES6+ inside inline `<script>` tags at the bottom of `<body>`. No external libraries or CDNs (e.g. Chart.js, Tailwind, React, Lucide) are currently loaded.
- **Layout Architecture**: `dashboard.html` uses a fixed 3-column CSS Grid layout (`260px 1fr 290px`) with a top navigation header and a bottom full-width "Roast Zone" card. It lacks responsive CSS breakpoints for mobile/tablet viewports and has no sidebar navigation.
- **Backend Bindings**: Communicates with 7 REST API endpoints and 1 real-time WebSocket connection (`/ws`).

---

## 2. Line-by-Line Catalog of `static/dashboard.html`

### 2.1 DOM Elements & IDs Catalog

| DOM ID | Element Type | Parent / Container | Description & Usage |
| :--- | :--- | :--- | :--- |
| `clock` | `<span>` | `header > .hdr-right` | Displays real-time formatted time & date (`toLocaleTimeString` / `toLocaleDateString`) |
| `ws-dot` | `<div>` | `header > .ws-pill` | Indicator dot showing WebSocket connection state (`.ws-dot.live` when connected) |
| `ws-lbl` | `<span>` | `header > .ws-pill` | Connection state text label ("Connecting", "LIVE", "Reconnecting…") |
| `gauge-card` | `<div>` | `.left-col` | Card container for focus score SVG gauge and time breakdown bars |
| `gauge-fill` | `<circle>` | `svg.gauge-svg` | SVG progress arc circle with `stroke-dashoffset` animation (circumference = 440) |
| `gauge-score` | `<div>` | `.gauge-center` | Displays numerical focus score (0–100) |
| `grade-badge` | `<div>` | `#gauge-card` | Displays letter grade badge (`grade-A` through `grade-F`) |
| `score-verdict` | `<div>` | `#gauge-card` | Qualitative score summary text string |
| `bv-prod` | `<span>` | `.bar-meta` (Productive) | Productive time value text (e.g., `45m`) |
| `bf-prod` | `<div>` | `.bar-track` (Productive) | Progress bar fill for productive time percentage |
| `bv-dist` | `<span>` | `.bar-meta` (Distracting) | Distracting time value text (e.g., `12m`) |
| `bf-dist` | `<div>` | `.bar-track` (Distracting) | Progress bar fill for distracting time percentage |
| `bv-neut` | `<span>` | `.bar-meta` (Neutral) | Neutral time value text (e.g., `30m`) |
| `bf-neut` | `<div>` | `.bar-track` (Neutral) | Progress bar fill for neutral time percentage |
| `history-card` | `<div>` | `.left-col` | Card container for 7-day focus score history and streak counter |
| `streak-num` | `<span>` | `.streak-row` | Consecutive day focus streak number (score >= 50) |
| `week-bars` | `<div>` | `#history-card` | Dynamic container rendering 7 vertical score bars |
| `week-day-labels` | `<div>` | `#history-card` | Dynamic container rendering 7 day labels ('M','T','W' etc.) |
| `patterns-card` | `<div>` | `.left-col` | Card container for behavioral pattern insights |
| `insight-list` | `<ul>` | `#patterns-card` | List container populated with weekly pattern insight bullet points |
| `app-card` | `<div>` | `.center-col` | Hero card displaying currently active application window details |
| `app-name` | `<div>` | `#app-card` | Large title of current active application (e.g., `VS Code`) |
| `app-title` | `<div>` | `#app-card` | Subtitle displaying active window title string |
| `cat-badge` | `<span>` | `#app-card` | Category badge pill (`PRODUCTIVE`, `DISTRACTING`, `NEUTRAL`) |
| `dist-count` | `<span>` | `.counter-pill` | Distraction count value |
| `desk-time` | `<span>` | `.counter-pill` | Desk time value in minutes |
| `focus-streak` | `<span>` | `.counter-pill` | Longest focus session in minutes |
| `cv-card` | `<div>` | `.center-col` | Card container for computer vision presence monitor |
| `pres-dot` | `<div>` | `.presence-row` | Status indicator dot for camera monitor (`present`, `absent`, `distracted`) |
| `pres-text` | `<span>` | `.presence-row` | Camera presence main text string |
| `pres-detail` | `<span>` | `.presence-row` | Camera presence secondary detail/action hint |
| `activity-card` | `<div>` | `.center-col` | Card container for live activity log stream |
| `act-list` | `<ul>` | `#activity-card` | Scrollable timeline list of window change events (max 25 items) |
| `asgn-list` | `<ul>` | `.right-col > .card` | List of upcoming assignments with urgency color indicators |
| `quick-input` | `<input>` | `.quick-row` | Input field for quick natural language assignment creation |
| `study-card` | `<div>` | `.right-col` | Card container for AI study recommendations |
| `rec-list` | `<ul>` | `#study-card` | List of recommended study actions with priority tags |
| `plan-card` | `<div>` | `.right-col` | Card container for daily suggested study plan |
| `plan-list` | `<ul>` | `#plan-card` | Timetable list of suggested study slots |
| `roast-zone` | `<div>` | Grid row 2 (1 / 4) | Full-width container for AI roast messages feed |
| `roast-msgs` | `<div>` | `#roast-zone` | Feed container for roast notification boxes |
| `qa-overlay` | `<div>` | Body child (fixed) | Full-screen modal overlay for Morning Q&A accountability check-in |
| `qa-q` | `<div>` | `.qa-modal` | Text prompt for current Q&A question |
| `qa-ans` | `<textarea>` | `.qa-modal` | Multiline text response input for Q&A |
| `toast` | `<div>` | Body child (fixed) | Centered bottom toast notification element |

---

### 2.2 Complete CSS System & Class Catalog

#### Root Design Tokens (`:root` variables)
- `--bg`: `#07070f` (Dark blue-black background)
- `--bg2`: `#0e0e1c` (Card background)
- `--bg3`: `#14142a` (Input & elevated surface background)
- `--border`: `rgba(255, 255, 255, 0.07)`
- `--text`: `#e2e2f0`
- `--muted`: `#5a5a7a`
- `--muted2`: `#3a3a5a`
- `--purple`: `#7c6fe0` (Primary accent color)
- `--purple-glow`: `rgba(124, 111, 224, 0.3)`
- `--green`: `#22c55e` (Productive / Success accent)
- `--green-glow`: `rgba(34, 197, 94, 0.3)`
- `--red`: `#f03a3a` (Distracting / High priority accent)
- `--red-glow`: `rgba(240, 58, 58, 0.3)`
- `--amber`: `#f59e0b` (Medium priority / Warning accent)
- `--amber-glow`: `rgba(245, 158, 11, 0.3)`
- `--blue`: `#38bdf8`
- `--cyan`: `#06b6d4`
- `--radius`: `14px`
- `--font`: `'Segoe UI', system-ui, sans-serif`
- `--font-mono`: `'Cascadia Code', 'Fira Code', monospace`

#### Component CSS Classes
- `.logo`, `.hdr-right`, `.ws-pill`, `.gear-link`, `.nav-link`, `.ws-dot`, `.ws-dot.live`
- `.layout` (Grid layout: `grid-template-columns: 260px 1fr 290px; gap: 14px; max-width: 1400px`)
- `.left-col`, `.center-col`, `.right-col`
- `.card`, `.card-label`
- `.gauge-wrap`, `.gauge-svg`, `.gauge-track`, `.gauge-fill`, `.gauge-center`, `.gauge-score`, `.gauge-denom`
- `.grade-badge`, `.grade-A`, `.grade-B`, `.grade-C`, `.grade-D`, `.grade-F`
- `.time-bars`, `.bar-row`, `.bar-meta`, `.bar-name`, `.bar-val`, `.bar-track`, `.bar-fill`, `.bar-fill.prod`, `.bar-fill.dist`, `.bar-fill.neut`
- `.streak-row`, `.streak-num`, `.streak-unit`, `.week-bars`, `.week-bar`, `.week-bar.today`, `.week-bar.good`, `.week-bar.ok`, `.week-bar.bad`, `.week-day-labels`, `.week-day-label`
- `.app-name-big`, `.app-title-small`, `.cat-badge`, `.cat-badge.productive`, `.cat-badge.distracting`, `.cat-badge.neutral`, `.counter-row`, `.counter-pill`
- `.presence-row`, `.pres-dot`, `.pres-dot.present`, `.pres-dot.absent`, `.pres-dot.distracted`, `.pres-text`, `.pres-detail`
- `.act-list`, `.act-item`, `.act-dot`, `.act-app`, `.act-time`
- `.insight-list`, `.insight-item`, `.insight-icon`
- `.asgn-list`, `.asgn-item`, `.asgn-item.done`, `.asgn-bar`, `.asgn-info`, `.asgn-title`, `.asgn-sub`, `.asgn-due`, `.quick-row`, `.quick-input`, `.quick-btn`
- `.rec-list`, `.rec-item`, `.rec-priority`
- `.plan-list`, `.plan-item`, `.plan-time`, `.plan-subject`, `.plan-dur`
- `.roast-hdr`, `.roast-msgs`, `.roast-msg`, `.roast-icon`, `.roast-text`, `.roast-meta`, `.roast-empty`
- `.qa-modal`, `.qa-title`, `.qa-sub`, `.qa-q`, `.qa-input`, `.qa-actions`, `.qa-btn`, `.qa-btn.primary`, `.qa-btn.skip`
- `#toast`, `#toast.show`

---

### 2.3 JavaScript State Architecture

The application state is centralized in a global object `S`:

```javascript
const S = {
  score: 0,            // Focus score (0-100)
  grade: 'F',          // Letter grade (A, B, C, D, F)
  verdict: '',        // Focus verdict string
  prodMin: 0,          // Productive minutes today
  distMin: 0,          // Distracting minutes today
  neutMin: 0,          // Neutral minutes today
  deskMin: 0,          // Desk time minutes
  distCount: 0,        // Total distraction count
  longestMin: 0,      // Longest focus streak (min)
  peakHour: null,      // Peak productivity hour
  presence: 'unknown', // Camera presence state
  currentApp: '—',     // Currently focused window application name
  currentCat: 'neutral',// Category (productive/distracting/neutral)
  assignments: [],     // Array of assignment objects
  roasts: [],          // Array of roast messages
  history: [],         // 7-day focus score history array
  streak: 0,           // Daily streak count
  studyRecs: [],       // Array of AI study recommendations
  studyPlan: [],       // Array of daily study plan time slots
  patterns: []         // Array of weekly behavioral pattern insights
};
```

---

### 2.4 API Bindings & WebSocket Handlers Catalog

#### REST API Endpoints

| Method | Endpoint Path | Called By Function | Description / Payload |
| :--- | :--- | :--- | :--- |
| `GET` | `/reports/stats` | `loadInitial()` | Fetches today's focus score, breakdown minutes, grade, verdict, desk time, streak |
| `GET` | `/reports/history?days=7` | `loadInitial()` | Fetches 7-day historical focus score list |
| `GET` | `/assignments/upcoming?days=14` | `loadInitial()`, `fetchAssignments()` | Fetches upcoming assignments within 14 days |
| `POST` | `/assignments/nlp` | `addNLP()` | Payload: `{ text: string }`. Parses natural language text into assignment |
| `POST` | `/assignments/{id}/done` | `markDone(id, title)` | Marks assignment `{id}` as completed |
| `GET` | `/study/recommendations` | `fetchStudy()` | Fetches AI recommendations, daily study plan, and weekly behavioral patterns |
| `POST` | `/reports/accountability` | `qaNext()` | Payload: `{ question: string, answer: string }`. Submits morning Q&A response |

#### WebSocket Integration (`/ws`)

Connection URL: `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`  
Heartbeat: `ws.send('ping')` every 25 seconds  
Auto-reconnect: Exponential backoff `retryMs = Math.min(retryMs * 1.5, 12000)` starting at 1000ms.

#### WebSocket Event Dispatch Table

| Event `type` | Handler Function | Action / Behavior |
| :--- | :--- | :--- |
| `stats_update` | `applyStats(msg.stats)` | Updates state `S` and re-renders gauge, bars, counters |
| `window_change` | `applyWindow(msg)` | Updates hero card app name, title, category; prepends to activity log |
| `cv_event` | `applyPresence(msg.event)` | Updates camera monitor dot, status text, detail label |
| `roast` | `addRoast(msg)` | Prepends roast message card to roast feed, scrolls into view, shows toast |
| `assignment_added` | `fetchAssignments()` | Refreshes assignment list from API |
| `assignment_updated` | `fetchAssignments()` | Refreshes assignment list from API |
| `assignment_done` | `fetchAssignments()` | Refreshes assignment list from API |
| `tasks_list` | `renderAssignments(msg.tasks)` | Re-renders assignment list from incoming WebSocket payload |
| `reminder` | `showReminder(msg.message)` | Displays toast popup with reminder message |
| `morning_qa` | `startQA(msg.questions)` | Opens morning Q&A modal overlay with question queue |
| `eod_report` | `onEOD(msg)` | Handles end-of-day summary report & roast/praise toast |
| `study_advice` | `showToast('🎯 ' + msg.message)` | Displays study advice toast popup |
| `voice_response` | `showToast('🔊 ' + msg.message)` | Displays voice feedback toast popup |

---

## 3. Cross-Application Survey: `schedule.html` and `settings.html`

### 3.1 `static/schedule.html`
- **Purpose**: Onboarding form to set wake/sleep boundaries, study goal, school schedule, subject priorities, and fixed commitments to generate a weekly study timetable.
- **Header Structure**: `<header><div class="logo"><em>Mimo</em> Schedule</div><a class="back-btn" href="/">Back to Dashboard</a></header>`
- **Layout**: 2-column Grid (`420px 1fr`). Responsive breakpoint `@media(max-width: 900px)` collapses to 1 column.
- **REST Endpoints**:
  - `POST /schedule/onboarding` — Payload: `{ wake_time, sleep_time, school_days, school_start, school_end, study_goal_minutes, session_minutes, break_minutes, subjects, fixed_blocks, notes }`
  - `GET /schedule/weekly` — Loads generated weekly blocks.

### 3.2 `static/settings.html`
- **Purpose**: System configuration management for hardware, voice, API keys, and thresholds.
- **Header Structure**: `<header><div class="logo">🔥 <em>Mimo</em> Settings</div><a class="back-btn" href="/">← Back to Dashboard</a></header>`
- **Layout**: Single column centered container (`max-width: 720px`) with fixed bottom action bar.
- **REST Endpoints**:
  - `GET /settings/data` — Loads configuration sections & items.
  - `POST /settings/save-all` — Saves key-value updates to `.env`.
  - `POST /settings/save` — Saves single key-value update.
  - `POST /settings/restart` — Restarts background services.
  - `GET /settings/openai-test` — Tests OpenAI API key validity.

---

## 4. Gap Analysis & Redesign Requirements Matrix

Comparing existing implementation against `ORIGINAL_REQUEST.md` requirements R1–R3:

| Requirement Feature | Current State in `dashboard.html` | Gap / Action Needed for Redesign |
| :--- | :--- | :--- |
| **R1. Modern Premium Aesthetics** | Basic dark theme, generic cards, no animations except gauge and roast | Full redesign: glassmorphism/elevated cards, glow effects, refined typography, smooth transitions |
| **R1. Dark / Light Theme Toggle** | Hardcoded dark theme (`#07070f`) in `:root` | Add theme toggle switch, CSS variables for light theme, `localStorage` persistence |
| **R2.1 Animated Focus Gauge** | SVG circle with dashoffset transition | Upgrade visual design, clear letter grade badge, high contrast |
| **R2.2 Weekly Focus Bar Chart** | Custom HTML `<div>` bars inside `#week-bars` | Upgrade to sleek interactive bar chart with clear tooltips and date labels |
| **R2.3 App Usage Breakdown** | Horizontal progress bar stack (`bf-prod`, `bf-dist`, `bf-neut`) | Upgrade to interactive Doughnut / Pie Chart (`/screen/breakdown` API) |
| **R2.4 Real-time Activity Timeline**| Linear list `#act-list` (max 25 items) | Enhance timeline styling with badges, time distance, icons |
| **R2.5 Assignment List & Urgency** | Color bar indicator (`high`, `medium`, `low`) | Enhance urgency tags (`today`, `soon`, `ok`), checkbox state transitions |
| **R2.6 Quick-Add Assignment** | Input + button (`addNLP`) calling `/assignments/nlp` | Refine quick-add UI, support NLP or structured input |
| **R2.7 Live WS Status Indicator** | Pill `.ws-pill` with dot & label | Refine indicator with status pulse & auto-reconnect text |
| **R2.8 Responsive Layout** | Fixed grid `260px 1fr 290px`. NO `@media` queries! | Add `@media` queries for Desktop (>=1200px), Tablet (>=768px), Mobile (>=375px) |
| **R2.9 Sidebar Navigation** | Header links only (`/schedule`, `/settings`). NO sidebar! | Implement collapsable/responsive Sidebar Navigation with active state highlighting |
| **R2.10 Focus Session Timer** | **MISSING!** No focus timer component exists in `dashboard.html`. | Add interactive Focus Session Timer (Start / Pause / Reset, elapsed time display) |
| **R3. Backend Integration** | Working REST API fetches & WebSocket listeners | **MUST PRESERVE** all API URLs, JSON formats, and WebSocket message type handlers |

---

## 5. Architectural Recommendations for Redesign Phase

1. **Maintain Single-File Integrity or Clean Component Modularity**: All static assets must be served from `static/`.
2. **Preserve ID and Handler Contract**: Maintain or map existing element IDs (`gauge-fill`, `gauge-score`, `asgn-list`, `act-list`, `roast-msgs`, `qa-overlay`, `ws-dot`, `ws-lbl`) so WebSocket and API event handlers connect seamlessly.
3. **Add Missing Endpoints Integration**:
   - `GET /screen/breakdown` for doughnut chart rendering.
   - Focus Timer component (client-side state with optional notification/log).
4. **Implement Responsive Breakpoints**:
   - Desktop (>=1200px): Sidebar + Main Grid (2 or 3 columns).
   - Tablet (768px - 1199px): Collapsible/Icon Sidebar + Stacked Columns.
   - Mobile (<768px): Hamburger Navigation + Single Column stacked layout.

