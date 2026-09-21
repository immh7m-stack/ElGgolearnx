(function() {
  const tracker = {
    STORAGE_KEY: 'elgo-focus-active',
    active: false,
    stream: null,
    previewVideo: null,
    statusLabel: null,
    stateLabel: null,
    canvas: null,
    ctx: null,
    telemetry: [],
    sessionStart: null,
    frameTimer: null,
    sendTimer: null,
    sessionId: null,
    lastScore: 0,
    distractionCount: 0,
    analysisInFlight: false,

    start(previewVideo, statusLabel) {
      this.previewVideo = previewVideo || this.previewVideo;
      this.statusLabel = statusLabel || this.statusLabel;
      this.stateLabel = document.getElementById('focus-live-state');
      if (!this.previewVideo || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        this.setStatus('تعذر تشغيل الكاميرا', 'bg-rose-500/20 text-rose-200');
        return;
      }

      if (this.active && this.stream) {
        if (this.previewVideo) {
          this.previewVideo.srcObject = this.stream;
          this.previewVideo.play().catch(() => {});
        }
        return;
      }

      const self = this;
      navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' }, audio: false })
        .then((stream) => {
          self.stream = stream;
          if (self.previewVideo) {
            self.previewVideo.srcObject = stream;
            self.previewVideo.play().catch(() => {});
          }
          self.setupCanvas();
          self.sessionStart = new Date();
          self.sessionId = Date.now();
          self.active = true;
          localStorage.setItem(self.STORAGE_KEY, 'true');
          self.setStatus('الكاميرا مشغلة', 'bg-emerald-500/20 text-emerald-200');
          self.setLiveState('جارٍ التحليل', 'bg-slate-700/70 text-slate-100');
          self.startLoop();
          self.updateCards(self.lastScore, this.telemetry.length, this.distractionCount, 'جار التحليل الحقيقي...');
        })
        .catch(() => {
          self.setStatus('تعذر الوصول للكاميرا', 'bg-rose-500/20 text-rose-200');
        });
    },

    stop(force = false) {
      if (this.frameTimer) {
        clearInterval(this.frameTimer);
        this.frameTimer = null;
      }
      if (this.sendTimer) {
        clearInterval(this.sendTimer);
        this.sendTimer = null;
      }
      if (this.stream) {
        this.stream.getTracks().forEach((track) => track.stop());
      }
      this.active = false;
      if (!force) {
        localStorage.removeItem(this.STORAGE_KEY);
      }
      this.sendSummary(true);
    },

    toggle(previewVideo, statusLabel) {
      if (this.active) {
        this.stop();
        this.setStatus('أوقف التتبع', 'bg-slate-700/70 text-slate-100');
      } else {
        this.start(previewVideo, statusLabel);
      }
    },

    setupCanvas() {
      this.canvas = document.createElement('canvas');
      this.canvas.width = 320;
      this.canvas.height = 240;
      this.ctx = this.canvas.getContext('2d');
    },

    startLoop() {
      const self = this;
      this.frameTimer = setInterval(() => {
        if (!self.active || !self.previewVideo) return;
        self.captureAndAnalyze();
      }, 1200);

      this.sendTimer = setInterval(() => {
        if (self.active && self.telemetry.length) {
          self.sendSummary(false);
        }
      }, 6000);
    },

    captureAndAnalyze() {
      if (!this.ctx || !this.previewVideo.videoWidth) return;
      this.ctx.drawImage(this.previewVideo, 0, 0, this.canvas.width, this.canvas.height);
      this.analyzeFrameWithBackend(this.canvas.toDataURL('image/jpeg', 0.7));
    },

    analyzeFrameWithBackend(imageBase64) {
      if (this.analysisInFlight) return;
      this.analysisInFlight = true;
      const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';
      fetch('/monitoring/analyze/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({ image_base64: imageBase64 })
      })
        .then((response) => response.json())
        .then((result) => {
          if (!result || typeof result.score !== 'number') return;
          const normalizedScore = Math.max(0, Math.min(100, Math.round(result.score)));
          const note = result.note || 'جاري التحليل';
          if (note.includes('تشتت')) {
            this.distractionCount += 1;
          }
          this.lastScore = normalizedScore;
          const isDistracted = /تشتت|distracted|Drowsiness|No face|No frame/i.test(note) || Boolean(result.is_drowsy) || Boolean(result.iris_distracted) || !Boolean(result.is_focused);
          const stateText = isDistracted ? 'مشتت' : 'مُركز';
          const stateClass = isDistracted ? 'bg-rose-500/20 text-rose-200' : 'bg-emerald-500/20 text-emerald-200';
          this.updateCards(normalizedScore, this.telemetry.length + 1, this.distractionCount, note);
          this.telemetry.push({
            score: normalizedScore,
            state: note,
            timestamp: this.formatTimestamp(new Date())
          });
          this.setStatus(`${normalizedScore}% • ${note}`, normalizedScore < 70 ? 'bg-rose-500/20 text-rose-200' : normalizedScore < 82 ? 'bg-amber-500/20 text-amber-200' : 'bg-emerald-500/20 text-emerald-200');
          this.setLiveState(stateText, stateClass);
        })
        .catch(() => {})
        .finally(() => {
          this.analysisInFlight = false;
        });
    },

    updateCards(score, sessions, distractions, note) {
      const scoreNode = document.getElementById('focus-day-score');
      const sessionsNode = document.getElementById('focus-day-sessions');
      const distractionsNode = document.getElementById('focus-day-distractions');
      const notesNode = document.getElementById('focus-day-notes');
      if (scoreNode) scoreNode.textContent = `${score}%`;
      if (sessionsNode) sessionsNode.textContent = sessions;
      if (distractionsNode) distractionsNode.textContent = distractions;
      if (notesNode) notesNode.textContent = note;
    },

    setStatus(text, className) {
      if (!this.statusLabel) return;
      this.statusLabel.textContent = text;
      this.statusLabel.className = `rounded-full px-3 py-1 text-xs ${className}`;
    },

    setLiveState(text, className) {
      if (!this.stateLabel) return;
      this.stateLabel.textContent = text;
      this.stateLabel.className = `rounded-full px-3 py-1 text-xs ${className}`;
    },

    sendSummary(force = false) {
      if (!this.active && !force) return;
      if (!this.telemetry.length) return;
      const summary = {
        session_summary: {
          session_id: this.sessionId || Date.now(),
          avg_focus_score: Math.round(this.telemetry.reduce((sum, item) => sum + item.score, 0) / this.telemetry.length),
          total_distractions: this.distractionCount,
          duration_seconds: Math.max(1, Math.round((new Date() - this.sessionStart) / 1000)),
          telemetry_points_count: this.telemetry.length
        },
        telemetry: this.telemetry.slice(-8)
      };
      const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';
      fetch('/api/progress/focus-sessions/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        body: JSON.stringify(summary)
      }).catch(() => {});
      if (!this.active) {
        this.telemetry = [];
      }
    },

    formatTimestamp(date) {
      const pad = (value) => `${value}`.padStart(2, '0');
      return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}.000`;
    },

    shouldAutoStart() {
      return localStorage.getItem(this.STORAGE_KEY) === 'true';
    }
  };

  window.ElGoFocusTracker = tracker;
})();
