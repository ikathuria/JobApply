import { useState, useMemo, useEffect, useContext } from 'react'
import { ThemeCtx } from './ThemeContext.jsx'
import { DARK, LIGHT } from '../theme.js'
import { Input, Btn, EmptyState, Spinner } from './ui/index.jsx'
import JobRow from './JobRow.jsx'
import { api } from '../api.js'

// ── Import modal ─────────────────────────────────────────────────────────────
const STATUS_OPTIONS = ['new','queued','approved','applied','oa','interview','offer','rejected','skipped']
const BLANK = { title:'', company:'', url:'', status:'applied', date_applied:'', location:'', notes:'' }

function ImportModal({ dark, onClose, onSuccess }) {
  const T = dark ? DARK : LIGHT
  const [form, setForm]     = useState({ ...BLANK, date_applied: new Date().toISOString().slice(0,10) })
  const [saving, setSaving] = useState(false)
  const [error, setError]   = useState('')

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const submit = async () => {
    if (!form.title.trim() || !form.company.trim()) { setError('Title and Company are required.'); return }
    setSaving(true); setError('')
    try {
      await api.import({
        title:        form.title.trim(),
        company:      form.company.trim(),
        url:          form.url.trim(),
        status:       form.status,
        date_applied: form.date_applied || null,
        location:     form.location.trim(),
        notes:        form.notes.trim(),
      })
      onSuccess()
      onClose()
    } catch (e) {
      setError(e.message || 'Import failed')
      setSaving(false)
    }
  }

  const overlay = {
    position:'fixed', inset:0, zIndex:1000,
    background:'rgba(0,0,0,0.55)', backdropFilter:'blur(4px)',
    display:'flex', alignItems:'center', justifyContent:'center',
  }
  const modal = {
    background: T.card, border: `1px solid ${T.border}`,
    borderRadius: 14, padding: '28px 32px', width: 520, maxWidth: '95vw',
    boxShadow: '0 24px 64px rgba(0,0,0,0.4)',
  }
  const label = { fontSize: 11, fontWeight: 700, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 5 }
  const inp = {
    width: '100%', padding: '8px 12px', borderRadius: 8,
    border: `1px solid ${T.border}`, background: dark ? '#1A1A28' : '#FAFAFA',
    color: T.text, fontSize: 13, fontFamily: 'DM Sans, sans-serif', outline: 'none',
    boxSizing: 'border-box',
  }

  return (
    <div style={overlay} onClick={e => e.target === e.currentTarget && onClose()}>
      <div style={modal}>
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:22 }}>
          <div style={{ fontSize:16, fontWeight:800, color:T.text }}>Import Job</div>
          <button onClick={onClose} style={{ background:'none', border:'none', color:T.muted, fontSize:20, cursor:'pointer', lineHeight:1 }}>×</button>
        </div>

        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'14px 16px' }}>
          <div style={{ gridColumn:'1/-1' }}>
            <div style={label}>Job Title *</div>
            <input style={inp} value={form.title} onChange={e => set('title', e.target.value)} placeholder="Software Engineer Intern" />
          </div>
          <div>
            <div style={label}>Company *</div>
            <input style={inp} value={form.company} onChange={e => set('company', e.target.value)} placeholder="Acme Corp" />
          </div>
          <div>
            <div style={label}>Status</div>
            <select style={inp} value={form.status} onChange={e => set('status', e.target.value)}>
              {STATUS_OPTIONS.map(s => <option key={s} value={s}>{s.charAt(0).toUpperCase()+s.slice(1)}</option>)}
            </select>
          </div>
          <div style={{ gridColumn:'1/-1' }}>
            <div style={label}>Job URL</div>
            <input style={inp} value={form.url} onChange={e => set('url', e.target.value)} placeholder="https://jobs.example.com/..." />
          </div>
          <div>
            <div style={label}>Date Applied</div>
            <input type="date" style={inp} value={form.date_applied} onChange={e => set('date_applied', e.target.value)} />
          </div>
          <div>
            <div style={label}>Location</div>
            <input style={inp} value={form.location} onChange={e => set('location', e.target.value)} placeholder="Remote / NYC" />
          </div>
          <div style={{ gridColumn:'1/-1' }}>
            <div style={label}>Notes</div>
            <textarea style={{ ...inp, resize:'vertical', minHeight:68 }} value={form.notes} onChange={e => set('notes', e.target.value)} placeholder="Referral from Jane, apply before May 1…" />
          </div>
        </div>

        {error && <div style={{ marginTop:12, fontSize:12, color:'#EF4444' }}>{error}</div>}

        <div style={{ display:'flex', gap:10, marginTop:22 }}>
          <Btn variant="primary" onClick={submit} disabled={saving}>
            {saving ? 'Importing…' : 'Import Job'}
          </Btn>
          <Btn variant="secondary" onClick={onClose}>Cancel</Btn>
        </div>
      </div>
    </div>
  )
}

// ── Focus queue ───────────────────────────────────────────────────────────────
function FocusQueue({ focus, onSelectJob, setTab, dark }) {
  const T = dark ? DARK : LIGHT
  if (!focus?.length) return null
  return (
    <div style={{ marginBottom: 24 }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10 }}>
        Today's Focus
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 10 }}>
        {focus.map(item => (
          <div key={item.id}
            onClick={() => {
              if (item.jobId) onSelectJob({ id: item.jobId, _needsFetch: true })
              else setTab(item.tab)
            }}
            style={{
              background: T.card, border: `1px solid ${T.border}`,
              borderLeft: `3px solid ${item.color}`,
              borderRadius: 10, padding: '12px 14px', cursor: 'pointer',
              transition: 'all 0.15s',
              display: 'flex', flexDirection: 'column', gap: 6,
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = item.color; e.currentTarget.style.boxShadow = `0 0 0 3px ${item.color}18` }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = T.border; e.currentTarget.style.borderLeftColor = item.color; e.currentTarget.style.boxShadow = 'none' }}
          >
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
              <span style={{ fontSize: 16, lineHeight: 1.2 }}>{item.icon}</span>
              <span style={{ fontSize: 12, color: T.text, fontWeight: 500, flex: 1, lineHeight: 1.4 }}>{item.label}</span>
            </div>
            <span style={{ fontSize: 11, fontWeight: 700, color: item.color, alignSelf: 'flex-start' }}>{item.cta} →</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Tab definitions ───────────────────────────────────────────────────────────
const TABS = [
  { id: 'new',      label: 'New',      statusFilter: 'new' },
  { id: 'ready',    label: 'Ready',    statusFilter: 'queued' },
  { id: 'approved', label: 'Approved', statusFilter: 'approved' },
  { id: 'applied',  label: 'Applied',  statusFilter: null },   // applied+oa+interview
  { id: 'all',      label: 'All',      statusFilter: null },
]

export default function JobsView({ onSelectJob, selectedJob, tab, setTab, stats, onRefresh, triggerRefresh }) {
  const { dark } = useContext(ThemeCtx)
  const T = dark ? DARK : LIGHT

  const [search, setSearch]       = useState('')
  const [sort, setSort]           = useState('score')
  const [minScore, setMinScore]   = useState(0)
  const [jobs, setJobs]           = useState([])
  const [focus, setFocus]         = useState([])
  const [loading, setLoading]     = useState(true)
  const [showImport, setShowImport] = useState(false)

  // Fetch jobs when tab or filters change
  useEffect(() => {
    setLoading(true)
    const tabDef = TABS.find(t => t.id === tab)
    const params = { min_score: minScore, sort, limit: 500 }

    if (tab === 'applied') {
      // fetch all applied-stage statuses
      Promise.all(['applied','oa','interview','offer'].map(s =>
        api.jobs({ ...params, status: s, limit: 200 })
      )).then(results => {
        setJobs(results.flatMap(r => r.jobs))
        setLoading(false)
      }).catch(() => setLoading(false))
    } else {
      if (tabDef?.statusFilter) params.status = tabDef.statusFilter
      api.jobs(params).then(r => { setJobs(r.jobs); setLoading(false) }).catch(() => setLoading(false))
    }
  }, [tab, minScore, sort, onRefresh])

  // Fetch focus items once
  useEffect(() => {
    api.focus().then(setFocus).catch(() => {})
  }, [onRefresh])

  // Client-side search filter
  const filteredJobs = useMemo(() => {
    if (!search) return jobs
    const q = search.toLowerCase()
    return jobs.filter(j =>
      (j.title    || '').toLowerCase().includes(q) ||
      (j.company  || '').toLowerCase().includes(q) ||
      (j.location || '').toLowerCase().includes(q)
    )
  }, [jobs, search])

  const tabCount = (tabId) => {
    if (!stats) return 0
    if (tabId === 'new')      return stats.new
    if (tabId === 'ready')    return stats.ready
    if (tabId === 'approved') return stats.approved
    if (tabId === 'applied')  return stats.applied + stats.oa + stats.interview
    if (tabId === 'all')      return stats.total
    return 0
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Focus queue */}
      <div style={{ padding: '20px 24px 0', flexShrink: 0 }}>
        <FocusQueue focus={focus} onSelectJob={onSelectJob} setTab={setTab} dark={dark} />
      </div>

      {/* Tab bar */}
      <div style={{ padding: '0 24px', flexShrink: 0, borderBottom: `1px solid ${T.border}`, display: 'flex', alignItems: 'center', gap: 2 }}>
        {TABS.map(t => {
          const active = tab === t.id
          const count  = tabCount(t.id)
          return (
            <button key={t.id} onClick={() => setTab(t.id)}
              style={{
                padding: '10px 14px', border: 'none', cursor: 'pointer',
                borderRadius: '8px 8px 0 0', background: 'transparent',
                fontFamily: 'DM Sans, sans-serif', fontSize: 12,
                fontWeight: active ? 700 : 500,
                color: active ? T.accent : T.muted,
                borderBottom: active ? `2px solid ${T.accent}` : '2px solid transparent',
                display: 'flex', alignItems: 'center', gap: 6, transition: 'all 0.12s',
              }}>
              {t.label}
              {count > 0 && (
                <span style={{
                  background: active ? T.accent : (dark ? '#252538' : '#E2E2EE'),
                  color: active ? '#fff' : T.muted,
                  fontSize: 10, fontWeight: 800, borderRadius: 10, padding: '1px 6px',
                }}>{count}</span>
              )}
            </button>
          )
        })}
        <div style={{ flex: 1 }} />
        <button style={{
          padding: '6px 12px', borderRadius: 6, border: `1px solid ${T.border}`,
          background: 'transparent', color: T.muted, fontSize: 11, fontWeight: 600,
          cursor: 'pointer', fontFamily: 'DM Sans, sans-serif', marginBottom: 2,
        }} onClick={() => setShowImport(true)}>+ Import</button>
      </div>

      {/* Filter bar */}
      <div style={{ padding: '12px 24px', flexShrink: 0, display: 'flex', gap: 10, alignItems: 'center' }}>
        <Input value={search} onChange={setSearch} placeholder="Search title, company, location…" icon="⌕" style={{ flex: 1, maxWidth: 360 }} />

        <select value={sort} onChange={e => setSort(e.target.value)}
          style={{
            padding: '8px 12px', borderRadius: 8, border: `1px solid ${T.border}`,
            background: dark ? '#1A1A28' : '#FAFAFA', color: T.text,
            fontSize: 12, fontFamily: 'DM Sans, sans-serif', cursor: 'pointer', outline: 'none',
          }}>
          <option value="score">Score ↓</option>
          <option value="company">Company A–Z</option>
          <option value="starred">Starred first</option>
        </select>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 11, color: T.muted, whiteSpace: 'nowrap' }}>Min score</span>
          <input type="range" min={0} max={1} step={0.05} value={minScore}
            onChange={e => setMinScore(parseFloat(e.target.value))}
            style={{ width: 80, accentColor: T.accent }}
          />
          <span style={{ fontSize: 11, color: T.text, fontFamily: 'JetBrains Mono, monospace', width: 32 }}>
            {Math.round(minScore * 100)}%
          </span>
        </div>

        <div style={{ fontSize: 11, color: T.muted, whiteSpace: 'nowrap' }}>
          {filteredJobs.length} jobs
        </div>
      </div>

      {/* Job list */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '0 12px 24px' }}>
        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}>
            <Spinner size={28} />
          </div>
        ) : filteredJobs.length === 0 ? (
          <EmptyState icon="◌" title="No jobs match these filters" sub="Try adjusting the score slider or search term" />
        ) : (
          filteredJobs.map(job => (
            <JobRow key={job.id} job={job} onSelect={onSelectJob} selected={selectedJob?.id === job.id} />
          ))
        )}
      </div>

      {showImport && (
        <ImportModal
          dark={dark}
          onClose={() => setShowImport(false)}
          onSuccess={() => triggerRefresh?.()}
        />
      )}
    </div>
  )
}
