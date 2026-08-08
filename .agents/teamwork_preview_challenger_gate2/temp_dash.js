
    tailwind.config = {
      darkMode: ['class', '[data-theme="dark"]'],
      theme: {
        extend: {
          fontFamily: {
            sans: ['Plus Jakarta Sans', 'system-ui', 'sans-serif'],
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
  

    /* ═══════════════════════════════════════════════════════════════════════════
       MIMO DASHBOARD MASTER JS ENGINE
       ═══════════════════════════════════════════════════════════════════════════ */

    // Global State Single-Source-of-Truth
    const S = {
      score: 0,
      grade: 'F',
      verdict: '',
      prodMin: 0,
      distMin: 0,
      neutMin: 0,
      deskMin: 0,
      distCount: 0,
      longestMin: 0,
      presence: 'unknown',
      currentApp: '—',
      currentTitle: '',
      currentCat: 'neutral',
      assignments: [],
      roasts: [],
      history: [],
      streak: 0,
      studyRecs: [],
      studyPlan: [],
      patterns: [],
      breakdown: null,
      
      // Timer State
      timer: {
        mode: 'pomodoro',
        durationSeconds: 1500,
        elapsedSeconds: 0,
        running: false,
        intervalId: null
      },

      // QA Queue State
      qaQuestions: [],
      qaIndex: 0,

      // Theme State
      theme: localStorage.getItem('mimo_theme') || 'dark'
    };

    // Utilities
    const esc = s => String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    const fmtTime = d => (d instanceof Date && !isNaN(d)) ? d.toLocaleTimeString('en-US',{hour:'2-digit',minute:'2-digit',hour12:true}) : '—';
    const formatMin = mins => (!mins || mins <= 0) ? '0m' : (mins < 60 ? mins + 'm' : `${Math.floor(mins/60)}h ${mins%60}m`);

    /* ═══════════════════════════════════════════════════════════════════════════
       1. BOOTSTRAP & INITIALIZATION
       ═══════════════════════════════════════════════════════════════════════════ */
    document.addEventListener('DOMContentLoaded', () => {
      applyTheme(S.theme);
      startClock();
      initBreakdownChart();
      loadInitialData();
      connectWebSocket();

      if (typeof lucide !== 'undefined') {
        lucide.createIcons();
      }
    });

    function startClock() {
      const clockEl = document.getElementById('clock');
      const tick = () => {
        if (clockEl) clockEl.textContent = new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      };
      tick();
      setInterval(tick, 1000);
    }

    /* ═══════════════════════════════════════════════════════════════════════════
       2. REST API DATA LOADERS
       ═══════════════════════════════════════════════════════════════════════════ */
    async function loadInitialData() {
      await Promise.allSettled([
        fetchStats(),
        fetchHistory(),
        fetchAssignments(),
        fetchScreenBreakdown(),
        fetchStudyRecommendations()
      ]);
    }

    async function fetchStats() {
      try {
        const res = await fetch('/reports/stats');
        if (!res.ok) return;
        const data = await res.json();
        applyStats(data);
      } catch (e) {
        console.warn('Failed to fetch stats:', e);
      }
    }

    function applyStats(stats) {
      if (!stats) return;
      S.score = stats.focus_score !== undefined ? stats.focus_score : (stats.score || 0);
      S.grade = stats.letter_grade || stats.grade || 'F';
      S.verdict = stats.score_verdict || stats.verdict || '';
      S.prodMin = stats.productive_min || 0;
      S.distMin = stats.distracting_min || 0;
      S.neutMin = stats.neutral_min || 0;
      S.deskMin = stats.desk_time_min || 0;
      S.distCount = stats.distraction_count || 0;
      S.longestMin = stats.longest_focus_min || 0;

      renderGauge();
      renderBars();
      renderCounters();
    }

    async function fetchHistory() {
      try {
        const res = await fetch('/reports/history?days=7');
        if (!res.ok) return;
        const data = await res.json();
        S.history = Array.isArray(data) ? data : (data.history || []);
        renderHistory(S.history);
      } catch (e) {
        console.warn('Failed to fetch history:', e);
      }
    }

    async function fetchAssignments() {
      try {
        let res = await fetch('/assignments/');
        if (!res.ok) {
          res = await fetch('/assignments/upcoming?days=14');
        }
        if (!res.ok) return;
        const data = await res.json();
        S.assignments = Array.isArray(data) ? data : (data.tasks || data.assignments || []);
        renderAssignments(S.assignments);
      } catch (e) {
        console.warn('Failed to fetch assignments:', e);
      }
    }

    async function fetchScreenBreakdown() {
      try {
        const res = await fetch('/screen/breakdown');
        if (!res.ok) return;
        const data = await res.json();
        S.breakdown = data;
        renderBreakdownChart(data);
        renderTopApps(data);
      } catch (e) {
        console.warn('Failed to fetch screen breakdown:', e);
      }
    }

    async function fetchStudyRecommendations() {
      try {
        const res = await fetch('/study/recommendations');
        if (!res.ok) return;
        const data = await res.json();
        S.studyRecs = data.recommendations || [];
        S.studyPlan = data.daily_study_plan || [];
        S.patterns = data.weekly_patterns || [];

        renderStudyRecs();
        renderStudyPlan();
        renderPatterns();
      } catch (e) {
        console.warn('Failed to fetch study recs:', e);
      }
    }

    /* ═══════════════════════════════════════════════════════════════════════════
       3. WEBSOCKET ENGINE WITH EXPONENTIAL BACKOFF
       ═══════════════════════════════════════════════════════════════════════════ */
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

    function handleWSEvent(msg) {
      switch (msg.type) {
        case 'stats_update':
          applyStats(msg.stats);
          break;
        case 'window_change':
          applyWindow(msg);
          break;
        case 'cv_event':
          applyPresence(msg.event);
          break;
        case 'roast':
          addRoast(msg);
          break;
        case 'assignment_added':
        case 'assignment_updated':
        case 'assignment_done':
          fetchAssignments();
          break;
        case 'tasks_list':
          renderAssignments(msg.tasks || []);
          break;
        case 'reminder':
          showToast('🔔 ' + (msg.message || msg.text || 'Reminder'));
          break;
        case 'morning_qa':
          startQA(msg.questions || []);
          break;
        case 'eod_report':
          showToast('📊 EOD Summary: ' + (msg.report?.summary || 'Report generated'));
          break;
        case 'study_advice':
          showToast('🎯 ' + (msg.message || 'Study advice received'));
          break;
        case 'voice_response':
          showToast('🔊 ' + (msg.message || 'Voice update'));
          break;
      }
    }

    /* ═══════════════════════════════════════════════════════════════════════════
       4. UI RENDERERS
       ═══════════════════════════════════════════════════════════════════════════ */
    const GAUGE_C = 440;

    function renderGauge() {
      const fill = document.getElementById('gauge-fill');
      const scoreEl = document.getElementById('gauge-score');
      const gradeEl = document.getElementById('grade-badge');
      const verdictEl = document.getElementById('score-verdict');

      if (!fill || !scoreEl) return;
      const score = Math.max(0, Math.min(100, S.score));
      fill.style.strokeDashoffset = GAUGE_C - (score / 100) * GAUGE_C;

      scoreEl.textContent = Math.round(score);

      if (gradeEl) {
        gradeEl.textContent = S.grade;
        const cleanClass = 'grade-' + String(S.grade).replace('+', '');
        gradeEl.className = `grade-badge ${cleanClass}`;
      }

      if (verdictEl) verdictEl.textContent = S.verdict || 'Tracking active';
    }

    function renderBars() {
      const total = Math.max(S.prodMin + S.distMin + S.neutMin, 1);
      
      const updateBar = (key, val) => {
        const f = document.getElementById('bf-' + key);
        const v = document.getElementById('bv-' + key);
        if (f) f.style.width = Math.round((val / total) * 100) + '%';
        if (v) v.textContent = formatMin(val);
      };

      updateBar('prod', S.prodMin);
      updateBar('dist', S.distMin);
      updateBar('neut', S.neutMin);
    }

    function renderCounters() {
      const dt = document.getElementById('desk-time');
      const dc = document.getElementById('dist-count');
      const fs = document.getElementById('focus-streak');

      if (dt) dt.textContent = S.deskMin;
      if (dc) dc.textContent = S.distCount;
      if (fs) fs.textContent = S.longestMin;
    }

    function applyWindow(msg) {
      S.currentApp = msg.app || '—';
      S.currentTitle = msg.title || '';
      S.currentCat = (msg.category || 'neutral').toLowerCase();

      const appCard = document.getElementById('app-card');
      const appName = document.getElementById('app-name');
      const appTitle = document.getElementById('app-title');
      const catBadge = document.getElementById('cat-badge');

      if (appCard) appCard.className = `card ${S.currentCat}`;
      if (appName) appName.textContent = S.currentApp;
      if (appTitle) appTitle.textContent = S.currentTitle || 'Active Window';
      if (catBadge) {
        catBadge.textContent = S.currentCat.toUpperCase();
        catBadge.className = `cat-badge ${S.currentCat}`;
      }

      prependActivityLog(msg);
    }

    function prependActivityLog(msg) {
      const list = document.getElementById('act-list');
      if (!list) return;

      const cat = (msg.category || 'neutral').toLowerCase();
      const li = document.createElement('li');
      li.className = 'act-item';
      li.innerHTML = `
        <span class="act-dot ${cat}"></span>
        <span class="act-app" title="${esc(msg.title || '')}">${esc(msg.app || 'App')} — ${esc(msg.title || '')}</span>
        <span class="act-time">${fmtTime(new Date())}</span>
      `;

      list.insertBefore(li, list.firstChild);
      while (list.children.length > 25) list.removeChild(list.lastChild);
    }

    function applyPresence(evt) {
      S.presence = evt;
      const dot = document.getElementById('pres-dot');
      const txt = document.getElementById('pres-text');
      const det = document.getElementById('pres-detail');

      if (dot) dot.className = `pres-dot ${evt}`;
      if (txt) {
        txt.textContent = evt === 'present' ? 'User Present at Desk' : (evt === 'distracted' ? 'Distraction Detected' : 'User Away from Desk');
      }
      if (det) det.textContent = evt === 'present' ? 'Camera active & focused' : (evt === 'distracted' ? 'Attention diverted' : 'No user detected');
    }

    function renderAssignments(list) {
      const container = document.getElementById('asgn-list');
      if (!container) return;

      if (!list || list.length === 0) {
        container.innerHTML = '<li class="text-xs text-muted text-center py-3">No upcoming assignments! 🎉</li>';
        return;
      }

      const todayStr = new Date().toISOString().split('T')[0];

      container.innerHTML = list.map(item => {
        const isDone = item.status === 'done' || item.completed;
        let urgencyClass = 'urgency-ok';
        let urgencyLabel = item.due_date || 'Upcoming';

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

        const prio = (item.priority || 'medium').toLowerCase();
        const safeTitle = esc(item.title).replace(/'/g, "\\'");

        return `
          <li class="asgn-item ${isDone ? 'done' : ''}" onclick="markDone(${item.id}, '${safeTitle}')">
            <div class="asgn-bar ${prio}"></div>
            <div class="asgn-info">
              <div class="asgn-title">${esc(item.title)}</div>
              <div class="asgn-sub">${esc(item.subject || 'General')}</div>
            </div>
            <span class="urgency-badge ${urgencyClass}">${urgencyLabel}</span>
          </li>
        `;
      }).join('');
    }

    async function markDone(id, title) {
      try {
        const res = await fetch(`/assignments/${id}/done`, { method: 'POST' });
        if (res.ok) {
          showToast(`✓ Marked "${title}" as completed`);
          fetchAssignments();
        }
      } catch (e) {
        showToast('Failed to update assignment status');
      }
    }

    async function handleQuickAdd(event) {
      event.preventDefault();
      const input = document.getElementById('quick-input');
      const text = input ? input.value.trim() : '';
      if (!text) return;

      try {
        const res = await fetch('/assignments/nlp', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text })
        });

        if (res.ok) {
          showToast('✓ Assignment added!');
          if (input) input.value = '';
          fetchAssignments();
        } else {
          // Fallback to structured POST if NLP unavailable
          const today = new Date().toISOString().split('T')[0];
          const fallbackRes = await fetch('/assignments/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: text, subject: 'General', due_date: today, priority: 'medium' })
          });
          if (fallbackRes.ok) {
            showToast('✓ Assignment added!');
            if (input) input.value = '';
            fetchAssignments();
          }
        }
      } catch (e) {
        showToast('Failed to add assignment');
      }
    }

    function addRoast(msg) {
      const container = document.getElementById('roast-msgs');
      if (!container) return;

      const text = msg.message || msg.text || msg.roast || 'Stay focused!';
      const trigger = msg.trigger || 'Accountability';

      const card = document.createElement('div');
      card.className = 'roast-msg';
      card.innerHTML = `
        <span class="roast-icon">🔥</span>
        <div>
          <div class="text-xs font-bold text-red mb-0.5">${esc(trigger)} Alert</div>
          <div class="text-xs text-primary leading-relaxed">${esc(text)}</div>
        </div>
      `;

      if (container.children.length === 1 && container.children[0].classList.contains('text-muted')) {
        container.innerHTML = '';
      }

      container.insertBefore(card, container.firstChild);
      showToast('🔥 AI Roast Received!');
    }

    /* ═══════════════════════════════════════════════════════════════════════════
       5. 7-DAY HISTORY BAR CHART & TOOLTIPS
       ═══════════════════════════════════════════════════════════════════════════ */
    function renderHistory(historyData) {
      const barsContainer = document.getElementById('week-bars');
      const labelsContainer = document.getElementById('week-day-labels');
      const streakNum = document.getElementById('streak-num');

      if (!barsContainer || !labelsContainer) return;

      const days = Array.isArray(historyData) ? historyData : [];
      
      let currentStreak = 0;
      for (let i = days.length - 1; i >= 0; i--) {
        if ((days[i].focus_score || days[i].score || 0) >= 50) {
          currentStreak++;
        } else {
          break;
        }
      }
      S.streak = currentStreak;
      if (streakNum) streakNum.textContent = S.streak;

      if (days.length === 0) {
        barsContainer.innerHTML = '<div class="text-xs text-muted text-center w-full py-4">No history data available</div>';
        labelsContainer.innerHTML = '';
        return;
      }

      const lastIndex = days.length - 1;
      const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

      barsContainer.innerHTML = days.map((day, idx) => {
        const score = Math.max(0, Math.min(100, day.focus_score || day.score || 0));
        const isToday = idx === lastIndex;
        
        let barClass = 'bad';
        if (score >= 80) barClass = 'good';
        else if (score >= 60) barClass = 'ok';
        if (isToday) barClass += ' today';
        if (score === 0) barClass = 'empty';

        const heightPct = Math.max(8, score);

        return `
          <div class="week-bar-wrapper" 
               onmouseenter="showChartTooltip(event, ${idx})" 
               onmouseleave="hideChartTooltip()" 
               onmousemove="moveChartTooltip(event)">
            <div class="week-bar ${barClass}" style="height: ${heightPct}%"></div>
          </div>
        `;
      }).join('');

      labelsContainer.innerHTML = days.map((day, idx) => {
        const d = new Date(day.date || Date.now());
        const dayLabel = dayNames[d.getDay()] || 'Day';
        const isToday = idx === lastIndex;
        return `
          <div class="week-day-label ${isToday ? 'today' : ''}">${isToday ? 'Today' : dayLabel}</div>
        `;
      }).join('');
    }

    function showChartTooltip(evt, idx) {
      const tooltip = document.getElementById('chart-tooltip');
      if (!tooltip || !S.history || !S.history[idx]) return;

      const item = S.history[idx];
      const d = new Date(item.date || Date.now());
      const dateStr = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      const isToday = idx === S.history.length - 1;

      document.getElementById('tooltip-date').textContent = dateStr;
      document.getElementById('tooltip-tag').style.display = isToday ? 'inline-block' : 'none';
      document.getElementById('tooltip-score').textContent = `${Math.round(item.focus_score || item.score || 0)}/100`;
      document.getElementById('tooltip-prod').textContent = formatMin(item.productive_min || 0);
      document.getElementById('tooltip-dist').textContent = formatMin(item.distracting_min || 0);

      tooltip.style.opacity = '1';
      moveChartTooltip(evt);
    }

    function moveChartTooltip(evt) {
      const tooltip = document.getElementById('chart-tooltip');
      if (!tooltip) return;
      const rect = evt.currentTarget.getBoundingClientRect();
      const parentRect = evt.currentTarget.parentElement.getBoundingClientRect();
      const left = rect.left - parentRect.left + (rect.width / 2);
      tooltip.style.left = `${left}px`;
      tooltip.style.top = `0px`;
    }

    function hideChartTooltip() {
      const tooltip = document.getElementById('chart-tooltip');
      if (tooltip) tooltip.style.opacity = '0';
    }

    /* ═══════════════════════════════════════════════════════════════════════════
       6. APP USAGE BREAKDOWN DOUGHNUT CHART & TOP APPS
       ═══════════════════════════════════════════════════════════════════════════ */
    let breakdownChart = null;

    function initBreakdownChart() {
      const ctx = document.getElementById('breakdown-doughnut-canvas');
      if (!ctx) return;
      
      breakdownChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
          labels: ['Productive', 'Distracting', 'Neutral'],
          datasets: [{
            data: [0, 0, 0],
            backgroundColor: ['#22c55e', '#f03a3a', '#7c6fe0'],
            borderColor: 'transparent',
            borderWidth: 0,
            hoverOffset: 6
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          cutout: '78%',
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: function(context) {
                  const label = context.label || '';
                  const value = context.raw || 0;
                  return `${label}: ${formatMin(value)}`;
                }
              }
            }
          }
        }
      });
    }

    function renderBreakdownChart(data) {
      if (!data) return;
      const prod = data.productive_min || S.prodMin || 0;
      const dist = data.distracting_min || S.distMin || 0;
      const neut = data.neutral_min || S.neutMin || 0;
      const total = prod + dist + neut;

      if (breakdownChart) {
        breakdownChart.data.datasets[0].data = [prod, dist, neut];
        breakdownChart.update();
      }

      const centerVal = document.getElementById('center-total-val');
      if (centerVal) {
        centerVal.textContent = (total / 60).toFixed(1) + 'h';
      }

      const totalBadge = document.getElementById('breakdown-total-badge');
      if (totalBadge) {
        totalBadge.textContent = `Total: ${formatMin(total)}`;
      }

      const legendProd = document.getElementById('legend-prod-val');
      const legendDist = document.getElementById('legend-dist-val');
      const legendNeut = document.getElementById('legend-neut-val');

      const pPct = total > 0 ? Math.round((prod / total) * 100) : 0;
      const dPct = total > 0 ? Math.round((dist / total) * 100) : 0;
      const nPct = total > 0 ? Math.round((neut / total) * 100) : 0;

      if (legendProd) legendProd.textContent = `${formatMin(prod)} (${pPct}%)`;
      if (legendDist) legendDist.textContent = `${formatMin(dist)} (${dPct}%)`;
      if (legendNeut) legendNeut.textContent = `${formatMin(neut)} (${nPct}%)`;
    }

    function updateBreakdownTheme(theme) {
      if (!breakdownChart) return;
      const isDark = theme === 'dark';
      breakdownChart.options.plugins.tooltip.backgroundColor = isDark ? 'rgba(15,23,42,0.95)' : 'rgba(255,255,255,0.95)';
      breakdownChart.options.plugins.tooltip.titleColor = isDark ? '#ffffff' : '#0f172a';
      breakdownChart.options.plugins.tooltip.bodyColor = isDark ? '#cbd5e1' : '#475569';
      breakdownChart.update();
    }

    function toggleBreakdownSegment(index) {
      if (!breakdownChart) return;
      const meta = breakdownChart.getDatasetMeta(0);
      meta.data[index].hidden = !meta.data[index].hidden;
      breakdownChart.update();

      const pills = ['pill-prod', 'pill-dist', 'pill-neut'];
      const pill = document.getElementById(pills[index]);
      if (pill) {
        pill.classList.toggle('inactive', meta.data[index].hidden);
      }
    }

    let currentTopAppsTab = 'productive';

    function switchTopAppsTab(tab) {
      currentTopAppsTab = tab;
      const prodTab = document.getElementById('tab-top-prod');
      const distTab = document.getElementById('tab-top-dist');
      if (prodTab) prodTab.className = `tab-btn ${tab === 'productive' ? 'active' : ''}`;
      if (distTab) distTab.className = `tab-btn ${tab === 'distracting' ? 'active' : ''}`;
      renderTopApps(S.breakdown);
    }

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

    /* ═══════════════════════════════════════════════════════════════════════════
       7. AI STUDY RECOMMENDATIONS & PATTERNS RENDERER
       ═══════════════════════════════════════════════════════════════════════════ */
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

    function renderPatterns() {
      const list = document.getElementById('insight-list');
      if (!list) return;
      const patterns = S.patterns;
      if (!patterns || patterns.length === 0) {
        list.innerHTML = `
          <li class="insight-item"><span>💡</span><span>Peak focus observed during morning study sessions.</span></li>
          <li class="insight-item"><span>⚡</span><span>Frequent task switching detected after 3:00 PM.</span></li>
        `;
        return;
      }
      list.innerHTML = patterns.map(p => `
        <li class="insight-item">
          <span>💡</span>
          <span>${esc(p.insight || p.message || p)}</span>
        </li>
      `).join('');
    }

    /* ═══════════════════════════════════════════════════════════════════════════
       8. FOCUS SESSION TIMER CONTROLLER
       ═══════════════════════════════════════════════════════════════════════════ */
    function setTimerMode(mode) {
      S.timer.mode = mode;
      S.timer.durationSeconds = mode === 'pomodoro' ? 1500 : 3000;
      S.timer.elapsedSeconds = 0;
      const modeLbl = document.getElementById('timer-mode-lbl');
      if (modeLbl) modeLbl.textContent = mode === 'pomodoro' ? 'Pomodoro Session' : 'Deep Work Session';
      updateTimerDisplay();
    }

    function toggleTimer() {
      const btn = document.getElementById('timer-start-btn');
      if (S.timer.running) {
        clearInterval(S.timer.intervalId);
        S.timer.running = false;
        if (btn) { btn.textContent = 'Resume Focus'; btn.className = 'timer-btn start'; }
      } else {
        S.timer.running = true;
        if (btn) { btn.textContent = 'Pause Focus'; btn.className = 'timer-btn pause'; }
        S.timer.intervalId = setInterval(() => {
          S.timer.elapsedSeconds++;
          updateTimerDisplay();
          if (S.timer.elapsedSeconds >= S.timer.durationSeconds) {
            clearInterval(S.timer.intervalId);
            S.timer.running = false;
            showToast('🎉 Focus Session Complete!');
            if (btn) { btn.textContent = 'Start Focus'; btn.className = 'timer-btn start'; }
          }
        }, 1000);
      }
    }

    function resetTimer() {
      clearInterval(S.timer.intervalId);
      S.timer.running = false;
      S.timer.elapsedSeconds = 0;
      const btn = document.getElementById('timer-start-btn');
      if (btn) { btn.textContent = 'Start Focus'; btn.className = 'timer-btn start'; }
      updateTimerDisplay();
    }

    function updateTimerDisplay() {
      const remaining = Math.max(0, S.timer.durationSeconds - S.timer.elapsedSeconds);
      const m = String(Math.floor(remaining / 60)).padStart(2, '0');
      const s = String(remaining % 60).padStart(2, '0');
      const display = document.getElementById('timer-display');
      const sideDisplay = document.getElementById('sidebar-timer-status');

      if (display) display.textContent = `${m}:${s}`;
      if (sideDisplay) sideDisplay.textContent = S.timer.running ? `${m}:${s} Active` : 'Idle';
    }

    /* ═══════════════════════════════════════════════════════════════════════════
       9. THEME ENGINE & PERSISTENCE
       ═══════════════════════════════════════════════════════════════════════════ */
    function toggleTheme() {
      const newTheme = S.theme === 'dark' ? 'light' : 'dark';
      applyTheme(newTheme);
    }

    function applyTheme(theme) {
      S.theme = theme;
      document.documentElement.setAttribute('data-theme', theme);
      localStorage.setItem('mimo_theme', theme);

      const txt = document.getElementById('theme-btn-text');
      if (txt) txt.textContent = theme === 'dark' ? 'Dark Mode' : 'Light Mode';

      updateBreakdownTheme(theme);
    }

    /* ═══════════════════════════════════════════════════════════════════════════
       10. TOAST & MORNING Q&A CONTROLLER
       ═══════════════════════════════════════════════════════════════════════════ */
    let toastTimeout = null;
    function showToast(msg) {
      const t = document.getElementById('toast');
      if (!t) return;
      t.textContent = msg;
      t.classList.add('show');
      clearTimeout(toastTimeout);
      toastTimeout = setTimeout(() => t.classList.remove('show'), 3500);
    }

    function startQA(questions) {
      if (!questions || questions.length === 0) return;
      S.qaQuestions = questions;
      S.qaIndex = 0;
      showQAQuestion();
      const overlay = document.getElementById('qa-overlay');
      if (overlay) overlay.classList.add('open');
    }

    function showQAQuestion() {
      const qEl = document.getElementById('qa-q');
      const inputEl = document.getElementById('qa-ans');
      if (qEl) qEl.textContent = S.qaQuestions[S.qaIndex] || 'What is your goal today?';
      if (inputEl) inputEl.value = '';
    }

    async function submitQA() {
      const inputEl = document.getElementById('qa-ans');
      const answer = inputEl ? inputEl.value.trim() : '';

      if (answer) {
        try {
          await fetch('/reports/accountability', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: S.qaQuestions[S.qaIndex], answer })
          });
        } catch (e) {}
      }

      S.qaIndex++;
      if (S.qaIndex < S.qaQuestions.length) {
        showQAQuestion();
      } else {
        skipQA();
        showToast('✓ Morning Check-In Completed!');
      }
    }

    function skipQA() {
      const overlay = document.getElementById('qa-overlay');
      if (overlay) overlay.classList.remove('open');
    }

    function toggleMobileMenu() {
      const sidebar = document.getElementById('sidebar');
      if (sidebar) sidebar.classList.toggle('mobile-open');
    }
  