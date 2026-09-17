import { useState, useEffect, useContext } from 'react'
import { ThemeCtx } from './ThemeContext.jsx'
import { DARK, LIGHT } from '../theme.js'
import { api } from '../api.js'
import JobsView from './JobsView.jsx'

// PipelineView (M29) — the single primary surface for the daily apply loop.
// It composes the existing JobsView board (Today's Focus + stage tabs New →
// Ready → Approved → Applied → All + review/apply decks) and folds the one
// unique "needs action" cue from the old Dashboard — stale applications due for
// follow-up — into a slim header above it. At-a-glance funnel counts already
// live in the sidebar, so we don't duplicate the old stat-card grid here.

function FollowupBanner({ followups, onSelectJob, setTab }) {
  const { dark } = useContext(ThemeCtx)
  const T = dark ? DARK : LIGHT
  const [open, setOpen] = useState(false)
  if (!followups.length) return null

  return (
    <div
      style={{
        margin: '16px 24px 0', flexShrink: 0,
        background: 'rgba(245,158,11,0.08)',
        border: '1px solid rgba(245,158,11,0.35)',
        borderRadius: 12, padding: '12px 16px',
      }}
    >
      <div className="row" style={{ alignItems: 'center', gap: 10 }}>
        <button
          onClick={() => setOpen(o => !o)}
          aria-expanded={open}
          style={{
            display: 'flex', alignItems: 'center', gap: 8, flex: 1,
            background: 'none', border: 'none', cursor: 'pointer', padding: 0, textAlign: 'left',
            fontFamily: 'Inter, system-ui, sans-serif',
          }}
        >
          <span style={{ fontSize: 13, fontWeight: 700, color: T.text }}>
            ⏰ {followups.length} application{followups.length !== 1 ? 's' : ''} to follow up
          </span>
          <span style={{ fontSize: 11, color: T.muted }}>· no response in 7+ days</span>
          <span style={{ flex: 1 }} />
          <span style={{ fontSize: 11, color: T.muted, transform: open ? 'rotate(90deg)' : 'none', transition: 'transform 0.15s' }}>▸</span>
        </button>
        <button
          onClick={() => setTab('applied')}
          style={{
            padding: '5px 12px', borderRadius: 6, border: `1px solid ${T.border}`,
            background: 'transparent', color: '#B45309', fontSize: 11, fontWeight: 700,
            cursor: 'pointer', fontFamily: 'Inter, system-ui, sans-serif', flexShrink: 0,
          }}
        >
          View applied →
        </button>
      </div>

      {open && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 10 }}>
          {followups.slice(0, 6).map(j => (
            <div key={j.id}
              role="button" tabIndex={0}
              onClick={() => onSelectJob({ id: j.id, _needsFetch: true })}
              onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), onSelectJob({ id: j.id, _needsFetch: true }))}
              style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, padding: '8px 12px', background: 'rgba(255,255,255,0.5)', borderRadius: 8, cursor: 'pointer' }}>
              <span style={{ fontSize: 12, color: 'var(--ink)', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {j.title} <span style={{ color: 'var(--ink-3)' }}>@ {j.company || 'N/A'}</span>
              </span>
              <span style={{ fontSize: 11, fontWeight: 700, color: '#B45309', flexShrink: 0, fontFamily: 'JetBrains Mono, monospace' }}>
                {j.days_since_applied != null ? `${j.days_since_applied}d` : ''}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function PipelineView(props) {
  const { onSelectJob, setTab, onRefresh } = props
  const [followups, setFollowups] = useState([])

  useEffect(() => {
    api.appFollowups(7).then(setFollowups).catch(() => setFollowups([]))
  }, [onRefresh])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <FollowupBanner followups={followups} onSelectJob={onSelectJob} setTab={setTab} />
      <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <JobsView {...props} />
      </div>
    </div>
  )
}
