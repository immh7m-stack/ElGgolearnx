/**
 * ElGgolearn — widget المساعد (بدون console في الإنتاج)
 */
(function () {
  const widget = document.getElementById('chat-widget');
  if (!widget) return;

  const toggle = document.getElementById('chat-toggle');
  const panel = document.getElementById('chat-panel');
  const form = document.getElementById('chat-form');
  const input = document.getElementById('chat-input');
  const messages = document.getElementById('chat-messages');
  const SESSION_KEY = 'elgolearn_chat_session_v1';
  const PANEL_KEY = 'elgolearn_chat_panel_open_v1';
  let sessionId = null;
  let restored = false;
  const isDebug =
    typeof window !== 'undefined' &&
    window.location &&
    (window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost');

  function logChat(stage, detail) {
    const d = typeof detail === 'string' ? detail : JSON.stringify(detail);
    if (isDebug) {
      console.error('[ElGgolearn chatbot]', stage, d);
    }
  }

  function contextLabelForPath(pathname) {
    const p = (pathname || '/').split('?')[0].replace(/\/$/, '') || '/';
    const rules = [
      ['/library/search', 'سياق: بحث المكتبة — اسأل عن الكورسات أو كيفية الحفظ والتحميل'],
      ['/library/my', 'سياق: مكتبتك — القوائم، الكتب، والتحميلات'],
      ['/library/watch', 'سياق: مشغّل الدروس — يمكنك السؤال عن الدرس أو عن مشاكل التضمين'],
      ['/library/history', 'سياق: السجل — القوائم التي فتحتها سابقًا'],
      ['/library/sites', 'سياق: مواقع موثوقة للتعلم'],
      ['/plan', 'سياق: ElGoPlan — أهدافك ومهامك على المنصة'],
      ['/dashboard', 'سياق: لوحة التقدّم — المهارات والمشاريع'],
      ['/fields', 'سياق: مسار تعليمي — يمكنك السؤال عن المهارات أو الخطوات التالية'],
      ['/accounts', 'سياق: الحساب — تسجيل الدخول والملف الشخصي'],
      ['/community', 'سياق: المجتمع'],
    ];
    for (let i = 0; i < rules.length; i++) {
      const pre = rules[i][0];
      if (p === pre || p.startsWith(pre + '/')) return rules[i][1];
    }
    if (p === '/' || p === '') return 'سياق عام — اسأل عن المنصة أو عن أي موضوع تقني';
    return 'اسأل عن التعلّم أو عن استخدام منصة ElGgolearn';
  }

  function refreshContextLabel() {
    const el = document.getElementById('chat-context-label');
    if (el) el.textContent = contextLabelForPath(window.location.pathname);
  }
  refreshContextLabel();

  toggle?.addEventListener('click', () => {
    const show = !panel.classList.contains('open');
    setPanelOpen(show);
    refreshContextLabel();
    if (show && !sessionId) startSession();
  });

  function loadSessionId() {
    try { return localStorage.getItem(SESSION_KEY); } catch (e) { return null; }
  }

  function saveSessionId(id) {
    try { localStorage.setItem(SESSION_KEY, String(id)); } catch (e) {}
  }

  function clearSessionId() {
    try { localStorage.removeItem(SESSION_KEY); } catch (e) {}
  }

  function loadPanelOpen() {
    try { return localStorage.getItem(PANEL_KEY) === '1'; } catch (e) { return false; }
  }

  function savePanelOpen(open) {
    try { localStorage.setItem(PANEL_KEY, open ? '1' : '0'); } catch (e) {}
  }

  function setPanelOpen(open) {
    if (!panel) return;
    panel.classList.toggle('open', open);
    panel.classList.toggle('hidden', !open);
    savePanelOpen(open);
  }

  async function restoreHistory(sessionId) {
    try {
      const res = await fetch('/api/chat/' + sessionId + '/history/', {
        method: 'GET',
        credentials: 'same-origin',
      });
      if (!res.ok) {
        logChat('restoreHistory HTTP ' + res.status, await res.text());
        return false;
      }
      const data = await res.json();
      if (!Array.isArray(data)) {
        return false;
      }
      messages.innerHTML = '';
      data.forEach((message) => {
        appendMsg(message.role === 'user' ? 'user' : 'assistant', message.content || '');
      });
      messages.scrollTop = messages.scrollHeight;
      return true;
    } catch (e) {
      logChat('restoreHistory network', e.message || e);
      return false;
    }
  }

  async function restoreSession() {
    const storedId = loadSessionId();
    if (!storedId) return;
    sessionId = storedId;
    const ok = await restoreHistory(sessionId);
    if (!ok) {
      clearSessionId();
      sessionId = null;
      return;
    }
    restored = true;

    if (loadPanelOpen()) {
      setPanelOpen(true);
    }
  }

  // Attempt to restore any previous chat session and history on page load.
  restoreSession();

  async function startSession() {
    if (sessionId && !restored) {
      const ok = await restoreHistory(sessionId);
      if (ok) {
        restored = true;
        return;
      }
      clearSessionId();
      sessionId = null;
    }

    try {
      const res = await fetch('/api/chat/start/', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
        body: JSON.stringify({
          field_slug: widget.dataset.field || '',
          track_level: widget.dataset.level || '',
          module_title: widget.dataset.module || '',
          page_path: window.location.pathname || '/',
        }),
      });
      const text = await res.text();
      if (!res.ok) {
        logChat('startSession HTTP ' + res.status, text.slice(0, 500));
        appendMsg('assistant', 'تعذر بدء المحادثة (HTTP ' + res.status + ').');
        return;
      }
      let data;
      try {
        data = JSON.parse(text);
      } catch (e) {
        logChat('startSession invalid JSON', text);
        appendMsg('assistant', 'خطأ في رد الخادم أثناء بدء المحادثة.');
        return;
      }
      sessionId = data.id;
      saveSessionId(sessionId);
      restored = true;
    } catch (e) {
      logChat('startSession network', e.message || e);
      appendMsg('assistant', 'خطأ شبكة عند بدء المحادثة.');
    }
  }

  function getCsrf() {
    const c = document.cookie.match(/csrftoken=([^;]+)/);
    return c ? c[1] : '';
  }

  function appendMsg(role, text) {
    const el = document.createElement('div');
    el.className = role === 'user' ? 'chat-msg-user' : 'chat-msg-assistant';
    el.textContent = text;
    messages.appendChild(el);
    messages.scrollTop = messages.scrollHeight;
  }

  function appendThinking() {
    const wrap = document.createElement('div');
    wrap.className = 'chat-msg-assistant chat-msg-thinking';
    wrap.setAttribute('aria-busy', 'true');
    wrap.innerHTML =
      '<span class="chat-thinking-label">يفكر…</span>' +
      '<span class="chat-thinking-dots" aria-hidden="true"><span></span><span></span><span></span></span>';
    messages.appendChild(wrap);
    messages.scrollTop = messages.scrollHeight;
    return wrap;
  }

  function removeThinking(node) {
    if (node && node.parentNode) node.parentNode.removeChild(node);
  }

  function appendRateLimitAssistant(text) {
    const wrap = document.createElement('div');
    wrap.className = 'chat-msg-assistant chat-msg-rate-limit';

    const p = document.createElement('div');
    p.textContent = text;
    wrap.appendChild(p);

    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className =
      'mt-2 w-full py-2 rounded-lg bg-brand/20 border border-brand text-brand text-sm font-medium hover:bg-brand/30 transition disabled:opacity-50';
    btn.textContent = 'إعادة المحاولة';
    btn.addEventListener('click', async () => {
      btn.disabled = true;
      const thinking = appendThinking();
      try {
        const res = await fetch('/api/chat/' + sessionId + '/retry-assistant/', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
          body: '{}',
        });
        const bodyText = await res.text();
        let data;
        try {
          data = JSON.parse(bodyText);
        } catch (err) {
          logChat('retry invalid JSON', bodyText);
          appendMsg('assistant', 'رد غير صالح من الخادم.');
          return;
        }
        if (!res.ok) {
          appendMsg('assistant', data.detail || 'تعذرت إعادة المحاولة.');
          return;
        }
        appendMsg('assistant', data.content || '(فارغ)');
        if (data.rate_limit_exhausted) {
          appendRateLimitAssistant('النظام عليه ضغط حالياً، حاول تاني بعد دقيقة 🔄');
        }
      } catch (err) {
        logChat('retry network', err.message || err);
        appendMsg('assistant', 'خطأ شبكة عند إعادة المحاولة.');
      } finally {
        removeThinking(thinking);
        btn.disabled = false;
      }
    });
    wrap.appendChild(btn);
    messages.appendChild(wrap);
    messages.scrollTop = messages.scrollHeight;
  }

  let sending = false;

  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (sending) return;
    const text = input.value.trim();
    if (!text) return;
    if (!sessionId) await startSession();
    if (!sessionId) return;

    appendMsg('user', text);
    input.value = '';
    sending = true;
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) submitBtn.disabled = true;

    const thinking = appendThinking();
    try {
      const res = await fetch('/api/chat/' + sessionId + '/message/', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
        body: JSON.stringify({ content: text }),
      });
      const bodyText = await res.text();
      if (!res.ok) {
        logChat('message HTTP ' + res.status, bodyText.slice(0, 600));
        if (res.status === 429) {
          appendMsg(
            'assistant',
            'النظام عليه ضغط حالياً، حاول تاني بعد دقيقة 🔄'
          );
          return;
        }
        let errMsg = 'HTTP ' + res.status;
        if (res.status === 401 || res.status === 403) errMsg += ' — صلاحية / CSRF';
        if (res.status === 404) errMsg += ' — الجلسة غير موجودة؛ جرّب إغلاق اللوحة وفتحها من جديد';
        appendMsg('assistant', 'لم يصل رد من المساعد (' + errMsg + ').');
        return;
      }
      let data;
      try {
        data = JSON.parse(bodyText);
      } catch (err) {
        logChat('message invalid JSON', bodyText);
        appendMsg('assistant', 'رد غير صالح من الخادم.');
        return;
      }
      if (data.rate_limit_exhausted) {
        appendRateLimitAssistant(data.content || 'النظام عليه ضغط حالياً، حاول تاني بعد دقيقة 🔄');
      } else {
        appendMsg('assistant', data.content || '(فارغ)');
      }
    } catch (err) {
      logChat('message network', err.message || err);
      appendMsg('assistant', 'خطأ شبكة عند إرسال الرسالة.');
    } finally {
      removeThinking(thinking);
      sending = false;
      if (submitBtn) submitBtn.disabled = false;
    }
  });
})();
