import { useState, useMemo, useEffect, useContext } from 'react'
import { ThemeCtx } from './ThemeContext.jsx'
import { DARK, LIGHT } from '../theme.js'
import { Input, EmptyState, Spinner } from './ui/index.jsx'
import JobRow from './JobRow.jsx'
import { api } from '../api.js'

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

export default function JobsView({ onSelectJob, selectedJob, tab, setTab, stats, onRefresh }) {
  const { dark } = useContext(ThemeCtx)
  const T = dark ? DARK : LIGHT

  const [search, setSearch]       = useState('')
  const [sort, setSort]           = useState('score')
  const [minScore, setMinScore]   = useState(0)
  const [jobs, setJobs]           = useState([])
  const [focus, setFocus]         = useState([])
  const [loading, setLoading]     = useState(true)

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
        }}>+ Import</button>
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
    </div>
  )
}
