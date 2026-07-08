(function () {
  'use strict';
  var KEY = 'elgoplan_pomo_sessions_v1';
  var WORK = 25 * 60;
  var SHORT = 5 * 60;
  var LONG = 15 * 60;
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

  function fmt(s) {
    var m = Math.floor(s / 60);
    var sec = s % 60;
    return String(m).padStart(2, '0') + ':' + String(sec).padStart(2, '0');
  }

  var mode = 'work';
  var dur = { work: WORK, short: SHORT, long: LONG };
  var timeLeft = WORK;
  var running = false;
  var interval = null;
  var taskLabel = '';

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
    width: '280px', padding: '16px', borderRadius: '16px',
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

  var labelInp = document.createElement('input');
  labelInp.placeholder = 'ماذا تدرس الآن؟ · ElGoPlan';
  labelInp.style.cssText = 'width:100%;box-sizing:border-box;padding:8px 10px;border-radius:8px;border:1px solid ' +
    border + ';background:#0f172a;color:' + text + ';margin-bottom:10px;font-size:12px';
  labelInp.addEventListener('input', function () { taskLabel = labelInp.value; });

  function modeColor() {
    return mode === 'work' ? accent : mode === 'short' ? '#4ade80' : '#a78bfa';
  }

  function tick() {
    timeLeft--;
    timeEl.textContent = fmt(timeLeft);
    timeEl.style.color = modeColor();
    btn.textContent = fmt(timeLeft);
    if (timeLeft <= 0) {
      clearInterval(interval);
      interval = null;
      running = false;
      if (mode === 'work') {
        var sessions = loadSessions();
        var today = new Date().toISOString().slice(0, 10);
        sessions.push({ label: taskLabel, date: today, durationMin: WORK / 60 });
        saveSessions(sessions);
      }
      timeLeft = dur[mode];
      timeEl.textContent = fmt(timeLeft);
      btn.textContent = '🍅';
    }
  }

  function buildPanel() {
    panel.innerHTML = '';
    var head = document.createElement('div');
    head.style.cssText = 'display:flex;justify-content:space-between;align-items:center;margin-bottom:10px';
    var title = document.createElement('strong');
    title.textContent = '🍅 Pomodoro · ElGoPlan';
    title.style.color = modeColor();
    var close = document.createElement('button');
    close.type = 'button';
    close.textContent = '×';
    close.style.cssText = 'background:none;border:none;color:' + dim + ';cursor:pointer;font-size:20px';
    close.onclick = function () { panel.style.display = 'none'; };
    head.appendChild(title);
    head.appendChild(close);
    panel.appendChild(head);

    var modes = document.createElement('div');
    modes.style.cssText = 'display:flex;gap:4px;margin-bottom:10px';
    [['work', 'تركيز'], ['short', 'قصيرة'], ['long', 'طويلة']].forEach(function (x) {
      var b = document.createElement('button');
      b.type = 'button';
      b.textContent = x[1];
      b.dataset.m = x[0];
      b.style.cssText = 'flex:1;padding:6px;border-radius:8px;cursor:pointer;font-size:10px;font-weight:700;border:1px solid ' +
        border + ';background:transparent;color:' + dim;
      if (x[0] === mode) {
        b.style.borderColor = modeColor();
        b.style.color = modeColor();
        b.style.background = 'rgba(99,102,241,.12)';
      }
      b.onclick = function () {
        mode = b.dataset.m;
        timeLeft = dur[mode];
        running = false;
        if (interval) { clearInterval(interval); interval = null; }
        buildPanel();
        timeEl.textContent = fmt(timeLeft);
        timeEl.style.color = modeColor();
        btn.textContent = '🍅';
      };
      modes.appendChild(b);
    });
    panel.appendChild(modes);
    timeEl.textContent = fmt(timeLeft);
    timeEl.style.color = modeColor();
    panel.appendChild(timeEl);
    panel.appendChild(labelInp);

    var row = document.createElement('div');
    row.style.cssText = 'display:flex;gap:8px';
    var go = document.createElement('button');
    go.type = 'button';
    go.style.cssText = 'flex:1;padding:10px;border-radius:10px;font-weight:700;cursor:pointer;border:1px solid ' +
      modeColor() + ';background:rgba(99,102,241,.2);color:' + modeColor();
    go.textContent = running ? 'إيقاف مؤقت' : '▶ تشغيل';
    go.onclick = function () {
      running = !running;
      if (running) {
        interval = setInterval(tick, 1000);
        go.textContent = 'إيقاف مؤقت';
        btn.textContent = fmt(timeLeft);
      } else {
        if (interval) { clearInterval(interval); interval = null; }
        go.textContent = '▶ تشغيل';
        btn.textContent = '🍅';
      }
    };
    var reset = document.createElement('button');
    reset.type = 'button';
    reset.textContent = '↺';
    reset.style.cssText = 'padding:10px 14px;border-radius:10px;cursor:pointer;border:1px solid ' + border +
      ';background:transparent;color:' + dim;
    reset.onclick = function () {
      running = false;
      if (interval) { clearInterval(interval); interval = null; }
      timeLeft = dur[mode];
      timeEl.textContent = fmt(timeLeft);
      go.textContent = '▶ تشغيل';
      btn.textContent = '🍅';
    };
    row.appendChild(go);
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
})();
