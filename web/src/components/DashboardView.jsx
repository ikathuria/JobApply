import { useState, useEffect } from 'react'
import { api } from '../api.js'
import { StatusBadge } from './ui/index.jsx'

function StatCard({ tone, label, value, sub }) {
  return (
    <div
      className="stat-card"
      style={{
        background: `var(--${tone}-soft)`,
        borderColor: `var(--${tone})`,
      }}
    >
      <div
        className="stat-card-icon"
        style={{
          background: `var(--${tone})`,
          color:      `var(--${tone}-ink)`,
        }}
      >
        <svg width="13" height="13" viewBox="0 0 16 16" fill="currentColor">
          <circle cx="8" cy="8" r="6" />
        </svg>
      </div>
      <div className="col gap-1">
        <div className="stat-value" style={{ color: `var(--${tone}-ink)` }}>{value}</div>
        <div className="stat-label">{label}</div>
        <div className="stat-sub">{sub}</div>
      </div>
    </div>
  )
}

function MatchCard({ job, onClick }) {
  const pct = Math.round((job.score ?? 0) * 100)
  const scoreColor = pct >= 75 ? 'var(--ok)' : pct >= 55 ? 'var(--warn)' : 'var(--bad)'
  return (
    <div className="match-card" onClick={() => onClick(job)}>
      <div
        className="score-chip"
        style={{
          background: pct >= 75 ? 'var(--green-soft)' : pct >= 55 ? 'var(--yellow-soft)' : 'var(--bad-soft)',
        }}
      >
        <span className="score-num" style={{ color: scoreColor }}>{pct}</span>
        <span className="score-lbl" style={{ color: scoreColor }}>match</span>
      </div>
      <div className="col grow" style={{ minWidth: 0 }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {job.starred ? <span style={{ color: 'var(--warn)', marginRight: 4 }}>★</span> : null}
          {job.title}
        </span>
        <span style={{ fontSize: 11, color: 'var(--ink-3)', marginTop: 2 }}>
          {job.company}{job.location ? ` · ${job.location}` : ''}
        </span>
      </div>
      <StatusBadge status={job.status} />
    </div>
  )
}

export default function DashboardView({ stats, setTab, onSelectJob, onRefresh }) {
  const [topJobs, setTopJobs] = useState([])
  const [focus, setFocus]     = useState([])

  useEffect(() => {
    api.jobs({ sort: 'score', limit: 6, min_score: 0 })
      .then(r => setTopJobs(r.jobs.filter(j => !['rejected','skipped'].includes(j.status)).slice(0, 4)))
      .catch(() => {})
    api.focus().then(setFocus).catch(() => {})
  }, [onRefresh])

  const s = stats || {}
  const tailored   = (s.ready ?? 0) + (s.approved ?? 0)
  const inPipeline = (s.oa ?? 0) + (s.interview ?? 0)
  const totalApplied = (s.applied ?? 0) + (s.oa ?? 0) + (s.interview ?? 0) + (s.offer ?? 0) + (s.rejected ?? 0)

  return (
    <div className="scroll" style={{ flex: 1, padding: 24, minHeight: 0 }}>

      {/* Hero banner */}
      <div className="hero-banner">
        <div className="row" style={{ justifyContent: 'space-between', alignItems: 'flex-end', gap: 24, flexWrap: 'wrap' }}>
          <div className="col gap-3" style={{ maxWidth: 520 }}>
            <span className="eyebrow" style={{ padding: 0 }}>AI/ML Internship Search · Summer 2026</span>
            <h1 className="hero-title">
              The hunt is <em>on.</em>
            </h1>
            <div style={{ fontSize: 14, color: 'var(--ink-2)', lineHeight: 1.6, maxWidth: 460 }}>
              Tracked <strong>{s.total ?? 0} job leads</strong>, tailored{' '}
              <strong>{tailored} resumes</strong>, submitted{' '}
              <strong>{totalApplied} applications</strong>.
            </div>
            <div className="row gap-2" style={{ marginTop: 4, flexWrap: 'wrap' }}>
              <button className="btn-primary" onClick={() => setTab('ready')}>
                Review Queue →
              </button>
              <button className="btn-secondary" onClick={() => setTab('new')}>
                View New Jobs
              </button>
            </div>
          </div>

          {/* Focus tasks */}
          {focus.length > 0 && (
            <div className="col gap-2" style={{ minWidth: 200, maxWidth: 240 }}>
              <span className="eyebrow" style={{ padding: 0 }}>Today's focus</span>
              {focus.slice(0, 3).map(item => (
                <div
                  key={item.id}
                  onClick={() => item.jobId ? onSelectJob({ id: item.jobId, _needsFetch: true }) : setTab(item.tab)}
                  style={{
                    background: 'rgba(255,255,255,0.55)',
                    border: `1px solid ${item.color}50`,
                    borderLeft: `3px solid ${item.color}`,
                    borderRadius: 10,
                    padding: '9px 12px',
                    cursor: 'pointer',
                    backdropFilter: 'blur(4px)',
                  }}
                >
                  <div className="row gap-2">
                    <span style={{ fontSize: 15 }}>{item.icon}</span>
                    <span style={{ fontSize: 12, color: 'var(--ink)', fontWeight: 500, lineHeight: 1.35 }}>{item.label}</span>
                  </div>
                  <span style={{ fontSize: 11, fontWeight: 700, color: item.color, marginTop: 4, display: 'block' }}>{item.cta} →</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Stat cards */}
      <div className="stats-grid">
        <StatCard tone="blue"   label="Total Discovered" value={s.total ?? 0}    sub="all sources" />
        <StatCard tone="orange" label="Applications"     value={totalApplied}    sub="submitted" />
        <StatCard tone="pink"   label="In Pipeline"      value={inPipeline}      sub="OA + interview" />
        <StatCard tone="teal"   label="Offers"           value={s.offer ?? 0}    sub="received" />
      </div>

      {/* Top matches */}
      {topJobs.length > 0 && (
        <div>
          <div className="row" style={{ justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <div>
              <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--ink)' }}>Top Matches</div>
              <div style={{ fontSize: 11, color: 'var(--ink-3)', marginTop: 2 }}>Highest-scored active leads</div>
            </div>
            <button className="btn-secondary" onClick={() => setTab('all')} style={{ padding: '6px 14px', fontSize: 11 }}>
              See all →
            </button>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 10 }}>
            {topJobs.map(job => (
              <MatchCard key={job.id} job={job} onClick={onSelectJob} />
            ))}
          </div>
        </div>
      )}

      {/* Empty state */}
      {!stats && (
        <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--ink-3)' }}>
          <div style={{ fontSize: 13 }}>Connecting to backend…</div>
        </div>
      )}
    </div>
  )
}
