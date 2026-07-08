/**
 * ElGoPlan — adapted from Nexus-style productivity UI for ElGgolearn.
 * Uses Preact + htm from esm.sh (no local build). Data: localStorage with API-ready hooks.
 */
import { h, render } from 'https://esm.sh/preact@10.19.6';
import { useState, useEffect } from 'https://esm.sh/preact@10.19.6/hooks';
import htm from 'https://esm.sh/htm@3.1.1';

const html = htm.bind(h);

const C = {
  bg: '#0f172a',
  card: '#1e293b',
  border: '#334155',
  accent: '#6366f1',
  accent2: '#818cf8',
  gold: '#fbbf24',
  green: '#4ade80',
  red: '#f87171',
  text: '#f1f5f9',
  dim: '#94a3b8',
};

const PREFIX = 'elgoplan_v1_';

/** Ready for future POST /api/plan/state/ — today uses localStorage only */
const ElGoStorage = {
  get(key, fallback) {
    try {
      const r = localStorage.getItem(PREFIX + key);
      return r != null ? JSON.parse(r) : fallback;
    } catch {
      return fallback;
    }
  },
  set(key, val) {
    try {
      localStorage.setItem(PREFIX + key, JSON.stringify(val));
    } catch (e) {
      console.warn('[ElGoPlan] persist failed', key, e);
    }
  },
  async syncToBackend(_url, _payload) {
    // Reserved: await fetch('/api/plan/state/', { method: 'POST', headers: { 'X-CSRFToken': ... }, body: JSON.stringify(...) })
    return null;
  },
};

function uid() {
  return Math.random().toString(36).slice(2, 10);
}

/** تاريخ محلي YYYY-MM-DD (بدون انزياح UTC) */
function localYMD(d) {
  const x = d instanceof Date ? d : new Date(d);
  const y = x.getFullYear();
  const m = String(x.getMonth() + 1).padStart(2, '0');
  const day = String(x.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function todayLocal() {
  return localYMD(new Date());
}

function fmtAr(iso) {
  try {
    return new Date(iso + 'T12:00:00').toLocaleDateString('ar-EG', {
      weekday: 'short',
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  } catch {
    return iso;
  }
}

function GlowBar({ pct, color, h = 4 }) {
  const p = Math.max(0, Math.min(100, pct));
  return html`
    <div style=${{ background: C.border, borderRadius: '99px', overflow: 'hidden', height: h + 'px' }}>
      <div
        style=${{
          width: p + '%',
          height: '100%',
          borderRadius: '99px',
          background: 'linear-gradient(90deg,' + color + '66,' + color + ')',
          boxShadow: '0 0 8px ' + color + '44',
          transition: 'width 0.75s cubic-bezier(0.4,0,0.2,1)',
        }}
      />
    </div>
  `;
}

const MOODS = ['😞', '😐', '🙂', '😊', '🌟'];
const MOOD_AR = ['صعب', 'عادي', 'لابأس', 'جيد', 'ممتاز'];

/** أيام السنة الحالية مع درجة الإنجاز من مهام ذلك اليوم (Nexus-style heatmap) */
function buildYearDays(year, entries) {
  const out = [];
  for (let month = 0; month < 12; month++) {
    const dim = new Date(year, month + 1, 0).getDate();
    for (let day = 1; day <= dim; day++) {
      const key = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
      const e = entries[key];
      const score =
        e && e.tasks && e.tasks.length ? e.tasks.filter((t) => t.done).length / e.tasks.length : e ? 0 : -1;
      out.push({ key, score, hasNote: !!(e && e.note && e.note.length), mood: e?.mood });
    }
  }
  return out;
}

function heatColor(score) {
  if (score < 0) return C.border;
  if (score === 0) return '#0f172a';
  if (score < 0.33) return '#14532d';
  if (score < 0.66) return '#166534';
  return C.green;
}

async function fetchFields() {
  const r = await fetch('/api/fields/', { credentials: 'same-origin' });
  if (!r.ok) throw new Error('fields ' + r.status);
  return r.json();
}

async function fetchTrack(slug, level) {
  const r = await fetch('/api/fields/' + encodeURIComponent(slug) + '/tracks/' + encodeURIComponent(level) + '/', {
    credentials: 'same-origin',
  });
  if (!r.ok) throw new Error('track ' + r.status);
  return r.json();
}

function roadmapTasksFromTrack(data) {
  const tasks = [];
  for (const m of data.modules || []) {
    const mlabel = m.title_ar || m.title_en || 'وحدة';
    for (const s of m.skills || []) {
      tasks.push({
        id: uid(),
        label: `[مهارة · ${mlabel}] ${s.title_ar || s.title_en}`,
        done: false,
        source: 'roadmap',
      });
    }
  }
  for (const p of data.projects || []) {
    tasks.push({
      id: uid(),
      label: `[مشروع GitHub] ${p.title_ar || p.title_en}`,
      done: false,
      source: 'roadmap',
    });
  }
  return tasks;
}

function GoalsSection() {
  const [goals, setGoals] = useState(() => ElGoStorage.get('goals', []));
  const [tab, setTab] = useState('list');
  const [slug, setSlug] = useState('');
  const [level, setLevel] = useState('junior');
  const [fields, setFields] = useState([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState('');

  useEffect(() => {
    ElGoStorage.set('goals', goals);
  }, [goals]);

  useEffect(() => {
    let cancelled = false;
    setErr('');
    setLoading(true);
    fetchFields()
      .then((f) => {
        if (cancelled) return;
        setFields(f);
        if (f.length) setSlug((s) => s || f[0].slug);
      })
      .catch((e) => {
        console.error('[ElGoPlan] fetch fields', e);
        if (!cancelled) setErr('تعذر تحميل المجالات. تأكد من تسجيل الدخول والسيرفر.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const importRoadmap = async () => {
    if (!slug) return;
    setErr('');
    setLoading(true);
    try {
      const track = await fetchTrack(slug, level);
      const field = fields.find((x) => x.slug === slug);
      const label = (field ? field.name_ar || field.name_en : slug) + ' · ' + level;
      const monthId = uid();
      const newTasks = roadmapTasksFromTrack(track);
      if (!newTasks.length) {
        setErr('لا توجد مهارات أو مشاريع في هذا المسار.');
        setLoading(false);
        return;
      }
      const g = {
        id: uid(),
        label,
        icon: field?.icon || '📚',
        color: field?.color || C.accent,
        category: 'مسار منصة',
        months: [{ id: monthId, label: 'استيراد مسار', tasks: newTasks }],
      };
      setGoals((prev) => [...prev, g]);
      setTab('list');
    } catch (e) {
      console.error('[ElGoPlan] import roadmap', e);
      setErr('فشل استيراد المسار: ' + e.message);
    } finally {
      setLoading(false);
    }
  };

  const addGoal = () => {
    setGoals((g) => [
      ...g,
      {
        id: uid(),
        label: 'هدف جديد',
        icon: '🎯',
        color: C.accent,
        category: 'عام',
        months: [{ id: uid(), label: 'الشهر الحالي', tasks: [] }],
      },
    ]);
  };

  const toggleTask = (gid, mid, tid) => {
    setGoals((gs) =>
      gs.map((g) =>
        g.id !== gid
          ? g
          : {
              ...g,
              months: g.months.map((m) =>
                m.id !== mid
                  ? m
                  : { ...m, tasks: m.tasks.map((t) => (t.id === tid ? { ...t, done: !t.done } : t)) }
              ),
            }
      )
    );
  };

  const addTask = (gid, mid, text) => {
    const t = text.trim();
    if (!t) return;
    setGoals((gs) =>
      gs.map((g) =>
        g.id !== gid
          ? g
          : {
              ...g,
              months: g.months.map((m) =>
                m.id !== mid ? m : { ...m, tasks: [...m.tasks, { id: uid(), label: t, done: false, source: 'manual' }] }
              ),
            }
      )
    );
  };

  return html`
    <div
      style=${{ background: C.card, border: '1px solid ' + C.border, borderRadius: '20px', padding: '24px', color: C.text }}
    >
      <div style=${{ display: 'flex', gap: '12px', marginBottom: '20px', flexWrap: 'wrap', alignItems: 'center' }}>
        <button
          type="button"
          onClick=${() => setTab('list')}
          style=${{
            padding: '8px 16px',
            borderRadius: '10px',
            border: '1px solid ' + (tab === 'list' ? C.accent : C.border),
            background: tab === 'list' ? 'rgba(99,102,241,.15)' : 'transparent',
            color: tab === 'list' ? C.accent : C.dim,
            cursor: 'pointer',
            fontWeight: '700',
          }}
        >
          أهدافي
        </button>
        <button
          type="button"
          onClick=${() => setTab('sync')}
          style=${{
            padding: '8px 16px',
            borderRadius: '10px',
            border: '1px solid ' + (tab === 'sync' ? C.accent : C.border),
            background: tab === 'sync' ? 'rgba(99,102,241,.15)' : 'transparent',
            color: tab === 'sync' ? C.accent : C.dim,
            cursor: 'pointer',
            fontWeight: '700',
          }}
        >
          ربط Roadmap
        </button>
        <button
          type="button"
          onClick=${addGoal}
          style=${{
            marginInlineStart: 'auto',
            padding: '8px 16px',
            borderRadius: '10px',
            border: 'none',
            background: C.accent,
            color: '#fff',
            cursor: 'pointer',
            fontWeight: '700',
          }}
        >
          + هدف
        </button>
      </div>

      ${err &&
      html`<div
        style=${{ color: C.red, fontSize: '13px', marginBottom: '12px', padding: '10px', background: 'rgba(248,113,113,.08)', borderRadius: '10px' }}
      >
        ${err}
      </div>`}

      ${tab === 'sync' &&
      html`<div>
        <p style=${{ color: C.dim, fontSize: '13px', marginBottom: '14px' }}>
          اختر مساراً من منصة ElGgolearn لإضافة مهاراته ومشاريعه كمهام تلقائياً ضمن هدف جديد.
        </p>
        <div style=${{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginBottom: '12px' }}>
          <select
            value=${slug}
            onChange=${(e) => setSlug(e.target.value)}
            style=${{ flex: '1', minWidth: '160px', padding: '10px', borderRadius: '10px', border: '1px solid ' + C.border, background: C.bg, color: C.text }}
          >
            ${fields.map((f) => html`<option value=${f.slug}>${f.icon || ''} ${f.name_ar || f.name_en}</option>`)}
          </select>
          <select
            value=${level}
            onChange=${(e) => setLevel(e.target.value)}
            style=${{ padding: '10px', borderRadius: '10px', border: '1px solid ' + C.border, background: C.bg, color: C.text }}
          >
            <option value="junior">Junior</option>
            <option value="mid">Mid</option>
            <option value="senior">Senior</option>
          </select>
          <button
            type="button"
            disabled=${loading}
            onClick=${importRoadmap}
            style=${{
              padding: '10px 18px',
              borderRadius: '10px',
              border: 'none',
              background: C.green,
              color: '#0f172a',
              cursor: loading ? 'wait' : 'pointer',
              fontWeight: '800',
            }}
          >
            استيراد إلى ElGoPlan
          </button>
        </div>
      </div>`}

      ${tab === 'list' &&
      html`<div style=${{ display: 'grid', gap: '16px' }}>
        ${goals.length === 0 &&
        html`<p style=${{ color: C.dim }}>لا أهداف بعد — أضف هدفاً أو استورد مساراً.</p>`}
        ${goals.map(
          (g) => html`
            <div
              key=${g.id}
              style=${{
                border: '1px solid ' + C.border,
                borderRadius: '16px',
                padding: '18px',
                background: 'linear-gradient(135deg, ' + g.color + '12, ' + C.bg + ')',
              }}
            >
              <div style=${{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
                <span style=${{ fontSize: '28px' }}>${g.icon}</span>
                <strong style=${{ fontSize: '18px' }}>${g.label}</strong>
              </div>
              ${g.months.map((m) => html`
                <div key=${m.id} style=${{ marginBottom: '12px' }}>
                  <div style=${{ fontSize: '12px', color: C.accent2, marginBottom: '6px', fontWeight: '700' }}>${m.label}</div>
                  <ul style=${{ listStyle: 'none', padding: 0, margin: 0 }}>
                    ${m.tasks.map(
                      (t) => html`
                        <li
                          key=${t.id}
                          style=${{
                            display: 'flex',
                            alignItems: 'flex-start',
                            gap: '10px',
                            padding: '8px 0',
                            borderBottom: '1px solid rgba(51,65,85,.4)',
                            color: t.done ? C.dim : C.text,
                            textDecoration: t.done ? 'line-through' : 'none',
                          }}
                        >
                          <input
                            type="checkbox"
                            checked=${t.done}
                            onChange=${() => toggleTask(g.id, m.id, t.id)}
                            style=${{ marginTop: '4px' }}
                          />
                          <span style=${{ flex: 1, fontSize: '13px', lineHeight: 1.5 }}>${t.label}</span>
                        </li>
                      `
                    )}
                  </ul>
                  <${TaskAddInput} onAdd=${(text) => addTask(g.id, m.id, text)} />
                </div>
              `)}
            </div>
          `
        )}
      </div>`}
    </div>
  `;
}

function TaskAddInput({ onAdd }) {
  const [v, setV] = useState('');
  return html`
    <div style=${{ display: 'flex', gap: '8px', marginTop: '8px' }}>
      <input
        value=${v}
        onInput=${(e) => setV(e.target.value)}
        onKeyDown=${(e) => {
          if (e.key === 'Enter') {
            onAdd(v);
            setV('');
          }
        }}
        placeholder="+ مهمة"
        style=${{
          flex: 1,
          padding: '8px 12px',
          borderRadius: '8px',
          border: '1px solid ' + C.border,
          background: C.bg,
          color: C.text,
          fontSize: '12px',
        }}
      />
      <button
        type="button"
        onClick=${() => {
          onAdd(v);
          setV('');
        }}
        style=${{ padding: '8px 14px', borderRadius: '8px', border: '1px solid ' + C.accent, background: 'rgba(99,102,241,.2)', color: C.accent, cursor: 'pointer' }}
      >
        إضافة
      </button>
    </div>
  `;
}

/**
 * يوميات + خريطة 365 يوم (مستوحاة من NexusLifeOS JournalPage — مدمجة مع ElGoPlan).
 * البيانات: مهام يومية + مزاج + ملاحظة؛ لون الخلية = نسبة إنجاز مهام ذلك اليوم.
 */
function JournalSection() {
  const [entries, setEntries] = useState(() => ElGoStorage.get('journal', {}));
  const [selectedDate, setSelectedDate] = useState(todayLocal());
  const [taskInput, setTaskInput] = useState('');
  const [viewMode, setViewMode] = useState('day');
  const yearNow = new Date().getFullYear();

  useEffect(() => {
    ElGoStorage.set('journal', entries);
  }, [entries]);

  const getEntry = (d) =>
    entries[d] || { tasks: [], note: '', mood: 2 };

  const setEntry = (d, updater) => {
    setEntries((e) => ({ ...e, [d]: updater(getEntry(d)) }));
  };

  const entry = getEntry(selectedDate);
  const addTask = () => {
    const t = taskInput.trim();
    if (!t) return;
    setEntry(selectedDate, (ex) => ({
      ...ex,
      tasks: [...ex.tasks, { id: uid(), label: t, done: false }],
    }));
    setTaskInput('');
  };

  const toggleTask = (tid) =>
    setEntry(selectedDate, (ex) => ({
      ...ex,
      tasks: ex.tasks.map((x) => (x.id === tid ? { ...x, done: !x.done } : x)),
    }));

  const setField = (field, val) => setEntry(selectedDate, (ex) => ({ ...ex, [field]: val }));

  const donePct = entry.tasks.length
    ? Math.round((entry.tasks.filter((t) => t.done).length / entry.tasks.length) * 100)
    : 0;

  const yearDays = buildYearDays(yearNow, entries);
  const prevDay = () => {
    const d = new Date(selectedDate + 'T12:00:00');
    d.setDate(d.getDate() - 1);
    setSelectedDate(localYMD(d));
  };
  const nextDay = () => {
    const d = new Date(selectedDate + 'T12:00:00');
    d.setDate(d.getDate() + 1);
    setSelectedDate(localYMD(d));
  };

  const legendColors = [C.border, '#0f172a', '#14532d', '#166534', C.green];

  return html`
    <div
      style=${{
        marginTop: '28px',
        background: C.card,
        border: '1px solid ' + C.border,
        borderRadius: '20px',
        padding: '24px',
        color: C.text,
      }}
    >
      <h2 style=${{ margin: '0 0 8px', fontSize: '18px', fontWeight: '800' }}>اليوميات والنشاط السنوي</h2>
      <p style=${{ margin: '0 0 18px', fontSize: '12px', color: C.dim }}>
        خريطة مستوحاة من NexusLifeOS: كل مربع يوم في السنة؛ الإشراق = نسبة مهام اليوم المكتملة.
      </p>

      <div style=${{ display: 'flex', gap: '8px', marginBottom: '18px', flexWrap: 'wrap' }}>
        <button
          type="button"
          onClick=${() => setViewMode('day')}
          style=${{
            padding: '8px 16px',
            borderRadius: '10px',
            border: '1px solid ' + (viewMode === 'day' ? C.accent : C.border),
            background: viewMode === 'day' ? 'rgba(99,102,241,.15)' : 'transparent',
            color: viewMode === 'day' ? C.accent : C.dim,
            cursor: 'pointer',
            fontWeight: '700',
          }}
        >
          سجل اليوم
        </button>
        <button
          type="button"
          onClick=${() => setViewMode('year')}
          style=${{
            padding: '8px 16px',
            borderRadius: '10px',
            border: '1px solid ' + (viewMode === 'year' ? C.green : C.border),
            background: viewMode === 'year' ? 'rgba(74,222,128,.12)' : 'transparent',
            color: viewMode === 'year' ? C.green : C.dim,
            cursor: 'pointer',
            fontWeight: '700',
          }}
        >
          عرض السنة (${yearNow})
        </button>
      </div>

      ${viewMode === 'year' &&
      html`<div>
        <div style=${{ overflowX: 'auto', paddingBottom: '8px' }}>
          <div
            style=${{
              display: 'grid',
              gridTemplateColumns: 'repeat(53, 1fr)',
              gap: '3px',
              minWidth: '720px',
            }}
          >
            ${yearDays.map(
              (day) => html`
                <div
                  key=${day.key}
                  title=${day.key + (day.hasNote ? ' · ملاحظة' : '')}
                  onClick=${() => {
                    setSelectedDate(day.key);
                    setViewMode('day');
                  }}
                  style=${{
                    width: '12px',
                    height: '12px',
                    borderRadius: '3px',
                    background: day.key === selectedDate ? C.accent : heatColor(day.score),
                    cursor: 'pointer',
                    border: day.key === todayLocal() ? '1px solid ' + C.accent2 : 'none',
                    boxSizing: 'border-box',
                  }}
                />
              `
            )}
          </div>
        </div>
        <div style=${{ display: 'flex', gap: '10px', marginTop: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
          <span style=${{ fontSize: '10px', color: C.dim }}>أقل</span>
          ${legendColors.map((c, i) => html`<div key=${i} style=${{ width: '12px', height: '12px', borderRadius: '3px', background: c }} />`)}
          <span style=${{ fontSize: '10px', color: C.dim }}>أكثر — اضغط لليوم</span>
        </div>

        <div style=${{ marginTop: '22px' }}>
          <div style=${{ fontSize: '11px', color: C.dim, marginBottom: '10px', fontWeight: '700' }}>آخر السجلات</div>
          ${Object.entries(entries)
            .sort((a, b) => b[0].localeCompare(a[0]))
            .slice(0, 8)
            .map(
              ([d, ex]) => html`
                <div
                  key=${d}
                  onClick=${() => {
                    setSelectedDate(d);
                    setViewMode('day');
                  }}
                  style=${{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    padding: '10px 14px',
                    background: C.bg,
                    borderRadius: '10px',
                    marginBottom: '6px',
                    cursor: 'pointer',
                    border: '1px solid ' + C.border,
                  }}
                >
                  <span style=${{ fontSize: '20px' }}>${MOODS[ex.mood ?? 2]}</span>
                  <div style=${{ flex: '1', minWidth: 0 }}>
                    <div style=${{ fontSize: '13px', fontWeight: '700' }}>${fmtAr(d)}</div>
                    ${ex.note &&
                    html`<div
                      style=${{
                        fontSize: '11px',
                        color: C.dim,
                        marginTop: '2px',
                        overflow: 'hidden',
                        whiteSpace: 'nowrap',
                        textOverflow: 'ellipsis',
                      }}
                    >
                      ${ex.note}
                    </div>`}
                  </div>
                  <span style=${{ fontSize: '11px', color: C.green, fontWeight: '700', flexShrink: 0 }}>
                    ${ex.tasks?.filter((t) => t.done).length || 0}/${ex.tasks?.length || 0}
                  </span>
                </div>
              `
            )}
          ${Object.keys(entries).length === 0 &&
          html`<p style=${{ color: C.dim, fontSize: '13px' }}>لا توجد أيام مسجلة بعد — افتح «سجل اليوم» ودوّن مهامك.</p>`}
        </div>
      </div>`}

      ${viewMode === 'day' &&
      html`<div>
        <div style=${{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '18px', flexWrap: 'wrap' }}>
          <button
            type="button"
            onClick=${prevDay}
            style=${{
              background: C.bg,
              border: '1px solid ' + C.border,
              color: C.dim,
              borderRadius: '8px',
              padding: '6px 12px',
              cursor: 'pointer',
            }}
          >
            ‹
          </button>
          <div style=${{ flex: '1', textAlign: 'center', minWidth: '140px' }}>
            <div style=${{ fontWeight: '800', fontSize: '16px' }}>${fmtAr(selectedDate)}</div>
            ${selectedDate === todayLocal() && html`<div style=${{ fontSize: '11px', color: C.accent }}>اليوم</div>`}
          </div>
          <button
            type="button"
            onClick=${nextDay}
            style=${{
              background: C.bg,
              border: '1px solid ' + C.border,
              color: C.dim,
              borderRadius: '8px',
              padding: '6px 12px',
              cursor: 'pointer',
            }}
          >
            ›
          </button>
          <button
            type="button"
            onClick=${() => setSelectedDate(todayLocal())}
            style=${{
              background: 'rgba(99,102,241,.15)',
              border: '1px solid rgba(99,102,241,.35)',
              color: C.accent,
              borderRadius: '8px',
              padding: '6px 12px',
              cursor: 'pointer',
              fontWeight: '700',
            }}
          >
            اليوم
          </button>
        </div>

        <div style=${{ background: C.bg, border: '1px solid ' + C.border, borderRadius: '14px', padding: '16px', marginBottom: '12px' }}>
          <div style=${{ fontSize: '10px', color: C.dim, fontWeight: '700', marginBottom: '12px' }}>المزاج</div>
          <div style=${{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            ${MOODS.map(
              (m, i) => html`
                <button
                  type="button"
                  key=${i}
                  onClick=${() => setField('mood', i)}
                  style=${{
                    flex: '1',
                    minWidth: '52px',
                    textAlign: 'center',
                    padding: '10px 6px',
                    borderRadius: '10px',
                    cursor: 'pointer',
                    background: entry.mood === i ? 'rgba(99,102,241,.15)' : 'transparent',
                    border: '1px solid ' + (entry.mood === i ? C.accent : C.border),
                    fontSize: '22px',
                    lineHeight: 1,
                  }}
                >
                  ${m}
                  <div style=${{ fontSize: '9px', color: entry.mood === i ? C.accent : C.dim, marginTop: '4px' }}>
                    ${MOOD_AR[i]}
                  </div>
                </button>
              `
            )}
          </div>
        </div>

        <div style=${{ background: C.bg, border: '1px solid ' + C.border, borderRadius: '14px', padding: '16px', marginBottom: '12px' }}>
          <div style=${{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', gap: '10px' }}>
            <span style=${{ fontSize: '10px', color: C.dim, fontWeight: '700' }}>مهام اليوم</span>
            <div style=${{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: '100px' }}>
              <${GlowBar} pct=${donePct} color=${C.accent} h=${4} />
              <span style=${{ fontSize: '11px', color: C.accent, fontWeight: '700' }}>${donePct}%</span>
            </div>
          </div>
          <ul style=${{ listStyle: 'none', padding: 0, margin: 0 }}>
            ${entry.tasks.map(
              (t) => html`
                <li
                  key=${t.id}
                  style=${{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    padding: '8px 0',
                    borderBottom: '1px solid rgba(51,65,85,.35)',
                    cursor: 'pointer',
                  }}
                  onClick=${() => toggleTask(t.id)}
                >
                  <span
                    style=${{
                      width: '20px',
                      height: '20px',
                      borderRadius: '6px',
                      flexShrink: 0,
                      border: '1.5px solid ' + (t.done ? C.accent : C.dim),
                      background: t.done ? 'rgba(99,102,241,.2)' : 'transparent',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '11px',
                      color: C.accent,
                    }}
                    >${t.done ? '✓' : ''}</span>
                  <span
                    style=${{
                      fontSize: '13px',
                      color: t.done ? C.dim : C.text,
                      textDecoration: t.done ? 'line-through' : 'none',
                    }}
                    >${t.label}</span>
                </li>
              `
            )}
          </ul>
          <div style=${{ display: 'flex', gap: '8px', marginTop: '10px' }}>
            <input
              value=${taskInput}
              onInput=${(e) => setTaskInput(e.target.value)}
              onKeyDown=${(e) => e.key === 'Enter' && addTask()}
              placeholder="+ مهمة لهذا اليوم"
              style=${{
                flex: 1,
                padding: '8px 12px',
                borderRadius: '8px',
                border: '1px solid ' + C.border,
                background: C.card,
                color: C.text,
                fontSize: '13px',
              }}
            />
            <button
              type="button"
              onClick=${addTask}
              style=${{
                padding: '8px 16px',
                borderRadius: '8px',
                border: '1px solid ' + C.accent,
                background: 'rgba(99,102,241,.2)',
                color: C.accent,
                cursor: 'pointer',
                fontWeight: '700',
              }}
            >
              إضافة
            </button>
          </div>
        </div>

        <div style=${{ background: C.bg, border: '1px solid ' + C.border, borderRadius: '14px', padding: '16px' }}>
          <div style=${{ fontSize: '10px', color: C.dim, fontWeight: '700', marginBottom: '10px' }}>مذكّرات اليوم</div>
          <textarea
            value=${entry.note}
            onInput=${(e) => setField('note', e.target.value)}
            placeholder="ما تعلّمته، تحدياتك، فكرة، امتنان..."
            rows=${5}
            style=${{
              width: '100%',
              boxSizing: 'border-box',
              background: C.card,
              border: '1px solid ' + C.border,
              color: C.text,
              borderRadius: '10px',
              padding: '12px',
              fontSize: '13px',
              resize: 'vertical',
              lineHeight: 1.6,
            }}
          />
          <div style=${{ fontSize: '11px', color: C.dim, marginTop: '6px', textAlign: 'end' }}>${entry.note.length} حرف</div>
        </div>
      </div>`}
    </div>
  `;
}

function App() {
  return html`
    <div style=${{ fontFamily: 'ui-sans-serif, system-ui, sans-serif' }}>
      <${GoalsSection} />
      <${JournalSection} />
      <p style=${{ color: C.dim, fontSize: '11px', marginTop: '16px' }}>
        «ElGoPlan» — مخزن محلياً في المتصفح حالياً.         تكامل الخادم الكامل عبر
        <code style=${{ color: C.accent2 }}>ElGoStorage.syncToBackend</code> جاهز للربط لاحقاً.
      </p>
    </div>
  `;
}

const root = document.getElementById('elgoplan-root');
if (root) render(html`<${App} />`, root);
