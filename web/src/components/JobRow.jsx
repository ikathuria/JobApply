import { useState, useContext } from 'react'
import { ThemeCtx } from './ThemeContext.jsx'
import { DARK, LIGHT, STATUS_META, NEXT_ACTION } from '../theme.js'
import { StatusBadge, Tag } from './ui/index.jsx'

export default function JobRow({ job, onSelect, selected }) {
  const { dark } = useContext(ThemeCtx)
  const T = dark ? DARK : LIGHT
  const [hov, setHov] = useState(false)

  const score = job.score ?? 0
  const pct   = Math.round(score * 100)
  const scoreColor = score >= 0.75 ? T.success : score >= 0.55 ? T.warning : T.danger
  const next = NEXT_ACTION[job.status] || { label: 'View →', color: T.muted }

  return (
    <div
      onClick={() => onSelect(job)}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        display: 'flex', alignItems: 'center', gap: 12,
        padding: '10px 16px', borderRadius: 8, cursor: 'pointer',
        transition: 'all 0.12s',
        background: selected ? T.accentBg : hov ? (dark ? '#1E1E2E' : '#F0F0FA') : 'transparent',
        borderLeft: selected ? `2px solid ${T.accent}` : '2px solid transparent',
        marginBottom: 1,
      }}
    >
      {/* Score circle */}
      <div style={{
        width: 36, height: 36, borderRadius: '50%', flexShrink: 0,
        background: `conic-gradient(${scoreColor} ${pct * 3.6}deg, ${dark ? '#252538' : '#E2E2EE'} 0deg)`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <div style={{
          width: 26, height: 26, borderRadius: '50%',
          background: selected ? T.accentBg : (dark ? T.surface : '#fff'),
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 9, fontWeight: 800, color: scoreColor,
          fontFamily: 'JetBrains Mono, monospace',
        }}>{pct}</div>
      </div>

      {/* Title + company */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          fontSize: 13, fontWeight: 600, color: T.text,
          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
          display: 'flex', alignItems: 'center', gap: 6,
        }}>
          {job.starred ? <span style={{ color: '#F59E0B', fontSize: 10 }}>★</span> : null}
          {job.title}
        </div>
        <div style={{ fontSize: 11, color: T.muted, display: 'flex', alignItems: 'center', gap: 5, marginTop: 1, flexWrap: 'nowrap' }}>
          <span style={{ fontWeight: 600 }}>{job.company}</span>
          <span>·</span>
          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{job.location}</span>
          {job.interview_date && (
            <span style={{ color: '#EC4899', fontWeight: 600, whiteSpace: 'nowrap' }}>
              · 🎤 {job.interview_date?.slice(0, 10)}
            </span>
          )}
        </div>
      </div>

      {/* Source tag */}
      {(hov || selected) && <Tag>{job.source}</Tag>}

      {/* Status badge */}
      <StatusBadge status={job.status} />

      {/* Action hint */}
      {(hov || selected) && (
        <div style={{ fontSize: 11, fontWeight: 700, color: next.color, whiteSpace: 'nowrap', minWidth: 60, textAlign: 'right' }}>
          {next.label}
        </div>
      )}
    </div>
  )
}
