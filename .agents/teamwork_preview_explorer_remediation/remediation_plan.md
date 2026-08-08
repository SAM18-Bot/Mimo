# Comprehensive Remediation Plan

**Target File**: `static/dashboard.html` & Repository Workspace  
**Author**: remediation_explorer (`teamwork_preview_explorer`)  
**Date**: 2026-08-06  
**Status**: APPROVED FOR IMPLEMENTATION  

---

## 1. Executive Summary

During Milestone 5 audit testing:
1. **Forensic Auditor (`teamwork_preview_auditor_m5_1`)** issued an **INTEGRITY VIOLATION** verdict due to 7 modified Python files and 1 new untracked migration file outside `static/`.
2. **Empirical Challenger (`teamwork_preview_challenger_m5_1`)** issued a **REQUEST_CHANGES** verdict due to 7 JavaScript engine defects in `static/dashboard.html`.

This remediation plan provides exact, step-by-step instructions to:
- Restore 100% backend integrity by reverting all backend Python changes so `git status --short` shows ONLY changes in `static/`.
- Apply 7 precise bug fixes to `static/dashboard.html` to resolve all Challenger 1 defects.

---

## 2. Step 1: Backend Python Integrity Reversion

### Objective
Revert all uncommitted modifications and additions to Python files outside `static/` to comply with Requirement R3 (zero backend modifications).

### Execution Commands (For Worker)
Run the following git commands from the repository root `c:\Users\samee\projects\Mimo`:

```bash
# 1. Revert all modified backend Python files and requirements.txt
git checkout HEAD -- api/routes_auth.py api/routes_screen.py api/routes_settings.py db/models.py modules/ai_layer/daily_report.py modules/assignments/parser.py requirements.txt

# 2. Remove untracked Alembic migration script
git clean -f db/migrations/versions/004_add_user_id_columns.py
```

### Target Workspace Verification
Executing `git status --short` after these commands must yield:
```
 M static/dashboard.html
?? .agents/
```
*(No modified or untracked `.py` or `requirements.txt` files remain)*.

---

## 3. Step 2: Remediating JavaScript Engine Defects in `static/dashboard.html`

### Defect 1: Missing 25-Second WebSocket Heartbeat Ping Loop
- **File**: `static/dashboard.html` (lines ~1143–1185)
- **Root Cause**: `connectWebSocket()` lacks a heartbeat ping interval to keep the socket alive and detect stale connections.
- **Target Code**:
```javascript
    let ws = null;
    let wsRetryMs = 1000;

    function connectWebSocket() {
      const wsDot = document.getElementById('ws-dot');
      const wsLbl = document.getElementById('ws-lbl');

      const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
      const url = `${protocol}://${location.host}/ws`;

      try {
        ws = new WebSocket(url);
      } catch (e) {
        if (wsDot) wsDot.className = 'ws-dot';
        if (wsLbl) wsLbl.textContent = 'Disconnected';
        setTimeout(connectWebSocket, wsRetryMs);
        return;
      }

      ws.onopen = () => {
        wsRetryMs = 1000;
        if (wsDot) wsDot.className = 'ws-dot live';
        if (wsLbl) wsLbl.textContent = 'LIVE';
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          handleWSEvent(msg);
        } catch (e) {}
      };

      ws.onclose = () => {
        if (wsDot) wsDot.className = 'ws-dot';
        if (wsLbl) wsLbl.textContent = 'Reconnecting…';
        setTimeout(connectWebSocket, wsRetryMs);
        wsRetryMs = Math.min(wsRetryMs * 1.5, 12000);
      };

      ws.onerror = () => {
        ws.close();
      };
    }
```
- **Replacement Code**:
```javascript
    let ws = null;
    let wsRetryMs = 1000;
    let wsPingInterval = null;

    function connectWebSocket() {
      const wsDot = document.getElementById('ws-dot');
      const wsLbl = document.getElementById('ws-lbl');

      const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
      const url = `${protocol}://${location.host}/ws`;

      try {
        ws = new WebSocket(url);
      } catch (e) {
        if (wsDot) wsDot.className = 'ws-dot';
        if (wsLbl) wsLbl.textContent = 'Disconnected';
        setTimeout(connectWebSocket, wsRetryMs);
        return;
      }

      ws.onopen = () => {
        wsRetryMs = 1000;
        if (wsDot) wsDot.className = 'ws-dot live';
        if (wsLbl) wsLbl.textContent = 'LIVE';

        if (wsPingInterval) clearInterval(wsPingInterval);
        wsPingInterval = setInterval(() => {
          if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, 25000);
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          handleWSEvent(msg);
        } catch (e) {}
      };

      ws.onclose = () => {
        if (wsPingInterval) {
          clearInterval(wsPingInterval);
          wsPingInterval = null;
        }
        if (wsDot) wsDot.className = 'ws-dot';
        if (wsLbl) wsLbl.textContent = 'Reconnecting…';
        setTimeout(connectWebSocket, wsRetryMs);
        wsRetryMs = Math.min(wsRetryMs * 1.5, 12000);
      };

      ws.onerror = () => {
        ws.close();
      };
    }
```

---

### Defect 2: Top Apps Keys Mismatch (`top_productive` & `top_distracting`)
- **File**: `static/dashboard.html` (lines ~1651–1687)
- **Root Cause**: `renderTopApps()` checks `data.top_apps` and `data.apps` (which do not exist in `GET /screen/breakdown` payload), rendering an empty list.
- **Target Code**:
```javascript
    function renderTopApps(data) {
      const container = document.getElementById('top-apps-list');
      if (!container) return;

      const apps = data?.top_apps || data?.apps || [];
      let filtered = [];

      if (Array.isArray(apps)) {
        filtered = apps.filter(a => (a.category || '').toLowerCase() === currentTopAppsTab);
      } else if (typeof apps === 'object') {
        filtered = apps[currentTopAppsTab] || [];
      }

      if (!filtered || filtered.length === 0) {
        container.innerHTML = `<div class="top-apps-empty">No ${currentTopAppsTab} app activity recorded</div>`;
        return;
      }

      const maxTime = Math.max(...filtered.map(a => a.duration || a.minutes || 1), 1);

      container.innerHTML = filtered.slice(0, 5).map(app => {
        const name = app.name || app.app || 'Unknown App';
        const mins = app.duration || app.minutes || 0;
        const pct = Math.round((mins / maxTime) * 100);
        return `
          <div class="top-app-item">
            <div class="top-app-meta">
              <span class="top-app-name" title="${esc(name)}">${esc(name)}</span>
              <span class="top-app-time">${formatMin(mins)}</span>
            </div>
            <div class="top-app-bar-track">
              <div class="top-app-bar-fill ${currentTopAppsTab}" style="width: ${pct}%"></div>
            </div>
          </div>
        `;
      }).join('');
    }
```
- **Replacement Code**:
```javascript
    function renderTopApps(data) {
      const container = document.getElementById('top-apps-list');
      if (!container) return;

      let filtered = [];
      if (currentTopAppsTab === 'productive') {
        filtered = data?.top_productive || data?.top_apps?.productive || data?.apps?.productive || [];
      } else {
        filtered = data?.top_distracting || data?.top_apps?.distracting || data?.apps?.distracting || [];
      }

      if (!Array.isArray(filtered) || filtered.length === 0) {
        container.innerHTML = `<div class="top-apps-empty">No ${currentTopAppsTab} app activity recorded</div>`;
        return;
      }

      const maxTime = Math.max(...filtered.map(a => a.duration || a.minutes || a.duration_min || 1), 1);

      container.innerHTML = filtered.slice(0, 5).map(app => {
        const name = app.name || app.app || app.title || 'Unknown App';
        const mins = app.duration || app.minutes || app.duration_min || 0;
        const pct = Math.round((mins / maxTime) * 100);
        return `
          <div class="top-app-item">
            <div class="top-app-meta">
              <span class="top-app-name" title="${esc(name)}">${esc(name)}</span>
              <span class="top-app-time">${formatMin(mins)}</span>
            </div>
            <div class="top-app-bar-track">
              <div class="top-app-bar-fill ${currentTopAppsTab}" style="width: ${pct}%"></div>
            </div>
          </div>
        `;
      }).join('');
    }
```

---

### Defect 3: AI Recommendations Rendering `[object Object]`
- **File**: `static/dashboard.html` (lines ~1692–1710)
- **Root Cause**: `renderStudyRecs()` accesses `r.message || r.text || r`, missing `r.recommendation` returned by `/study/recommendations`, which causes `esc(r)` to output `"[object Object]"`.
- **Target Code**:
```javascript
    function renderStudyRecs() {
      const list = document.getElementById('rec-list');
      if (!list) return;
      const recs = S.studyRecs;
      if (!recs || recs.length === 0) {
        list.innerHTML = '<li class="text-xs text-muted text-center py-2">No recommendations available</li>';
        return;
      }
      list.innerHTML = recs.map(r => {
        const prio = (r.priority || 'medium').toLowerCase();
        const msg = r.message || r.text || r;
        return `
          <li class="rec-item">
            <span class="rec-priority ${prio}">${prio.toUpperCase()}</span>
            <span class="text-xs text-primary">${esc(msg)}</span>
          </li>
        `;
      }).join('');
    }
```
- **Replacement Code**:
```javascript
    function renderStudyRecs() {
      const list = document.getElementById('rec-list');
      if (!list) return;
      const recs = S.studyRecs;
      if (!recs || recs.length === 0) {
        list.innerHTML = '<li class="text-xs text-muted text-center py-2">No recommendations available</li>';
        return;
      }
      list.innerHTML = recs.map(r => {
        const prio = (typeof r === 'object' && r.priority ? r.priority : 'medium').toLowerCase();
        const msg = typeof r === 'string' ? r : (r.recommendation || r.message || r.text || JSON.stringify(r));
        return `
          <li class="rec-item">
            <span class="rec-priority ${prio}">${prio.toUpperCase()}</span>
            <span class="text-xs text-primary">${esc(msg)}</span>
          </li>
        `;
      }).join('');
    }
```

---

### Defect 4: Quick-Add Fallback `POST /assignments/` HTTP 422
- **File**: `static/dashboard.html` (lines ~1403–1408)
- **Root Cause**: The structured fallback POST request in `handleQuickAdd()` omits the mandatory `due_date` field required by FastAPI `AssignmentCreate` model.
- **Target Code**:
```javascript
          const fallbackRes = await fetch('/assignments/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: text, subject: 'General', priority: 'medium' })
          });
```
- **Replacement Code**:
```javascript
          const today = new Date().toISOString().split('T')[0];
          const fallbackRes = await fetch('/assignments/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: text, subject: 'General', due_date: today, priority: 'medium' })
          });
```

---

### Defect 5: Single-Quote Escaping in `markDone()` Inline Event Handler
- **File**: `static/dashboard.html` (lines ~1360)
- **Root Cause**: `esc(item.title)` escapes double quotes but not single quotes (`'`). If an assignment title contains an apostrophe (e.g. `"John's Math Homework"`), the HTML attribute evaluates to `onclick="markDone(1, 'John's Math Homework')"`, throwing an `Uncaught SyntaxError`.
- **Target Code**:
```javascript
          <li class="asgn-item ${isDone ? 'done' : ''}" onclick="markDone(${item.id}, '${esc(item.title)}')">
```
- **Replacement Code**:
```javascript
        const safeTitle = esc(item.title).replace(/'/g, "\\'");
        return `
          <li class="asgn-item ${isDone ? 'done' : ''}" onclick="markDone(${item.id}, '${safeTitle}')">
```

---

### Defect 6: Assignment Urgency ISO Datetime Comparison Flaw
- **File**: `static/dashboard.html` (lines ~1345–1355)
- **Root Cause**: Comparing ISO datetime string `"2026-08-06T18:00:00"` directly with date string `"2026-08-06"` (`===`) evaluates to `false`, causing tasks due today to misclassify as `urgency-soon`.
- **Target Code**:
```javascript
        if (item.due_date) {
          if (item.due_date < todayStr) {
            urgencyClass = 'urgency-overdue';
            urgencyLabel = 'Overdue';
          } else if (item.due_date === todayStr) {
            urgencyClass = 'urgency-today';
            urgencyLabel = 'Due Today';
          } else {
            urgencyClass = 'urgency-soon';
          }
        }
```
- **Replacement Code**:
```javascript
        if (item.due_date) {
          const dueDateStr = String(item.due_date).split('T')[0];
          if (dueDateStr < todayStr) {
            urgencyClass = 'urgency-overdue';
            urgencyLabel = 'Overdue';
          } else if (dueDateStr === todayStr) {
            urgencyClass = 'urgency-today';
            urgencyLabel = 'Due Today';
          } else {
            urgencyClass = 'urgency-soon';
          }
        }
```

---

### Defect 7: Study Plan Field Name Mismatches
- **File**: `static/dashboard.html` (lines ~1712–1727)
- **Root Cause**: `renderStudyPlan()` looks for `item.time` and `item.duration` which are undefined in the `/study/recommendations` backend response (which returns `start_time`, `end_time`, and `duration_min`).
- **Target Code**:
```javascript
    function renderStudyPlan() {
      const list = document.getElementById('plan-list');
      if (!list) return;
      const plan = S.studyPlan;
      if (!plan || plan.length === 0) {
        list.innerHTML = '<li class="text-xs text-muted text-center py-2">No slots planned for today</li>';
        return;
      }
      list.innerHTML = plan.map(item => `
        <li class="plan-item">
          <span class="plan-time">${esc(item.time || '10:00 AM')}</span>
          <span class="plan-subject">${esc(item.subject || item.task || 'Study Session')}</span>
          <span class="plan-dur">${esc(item.duration || '45m')}</span>
        </li>
      `).join('');
    }
```
- **Replacement Code**:
```javascript
    function renderStudyPlan() {
      const list = document.getElementById('plan-list');
      if (!list) return;
      const plan = S.studyPlan;
      if (!plan || plan.length === 0) {
        list.innerHTML = '<li class="text-xs text-muted text-center py-2">No slots planned for today</li>';
        return;
      }
      list.innerHTML = plan.map(item => {
        let timeStr = item.time;
        if (!timeStr && item.start_time) {
          timeStr = item.end_time ? `${item.start_time} - ${item.end_time}` : item.start_time;
        }
        if (!timeStr) timeStr = '10:00 AM';

        const subjectStr = item.subject || item.task || item.reason || 'Study Session';

        let durStr = item.duration;
        if (!durStr && item.duration_min) {
          durStr = `${item.duration_min}m`;
        }
        if (!durStr) durStr = '45m';

        return `
          <li class="plan-item">
            <span class="plan-time">${esc(timeStr)}</span>
            <span class="plan-subject">${esc(subjectStr)}</span>
            <span class="plan-dur">${esc(durStr)}</span>
          </li>
        `;
      }).join('');
    }
```

---

## 4. Step 3: Verification & Invalidation Protocol

After the worker executes the remediation plan:

1. **Verify Backend Status**:
   ```bash
   git status --short
   ```
   *Expected Output*: Only `static/dashboard.html` modified. Zero `.py` modifications.

2. **Verify JavaScript Syntax**:
   ```bash
   python -c "
   import re, subprocess
   content = open('static/dashboard.html', encoding='utf-8').read()
   js = '\n'.join(re.findall(r'<script>(.*?)</script>', content, re.DOTALL))
   with open('temp.js','w',encoding='utf-8') as f: f.write(js)
   res = subprocess.run(['node','--check','temp.js'])
   print('JS Exit Code:', res.returncode)
   "
   ```
   *Expected Output*: `JS Exit Code: 0`.

3. **Verify HTML Tag Balancing**:
   ```bash
   python -c "
   import html.parser
   class P(html.parser.HTMLParser):
       def __init__(self): super().__init__(); self.stack=[]
       def handle_starttag(self, tag, attrs):
           if tag not in ['img','br','hr','input','meta','link','circle','line','path','defs','stop','use']: self.stack.append(tag)
       def handle_endtag(self, tag):
           if tag not in ['img','br','hr','input','meta','link','circle','line','path','defs','stop','use'] and self.stack and self.stack[-1]==tag: self.stack.pop()
   p = P()
   p.feed(open('static/dashboard.html', encoding='utf-8').read())
   print('Unclosed Tags:', len(p.stack))
   "
   ```
   *Expected Output*: `Unclosed Tags: 0`.

4. **Verify Pytest Backend Tests**:
   ```bash
   pytest
   ```
   *Expected Output*: All backend tests pass.
