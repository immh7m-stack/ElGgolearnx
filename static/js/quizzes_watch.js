(function () {
  var root = document.getElementById('watch-player-root');
  var panel = document.getElementById('quiz-panel');
  var status = document.getElementById('quiz-status');
  var overlay = document.getElementById('quiz-overlay');
  var overlayHeader = document.getElementById('quiz-overlay-header');
  var overlayPanel = document.getElementById('quiz-overlay-panel');
  var overlayStatus = document.getElementById('quiz-overlay-status');
  var closeOverlayButton = document.getElementById('close-quiz-overlay-btn');
  var minimizeOverlayButton = document.getElementById('minimize-quiz-overlay-btn');
  var fullscreenOverlayButton = document.getElementById('fullscreen-quiz-overlay-btn');
  var openOverlayButton = document.getElementById('open-quiz-overlay-btn');
  var loadOverlayQuizzesButton = document.getElementById('load-overlay-quizzes-btn');
  var loadOverlaySegmentButton = document.getElementById('load-overlay-segment-btn');
  var openFullPageButton = document.getElementById('open-full-quiz-page-btn');
  var refreshOverlayButton = document.getElementById('refresh-quiz-overlay-btn');
  if (!root || !panel || !status || !overlay) return;

  var videoId = root.getAttribute('data-first-video') || '';
  if (!videoId) return;

  function escapeHtml(value) {
    return String(value || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function renderLoading(message, targetStatus) {
    var statusTarget = targetStatus || status;
    if (statusTarget) {
      statusTarget.textContent = message;
    }
  }

  function renderError(message, targetPanel) {
    var panelTarget = targetPanel || panel;
    if (panelTarget) {
      panelTarget.innerHTML = '<div class="rounded-2xl border border-red-800/60 bg-red-950/40 p-4 text-sm text-red-200">' + escapeHtml(message) + '</div>';
    }
  }

  function buildQuestionCard(question, index, prefix) {
    var inputName = prefix + '-' + (question.id || index);
    var html = [];
    html.push('<div class="rounded-2xl border border-surface-border/70 bg-slate-950/70 p-3 mb-3 shadow-sm">');
    html.push('<div class="flex items-center justify-between gap-3 mb-2">');
    html.push('<span class="rounded-full border border-brand/30 bg-brand/10 px-2.5 py-1 text-[11px] font-medium text-brand">' + (prefix === 'final' ? 'اختبار نهائي' : 'سؤال دقيق') + '</span>');
    html.push('<span class="text-[11px] text-slate-400">#' + (index + 1) + '</span>');
    html.push('</div>');
    html.push('<div class="text-sm font-semibold leading-6 text-white">' + escapeHtml(question.text || 'سؤال') + '</div>');
    html.push('<div class="mt-3 grid gap-2">');
    (question.options || []).forEach(function (option) {
      html.push('<label class="flex items-center gap-2 rounded-xl border border-surface-border px-3 py-2 text-sm text-slate-300 hover:border-brand/40 hover:bg-brand/10 transition">');
      html.push('<input type="radio" name="' + inputName + '" value="' + escapeHtml(option) + '">');
      html.push('<span>' + escapeHtml(option) + '</span>');
      html.push('</label>');
    });
    html.push('</div>');
    html.push('</div>');
    return html.join('');
  }

  function getCurrentSegmentQuestions(data) {
    var microQuestions = Array.isArray(data.micro_questions) ? data.micro_questions : [];
    var finalQuestions = Array.isArray(data.final_questions) ? data.final_questions : [];
    var currentTime = 0;
    if (window.getCurrentVideoTime && typeof window.getCurrentVideoTime === 'function') {
      currentTime = Math.floor(window.getCurrentVideoTime());
    }

    var segmentMicro = microQuestions.filter(function (question) {
      var start = Number(question.timestamp_start || 0);
      var end = Number(question.timestamp_end || 0);
      if (!end) return currentTime >= start;
      return currentTime >= start && currentTime <= end;
    });

    return {
      microQuestions: segmentMicro,
      finalQuestions: finalQuestions,
      currentTime: currentTime,
    };
  }

  function renderQuestions(data, options) {
    var targetPanel = options && options.targetPanel ? options.targetPanel : panel;
    var targetStatus = options && options.targetStatus ? options.targetStatus : status;
    var microQuestions = Array.isArray(data.micro_questions) ? data.micro_questions : [];
    var finalQuestions = Array.isArray(data.final_questions) ? data.final_questions : [];
    var currentTime = options && options.currentTime ? options.currentTime : 0;

    if (!microQuestions.length && !finalQuestions.length) {
      targetPanel.innerHTML = '<div class="rounded-2xl border border-surface-border bg-slate-950/70 p-4 text-sm text-slate-400">لا توجد أسئلة متاحة لهذا الفيديو حاليًا. جرّب تحميل الاختبارات مرة أخرى أو افتح صفحة الاختبار الكاملة.</div>';
      return;
    }

    var html = [];
    html.push('<div class="rounded-2xl border border-surface-border/70 bg-slate-950/80 p-4 shadow-[0_0_30px_rgba(0,0,0,0.15)]">');
    html.push('<div class="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-800 bg-slate-900/70 px-3 py-2 text-sm text-slate-300">');
    html.push('<span>الأسئلة المجمّعة: ' + finalQuestions.length + ' · الأسئلة الدقيقة: ' + microQuestions.length + '</span>');
    if (currentTime) {
      html.push('<span class="text-xs text-brand">الجزء الحالي: ' + currentTime + ' ثانية</span>');
    } else {
      html.push('<span class="text-xs text-slate-400">ابدأ التشغيل لتصفية الأسئلة حسب اللحظة</span>');
    }
    html.push('</div>');
    html.push('<div class="mb-3 grid gap-2 rounded-xl border border-slate-800 bg-slate-900/60 p-3 text-sm text-slate-300 md:grid-cols-2">');
    html.push('<div class="rounded-lg border border-brand/20 bg-brand/10 px-3 py-2"><div class="text-[11px] uppercase tracking-wide text-brand">التركيز</div><div class="mt-1 font-semibold text-white">اختر إجابة واحدة لكل سؤال ثم أرسل التقييم</div></div>');
    html.push('<div class="rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-3 py-2"><div class="text-[11px] uppercase tracking-wide text-emerald-300">النتيجة</div><div class="mt-1 font-semibold text-white">ستظهر النتيجة فورًا وتُسجَّل في لوحة التقدم</div></div>');
    html.push('</div>');

    microQuestions.forEach(function (question, index) {
      html.push(buildQuestionCard(question, index, 'micro'));
    });

    if (finalQuestions.length) {
      html.push('<div class="rounded-2xl border border-brand/30 bg-brand/10 p-3">');
      html.push('<div class="text-sm font-semibold text-brand">اختبار نهائي</div>');
      finalQuestions.forEach(function (question, index) {
        html.push(buildQuestionCard(question, index, 'final'));
      });
      html.push('</div>');
    }

    html.push('<button id="submit-quizzes-btn" type="button" class="mt-3 inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-brand to-brand-light px-3 py-2 text-sm font-semibold text-white transition hover:opacity-90">إرسال الإجابات</button>');
    html.push('</div>');
    targetPanel.innerHTML = html.join('');

    targetPanel.querySelector('#submit-quizzes-btn').addEventListener('click', function () {
      var targetPanel = options && options.targetPanel ? options.targetPanel : panel;
      var targetStatus = options && options.targetStatus ? options.targetStatus : status;
      var answers = {};
      var selected = targetPanel.querySelectorAll('input[type="radio"]:checked');
      selected.forEach(function (input) {
        answers[input.name.replace('final-', '').replace('micro-', '')] = input.value;
      });

      if (!Object.keys(answers).length) {
        renderError('يرجى اختيار إجابة واحدة على الأقل قبل الإرسال.', targetPanel);
        return;
      }

      renderLoading('جاري إرسال الإجابات...', targetStatus);
      fetch('/quizzes/api/submit/', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken')},
        body: JSON.stringify({video_id: videoId, answers: answers})
      }).then(function (response) {
        return response.json();
      }).then(function (result) {
        if (result && result.status === 'success') {
          targetStatus.textContent = 'تم حفظ الإجابات بنجاح · النتيجة: ' + result.score + '%';
          targetPanel.innerHTML = '<div class="rounded-2xl border border-emerald-700/60 bg-emerald-950/40 p-4 text-sm text-emerald-100 shadow-[0_0_30px_rgba(16,185,129,0.15)]"><div class="mb-2 flex items-center gap-2"><span class="text-xl">✓</span><span class="font-semibold">تم حفظ إجاباتك بنجاح</span></div><div>النتيجة النهائية: <strong>' + result.score + '%</strong></div><div class="mt-2 text-xs text-emerald-200/90">سجلت النتيجة في لوحة التقدم وبدأت رحلة التحسين.</div></div>';
        } else {
          renderError(result && result.message ? result.message : 'تعذر إرسال الإجابات.', targetPanel);
        }
      }).catch(function () {
        renderError('تعذر الإرسال. تأكد من الاتصال بالإنترنت أو من وجود اختبارات محفوظة.', targetPanel);
      });
    });
  }

  function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      var cookies = document.cookie.split(';');
      for (var i = 0; i < cookies.length; i++) {
        var cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  function loadQuestions(mode, options) {
    var targetStatus = options && options.targetStatus ? options.targetStatus : status;
    renderLoading('جاري تحميل الاختبارات...', targetStatus);
    fetch('/quizzes/api/fetch-or-generate/', {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken')},
      body: JSON.stringify({video_id: videoId, trigger_mode: 'on_demand'})
    }).then(function (response) {
      return response.json();
    }).then(function (result) {
      if (result && result.status === 'success') {
        var payload = mode === 'segment' ? getCurrentSegmentQuestions(result) : result;
        renderQuestions(payload, {
          currentTime: payload.currentTime,
          targetPanel: options && options.targetPanel ? options.targetPanel : panel,
          targetStatus: options && options.targetStatus ? options.targetStatus : status
        });
        var statusTarget = options && options.targetStatus ? options.targetStatus : status;
        if (statusTarget) {
          statusTarget.textContent = result.cached ? 'تم تحميل الاختبارات من الذاكرة المؤقتة.' : 'تم إنشاء الاختبارات بنجاح.';
          if (mode === 'segment') {
            statusTarget.textContent += ' · تم تصفية الأسئلة للجزء الحالي.';
          }
        }
      } else {
        var errorTarget = options && options.targetPanel ? options.targetPanel : panel;
        renderError(result && result.message ? result.message : 'تعذر تحميل الاختبارات الآن.', errorTarget);
      }
    }).catch(function () {
      var errorTarget = options && options.targetPanel ? options.targetPanel : panel;
      renderError('تعذر تحميل الاختبارات الآن.', errorTarget);
    });
  }

  function loadAllPanels(mode) {
    loadQuestions(mode, {targetPanel: panel, targetStatus: status});
    if (overlay) {
      loadQuestions(mode, {targetPanel: overlayPanel, targetStatus: overlayStatus});
    }
  }

  var overlayIsMinimized = false;
  var overlayIsFullscreen = false;
  function setOverlayVisible(visible) {
    if (!overlay) return;
    overlay.style.display = visible ? 'block' : 'none';
    if (visible && overlayIsMinimized) {
      toggleOverlayMinimize(false);
    }
  }

  function toggleOverlayMinimize(forceState) {
    if (!overlay) return;
    overlayIsMinimized = typeof forceState === 'boolean' ? forceState : !overlayIsMinimized;
    var footer = document.getElementById('quiz-overlay-footer');
    overlayStatus.style.display = overlayIsMinimized ? 'none' : 'block';
    overlayPanel.style.display = overlayIsMinimized ? 'none' : 'block';
    if (footer) {
      footer.style.display = overlayIsMinimized ? 'none' : 'flex';
    }
    overlay.style.width = overlayIsMinimized ? '240px' : '';
    overlay.style.maxHeight = overlayIsMinimized ? '52px' : 'calc(80vh - 2rem)';
    overlay.style.height = overlayIsMinimized ? 'auto' : '';
    minimizeOverlayButton.textContent = overlayIsMinimized ? '▢' : '—';
  }

  function toggleOverlayFullscreen() {
    if (!overlay) return;
    overlayIsFullscreen = !overlayIsFullscreen;
    if (overlayIsFullscreen) {
      overlay.style.position = 'fixed';
      overlay.style.top = '0';
      overlay.style.left = '0';
      overlay.style.right = '0';
      overlay.style.bottom = '0';
      overlay.style.width = '100%';
      overlay.style.height = '100%';
      overlay.style.maxHeight = '100%';
      overlay.style.borderRadius = '0';
      overlay.style.zIndex = '1000';
      overlayHeader.style.cursor = 'default';
      fullscreenOverlayButton.textContent = '⤡';
    } else {
      overlay.style.position = 'absolute';
      overlay.style.top = '1rem';
      overlay.style.right = '1rem';
      overlay.style.left = 'auto';
      overlay.style.bottom = 'auto';
      overlay.style.width = '';
      overlay.style.height = '';
      overlay.style.maxHeight = 'calc(80vh - 2rem)';
      overlay.style.borderRadius = '';
      overlay.style.zIndex = '50';
      overlayHeader.style.cursor = 'move';
      fullscreenOverlayButton.textContent = '⤢';
    }
  }

  function bindOverlayDrag() {
    if (!overlayHeader || !overlay) return;

    var startX = 0;
    var startY = 0;
    var dragging = false;
    var dragThreshold = 8;
    var pointerStartX = 0;
    var pointerStartY = 0;

    function clamp(value, min, max) {
      return Math.min(Math.max(value, min), max);
    }

    function onMouseMove(event) {
      if (!dragging) {
        var movedX = event.clientX - pointerStartX;
        var movedY = event.clientY - pointerStartY;
        if (Math.abs(movedX) < dragThreshold && Math.abs(movedY) < dragThreshold) {
          return;
        }
        dragging = true;
      }
      event.preventDefault();
      var rootRect = root.getBoundingClientRect();
      var overlayRect = overlay.getBoundingClientRect();
      var x = event.clientX - rootRect.left - startX;
      var y = event.clientY - rootRect.top - startY;
      x = clamp(x, 0, rootRect.width - overlayRect.width);
      y = clamp(y, 0, rootRect.height - overlayRect.height);
      overlay.style.left = x + 'px';
      overlay.style.top = y + 'px';
      overlay.style.right = 'auto';
    }

    function onMouseUp() {
      dragging = false;
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    }

    overlayHeader.addEventListener('mousedown', function (event) {
      if (!overlay || overlayIsMinimized) return;
      var interactiveTarget = event.target && event.target.closest ? event.target.closest('button, a, input, select, textarea, [role="button"]') : null;
      if (interactiveTarget) {
        return;
      }

      pointerStartX = event.clientX;
      pointerStartY = event.clientY;
      dragging = false;
      var overlayRect = overlay.getBoundingClientRect();
      var rootRect = root.getBoundingClientRect();
      startX = event.clientX - overlayRect.left;
      startY = event.clientY - overlayRect.top;
      overlay.style.left = overlayRect.left - rootRect.left + 'px';
      overlay.style.top = overlayRect.top - rootRect.top + 'px';
      overlay.style.right = 'auto';
      document.addEventListener('mousemove', onMouseMove);
      document.addEventListener('mouseup', onMouseUp);
    });
  }

  function attachOverlayActionHandlers() {
    if (!overlay) return;

    overlay.addEventListener('click', function (event) {
      var target = event.target;
      if (!target || !target.closest) return;

      var actionButton = target.closest('[data-overlay-action]');
      if (!actionButton) return;

      event.stopPropagation();
      var action = actionButton.getAttribute('data-overlay-action');
      if (action === 'close') {
        setOverlayVisible(false);
      } else if (action === 'minimize') {
        toggleOverlayMinimize();
      } else if (action === 'fullscreen') {
        toggleOverlayFullscreen();
      } else if (action === 'load-all') {
        setOverlayVisible(true);
        loadAllPanels('all');
      } else if (action === 'load-segment') {
        setOverlayVisible(true);
        loadAllPanels('segment');
      } else if (action === 'open-full') {
        window.location.href = '/quizzes/exam/' + encodeURIComponent(videoId) + '/';
      }
    });
  }

  if (closeOverlayButton && overlay) {
    closeOverlayButton.addEventListener('click', function () {
      setOverlayVisible(false);
    });
  }

  if (overlay && !overlay.style.display) {
    overlay.style.display = 'block';
  }

  if (minimizeOverlayButton && overlay) {
    minimizeOverlayButton.addEventListener('click', function () {
      toggleOverlayMinimize();
    });
  }

  if (fullscreenOverlayButton && overlay) {
    fullscreenOverlayButton.addEventListener('click', function () {
      toggleOverlayFullscreen();
    });
  }

  if (refreshOverlayButton && overlay) {
    refreshOverlayButton.addEventListener('click', function () {
      loadAllPanels('all');
      if (overlayIsMinimized) {
        toggleOverlayMinimize(false);
      }
    });
  }

  if (openOverlayButton && overlay) {
    openOverlayButton.addEventListener('click', function () {
      setOverlayVisible(true);
      loadAllPanels('all');
    });
  }

  if (loadOverlayQuizzesButton && overlay) {
    loadOverlayQuizzesButton.addEventListener('click', function () {
      setOverlayVisible(true);
      loadAllPanels('all');
    });
  }

  if (loadOverlaySegmentButton && overlay) {
    loadOverlaySegmentButton.addEventListener('click', function () {
      setOverlayVisible(true);
      loadAllPanels('segment');
    });
  }

  attachOverlayActionHandlers();
  bindOverlayDrag();

  if (openFullPageButton) {
    openFullPageButton.addEventListener('click', function () {
      window.location.href = '/quizzes/exam/' + encodeURIComponent(videoId) + '/';
    });
  }

  loadAllPanels('all');
})();
