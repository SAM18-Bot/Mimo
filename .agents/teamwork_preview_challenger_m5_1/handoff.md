# Handoff Report — Empirical Challenger (m5_1)

## 1. Observation

### 1.1 WebSocket Heartbeat Ping Missing
- **File**: `static/dashboard.html`, lines 1146–1185 (`connectWebSocket`)
- **Code Quote**:
  ```javascript
  ws.onopen = () => {
    wsRetryMs = 1000;
    if (wsDot) wsDot.className = 'ws-dot live';
    if (wsLbl) wsLbl.textContent = 'LIVE';
  };
  ```
- **Observed Behavior**: Task 3 explicitly specifies verifying WebSocket 25s heartbeat ping logic. `connectWebSocket()` in `static/dashboard.html` does not start a 25-second ping interval (`setInterval`) or send ping messages on connection.

### 1.2 Top Apps Breakdown Key Mismatch
- **File**: `static/dashboard.html`, lines 1651–1667 (`renderTopApps`)
- **Code Quote**:
  ```javascript
  const apps = data?.top_apps || data?.apps || [];
  ```
- **Backend File**: `api/routes_screen.py`, lines 27–34, 83–90 (`GET /screen/breakdown`)
- **Backend Output Schema**:
  ```python
  return {
      "productive_min":  prod_s // 60,
      "distracting_min": dist_s // 60,
      "neutral_min":     neut_s // 60,
      "total_min":       (prod_s + dist_s + neut_s) // 60,
      "top_productive":  top_apps("productive"),
      "top_distracting": top_apps("distracting"),
  }
  ```
- **Observed Behavior**: `renderTopApps` checks `data.top_apps` and `data.apps` (both `undefined`), setting `apps` to `[]`. As a result, the UI always renders `<div class="top-apps-empty">No productive app activity recorded</div>` regardless of actual API data.

### 1.3 AI Recommendations Render `[object Object]`
- **File**: `static/dashboard.html`, lines 1692–1710 (`renderStudyRecs`)
- **Code Quote**:
  ```javascript
  const msg = r.message || r.text || r;
  return `
    <li class="rec-item">
      <span class="rec-priority ${prio}">${prio.toUpperCase()}</span>
      <span class="text-xs text-primary">${esc(msg)}</span>
    </li>
  `;
  ```
- **Backend File**: `modules/ai_layer/study_advisor.py`, lines 66–80, 268–270 (`GET /study/recommendations`)
- **Backend Output Schema**: `recommendations` list items use the key `"recommendation"` (e.g. `[{"recommendation": "Prioritise Math...", "priority": "high"}]`).
- **Observed Behavior**: `r.message` and `r.text` are undefined. `msg` falls back to the object `r`, which `esc(msg)` stringifies to `"[object Object]"`.

### 1.4 Quick-Add Fallback `POST /assignments/` HTTP 422 Error
- **File**: `static/dashboard.html`, lines 1403–1407 (`handleQuickAdd`)
- **Code Quote**:
  ```javascript
  const fallbackRes = await fetch('/assignments/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title: text, subject: 'General', priority: 'medium' })
  });
  ```
- **Backend File**: `api/routes_assignments.py`, lines 21–26 (`AssignmentCreate`)
- **Backend Input Schema**:
  ```python
  class AssignmentCreate(BaseModel):
      title:    str
      subject:  Optional[str] = None
      due_date: date
      priority: Optional[str] = "medium"
  ```
- **Observed Behavior**: `due_date` is a required field in FastAPI `AssignmentCreate`. The fallback request in `handleQuickAdd` omits `due_date`, causing FastAPI to reject requests with `422 Unprocessable Entity`.

### 1.5 Unescaped Single Quotes in `markDone` Inline Event Handler
- **File**: `static/dashboard.html`, line 1360 (`renderAssignments`)
- **Code Quote**:
  ```javascript
  <li class="asgn-item ${isDone ? 'done' : ''}" onclick="markDone(${item.id}, '${esc(item.title)}')">
  ```
- **File**: `static/dashboard.html`, line 1014 (`esc` definition):
  ```javascript
  const esc = s => String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  ```
- **Observed Behavior**: `esc()` escapes `"`, `<`, `>`, `&`, but not `'`. If an assignment title contains an apostrophe (e.g. `"John's Math Homework"`), the HTML attribute breaks into `onclick="markDone(1, 'John's Math Homework')"`, throwing an `Uncaught SyntaxError` on click.

### 1.6 Assignment Urgency Date Comparison Flaw
- **File**: `static/dashboard.html`, lines 1345–1355 (`renderAssignments`)
- **Code Quote**:
  ```javascript
  if (item.due_date < todayStr) { ... }
  else if (item.due_date === todayStr) { ... }
  ```
- **Backend File**: `main.py`, line 132 (`websocket_endpoint` task broadcast) sends `"due_date": str(a.due_date)`.
- **Observed Behavior**: If `item.due_date` contains time strings or ISO format (e.g. `"2026-08-06T18:00:00"`), `"2026-08-06T18:00:00" === "2026-08-06"` evaluates to `false`, causing assignments due today to misclassify as `urgency-soon`.

### 1.7 Study Plan Field Name Mismatches
- **File**: `static/dashboard.html`, lines 1720–1725 (`renderStudyPlan`)
- **Code Quote**: `${esc(item.time || '10:00 AM')}`, `${esc(item.duration || '45m')}`
- **Backend File**: `modules/ai_layer/study_advisor.py`, lines 230–236: returns `start_time`, `end_time`, `duration_min`.
- **Observed Behavior**: `item.time` and `item.duration` are undefined in backend payload, causing the UI to permanently display hardcoded default fallbacks (`"10:00 AM"` and `"45m"`).

---

## 2. Logic Chain

1. **Premise**: `static/dashboard.html` must function reliably as a single-page application and match the API schemas defined in the FastAPI backend (`api/` and `modules/`).
2. **Analysis of WS Engine**:
   - `connectWebSocket()` implements exponential backoff reconnection (`wsRetryMs = Math.min(wsRetryMs * 1.5, 12000)`).
   - All 10 WS event types (`stats_update`, `window_change`, `cv_event`, `roast`, `tasks_list`, `morning_qa`, `reminder`, `eod_report`, `voice_response`, `study_advice`) are handled in `handleWSEvent`.
   - However, no 25-second heartbeat ping loop exists in `connectWebSocket()`, leaving long-lived connections vulnerable to silent dropped sockets without ping detection.
3. **Analysis of REST API Bindings & UI Renderers**:
   - `fetchStats()`, `fetchHistory()`, `fetchAssignments()`, `fetchScreenBreakdown()`, `fetchStudyRecommendations()`, `markDone()`, `submitQA()` invoke correct API endpoints.
   - Schema mismatches in client UI renderers break features at runtime:
     - `GET /screen/breakdown` payload key `top_productive`/`top_distracting` is not read by `renderTopApps()`, making Top Apps permanently empty.
     - `GET /study/recommendations` payload key `recommendation` is ignored by `renderStudyRecs()`, rendering `[object Object]`.
     - `POST /assignments/` fallback in `handleQuickAdd()` omits `due_date`, triggering HTTP 422.
     - Single-quote titles break inline `onclick` JS syntax in `renderAssignments()`.
     - `renderStudyPlan()` looks for `item.time` instead of `item.start_time`/`item.end_time`, showing fixed fallback strings.
4. **Deduction**: Because the dashboard contains missing WebSocket specifications and runtime rendering bugs across multiple features, it cannot pass verification in its current state.

---

## 3. Caveats

- **No backend Python edits performed**: Pursuant to project constraints, only static frontend analysis and verification were performed; no backend files were modified.
- **Dynamic WS event flooding**: Tested event dispatch structure statically against backend `push_event` calls. Live browser DOM stress testing under 100+ msg/sec bursts was not conducted.

---

## 4. Conclusion

**Verdict**: **`REQUEST_CHANGES`**

The JavaScript engine in `static/dashboard.html` has intact syntax structure, ES6 modules, theme persistence, and WS event dispatch wiring. However, changes are requested to resolve:
1. Missing 25s WebSocket heartbeat ping mechanism.
2. Renderer payload key mismatches (`top_productive`/`top_distracting` in `renderTopApps`, `recommendation` in `renderStudyRecs`, `start_time`/`end_time`/`duration_min` in `renderStudyPlan`).
3. HTTP 422 validation failure on fallback `POST /assignments/` due to missing `due_date`.
4. Single-quote escaping flaw in assignment list `markDone` event handlers.
5. ISO datetime comparison flaw in assignment urgency badges.

---

## 5. Verification Method

1. **Verify Missing Heartbeat Ping**:
   - Inspect `static/dashboard.html` lines 1146–1185. Note absence of `setInterval` calling `ws.send(JSON.stringify({ type: 'ping' }))`.

2. **Verify Top Apps Key Mismatch**:
   - Inspect `static/dashboard.html` line 1655 (`const apps = data?.top_apps || data?.apps || [];`) vs `api/routes_screen.py` line 88–89 (`top_productive`, `top_distracting`).

3. **Verify AI Recommendations `[object Object]` Bug**:
   - Inspect `static/dashboard.html` line 1702 (`const msg = r.message || r.text || r;`) vs `modules/ai_layer/study_advisor.py` line 268 (`"recommendation": ...`).

4. **Verify Quick-Add Fallback HTTP 422**:
   - Inspect `static/dashboard.html` line 1405 (`body: JSON.stringify({ title: text, subject: 'General', priority: 'medium' })`) vs `api/routes_assignments.py` line 24 (`due_date: date` required).

5. **Verify Single Quote Syntax Bug**:
   - Inspect `static/dashboard.html` line 1360 (`onclick="markDone(${item.id}, '${esc(item.title)}')"`). Test with assignment title `Task's name`.
