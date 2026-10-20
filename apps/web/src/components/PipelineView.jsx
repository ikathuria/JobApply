import { useState, useEffect } from 'react'
import { api } from '../api.js'
import JobsView from './JobsView.jsx'

// PipelineView (M29) — the single primary surface for the daily apply loop.
// One ruled "Today" line sits above the JobsView board (stage tabs New → Ready →
// Approved → Applied → All + review/apply decks). It holds the two "needs
// action" cues: the top focus item and stale applications due for follow-up.
// Either half expands in place. Funnel counts live in the topbar and sidebar.

const label = {
  fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 600, color: 'var(--muted)',
  textTransform: 'uppercase', letterSpacing: '0.08em', flexShrink: 0,
}
const linkBtn = {
  background: 'none', border: 'none', cursor: 'pointer', padding: '6px 0', minHeight: 32,
  fontFamily: 'var(--font-text)', fontSize: 13, textAlign: 'left',
  display: 'flex', alignItems: 'center', gap: 8, minWidth: 0,
}
const listRow = {
  display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12,
  padding: '8px 0', borderTop: '1px solid var(--line)', cursor: 'pointer', fontSize: 13,
}

function TodayStrip({ focus, followups, onSelectJob, setTab }) {
  const [open, setOpen] = useState(null)  // 'focus' | 'followups' | null
  if (!focus.length && !followups.length) return null
  const toggle = k => setOpen(o => (o === k ? null : k))
  const openFocus = item => item.jobId ? onSelectJob({ id: item.jobId, _needsFetch: true }) : setTab(item.tab)
  const openJob = id => onSelectJob({ id, _needsFetch: true })
  const key = fn => e => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), fn())

  return (
    <section aria-label="Today" style={{ margin: '0 28px', borderBottom: '1px solid var(--line)', flexShrink: 0 }}>
      <div className="today-row">
        <span className="today-label" style={label}>Today</span>

        {focus.length > 0 && (
          <div className="today-cell">
            <button onClick={() => toggle('focus')} aria-expanded={open === 'focus'} style={{ ...linkBtn, color: 'var(--ink)', flex: 1 }}>
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{focus[0].label}</span>
              {focus.length > 1 && <span className="mono" style={{ color: 'var(--muted)', flexShrink: 0 }}>+{focus.length - 1}</span>}
            </button>
            <button onClick={() => openFocus(focus[0])} style={{ ...linkBtn, color: 'var(--accent)', fontWeight: 600, flexShrink: 0 }}>
              {focus[0].cta} →
            </button>
          </div>
        )}

        {followups.length > 0 && (
          <div className="today-cell today-warn">
            <button onClick={() => toggle('followups')} aria-expanded={open === 'followups'} style={{ ...linkBtn, color: 'var(--ink)', flex: 1 }}>
              <span className="mono tabular" style={{ color: 'var(--warn)', fontWeight: 700 }}>{followups.length}</span>
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>no reply in 7+ days</span>
            </button>
            <button onClick={() => setTab('applied')} style={{ ...linkBtn, color: 'var(--warn)', fontWeight: 600, flexShrink: 0 }}>
              Follow up →
            </button>
          </div>
        )}
      </div>

      {open === 'focus' && (
        <div style={{ paddingBottom: 8 }}>
          {focus.map(item => (
            <div key={item.id} role="button" tabIndex={0} onClick={() => openFocus(item)} onKeyDown={key(() => openFocus(item))} style={listRow}>
              <span style={{ color: 'var(--ink)' }}>{item.label}</span>
              <span style={{ color: 'var(--accent)', fontWeight: 600, flexShrink: 0 }}>{item.cta} →</span>
            </div>
          ))}
        </div>
      )}

      {open === 'followups' && (
        <div style={{ paddingBottom: 8 }}>
          {followups.slice(0, 8).map(j => (
            <div key={j.id} role="button" tabIndex={0} onClick={() => openJob(j.id)} onKeyDown={key(() => openJob(j.id))} style={listRow}>
              <span style={{ color: 'var(--ink)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {j.title} <span style={{ color: 'var(--muted)' }}>· {j.company || 'N/A'}</span>
              </span>
              <span className="mono tabular" style={{ color: 'var(--warn)', fontWeight: 600, flexShrink: 0 }}>
                {j.days_since_applied != null ? `${j.days_since_applied}d` : ''}
              </span>
            </div>
          ))}
          {followups.length > 8 && (
            <button onClick={() => setTab('applied')} style={{ ...linkBtn, color: 'var(--muted)' }}>
              {followups.length - 8} more in Applied →
            </button>
          )}
        </div>
      )}
    </section>
  )
}

export default function PipelineView(props) {
  const { onSelectJob, setTab, onRefresh } = props
  const [followups, setFollowups] = useState([])
  const [focus, setFocus] = useState([])

  useEffect(() => {
    api.appFollowups(7).then(setFollowups).catch(() => setFollowups([]))
    api.focus().then(setFocus).catch(() => setFocus([]))
  }, [onRefresh])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <TodayStrip focus={focus} followups={followups} onSelectJob={onSelectJob} setTab={setTab} />
      <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <JobsView {...props} />
      </div>
    </div>
  )
}
