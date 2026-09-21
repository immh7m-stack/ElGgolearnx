(function () {
  'use strict';

  var KEY = 'elgoplan_pomo_sessions_v1';
  var STATE_KEY = 'elgoplan_pomo_timer_v1';
  var DEFAULT_DURATION_MINUTES = 25;
  var accent = '#6366f1';
  var card = '#1e293b';
  var border = '#334155';
  var text = '#f1f5f9';
  var dim = '#94a3b8';

  function loadSessions() {
    try { return JSON.parse(localStorage.getItem(KEY) || '[]'); }
    catch (e) { return []; }
  }
  function saveSessions(s) {
    try { localStorage.setItem(KEY, JSON.stringify(s)); } catch (e) {}
  }
  function loadTimerState() {
    try { return JSON.parse(localStorage.getItem(STATE_KEY) || 'null'); }
    catch (e) { return null; }
  }
  function saveTimerState(state) {
    try { localStorage.setItem(STATE_KEY, JSON.stringify(state)); } catch (e) {}
  }
  function clearTimerState() {
    try { localStorage.removeItem(STATE_KEY); } catch (e) {}
  }
  function fmt(s) {
    var m = Math.floor(s / 60);
    var sec = s % 60;
    return String(m).padStart(2, '0') + ':' + String(sec).padStart(2, '0');
  }
  function getCsrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.content) { return meta.content; }
    var match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
  }
  function getConfig() {
    if (window.ElGoPlanConfig) { return window.ElGoPlanConfig; }
    return { isAuthenticated: false, studySessionUrl: '/api/progress/study-session/' };
  }
  function formatDurationLabel(mins) {
    if (mins >= 60) {
      var hours = Math.floor(mins / 60);
      var rem = mins % 60;
      return rem ? hours + ' ساعة و ' + rem + ' دقيقة' : hours + ' ساعة';
    }
    return mins + ' دقيقة';
  }
  function playAlarm() {
    try {
      var ctx = new (window.AudioContext || window.webkitAudioContext)();
      var osc = ctx.createOscillator();
      var gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.type = 'sine';
      osc.frequency.setValueAtTime(880, ctx.currentTime);
      gain.gain.setValueAtTime(0.1, ctx.currentTime);
      osc.start();
      osc.stop(ctx.currentTime + 0.6);
      setTimeout(function () { ctx.close(); }, 700);
    } catch (e) {}
    setTimeout(function () { alert('انتهت جلسة التركيز!'); }, 100);
  }
  function fetchJSON(url, options) {
    return fetch(url, options).then(function (response) {
      if (!response.ok) {
        throw new Error('Request failed');
      }
      return response.json();
    });
  }

  var config = getConfig();
  var isAuthenticated = config.isAuthenticated;
  var selectedDurationMinutes = DEFAULT_DURATION_MINUTES;
  var timeLeft = selectedDurationMinutes * 60;
  var running = false;
  var interval = null;
  var taskLabel = '';
  var timerState = null;
  var mainActionBtn = null;
  var durationInput = null;
  var unitSelect = null;
  var summaryEl = null;

  var btn = document.createElement('button');
  btn.type = 'button';
  btn.setAttribute('aria-label', 'Pomodoro');
  btn.textContent = '🍅';
  Object.assign(btn.style, {
    position: 'fixed', bottom: '88px', right: '24px', zIndex: '450',
    width: '56px', height: '56px', borderRadius: '50%', cursor: 'pointer',
    border: '2px solid ' + border, background: card, color: text,
    fontSize: '22px', lineHeight: '54px', textAlign: 'center',
    boxShadow: '0 4px 20px rgba(0,0,0,.45)',
    fontFamily: 'ui-sans-serif, system-ui, sans-serif'
  });

  var panel = document.createElement('div');
  Object.assign(panel.style, {
    position: 'fixed', bottom: '156px', right: '24px', zIndex: '451',
    width: '300px', padding: '16px', borderRadius: '16px',
    background: card, border: '1px solid ' + accent + '66',
    boxShadow: '0 8px 32px rgba(0,0,0,.55)', display: 'none',
    color: text, fontFamily: 'ui-sans-serif, system-ui, sans-serif', fontSize: '13px'
  });

  var timeEl = document.createElement('div');
  Object.assign(timeEl.style, {
    textAlign: 'center', fontSize: '30px', fontWeight: '800',
    fontFamily: 'monospace', margin: '8px 0', color: accent
  });
  timeEl.textContent = fmt(timeLeft);

  function resetTimer(cancelServerTimer) {
    if (cancelServerTimer === undefined) {
      cancelServerTimer = true;
    }
    running = false;
    if (interval) { clearInterval(interval); interval = null; }
    timeLeft = selectedDurationMinutes * 60;
    timeEl.textContent = fmt(timeLeft);
    btn.textContent = '🍅';
    if (mainActionBtn) { mainActionBtn.textContent = '▶ تشغيل'; }
    timerState = null;
    clearTimerState();
    if (cancelServerTimer && isAuthenticated && config.studyTimerCancelUrl) {
      fetchJSON(config.studyTimerCancelUrl, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
      }).catch(function () {});
    }
  }

  function persistSession(sessionData) {
    if (isAuthenticated) {
      fetch(config.studySessionUrl, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify(sessionData),
      }).catch(function () {
        var sessions = loadSessions();
        sessions.push(sessionData);
        saveSessions(sessions);
      });
      return;
    }
    var sessions = loadSessions();
    sessions.push(sessionData);
    saveSessions(sessions);
  }

  function syncPendingSessions() {
    if (!isAuthenticated) { return; }
    var sessions = loadSessions();
    if (!sessions.length) { return; }
    var next = sessions.shift();
    saveSessions(sessions);
    fetch(config.studySessionUrl, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken(),
      },
      body: JSON.stringify(next),
    }).catch(function () {
      var pending = loadSessions();
      pending.unshift(next);
      saveSessions(pending);
    });
  }

  function applySelectedDuration() {
    var value = Number(durationInput.value || DEFAULT_DURATION_MINUTES);
    if (Number.isNaN(value) || value < 1) { value = DEFAULT_DURATION_MINUTES; }
    if (unitSelect.value === 'hours') { value = value * 60; }
    selectedDurationMinutes = Math.min(Math.max(Math.round(value), 1), 480);
    if (!running) {
      timeLeft = selectedDurationMinutes * 60;
      timeEl.textContent = fmt(timeLeft);
      btn.textContent = '🍅';
    }
    if (summaryEl) {
      summaryEl.textContent = 'المدة المختارة: ' + formatDurationLabel(selectedDurationMinutes);
    }
  }

  function handleTimerFinished() {
    playAlarm();
    if (isAuthenticated && config.studyTimerFinishUrl) {
      fetchJSON(config.studyTimerFinishUrl, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
      }).catch(function () {
        // If finish fails, session will be recovered on next load.
      });
    } else {
      var today = new Date().toISOString().slice(0, 10);
      persistSession({
        label: taskLabel.trim() || 'جلسة تركيز',
        duration_minutes: selectedDurationMinutes,
        date: today,
      });
    }
    timerState = null;
    clearTimerState();
    resetTimer(false);
  }

  function tick() {
    timeLeft--;
    timeEl.textContent = fmt(timeLeft);
    btn.textContent = fmt(timeLeft);
    if (timeLeft <= 0) {
      clearInterval(interval); interval = null; running = false;
      handleTimerFinished();
    }
  }

  function computeTimeLeft(endAt) {
    var diff = Math.round((new Date(endAt).getTime() - Date.now()) / 1000);
    return Math.max(0, diff);
  }

  function startTimerState(state) {
    timerState = state;
    selectedDurationMinutes = state.duration_minutes || DEFAULT_DURATION_MINUTES;
    timeLeft = computeTimeLeft(state.end_at);
    taskLabel = state.label || '';
    if (summaryEl) {
      summaryEl.textContent = 'المدة المختارة: ' + formatDurationLabel(selectedDurationMinutes);
    }
    if (!running) {
      running = true;
      if (interval) { clearInterval(interval); }
      interval = setInterval(tick, 1000);
      if (mainActionBtn) { mainActionBtn.textContent = 'إيقاف مؤقت'; }
    }
    if (timeLeft <= 0) {
      handleTimerFinished();
    } else {
      if (mainActionBtn) { mainActionBtn.textContent = 'إيقاف مؤقت'; }
      btn.textContent = fmt(timeLeft);
    }
  }

  function restoreLocalTimerState() {
    var state = loadTimerState();
    if (!state || !state.end_at) { return false; }
    var diff = computeTimeLeft(state.end_at);
    if (diff <= 0) {
      clearTimerState();
      playAlarm();
      persistSession({
        label: state.label || 'جلسة تركيز',
        duration_minutes: state.duration_minutes || selectedDurationMinutes,
        date: new Date().toISOString().slice(0, 10),
      });
      return false;
    }
    startTimerState(state);
    return true;
  }

  function restoreServerTimerState() {
    if (!isAuthenticated || !config.studyTimerUrl) { return Promise.resolve(false); }
    return fetchJSON(config.studyTimerUrl, {
      method: 'GET',
      credentials: 'same-origin',
    }).then(function (data) {
      if (data.active) {
        startTimerState({
          label: data.label,
          duration_minutes: data.duration_minutes,
          end_at: data.ends_at,
        });
        return true;
      }
      if (data.finished_session) {
        playAlarm();
        return false;
      }
      return false;
    }).catch(function () {
      return false;
    });
  }

  function startServerTimer(label, duration) {
    if (!config.studyTimerUrl) { return Promise.reject(); }
    return fetchJSON(config.studyTimerUrl, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken(),
      },
      body: JSON.stringify({ label: label, duration_minutes: duration }),
    }).then(function (data) {
      if (data && data.remaining_seconds != null) {
        startTimerState({
          label: data.label,
          duration_minutes: data.duration_minutes,
          end_at: data.end_at,
        });
      }
    });
  }

  function startLocalTimer(label, duration) {
    var startAt = new Date();
    var endAt = new Date(startAt.getTime() + duration * 60000);
    var state = {
      label: label,
      duration_minutes: duration,
      start_at: startAt.toISOString(),
      end_at: endAt.toISOString(),
    };
    saveTimerState(state);
    startTimerState(state);
  }

  function buildPanel() {
    panel.innerHTML = '';
    var head = document.createElement('div');
    head.style.cssText = 'display:flex;justify-content:space-between;align-items:center;margin-bottom:10px';
    var title = document.createElement('strong');
    title.textContent = '🍅 Pomodoro · ElGoPlan';
    title.style.color = accent;
    var close = document.createElement('button');
    close.type = 'button';
    close.textContent = '×';
    close.style.cssText = 'background:none;border:none;color:' + dim + ';cursor:pointer;font-size:20px';
    close.onclick = function () { panel.style.display = 'none'; };
    head.appendChild(title);
    head.appendChild(close);
    panel.appendChild(head);

    var labelInp = document.createElement('input');
    labelInp.placeholder = 'ماذا تدرس الآن؟ · ElGoPlan';
    labelInp.value = taskLabel;
    labelInp.style.cssText = 'width:100%;box-sizing:border-box;padding:8px 10px;border-radius:8px;border:1px solid ' +
      border + ';background:#0f172a;color:' + text + ';margin-bottom:10px;font-size:12px';
    labelInp.addEventListener('input', function () { taskLabel = labelInp.value; });
    panel.appendChild(labelInp);

    var durationWrap = document.createElement('div');
    durationWrap.style.cssText = 'display:grid;grid-template-columns:1fr 90px;gap:8px;margin-bottom:8px';
    durationInput = document.createElement('input');
    durationInput.type = 'number';
    durationInput.min = '1';
    durationInput.max = '480';
    durationInput.value = String(selectedDurationMinutes);
    durationInput.style.cssText = 'padding:8px 10px;border-radius:8px;border:1px solid ' + border + ';background:#0f172a;color:' + text + ';font-size:12px';
    durationInput.addEventListener('change', applySelectedDuration);
    unitSelect = document.createElement('select');
    unitSelect.innerHTML = '<option value="minutes">دقيقة</option><option value="hours">ساعة</option>';
    unitSelect.value = 'minutes';
    unitSelect.style.cssText = 'padding:8px 10px;border-radius:8px;border:1px solid ' + border + ';background:#0f172a;color:' + text + ';font-size:12px';
    unitSelect.addEventListener('change', applySelectedDuration);
    durationWrap.appendChild(durationInput);
    durationWrap.appendChild(unitSelect);
    panel.appendChild(durationWrap);

    var presets = document.createElement('div');
    presets.style.cssText = 'display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px';
    [['25 د', 25], ['45 د', 45], ['1 س', 60], ['2 س', 120], ['3 س', 180]].forEach(function (item) {
      var pp = document.createElement('button');
      pp.type = 'button';
      pp.textContent = item[0];
      pp.style.cssText = 'padding:6px 8px;border-radius:8px;border:1px solid ' + border + ';background:transparent;color:' + dim + ';cursor:pointer;font-size:11px';
      pp.onclick = function () {
        durationInput.value = String(item[1]);
        unitSelect.value = 'minutes';
        applySelectedDuration();
      };
      presets.appendChild(pp);
    });
    panel.appendChild(presets);

    summaryEl = document.createElement('div');
    summaryEl.textContent = 'المدة المختارة: ' + formatDurationLabel(selectedDurationMinutes);
    summaryEl.style.cssText = 'font-size:11px;color:' + dim + ';margin-bottom:10px';
    panel.appendChild(summaryEl);

    timeEl.textContent = fmt(timeLeft);
    timeEl.style.color = accent;
    panel.appendChild(timeEl);

    var row = document.createElement('div');
    row.style.cssText = 'display:flex;gap:8px';
    mainActionBtn = document.createElement('button');
    mainActionBtn.type = 'button';
    mainActionBtn.style.cssText = 'flex:1;padding:10px;border-radius:10px;font-weight:700;cursor:pointer;border:1px solid ' + accent + ';background:rgba(99,102,241,.2);color:' + accent;
    mainActionBtn.textContent = running ? 'إيقاف مؤقت' : '▶ تشغيل';
    mainActionBtn.onclick = function () {
      if (!running) {
        if (timerState && timerState.end_at) {
          running = true;
          if (interval) { clearInterval(interval); }
          interval = setInterval(tick, 1000);
          mainActionBtn.textContent = 'إيقاف مؤقت';
          btn.textContent = fmt(timeLeft);
          return;
        }
        var label = taskLabel.trim() || 'جلسة تركيز';
        var duration = selectedDurationMinutes;
        if (isAuthenticated) {
          startServerTimer(label, duration).catch(function () {
            startLocalTimer(label, duration);
          });
        } else {
          startLocalTimer(label, duration);
        }
      } else {
        running = false;
        if (interval) { clearInterval(interval); interval = null; }
        mainActionBtn.textContent = '▶ تشغيل';
        btn.textContent = '🍅';
      }
    };

    var reset = document.createElement('button');
    reset.type = 'button';
    reset.textContent = '↺';
    reset.style.cssText = 'padding:10px 14px;border-radius:10px;cursor:pointer;border:1px solid ' + border + ';background:transparent;color:' + dim;
    reset.onclick = function () { resetTimer(); };

    row.appendChild(mainActionBtn);
    row.appendChild(reset);
    panel.appendChild(row);
  }

  btn.onclick = function () {
    if (panel.style.display === 'block') {
      panel.style.display = 'none';
      return;
    }
    panel.style.display = 'block';
    buildPanel();
  };

  document.body.appendChild(btn);
  document.body.appendChild(panel);
  syncPendingSessions();
  if (isAuthenticated) {
    restoreServerTimerState();
  } else {
    restoreLocalTimerState();
  }
})();
