# Milestone 1 Feature 2: Weekly Focus Score Bar Chart — Technical Implementation Plan

**Feature ID**: M1.F2  
**Target Component**: `#history-card`, `#week-bars`, `#week-day-labels`, `#streak-num` in `static/dashboard.html`  
**Backend Endpoint**: `GET /reports/history?days=7`  
**Investigator**: `m1_explorer_2` (`teamwork_preview_explorer`)  
**Date**: 2026-08-06  

---

## 1. Analysis of Existing Implementation

In the current `static/dashboard.html` (lines 87-100 CSS, 281-289 HTML, 706-739 JS):

1. **HTML Structure**:
   ```html
   <div class="card" id="history-card">
     <div class="card-label">7-Day History</div>
     <div class="streak-row">
       <span class="streak-num" id="streak-num">0</span>
       <span class="streak-unit">day streak 🔥</span>
     </div>
     <div class="week-bars" id="week-bars"></div>
     <div class="week-day-labels" id="week-day-labels"></div>
   </div>
   ```

2. **Current JS Rendering (`renderHistory(history)`)**:
   - Accepts `history` array from `GET /reports/history?days=7`.
   - The backend query (`api/routes_reports.py`:29-48) executes `DailySummary.order_by(DailySummary.date.desc()).limit(days)`, returning items ordered **date-descending** (e.g. `[Today, Yesterday, 2 days ago, ...]`).
   - The existing code pads missing days to 7 items and calculates `Math.max(4, score / maxScore * 100)`.
   - Tooltips are rendered via basic CSS `::after` content (`data-tip` attribute).
   - Streak calculation checks consecutive days with `score >= 50`.

3. **Gaps & Visual Limitations**:
   - The current bar container is fixed at only `44px` in height, which feels cramped and lacks visual impact.
   - The native CSS `::after` hover tooltip is basic and text-only (`"2026-08-06: 85/100"`).
   - The streak element is plain text without glowing badges or visual hierarchy.
   - Lacks clear theme integration (dark/light custom properties) and modern gradient fills.

---

## 2. API Contract & Schema Compatibility

- **Endpoint**: `GET /reports/history?days=7`
- **Status Code**: `200 OK`
- **Response Schema** (`List[DailySummary]`):
  ```json
  [
    {
      "date": "2026-08-06",
      "focus_score": 85.5,
      "productive_min": 120,
      "distracting_min": 30,
      "assignments_done": 2,
      "assignments_due": 3
    },
    {
      "date": "2026-08-05",
      "focus_score": 72.0,
      "productive_min": 90,
      "distracting_min": 45,
      "assignments_done": 1,
      "assignments_due": 2
    }
  ]
  ```
- **100% Backward Compatibility Requirement**: The function signature `renderHistory(history)` and DOM IDs (`#history-card`, `#streak-num`, `#week-bars`, `#week-day-labels`) MUST be preserved.

---

## 3. Redesign Architectural Specification

We provide a **Primary Recommended Approach** (Modern Custom HTML/SVG Component with Glassmorphic Floating Tooltip and Animated Streak Pill) as well as an **Alternative Approach** (Chart.js Canvas Integration).

### Feature Breakdown:
1. **Streak Indicator Pill**:
   - Displays flame icon + numerical count (`#streak-num`) + text label (`Day Streak`).
   - Uses glowing amber/orange pill styling (`background: rgba(245,158,11,0.12)`, `border: 1px solid rgba(245,158,11,0.25)`).
   - Calculates consecutive days where `focus_score >= 50` ending today or yesterday.
2. **7-Day Bar Chart Workspace**:
   - Expanded height (`110px` height) with background dashed grid lines at 0%, 50%, 100%.
   - 7 columns representing the last 7 calendar days chronologically ending Today (T-6 on left to T-0 on right).
   - Animated entrance growth (`height: 0%` -> `height: N%` with cubic-bezier easing).
3. **Dynamic Color Spectrum**:
   - `Today's Bar`: Violet/Indigo gradient (`#a855f7` to `#6366f1`) with soft back-glow (`box-shadow: 0 0 12px rgba(168,85,247,0.4)`).
   - `High Focus (>=70)`: Emerald gradient (`#34d399` to `#059669`).
   - `Moderate Focus (40-69)`: Amber gradient (`#fbbf24` to `#d97706`).
   - `Low Focus (<40)`: Rose gradient (`#fb7185` to `#e11d48`).
   - `Empty / No Data`: Muted dashed bar track.
4. **Rich Glassmorphic Hover Tooltip**:
   - Mouse tracking floating card displaying:
     - Date + `"TODAY"` badge.
     - Numerical score (`85/100`).
     - Productive minutes (`120m`) & Distracting minutes (`30m`).

---

## 4. Exact Implementation Code Snippets

### 4.1 HTML Structure (`static/dashboard.html`)

Replace the `#history-card` div in `static/dashboard.html` with:

```html
<!-- 7-Day History Card (Redesigned) -->
<div class="card p-5 rounded-2xl bg-card border border-subtle transition-all duration-300 hover:border-strong relative overflow-hidden" id="history-card">
  
  <!-- Header: Title & Streak Indicator Pill -->
  <div class="flex items-center justify-between mb-4">
    <div class="flex items-center gap-2.5">
      <div class="w-8 h-8 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 shadow-inner">
        <i data-lucide="flame" class="w-4.5 h-4.5"></i>
      </div>
      <div>
        <h3 class="text-sm font-bold text-primary tracking-wide">Weekly Focus</h3>
        <p class="text-[11px] text-muted font-medium">7-day score trend</p>
      </div>
    </div>
    
    <!-- Streak Indicator Pill -->
    <div class="streak-pill flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-amber-500/10 border border-amber-500/25 shadow-sm transition-all duration-300 hover:scale-105" id="streak-pill">
      <span class="inline-block w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span>
      <span class="text-sm font-extrabold text-amber-400 font-mono" id="streak-num">0</span>
      <span class="text-xs font-semibold text-amber-300/90">Day Streak</span>
    </div>
  </div>

  <!-- Chart Area with Grid Lines & Floating Tooltip -->
  <div class="relative mt-2">
    <!-- Grid Reference Lines -->
    <div class="absolute inset-0 flex flex-col justify-between pointer-events-none opacity-15 z-0">
      <div class="border-b border-dashed border-primary w-full h-0"></div>
      <div class="border-b border-dashed border-primary w-full h-0"></div>
      <div class="border-b border-dashed border-primary w-full h-0"></div>
    </div>

    <!-- Floating Glassmorphic Tooltip Element -->
    <div id="chart-tooltip" class="chart-tooltip opacity-0 pointer-events-none absolute z-30 transition-opacity duration-200 ease-out transform -translate-x-1/2 -translate-y-full mb-3 px-3 py-2 rounded-xl bg-slate-900/95 border border-white/15 backdrop-blur-md shadow-2xl text-xs text-white">
      <div class="font-bold text-primary flex items-center justify-between gap-3 mb-1">
        <span id="tooltip-date" class="text-slate-200">Aug 6</span>
        <span id="tooltip-tag" class="px-1.5 py-0.5 rounded text-[9px] font-extrabold bg-indigo-500/25 text-indigo-300 border border-indigo-500/40">TODAY</span>
      </div>
      <div class="flex items-center gap-2 mb-1">
        <span class="text-muted text-[11px]">Focus Score:</span>
        <span id="tooltip-score" class="font-mono font-bold text-emerald-400 text-xs">85/100</span>
      </div>
      <div class="grid grid-cols-2 gap-x-3 gap-y-0.5 text-[10px] text-slate-300 border-t border-white/10 pt-1 mt-1">
        <div><span class="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400 mr-1"></span>Prod: <span id="tooltip-prod" class="font-mono font-medium text-white">120m</span></div>
        <div><span class="inline-block w-1.5 h-1.5 rounded-full bg-rose-400 mr-1"></span>Dist: <span id="tooltip-dist" class="font-mono font-medium text-white">30m</span></div>
      </div>
    </div>

    <!-- Dynamic Bars Container -->
    <div class="week-bars flex items-end justify-between gap-2.5 h-28 pt-4 pb-1 relative z-10" id="week-bars">
      <!-- Generated by JS -->
    </div>

    <!-- Weekday Labels Row -->
    <div class="week-day-labels flex items-center justify-between gap-2.5 mt-2 pt-2 border-t border-subtle relative z-10" id="week-day-labels">
      <!-- Generated by JS -->
    </div>
  </div>
</div>
```

---

### 4.2 CSS Rules (`static/dashboard.html` or linked stylesheet)

```css
/* ═══════════════════════════════════════════════════════
   WEEKLY HISTORY BAR CHART SYSTEM
═══════════════════════════════════════════════════════ */
#history-card {
  background: var(--bg-card, rgba(17, 24, 39, 0.7));
  border: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.08));
  border-radius: var(--radius-lg, 16px);
  backdrop-filter: var(--glass-blur, blur(16px));
}

.streak-pill {
  background: rgba(245, 158, 11, 0.12);
  border: 1px solid rgba(245, 158, 11, 0.25);
  box-shadow: 0 0 12px rgba(245, 158, 11, 0.15);
}

.week-bars {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 8px;
  height: 110px;
  position: relative;
}

.week-bar-wrapper {
  flex: 1;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  align-items: center;
  position: relative;
  cursor: pointer;
}

.week-bar {
  width: 100%;
  max-width: 26px;
  border-radius: 6px 6px 2px 2px;
  min-height: 4px;
  transition: height 0.6s cubic-bezier(0.34, 1.56, 0.64, 1), background 0.3s, box-shadow 0.3s, transform 0.2s;
  position: relative;
}

/* Color Grades */
.week-bar.today {
  background: linear-gradient(180deg, #a855f7 0%, #6366f1 100%);
  box-shadow: 0 0 14px rgba(168, 85, 247, 0.45), 0 0 4px rgba(99, 102, 241, 0.6);
}
.week-bar.good {
  background: linear-gradient(180deg, #34d399 0%, #059669 100%);
  box-shadow: 0 0 8px rgba(52, 211, 153, 0.25);
}
.week-bar.ok {
  background: linear-gradient(180deg, #fbbf24 0%, #d97706 100%);
  box-shadow: 0 0 8px rgba(251, 191, 36, 0.25);
}
.week-bar.bad {
  background: linear-gradient(180deg, #fb7185 0%, #e11d48 100%);
  box-shadow: 0 0 8px rgba(251, 113, 133, 0.25);
}
.week-bar.empty {
  background: var(--bg-pill, rgba(255, 255, 255, 0.05));
  border: 1px dashed var(--border-subtle, rgba(255, 255, 255, 0.12));
}

.week-bar-wrapper:hover .week-bar {
  filter: brightness(1.2);
  transform: scaleX(1.1);
}

.week-day-labels {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  margin-top: 8px;
}

.week-day-label {
  flex: 1;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted, #6b7280);
  text-align: center;
  transition: color 0.3s;
}

.week-day-label.today {
  color: var(--accent-indigo, #6366f1);
  font-weight: 800;
}
.week-day-label.today::after {
  content: '';
  display: block;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--accent-indigo, #6366f1);
  margin: 3px auto 0 auto;
}
```

---

### 4.3 JavaScript Rendering Logic (`static/dashboard.html`)

Replace `function renderHistory(history)` with this updated implementation:

```javascript
/* ═══════════════════════════════════════════════════════
   7-DAY HISTORY BARS RENDERER
═══════════════════════════════════════════════════════ */
function renderHistory(history) {
  const barsEl   = document.getElementById('week-bars');
  const labelsEl = document.getElementById('week-day-labels');
  const streakEl = document.getElementById('streak-num');
  const tooltip  = document.getElementById('chart-tooltip');

  if (!barsEl || !labelsEl) return;
  barsEl.innerHTML = '';
  labelsEl.innerHTML = '';

  // 1. Generate 7 calendar dates ending today (YYYY-MM-DD)
  const todayObj = new Date();
  const dates = [];
  for (let i = 6; i >= 0; i--) {
    const d = new Date(todayObj);
    d.setDate(d.getDate() - i);
    const yyyy = d.getFullYear();
    const mm   = String(d.getMonth() + 1).padStart(2, '0');
    const dd   = String(d.getDate()).padStart(2, '0');
    dates.push({
      dateStr: `${yyyy}-${mm}-${dd}`,
      dayName: d.toLocaleDateString('en-US', { weekday: 'short' }),
      dateFormatted: d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      isToday: i === 0
    });
  }

  // 2. Map incoming API history array into date key lookup
  const historyMap = {};
  if (Array.isArray(history)) {
    history.forEach(item => {
      if (item && item.date) {
        historyMap[item.date] = item;
      }
    });
  }

  // 3. Build 7 day records
  const dayRecords = dates.map(d => {
    const rec = historyMap[d.dateStr] || null;
    return {
      dateStr: d.dateStr,
      dayName: d.dayName,
      dateFormatted: d.dateFormatted,
      isToday: d.isToday,
      score: rec ? Math.round(rec.focus_score || 0) : 0,
      prodMin: rec ? (rec.productive_min || 0) : 0,
      distMin: rec ? (rec.distracting_min || 0) : 0,
      asgnDone: rec ? (rec.assignments_done || 0) : 0,
      hasData: !!rec
    };
  });

  // 4. Calculate consecutive day streak (focus_score >= 50)
  let streak = 0;
  let checkIdx = dayRecords.length - 1; // start from today
  const todayRec = dayRecords[checkIdx];

  // If today's score is not yet >= 50, check if yesterday had an active streak
  if (todayRec.score < 50 && dayRecords.length > 1 && dayRecords[dayRecords.length - 2].score >= 50) {
    checkIdx = dayRecords.length - 2;
  }

  while (checkIdx >= 0 && dayRecords[checkIdx].score >= 50) {
    streak++;
    checkIdx--;
  }

  if (streakEl) streakEl.textContent = streak;

  // 5. Render bars & labels
  dayRecords.forEach(rec => {
    // Wrapper container
    const wrapper = document.createElement('div');
    wrapper.className = 'week-bar-wrapper';

    // Calculate bar height percentage (min 6% for visible track base)
    const heightPct = rec.hasData ? Math.max(6, Math.min(100, rec.score)) : 6;

    // Bar Color Class
    let barClass = 'week-bar';
    if (rec.isToday) {
      barClass += ' today';
    } else if (!rec.hasData) {
      barClass += ' empty';
    } else if (rec.score >= 70) {
      barClass += ' good';
    } else if (rec.score >= 40) {
      barClass += ' ok';
    } else {
      barClass += ' bad';
    }

    const bar = document.createElement('div');
    bar.className = barClass;
    bar.style.height = '0%'; // Initial height for smooth grow transition
    setTimeout(() => { bar.style.height = `${heightPct}%`; }, 40);

    wrapper.appendChild(bar);
    barsEl.appendChild(wrapper);

    // Weekday Label
    const lbl = document.createElement('div');
    lbl.className = `week-day-label ${rec.isToday ? 'today' : ''}`;
    lbl.textContent = rec.dayName;
    labelsEl.appendChild(lbl);

    // Mouse Events for Tooltip
    wrapper.addEventListener('mouseenter', () => {
      if (!tooltip) return;
      document.getElementById('tooltip-date').textContent = rec.dateFormatted;
      
      const tag = document.getElementById('tooltip-tag');
      if (tag) tag.style.display = rec.isToday ? 'inline-block' : 'none';

      document.getElementById('tooltip-score').textContent = rec.hasData ? `${rec.score}/100` : 'No Record';
      document.getElementById('tooltip-prod').textContent = `${rec.prodMin}m`;
      document.getElementById('tooltip-dist').textContent = `${rec.distMin}m`;

      // Position Tooltip
      const wrapperRect = wrapper.getBoundingClientRect();
      const cardRect    = barsEl.closest('#history-card').getBoundingClientRect();
      
      const leftOffset = wrapperRect.left - cardRect.left + (wrapperRect.width / 2);
      const topOffset  = wrapperRect.top - cardRect.top;

      tooltip.style.left = `${leftOffset}px`;
      tooltip.style.top  = `${topOffset}px`;
      tooltip.style.opacity = '1';
    });

    wrapper.addEventListener('mouseleave', () => {
      if (tooltip) tooltip.style.opacity = '0';
    });
  });

  // Re-initialize Lucide icons if loaded
  if (typeof lucide !== 'undefined' && lucide.createIcons) {
    lucide.createIcons();
  }
}
```

---

## 5. Verification & Testing Checklist

1. **API Schema Verification**:
   - Execute `GET /reports/history?days=7` via browser or cURL.
   - Confirm response returns array of JSON objects with `date`, `focus_score`, `productive_min`, `distracting_min`, `assignments_done`.
2. **Visual Inspection**:
   - Verify chart renders 7 bars aligned chronologically from T-6 (left) to Today (right).
   - Verify today's bar has violet/indigo gradient fill with glow.
   - Hover over each bar: verify floating glassmorphic tooltip displays date, score, productive, distracting minutes.
   - Verify streak count pill displays correct consecutive day count.
3. **Responsive Scaling**:
   - Resize viewport from 1920px down to 375px; verify chart bars contract smoothly without line overflow.

---
*Implementation Plan authored by m1_explorer_2.*
