# Mimo Dashboard Redesign — Comprehensive Design & UI Technical Specification

**Author:** survey_explorer_3 (teamwork_preview_explorer)  
**Target File:** `static/dashboard.html`  
**Target Aesthetic:** Linear / Vercel / Raycast Level — Dark & Light Theme System  
**Build Requirement:** 100% Static HTML/CSS/JS (Zero Node.js build pipeline, direct CDN embedding)

---

## 1. Executive Summary & Design Vision

Mimo is an AI-powered student accountability platform. The redesign transforms the current single-page dashboard into a world-class, responsive, production-ready interface that balances high-density information display with stunning visual polish.

### Key Design Principles:
1. **Precision & Polish (Linear / Vercel / Raycast Aesthetic)**: Dark/light mode theme system with ultra-subtle borders (`1px solid rgba(...)`), soft glassmorphism background blurs (`backdrop-filter: blur(12px)`), crisp typography, vibrant status glows, and micro-interactions.
2. **Zero-Build Pipeline Direct CDN Integration**: Embeds modern UI libraries (Chart.js, Lucide Icons, Plus Jakarta Sans, Tailwind CSS CDN / Vanilla CSS Variables) directly into single-file HTML.
3. **Data-Dense & Live**: Real-time visual updates via WebSockets with smooth animations for gauges, charts, timeline feeds, timer ticks, and roasts.
4. **Fluid Responsiveness**: Seamless scaling across 1920px (Desktop UHD), 1200px (Desktop HD), 768px (Tablet), and 375px (Mobile).

---

## 2. CDN Tech Stack & Integration Architecture

To ensure zero build pipeline dependency, all external assets will be imported via reliable CDNs in `<head>`.

```html
<!-- 1. Typography: Plus Jakarta Sans (UI) & JetBrains Mono (Code/Timers) -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">

<!-- 2. Tailwind CSS CDN (Script runtime engine for utility classes) -->
<script src="https://cdn.tailwindcss.com"></script>
<script>
  tailwind.config = {
    darkMode: 'class',
    theme: {
      extend: {
        fontFamily: {
          sans: ['Plus Jakarta Sans', 'sans-serif'],
          mono: ['JetBrains Mono', 'monospace'],
        },
        colors: {
          brand: {
            50: '#f0f3ff',
            500: '#6366f1',
            600: '#4f46e5',
            700: '#4338ca',
          }
        }
      }
    }
  }
</script>

<!-- 3. Lucide Icons (Web component / static SVG renderer) -->
<script src="https://unpkg.com/lucide@latest"></script>

<!-- 4. Chart.js CDN for Doughnut & Bar Charts -->
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
```

---

## 3. Design System & Theme Architecture (CSS Custom Properties)

The theme system utilizes CSS custom properties on `:root` (Dark by default or Light mode based on `data-theme` attribute on `<html>`). Theme state is toggled via a header/sidebar switch and persisted in `localStorage`.

### 3.1 CSS Custom Property Tokens

```css
/* Dark Theme (Default) */
:root, html[data-theme="dark"] {
  --bg-app:          #090d16;
  --bg-sidebar:      #0d1322;
  --bg-card:         rgba(17, 24, 39, 0.7);
  --bg-card-hover:   rgba(31, 41, 55, 0.8);
  --bg-input:        #111827;
  --bg-pill:         #1e293b;
  
  --border-subtle:   rgba(255, 255, 255, 0.08);
  --border-strong:   rgba(255, 255, 255, 0.16);
  --border-focus:    #6366f1;
  
  --text-primary:    #f9fafb;
  --text-secondary:  #9ca3af;
  --text-muted:      #6b7280;
  
  --accent-purple:   #8b5cf6;
  --accent-indigo:   #6366f1;
  --accent-cyan:     #06b6d4;
  --accent-emerald:  #10b981;
  --accent-amber:    #f59e0b;
  --accent-rose:     #f43f5e;

  --glow-purple:     rgba(139, 92, 246, 0.25);
  --glow-emerald:    rgba(16, 185, 129, 0.25);
  --glow-rose:       rgba(244, 63, 94, 0.25);
  
  --radius-sm:       6px;
  --radius-md:       10px;
  --radius-lg:       16px;
  --radius-xl:       24px;
  
  --shadow-card:     0 4px 20px -2px rgba(0, 0, 0, 0.5);
  --glass-blur:      blur(16px);
}

/* Light Theme */
html[data-theme="light"] {
  --bg-app:          #f8fafc;
  --bg-sidebar:      #ffffff;
  --bg-card:         rgba(255, 255, 255, 0.85);
  --bg-card-hover:   #ffffff;
  --bg-input:        #f1f5f9;
  --bg-pill:         #e2e8f0;
  
  --border-subtle:   rgba(0, 0, 0, 0.08);
  --border-strong:   rgba(0, 0, 0, 0.16);
  --border-focus:    #4f46e5;
  
  --text-primary:    #0f172a;
  --text-secondary:  #475569;
  --text-muted:      #94a3b8;

  --accent-purple:   #7c3aed;
  --accent-indigo:   #4f46e5;
  --accent-cyan:     #0891b2;
  --accent-emerald:  #059669;
  --accent-amber:    #d97706;
  --accent-rose:     #e11d48;

  --glow-purple:     rgba(124, 58, 237, 0.15);
  --glow-emerald:    rgba(5, 150, 105, 0.15);
  --glow-rose:       rgba(225, 29, 72, 0.15);
  
  --shadow-card:     0 4px 20px -2px rgba(0, 0, 0, 0.06);
  --glass-blur:      blur(12px);
}
```

---

## 4. Specification of the 10 Core Features

### Feature 1: Animated Circular Focus Score Gauge (0-100 with Grade Letter)
- **Visual Spec**:
  - Centerpiece SVG ring gauge with smooth `stroke-dashoffset` transition (1.2s cubic-bezier).
  - Centered focus score number (0-100) with dynamic color gradient based on score value (Emerald >= 85, Indigo/Amber 50-84, Rose < 50).
  - Centered grade letter badge (A, B, C, D, F) with soft back-glow and colored border.
  - Sub-bars showing Productive vs Distracting vs Neutral minutes breakdown directly under gauge.
- **Backend API**: `GET /reports/stats` (data fields: `focus_score`, `letter_grade`, `score_verdict`, `productive_min`, `distracting_min`, `neutral_min`).
- **Interaction**: Animated count-up number effect on page load and live WebSocket update.

### Feature 2: Weekly Focus Score Bar Chart with Hover Tooltips
- **Visual Spec**:
  - 7-day focus score bar chart powered by Chart.js (or SVG canvas fallback).
  - Custom dark/light tooltip on hover showing `[Date]: [Score]/100`.
  - Highlight current day with distinct glow accent (`var(--accent-indigo)`).
  - Active Streak Counter pill (e.g., `5 Day Streak 🔥`).
- **Backend API**: `GET /reports/history?days=7`.

### Feature 3: App Usage Breakdown (Doughnut Chart)
- **Visual Spec**:
  - Chart.js Doughnut chart displaying screen time distribution across categories: Productive (Emerald), Distracting (Rose), Neutral (Slate/Indigo).
  - Central summary text showing total desk time in hours/minutes.
  - Interactive legend with toggleable items and top apps list (e.g., VS Code 2.5h, YouTube 45m).
- **Backend API**: `GET /screen/breakdown` & `GET /reports/stats`.

### Feature 4: Real-time Activity Timeline
- **Visual Spec**:
  - Chronological activity feed showing recent window/app events.
  - Each item features category dot (Productive = Emerald, Distracting = Rose, Neutral = Muted), app icon/name, window title, and relative timestamp (`Just now`, `2m ago`).
  - Smooth entrance animation (`slide-down + fade-in`) when new WebSocket `window_change` events arrive. Max length 25 events.
- **Backend API / WS**: `WebSocket /ws` (`type: "window_change"`).

### Feature 5: Assignment List with Urgency Indicators
- **Visual Spec**:
  - Assignment list with clear urgency indicators:
    - **Overdue / Due Today**: Red status pill + glowing red border (`🚨 Due Today`).
    - **Due Soon (1-2 days)**: Amber status pill (`⚠️ Due Tomorrow` / `2d left`).
    - **Normal (> 2 days)**: Slate/Green status pill (`5d left`).
  - Priority tag (High, Medium, Low).
  - Strike-through text + opacity drop upon clicking checkmark to trigger `POST /assignments/{id}/done`.
- **Backend API**: `GET /assignments/upcoming?days=14`, `POST /assignments/{id}/done`.

### Feature 6: Quick-Add Assignment Input (Posting to API)
- **Visual Spec**:
  - Smart natural-language input field (`"Math homework due Friday high priority"`).
  - Quick action button (`+ Add Task`) with loading spinner state.
  - Toast feedback on submission success ("✓ Task added successfully") or error handling.
- **Backend API**: `POST /assignments/nlp` (with fallback to `POST /assignments/`).

### Feature 7: Live WebSocket Connection Status Indicator
- **Visual Spec**:
  - Header pill showing live status:
    - **Connected**: Glowing green dot + text `LIVE`.
    - **Reconnecting**: Pulsing yellow dot + text `Reconnecting...`.
    - **Disconnected**: Red dot + text `Offline`.
  - Automatic exponential backoff reconnect logic.
- **Backend API**: `WebSocket /ws`.

### Feature 8: Responsive Mobile Layout
- **Breakpoints**:
  - `Desktop UHD/HD (>=1200px)`: 3-column layout (Sidebar 240px | Main Content 1fr | Right Panel 320px).
  - `Tablet (768px - 1199px)`: 2-column layout (Sidebar collapses to icon-rail 64px | Main + Right content merged into grid).
  - `Mobile (375px - 767px)`: 1-column layout (Sidebar hidden, accessible via top slide-over mobile drawer or bottom nav bar; full vertical stack).
- **Quality Standard**: Zero horizontal scrollbar across all viewport sizes between 375px and 1920px.

### Feature 9: Sidebar Navigation
- **Visual Spec**:
  - Fixed left sidebar containing:
    - Mimo Logo + AI Accountability tag.
    - Navigation items: `Dashboard` (`/`), `Schedule` (`/schedule`), `Settings` (`/settings`).
    - Active item indicator with subtle left border line and background highlight.
    - Focus mode session widget summary at bottom.
    - Dark/Light Theme toggle button at bottom.
- **Backend Routing**: Links point directly to FastAPI served paths `/`, `/schedule`, `/settings`.

### Feature 10: Focus Session Timer Widget
- **Visual Spec**:
  - Interactive timer module embedded in the dashboard main workspace or right panel.
  - Displays formatted time `MM:SS` or `HH:MM:SS` in `JetBrains Mono` font.
  - Controls: Start Focus, Pause, Reset, Mode selector (Pomodoro 25m, Deep Work 50m, Custom).
  - Visual status ring/progress bar filling up as focus time elapses.
  - Sound alert / Toast notification on timer completion.

---

## 5. Layout Architecture & Component Grid Breakdown

### 5.1 Grid Blueprint (Desktop >=1200px)

```
+-----------------------------------------------------------------------------------------------+
| SIDEBAR (240px) | HEADER (Top Bar: Breadcrumbs, Timer Quick-Status, Theme Toggle, WS Status)  |
|                 +-----------------------------------------------------------------------------+
| • Logo          | MAIN CONTENT AREA (Grid 12-col)                                             |
| • Nav Links     | +------------------------------------+ +------------------------------------+ |
|   - Dashboard   | | HERO: Currently Active App (col-7)| | FOCUS SCORE GAUGE CARD (col-5)    | |
|   - Schedule    | | (App name, category, counters)     | | (Score gauge, grade, time bars)   | |
|   - Settings    | +------------------------------------+ +------------------------------------+ |
| • Focus Timer   | +------------------------------------+ +------------------------------------+ |
| • Theme Toggle  | | WEEKLY HISTORY CHART (col-7)       | | APP USAGE DOUGHNUT CHART (col-5) | |
|                 | +------------------------------------+ +------------------------------------+ |
|                 | +------------------------------------+ +------------------------------------+ |
|                 | | ASSIGNMENTS & QUICK ADD (col-6)    | | LIVE ACTIVITY TIMELINE (col-6)   | |
|                 | +------------------------------------+ +------------------------------------+ |
|                 | +-------------------------------------------------------------------------+ |
|                 | | ROAST ZONE — AI ACCOUNTABILITY FEED (col-12)                            | |
|                 | +-------------------------------------------------------------------------+ |
+-----------------------------------------------------------------------------------------------+
```

---

## 6. Backend API Contracts & Data Flow Mappings

| Feature | Primary Endpoint | WebSocket Trigger Event | UI Target Element ID |
|---|---|---|---|
| Focus Score Gauge | `GET /reports/stats` | `stats_update` | `#gauge-score`, `#gauge-fill`, `#grade-badge` |
| Weekly History Bar | `GET /reports/history?days=7` | `stats_update` | `#weekly-chart-canvas`, `#streak-num` |
| App Usage Doughnut | `GET /screen/breakdown` | `stats_update`, `window_change` | `#usage-doughnut-canvas`, `#time-bars` |
| Activity Timeline | — | `window_change` | `#activity-timeline-list` |
| Assignment List | `GET /assignments/upcoming?days=14` | `assignment_added`, `assignment_done` | `#assignment-list` |
| Quick Add Input | `POST /assignments/nlp` | `assignment_added` | `#quick-add-input`, `#quick-add-btn` |
| WS Status Dot | `WebSocket /ws` | `onopen`, `onclose`, `onerror` | `#ws-status-badge`, `#ws-dot` |
| Focus Timer | Client JS State | — | `#focus-timer-display`, `#timer-toggle-btn` |
| Sidebar Navigation | Static HTML Links | — | `#sidebar-nav` |
| Morning Q&A Modal | `POST /reports/accountability` | `morning_qa` | `#qa-overlay-modal` |

---

## 7. Quality & Verification Checklist for Implementers

1. **Theme Switch Verification**: Test dark and light mode toggle. Verify contrast ratios pass WCAG AA standards (minimum 4.5:1 contrast for text).
2. **Responsive Verification**: Test at 1920x1080, 1366x768, 768x1024 (Tablet), and 375x812 (Mobile iPhone X/12). Check for zero horizontal overflow.
3. **WebSocket Resilience**: Simulate network drop and verify automatic reconnect indicator switches from green to pulsing amber/red and recovers without page reload.
4. **Interactive Gauges & Charts**: Ensure SVG gauge and Chart.js canvases resize smoothly on window resize without distortion or canvas overflow.
5. **No Backend File Modification**: Confirm all changes reside strictly within `static/` directory.

---
*Report compiled by survey_explorer_3.*
