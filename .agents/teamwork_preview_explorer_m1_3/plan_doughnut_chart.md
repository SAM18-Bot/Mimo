# Implementation Guide: App Usage Breakdown Doughnut Chart (Milestone 1 Feature 3)

**Author**: m1_explorer_3 (teamwork_preview_explorer)  
**Target File**: `static/dashboard.html`  
**Endpoint**: `GET /screen/breakdown`  
**Library**: Chart.js v4 via CDN (`https://cdn.jsdelivr.net/npm/chart.js`)  

---

## 1. Executive Summary & Design Overview

Milestone 1 Feature 3 upgrades the basic horizontal progress bar breakdown into a modern **Chart.js Doughnut Chart component**. It provides a real-time, visual distribution of user screen time across **Productive**, **Distracting**, and **Neutral** categories, paired with a central total hours readout, interactive legend pills for segment filtering, and a top applications list tabbed by productivity classification.

### Key Visual & Functional Highlights:
1. **Linear/Vercel Glassmorphic Card**: Elevated dark/light container with subtle borders (`1px solid var(--border-subtle)`), soft backdrop blur, and crisp typography.
2. **Precision Doughnut Chart**: Modern thin ring (`72% cutout`), rounded arc edges (`borderRadius: 6`), and dynamic borders matching the card background (`borderColor: var(--bg-card)`).
3. **Central Total Time Readout**: High-contrast central readout overlay displaying formatted total hours/minutes (e.g. `2.8h` or `2h 45m`) with uppercase label.
4. **Interactive Legend Pills**: Color-coded buttons (`Productive`, `Distracting`, `Neutral`) with minute counts and percentage readouts. Clicking a pill toggles the segment on/off in the Chart.js canvas.
5. **Top Applications List**: Dual-tab selector (`Productive` vs `Distracting`) listing top 5 apps with rank badges, minute counts, formatted time strings, and percentage progress bars.
6. **Dark / Light Theme Adaptation**: Responsive theme switcher hook that dynamically updates chart border colors, tooltip themes, and arc accents without chart re-creation.

---

## 2. Backend API Schema & State Integration

### 2.1 API Endpoint Schema (`GET /screen/breakdown`)
- **URL**: `/screen/breakdown`
- **Query Parameter**: `target_date` (`Optional[date]`, format: `YYYY-MM-DD`, default: today)
- **Response Format**:
```json
{
  "productive_min": 120,
  "distracting_min": 30,
  "neutral_min": 15,
  "total_min": 165,
  "top_productive": [
    { "app": "code", "minutes": 90 },
    { "app": "notion", "minutes": 30 }
  ],
  "top_distracting": [
    { "app": "chrome", "minutes": 30 }
  ]
}
```

### 2.2 WebSocket & Real-Time Sync Strategy
- On page load, `fetchScreenBreakdown()` is invoked.
- When WebSocket broadcasts `stats_update` or `window_change` events, `fetchScreenBreakdown()` is called to synchronize state and re-render chart arcs and top app bars without full page reloads.
- State object integration: Store breakdown state in global `S.breakdown`.

---

## 3. Exact Component HTML Structure

This HTML snippet replaces or embeds into `.left-col` or `.center-col` (Milestone 1 grid layout):

```html
<!-- App Usage Breakdown Card (Milestone 1 Feature 3) -->
<div id="breakdown-card" class="card breakdown-card">
  <!-- Card Header -->
  <div class="card-header flex items-center justify-between mb-3">
    <div class="flex items-center gap-2">
      <svg class="w-4 h-4 text-brand-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 3.055A9.001 9.001 0 1020.945 13H11V3.055z"/>
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.488 9H15V3.512A9.025 9.025 0 0120.488 9z"/>
      </svg>
      <h3 class="card-label font-bold text-xs uppercase tracking-wider text-muted">App Usage Breakdown</h3>
    </div>
    <span id="breakdown-total-badge" class="total-badge text-xs font-semibold px-2.5 py-1 rounded-full bg-pill text-secondary">Total: 0h 0m</span>
  </div>

  <!-- Doughnut Chart Container with HTML Center Overlay -->
  <div class="chart-wrapper relative flex items-center justify-center my-2" style="height: 210px; width: 100%;">
    <canvas id="breakdown-doughnut-canvas"></canvas>
    
    <!-- Central Readout Overlay -->
    <div id="breakdown-center-overlay" class="center-overlay flex flex-col items-center justify-center text-center pointer-events-none absolute inset-0">
      <span id="center-total-val" class="text-2xl font-extrabold text-primary font-sans leading-tight">0.0h</span>
      <span id="center-total-lbl" class="text-[10px] text-muted uppercase tracking-widest font-semibold mt-0.5">Screen Time</span>
    </div>
  </div>

  <!-- Interactive Legend Pills -->
  <div class="legend-pills-row grid grid-cols-3 gap-1.5 my-3">
    <button id="pill-prod" class="legend-pill active flex flex-col items-center p-2 rounded-lg bg-pill border border-subtle hover:border-strong transition-all" onclick="toggleBreakdownSegment(0)">
      <div class="flex items-center gap-1.5 mb-1">
        <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
        <span class="text-[11px] font-medium text-secondary">Productive</span>
      </div>
      <span id="legend-prod-val" class="text-xs font-bold text-primary">0m (0%)</span>
    </button>

    <button id="pill-dist" class="legend-pill active flex flex-col items-center p-2 rounded-lg bg-pill border border-subtle hover:border-strong transition-all" onclick="toggleBreakdownSegment(1)">
      <div class="flex items-center gap-1.5 mb-1">
        <span class="w-2 h-2 rounded-full bg-rose-500"></span>
        <span class="text-[11px] font-medium text-secondary">Distracting</span>
      </div>
      <span id="legend-dist-val" class="text-xs font-bold text-primary">0m (0%)</span>
    </button>

    <button id="pill-neut" class="legend-pill active flex flex-col items-center p-2 rounded-lg bg-pill border border-subtle hover:border-strong transition-all" onclick="toggleBreakdownSegment(2)">
      <div class="flex items-center gap-1.5 mb-1">
        <span class="w-2 h-2 rounded-full bg-indigo-500"></span>
        <span class="text-[11px] font-medium text-secondary">Neutral</span>
      </div>
      <span id="legend-neut-val" class="text-xs font-bold text-primary">0m (0%)</span>
    </button>
  </div>

  <!-- Top Applications List Section -->
  <div class="top-apps-container pt-3 border-t border-subtle">
    <div class="flex items-center justify-between mb-2.5">
      <span class="text-[11px] font-bold uppercase tracking-wider text-muted">Top Apps</span>
      <div class="app-tab-pills flex gap-1 bg-pill p-0.5 rounded-md border border-subtle">
        <button id="tab-top-prod" class="tab-btn text-[10px] font-semibold px-2 py-0.5 rounded bg-card text-primary shadow-sm" onclick="switchTopAppsTab('productive')">Productive</button>
        <button id="tab-top-dist" class="tab-btn text-[10px] font-semibold px-2 py-0.5 rounded text-muted hover:text-secondary" onclick="switchTopAppsTab('distracting')">Distracting</button>
      </div>
    </div>

    <!-- Dynamic App List -->
    <div id="top-apps-list" class="top-apps-list flex flex-col gap-2 max-h-[140px] overflow-y-auto pr-1">
      <div class="text-xs text-muted text-center py-3">No activity recorded today</div>
    </div>
  </div>
</div>
```

---

## 4. Complete CSS Rules & Design Tokens

Add these rules to `<style>` in `static/dashboard.html` or style block:

```css
/* ── App Usage Breakdown Card Styling ── */
.breakdown-card {
  position: relative;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 18px 20px;
  backdrop-filter: var(--glass-blur);
  transition: border-color 0.3s ease, box-shadow 0.3s ease;
}

.breakdown-card:hover {
  border-color: var(--border-strong);
  box-shadow: var(--shadow-card);
}

.total-badge {
  background: var(--bg-pill);
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
}

/* Central Overlay Readout */
.center-overlay {
  pointer-events: none;
  z-index: 10;
}

#center-total-val {
  color: var(--text-primary);
  font-family: 'Plus Jakarta Sans', sans-serif;
  letter-spacing: -0.02em;
}

#center-total-lbl {
  color: var(--text-muted);
}

/* Legend Pills */
.legend-pill {
  cursor: pointer;
  background: var(--bg-pill);
  border: 1px solid var(--border-subtle);
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.legend-pill:hover {
  background: var(--bg-card-hover);
  border-color: var(--border-strong);
  transform: translateY(-1px);
}

.legend-pill.inactive {
  opacity: 0.45;
  filter: grayscale(60%);
  border-style: dashed;
}

/* Top Apps List & Tab Buttons */
.tab-btn {
  transition: all 0.15s ease;
}

.tab-btn.active {
  background: var(--bg-card);
  color: var(--text-primary);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15);
}

.top-app-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 6px 8px;
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--border-subtle);
}

.top-app-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11px;
}

.top-app-name {
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.top-app-time {
  font-weight: 700;
  color: var(--text-secondary);
  font-family: 'JetBrains Mono', monospace;
}

.top-app-bar-track {
  height: 4px;
  background: var(--bg-pill);
  border-radius: 2px;
  overflow: hidden;
}

.top-app-bar-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);
}

.top-app-bar-fill.productive {
  background: linear-gradient(90deg, #10b981, #059669);
}

.top-app-bar-fill.distracting {
  background: linear-gradient(90deg, #f43f5e, #e11d48);
}
```

---

## 5. Complete JavaScript Engine & Chart.js Wiring

```javascript
/* ═══════════════════════════════════════════════════════════════════════════
   MILESTONE 1 FEATURE 3: APP USAGE BREAKDOWN DOUGHNUT CHART ENGINE
   ═══════════════════════════════════════════════════════════════════════════ */

// Chart instance reference
let breakdownChart = null;
let currentTopAppsTab = 'productive';

// Category color palettes (Dark vs Light theme aware)
const BREAKDOWN_COLORS = {
  dark: {
    productive: '#10b981',
    distracting: '#f43f5e',
    neutral: '#6366f1',
    hover: ['#059669', '#e11d48', '#4f46e5'],
    border: '#0d1322'
  },
  light: {
    productive: '#059669',
    distracting: '#e11d48',
    neutral: '#4f46e5',
    hover: ['#047857', '#be123c', '#4338ca'],
    border: '#ffffff'
  }
};

/**
 * Initializes the Chart.js Doughnut instance
 */
function initBreakdownChart() {
  const ctx = document.getElementById('breakdown-doughnut-canvas');
  if (!ctx) return;

  const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
  const colors = BREAKDOWN_COLORS[currentTheme] || BREAKDOWN_COLORS.dark;

  breakdownChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Productive', 'Distracting', 'Neutral'],
      datasets: [{
        data: [0, 0, 0],
        backgroundColor: [colors.productive, colors.distracting, colors.neutral],
        hoverBackgroundColor: colors.hover,
        borderColor: colors.border,
        borderWidth: 3,
        borderRadius: 6,
        borderAlign: 'inner',
        hoverOffset: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '72%',
      animation: {
        duration: 1000,
        easing: 'easeOutQuart'
      },
      plugins: {
        legend: {
          display: false // Custom HTML legend pills used instead
        },
        tooltip: {
          enabled: true,
          backgroundColor: currentTheme === 'dark' ? 'rgba(15, 23, 42, 0.95)' : 'rgba(255, 255, 255, 0.95)',
          titleColor: currentTheme === 'dark' ? '#f8fafc' : '#0f172a',
          bodyColor: currentTheme === 'dark' ? '#cbd5e1' : '#334155',
          borderColor: currentTheme === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)',
          borderWidth: 1,
          padding: 10,
          boxPadding: 4,
          usePointStyle: true,
          callbacks: {
            label: function(context) {
              const label = context.label || '';
              const value = context.raw || 0;
              const total = context.dataset.data.reduce((a, b) => a + b, 0);
              const percentage = total > 0 ? Math.round((value / total) * 100) : 0;
              
              const hours = Math.floor(value / 60);
              const mins = value % 60;
              const timeStr = hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
              
              return ` ${label}: ${timeStr} (${percentage}%)`;
            }
          }
        }
      }
    }
  });
}

/**
 * Fetches breakdown data from GET /screen/breakdown
 */
async function fetchScreenBreakdown() {
  try {
    const res = await fetch('/screen/breakdown');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    // Cache state
    if (typeof S !== 'undefined') {
      S.breakdown = data;
    }

    renderBreakdownData(data);
  } catch (err) {
    console.warn('Failed to fetch /screen/breakdown:', err);
  }
}

/**
 * Renders data onto doughnut chart, center readout, legend pills, and top apps list
 */
function renderBreakdownData(data) {
  const prodMin = data.productive_min || 0;
  const distMin = data.distracting_min || 0;
  const neutMin = data.neutral_min || 0;
  const totalMin = data.total_min || (prodMin + distMin + neutMin);

  // 1. Update Chart.js dataset
  if (breakdownChart) {
    breakdownChart.data.datasets[0].data = [prodMin, distMin, neutMin];
    breakdownChart.update();
  }

  // 2. Update Central Readout
  const centerValEl = document.getElementById('center-total-val');
  if (centerValEl) {
    const totalHours = (totalMin / 60).toFixed(1);
    centerValEl.textContent = `${totalHours}h`;
  }

  // 3. Update Header Total Badge
  const totalBadgeEl = document.getElementById('breakdown-total-badge');
  if (totalBadgeEl) {
    const h = Math.floor(totalMin / 60);
    const m = totalMin % 60;
    totalBadgeEl.textContent = `Total: ${h}h ${m}m`;
  }

  // 4. Update Legend Pills
  const calcPct = (val) => (totalMin > 0 ? Math.round((val / totalMin) * 100) : 0);

  const prodValEl = document.getElementById('legend-prod-val');
  if (prodValEl) prodValEl.textContent = `${prodMin}m (${calcPct(prodMin)}%)`;

  const distValEl = document.getElementById('legend-dist-val');
  if (distValEl) distValEl.textContent = `${distMin}m (${calcPct(distMin)}%)`;

  const neutValEl = document.getElementById('legend-neut-val');
  if (neutValEl) neutValEl.textContent = `${neutMin}m (${calcPct(neutMin)}%)`;

  // 5. Render Top Apps
  renderTopAppsList(data);
}

/**
 * Toggles dataset segment visibility when legend pill is clicked
 */
function toggleBreakdownSegment(index) {
  if (!breakdownChart) return;

  const isVisible = breakdownChart.isDatasetVisible(0);
  const meta = breakdownChart.getDatasetMeta(0);

  // Toggle index hidden status
  meta.data[index].hidden = !meta.data[index].hidden;
  breakdownChart.update();

  // Toggle active class on button pill
  const pillIds = ['pill-prod', 'pill-dist', 'pill-neut'];
  const pillBtn = document.getElementById(pillIds[index]);
  if (pillBtn) {
    pillBtn.classList.toggle('inactive', meta.data[index].hidden);
  }
}

/**
 * Switches tab view between Productive and Distracting top apps
 */
function switchTopAppsTab(tabCategory) {
  currentTopAppsTab = tabCategory;

  const prodTabBtn = document.getElementById('tab-top-prod');
  const distTabBtn = document.getElementById('tab-top-dist');

  if (tabCategory === 'productive') {
    prodTabBtn?.classList.add('active', 'bg-card', 'text-primary');
    prodTabBtn?.classList.remove('text-muted');
    distTabBtn?.classList.remove('active', 'bg-card', 'text-primary');
    distTabBtn?.classList.add('text-muted');
  } else {
    distTabBtn?.classList.add('active', 'bg-card', 'text-primary');
    distTabBtn?.classList.remove('text-muted');
    prodTabBtn?.classList.remove('active', 'bg-card', 'text-primary');
    prodTabBtn?.classList.add('text-muted');
  }

  if (typeof S !== 'undefined' && S.breakdown) {
    renderTopAppsList(S.breakdown);
  }
}

/**
 * Renders top applications list items with percentage bars
 */
function renderTopAppsList(data) {
  const container = document.getElementById('top-apps-list');
  if (!container) return;

  const apps = currentTopAppsTab === 'productive'
    ? (data.top_productive || [])
    : (data.top_distracting || []);

  if (apps.length === 0) {
    container.innerHTML = `<div class="text-xs text-muted text-center py-3">No ${currentTopAppsTab} app data recorded</div>`;
    return;
  }

  // Calculate maximum minutes for scaled percentage bars
  const maxMin = Math.max(...apps.map(a => a.minutes || 0), 1);

  container.innerHTML = apps.map((item, i) => {
    const mins = item.minutes || 0;
    const hrs = Math.floor(mins / 60);
    const m = mins % 60;
    const timeDisplay = hrs > 0 ? `${hrs}h ${m}m` : `${m}m`;
    const barWidthPct = Math.round((mins / maxMin) * 100);

    return `
      <div class="top-app-item">
        <div class="top-app-meta">
          <span class="top-app-name" title="${item.app}">${i + 1}. ${item.app}</span>
          <span class="top-app-time">${timeDisplay}</span>
        </div>
        <div class="top-app-bar-track">
          <div class="top-app-bar-fill ${currentTopAppsTab}" style="width: ${barWidthPct}%;"></div>
        </div>
      </div>
    `;
  }).join('');
}

/**
 * Dynamic theme update hook (call when dark/light mode toggles)
 */
function updateBreakdownTheme(newTheme) {
  if (!breakdownChart) return;

  const colors = BREAKDOWN_COLORS[newTheme] || BREAKDOWN_COLORS.dark;
  
  breakdownChart.data.datasets[0].backgroundColor = [colors.productive, colors.distracting, colors.neutral];
  breakdownChart.data.datasets[0].hoverBackgroundColor = colors.hover;
  breakdownChart.data.datasets[0].borderColor = colors.border;
  
  breakdownChart.options.plugins.tooltip.backgroundColor = newTheme === 'dark' ? 'rgba(15, 23, 42, 0.95)' : 'rgba(255, 255, 255, 0.95)';
  breakdownChart.options.plugins.tooltip.titleColor = newTheme === 'dark' ? '#f8fafc' : '#0f172a';
  breakdownChart.options.plugins.tooltip.bodyColor = newTheme === 'dark' ? '#cbd5e1' : '#334155';
  
  breakdownChart.update('none'); // Update without re-triggering full entrance animation
}
```

---

## 6. Layout & Responsiveness Guidelines

| Viewport Width | Breakdown Card Behavior |
|---|---|
| **Desktop (>=1200px)** | Fits neatly into 3-column dashboard grid. Chart container height 210px, doughnut canvas centered. |
| **Tablet (768px - 1199px)** | Grid reflows to 2 columns. Doughnut chart scales fluidly, legend pills stack nicely in 3 columns. |
| **Mobile (<768px)** | Single column stack. Legend pills grid adjusts to fit full width with legible minimum font size (`11px`). |

---

## 7. Verification & Testing Steps

1. **Static HTML/JS Verification**:
   - Ensure `<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>` is loaded in `<head>`.
   - Call `initBreakdownChart()` and `fetchScreenBreakdown()` inside `DOMContentLoaded` event listener.

2. **API Data Verification**:
   - Trigger `GET /screen/breakdown` via browser console or network tab.
   - Verify center readout updates with total hours, legend pills update with minutes and percentage, and top apps render progress bars.

3. **Theme Switch Verification**:
   - Toggle theme state (`document.documentElement.setAttribute('data-theme', 'light')`).
   - Confirm `updateBreakdownTheme('light')` switches doughnut border color to white and updates tooltip background.
