# Implementation Plan — Milestone 1 Feature 1: Animated Circular Focus Score Gauge

**Target Module**: Focus Score Gauge & Time Breakdown Bars (`#gauge-card`)  
**Target File**: `static/dashboard.html`  
**Author**: m1_explorer_1 (teamwork_preview_explorer)  
**Date**: 2026-08-06  

---

## 1. Feature Overview & Architecture

Milestone 1 Feature 1 delivers a **modern SVG circular focus score gauge** (0–100 scale), a glowing letter grade badge (A–F), a dynamic qualitative score verdict, and time breakdown progress bars (Productive, Distracting, Neutral screen minutes).

### Key Design Principles:
1. **Modern Aesthetic**: Ultra-sleek SVG ring gauge with smooth `stroke-dashoffset` animation, dynamic SVG stroke colors, glowing backdrops, and glassmorphic card boundaries matching Linear/Vercel/Raycast design languages.
2. **Dynamic Color Tiering**:
   - **High Focus (>= 85)**: Emerald Green (`#10b981`, glow `rgba(16, 185, 129, 0.35)`)
   - **Medium Focus (50–84)**: Indigo / Amber (`#6366f1` / `#f59e0b`, glow `rgba(99, 102, 241, 0.35)`)
   - **Low Focus (< 50)**: Rose / Red (`#f43f5e`, glow `rgba(244, 63, 94, 0.35)`)
3. **Smooth Number Interpolation**: Animated count-up effect for the numerical score on page load and live WebSocket updates.
4. **100% Backward Compatibility**: Full adherence to existing element ID contracts (`#gauge-fill`, `#gauge-score`, `#grade-badge`, `#score-verdict`, `#bv-prod`, `#bf-prod`, `#bv-dist`, `#bf-dist`, `#bv-neut`, `#bf-neut`).

---

## 2. API Contract & State Data Flow

### 2.1 Backend Data Sources
- **REST Endpoint**: `GET /reports/stats`
- **WebSocket Event**: `stats_update` (`msg.stats`)

### 2.2 Global State Mapping (`S`)
| Field Name | Type | Description | Source Field in API |
| :--- | :--- | :--- | :--- |
| `S.score` | `number` | Focus score from 0.0 to 100.0 | `stats.focus_score` |
| `S.grade` | `string` | Letter grade (`A+`, `A`, `B`, `C`, `D`, `F`) | `stats.letter_grade` |
| `S.verdict` | `string` | Qualitative summary string | `stats.score_verdict` |
| `S.prodMin` | `number` | Productive minutes today | `stats.productive_min` |
| `S.distMin` | `number` | Distracting minutes today | `stats.distracting_min` |
| `S.neutMin` | `number` | Neutral minutes today | `stats.neutral_min` |

### 2.3 Preserved DOM Element ID Matrix
| DOM ID | Element Type | Function / Usage | Preserved In Redesign |
| :--- | :--- | :--- | :---: |
| `gauge-card` | `<div>` | Card wrapper container | ✅ YES |
| `gauge-fill` | `<circle>` | SVG progress arc circle (`stroke-dashoffset`) | ✅ YES |
| `gauge-score` | `<div>` | Numerical focus score (0-100) display | ✅ YES |
| `grade-badge` | `<div>` | Letter grade badge element | ✅ YES |
| `score-verdict` | `<div>` | Qualitative focus verdict text string | ✅ YES |
| `bv-prod` | `<span>` | Productive time value text (e.g. `120m`) | ✅ YES |
| `bf-prod` | `<div>` | Productive time progress fill bar | ✅ YES |
| `bv-dist` | `<span>` | Distracting time value text (e.g. `30m`) | ✅ YES |
| `bf-dist` | `<div>` | Distracting time progress fill bar | ✅ YES |
| `bv-neut` | `<span>` | Neutral time value text (e.g. `10m`) | ✅ YES |
| `bf-neut` | `<div>` | Neutral time progress fill bar | ✅ YES |

---

## 3. Exact HTML Structure

Replace the current `#gauge-card` HTML block in `static/dashboard.html` with this updated component structure:

```html
<!-- Focus gauge + grade card -->
<div class="card" id="gauge-card">
  <div class="card-header">
    <div class="card-label">
      <svg class="icon-sm" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="m12 6 4 6-4 6-4-6z"/></svg>
      <span>Focus Score</span>
    </div>
    <div id="grade-badge" class="grade-badge grade-F">—</div>
  </div>

  <div class="gauge-wrap">
    <svg class="gauge-svg" viewBox="0 0 160 160">
      <defs>
        <linearGradient id="gauge-grad-emerald" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#10b981" />
          <stop offset="100%" stop-color="#34d399" />
        </linearGradient>
        <linearGradient id="gauge-grad-indigo" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#6366f1" />
          <stop offset="100%" stop-color="#818cf8" />
        </linearGradient>
        <linearGradient id="gauge-grad-amber" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#f59e0b" />
          <stop offset="100%" stop-color="#fbbf24" />
        </linearGradient>
        <linearGradient id="gauge-grad-rose" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#f43f5e" />
          <stop offset="100%" stop-color="#fb7185" />
        </linearGradient>
      </defs>

      <!-- Background gauge track -->
      <circle class="gauge-track" cx="80" cy="80" r="70" />
      
      <!-- Animated focus progress arc -->
      <circle class="gauge-fill" id="gauge-fill" cx="80" cy="80" r="70" />
    </svg>

    <div class="gauge-center">
      <div class="gauge-score-wrap">
        <span class="gauge-score" id="gauge-score">0</span>
        <span class="gauge-denom">/100</span>
      </div>
      <div id="score-verdict" class="score-verdict">Initializing…</div>
    </div>
  </div>

  <!-- Time breakdown bars -->
  <div class="time-bars">
    <div class="bar-row">
      <div class="bar-meta">
        <span class="bar-name">
          <span class="bar-dot dot-prod"></span>
          Productive
        </span>
        <span class="bar-val" id="bv-prod">0m</span>
      </div>
      <div class="bar-track">
        <div class="bar-fill prod" id="bf-prod"></div>
      </div>
    </div>

    <div class="bar-row">
      <div class="bar-meta">
        <span class="bar-name">
          <span class="bar-dot dot-dist"></span>
          Distracting
        </span>
        <span class="bar-val" id="bv-dist">0m</span>
      </div>
      <div class="bar-track">
        <div class="bar-fill dist" id="bf-dist"></div>
      </div>
    </div>

    <div class="bar-row">
      <div class="bar-meta">
        <span class="bar-name">
          <span class="bar-dot dot-neut"></span>
          Neutral
        </span>
        <span class="bar-val" id="bv-neut">0m</span>
      </div>
      <div class="bar-track">
        <div class="bar-fill neut" id="bf-neut"></div>
      </div>
    </div>
  </div>
</div>
```

---

## 4. Exact CSS Rules

Add or update these CSS rules in `<style>` in `static/dashboard.html`:

```css
/* ═══════════════════════════════════════════════════════
   FEATURE 1: FOCUS SCORE GAUGE & BREAKDOWN BARS
═══════════════════════════════════════════════════════ */

#gauge-card {
  position: relative;
  padding: 20px;
  background: var(--bg-card, rgba(17, 24, 39, 0.7));
  border: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.08));
  border-radius: var(--radius-lg, 16px);
  backdrop-filter: var(--glass-blur, blur(16px));
  box-shadow: var(--shadow-card, 0 4px 20px -2px rgba(0, 0, 0, 0.4));
  transition: border-color 0.3s ease, box-shadow 0.3s ease;
}

#gauge-card:hover {
  border-color: var(--border-strong, rgba(255, 255, 255, 0.16));
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.card-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary, #9ca3af);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.icon-sm {
  stroke: var(--accent-indigo, #6366f1);
}

/* Gauge SVG Wrapper */
.gauge-wrap {
  position: relative;
  width: 180px;
  height: 180px;
  margin: 0 auto 16px;
}

.gauge-svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg); /* Start arc from 12 o'clock */
  overflow: visible;
}

.gauge-track {
  fill: none;
  stroke: var(--bg-pill, rgba(255, 255, 255, 0.05));
  stroke-width: 12;
  stroke-linecap: round;
}

.gauge-fill {
  fill: none;
  stroke: var(--accent-emerald, #10b981);
  stroke-width: 12;
  stroke-linecap: round;
  stroke-dasharray: 440;       /* 2π × r (r=70) ≈ 439.82 */
  stroke-dashoffset: 440;      /* Default empty */
  transition: stroke-dashoffset 1.2s cubic-bezier(0.34, 1.56, 0.64, 1), stroke 0.5s ease;
  filter: drop-shadow(0 0 8px var(--glow-emerald, rgba(16, 185, 129, 0.35)));
}

/* Gauge Center Text Layout */
.gauge-center {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  pointer-events: none;
}

.gauge-score-wrap {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 2px;
}

.gauge-score {
  font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
  font-size: 44px;
  font-weight: 800;
  line-height: 1;
  letter-spacing: -0.03em;
  color: var(--text-primary, #f9fafb);
  transition: color 0.5s ease;
}

.gauge-denom {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-muted, #6b7280);
}

.score-verdict {
  margin-top: 4px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary, #9ca3af);
  max-width: 140px;
  line-height: 1.3;
  transition: color 0.5s ease;
}

/* Grade Badges */
.grade-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px 12px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  font-weight: 700;
  border-radius: var(--radius-sm, 6px);
  border: 1px solid transparent;
  transition: all 0.4s ease;
}

.grade-badge.grade-A, .grade-badge.grade-A\+ {
  background: rgba(16, 185, 129, 0.12);
  border-color: rgba(16, 185, 129, 0.3);
  color: #34d399;
  box-shadow: 0 0 12px rgba(16, 185, 129, 0.25);
}

.grade-badge.grade-B {
  background: rgba(99, 102, 241, 0.12);
  border-color: rgba(99, 102, 241, 0.3);
  color: #818cf8;
  box-shadow: 0 0 12px rgba(99, 102, 241, 0.25);
}

.grade-badge.grade-C {
  background: rgba(245, 158, 11, 0.12);
  border-color: rgba(245, 158, 11, 0.3);
  color: #fbbf24;
  box-shadow: 0 0 12px rgba(245, 158, 11, 0.25);
}

.grade-badge.grade-D {
  background: rgba(249, 115, 22, 0.12);
  border-color: rgba(249, 115, 22, 0.3);
  color: #fb923c;
  box-shadow: 0 0 12px rgba(249, 115, 22, 0.25);
}

.grade-badge.grade-F {
  background: rgba(244, 63, 94, 0.12);
  border-color: rgba(244, 63, 94, 0.3);
  color: #fb7185;
  box-shadow: 0 0 12px rgba(244, 63, 94, 0.25);
}

/* Breakdown Time Bars */
.time-bars {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.06));
}

.bar-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.bar-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
}

.bar-name {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 500;
  color: var(--text-secondary, #9ca3af);
}

.bar-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

.dot-prod { background: #10b981; box-shadow: 0 0 6px rgba(16, 185, 129, 0.5); }
.dot-dist { background: #f43f5e; box-shadow: 0 0 6px rgba(244, 63, 94, 0.5); }
.dot-neut { background: #6366f1; box-shadow: 0 0 6px rgba(99, 102, 241, 0.5); }

.bar-val {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary, #f9fafb);
}

.bar-track {
  width: 100%;
  height: 8px;
  background: var(--bg-input, rgba(255, 255, 255, 0.05));
  border-radius: 9999px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  width: 0%;
  border-radius: 9999px;
  transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);
}

.bar-fill.prod {
  background: linear-gradient(90deg, #10b981, #34d399);
}

.bar-fill.dist {
  background: linear-gradient(90deg, #f43f5e, #fb7185);
}

.bar-fill.neut {
  background: linear-gradient(90deg, #6366f1, #818cf8);
}
```

---

## 5. Exact JavaScript Rendering Code

Ensure `GAUGE_C` and the functions `renderGauge()` and `renderBars()` are implemented in `<script>` as follows:

```javascript
/* ═══════════════════════════════════════════════════════
   GAUGE CONSTANT & ANIMATION STATE
═══════════════════════════════════════════════════════ */
const GAUGE_C = 440; // 2π × 70 (r=70)
let currentDisplayedScore = 0;
let scoreAnimFrame = null;

/**
 * Renders the circular SVG gauge, score counter, letter grade, and verdict text.
 */
function renderGauge() {
  const fill      = document.getElementById('gauge-fill');
  const scoreEl   = document.getElementById('gauge-score');
  const gradeEl   = document.getElementById('grade-badge');
  const verdictEl = document.getElementById('score-verdict');

  if (!fill || !scoreEl) return;

  const targetScore = Math.max(0, Math.min(100, S.score || 0));

  // 1. Calculate stroke-dashoffset
  const offset = GAUGE_C - (targetScore / 100) * GAUGE_C;
  fill.style.strokeDashoffset = offset;

  // 2. Dynamic Color Palette & Gradient Selection based on Focus Score
  let themeColor, glowColor;
  if (targetScore >= 85) {
    themeColor = '#10b981'; // Emerald
    glowColor  = 'rgba(16, 185, 129, 0.4)';
    fill.style.stroke = 'url(#gauge-grad-emerald)';
  } else if (targetScore >= 50) {
    themeColor = '#6366f1'; // Indigo
    glowColor  = 'rgba(99, 102, 241, 0.4)';
    fill.style.stroke = 'url(#gauge-grad-indigo)';
  } else {
    themeColor = '#f43f5e'; // Rose
    glowColor  = 'rgba(244, 63, 94, 0.4)';
    fill.style.stroke = 'url(#gauge-grad-rose)';
  }

  fill.style.filter = `drop-shadow(0 0 10px ${glowColor})`;

  // 3. Smooth Score Counter Animation (Interpolation)
  animateScoreCount(targetScore, scoreEl, themeColor);

  // 4. Update Letter Grade Badge
  if (gradeEl) {
    const rawGrade = S.grade || 'F';
    gradeEl.textContent = rawGrade;
    // Normalize grade class (e.g. "grade-A+" -> "grade-A")
    const cleanClass = 'grade-' + rawGrade.replace('+', '');
    gradeEl.className = `grade-badge ${cleanClass}`;
  }

  // 5. Update Score Verdict
  if (verdictEl) {
    verdictEl.textContent = S.verdict || 'No data yet today';
    verdictEl.style.color = themeColor;
  }
}

/**
 * Interpolates score number smoothly from current value to target value.
 */
function animateScoreCount(target, el, color) {
  if (scoreAnimFrame) cancelAnimationFrame(scoreAnimFrame);

  const start = currentDisplayedScore;
  const startTime = performance.now();
  const duration = 800; // ms

  function step(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    
    // Ease-out cubic formula
    const easeProgress = 1 - Math.pow(1 - progress, 3);
    const currentVal = Math.round(start + (target - start) * easeProgress);

    currentDisplayedScore = currentVal;
    el.textContent = currentVal;
    el.style.color = color;

    if (progress < 1) {
      scoreAnimFrame = requestAnimationFrame(step);
    }
  }

  scoreAnimFrame = requestAnimationFrame(step);
}

/**
 * Formats minutes into human-readable strings (e.g., 125 -> "2h 5m").
 */
function formatMin(mins) {
  if (!mins || mins <= 0) return '0m';
  if (mins < 60) return mins + 'm';
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

/**
 * Renders Productive, Distracting, and Neutral time breakdown bars.
 */
function renderBars() {
  const total = Math.max(S.prodMin + S.distMin + S.neutMin, 1);

  const updateCategoryBar = (key, mins) => {
    const fillEl = document.getElementById('bf-' + key);
    const valEl  = document.getElementById('bv-' + key);

    if (fillEl) {
      const pct = Math.round((mins / total) * 100);
      fillEl.style.width = pct + '%';
    }
    if (valEl) {
      valEl.textContent = formatMin(mins);
    }
  };

  updateCategoryBar('prod', S.prodMin);
  updateCategoryBar('dist', S.distMin);
  updateCategoryBar('neut', S.neutMin);
}
```

---

## 6. Verification & Test Protocol

1. **Static HTML Check**: Confirm that all element IDs (`#gauge-fill`, `#gauge-score`, `#grade-badge`, `#score-verdict`, `#bv-prod`, `#bf-prod`, `#bv-dist`, `#bf-dist`, `#bv-neut`, `#bf-neut`) exist and match target types.
2. **Initial Load Test**: Load `http://localhost:8000/` and verify `GET /reports/stats` populates score, letter grade, verdict text, and time bars.
3. **WebSocket Event Test**: Run `python mock_screen.py --demo` or send a simulated WebSocket `stats_update` payload to verify smooth arc animation, number count-up, and breakdown bar width updates.
4. **Theme Switch Verification**: Toggle dark/light theme to verify contrast ratios pass WCAG AA standards.
