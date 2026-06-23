import { useState, useContext } from 'react'
import { ThemeCtx } from './ThemeContext.jsx'
import { DARK, LIGHT, STATUS_META, NEXT_ACTION } from '../theme.js'
import { StatusBadge, Tag } from './ui/index.jsx'

export default function JobRow({ job, onSelect, selected, checked, onCheck, multiSelectMode }) {
  const { dark } = useContext(ThemeCtx)
  const T = dark ? DARK : LIGHT
  const [hov, setHov] = useState(false)

  const score = job.score ?? 0
  const pct   = Math.round(score * 100)
  const scoreColor = score >= 0.75 ? T.success : score >= 0.55 ? T.warning : T.danger
  const next = NEXT_ACTION[job.status] || { label: 'View →', color: T.muted }

  // Show checkbox when: any item is selected (multi-select mode), or hovering
  const showCheck = multiSelectMode || hov || checked

  return (
    <div
      onClick={() => multiSelectMode ? onCheck(job.id) : onSelect(job)}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        display: 'flex', alignItems: 'center', gap: 12,
        padding: '10px 16px', borderRadius: 8, cursor: 'pointer',
        transition: 'all 0.12s',
        background: checked
          ? (dark ? '#8B5CF615' : '#F3F0FF')
          : selected
            ? T.accentBg
            : hov
              ? (dark ? '#1E1E2E' : '#F0F0FA')
              : 'transparent',
        borderLeft: checked
          ? '2px solid #8B5CF6'
          : selected
            ? `2px solid ${T.accent}`
            : '2px solid transparent',
        marginBottom: 1,
      }}
    >
      {/* Score circle — doubles as checkbox in multi-select mode */}
      <div
        onClick={e => { e.stopPropagation(); onCheck?.(job.id) }}
        style={{ position: 'relative', width: 36, height: 36, flexShrink: 0, cursor: onCheck ? 'pointer' : 'default' }}
      >
        {/* Score ring (fades when checkbox is shown) */}
        <div style={{
          position: 'absolute', inset: 0,
          borderRadius: '50%',
          background: `conic-gradient(${scoreColor} ${pct * 3.6}deg, ${dark ? '#252538' : '#E2E2EE'} 0deg)`,
          opacity: showCheck ? 0 : 1,
          transition: 'opacity 0.15s',
        }} />
        {/* Inner score number */}
        <div style={{
          position: 'absolute', inset: 5,
          borderRadius: '50%',
          background: checked ? '#8B5CF620' : selected ? T.accentBg : (dark ? T.surface : '#fff'),
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 9, fontWeight: 800, color: scoreColor,
          fontFamily: 'JetBrains Mono, monospace',
          opacity: showCheck ? 0 : 1,
          transition: 'opacity 0.15s',
        }}>{pct}</div>

        {/* Checkbox overlay */}
        <div style={{
          position: 'absolute', inset: 0,
          borderRadius: '50%',
          background: checked ? '#8B5CF6' : (dark ? '#252538' : '#E8E8F4'),
          border: `2px solid ${checked ? '#8B5CF6' : (dark ? '#444' : '#C8C8DC')}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          opacity: showCheck ? 1 : 0,
          transition: 'opacity 0.15s, background 0.15s',
        }}>
          {checked && (
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M2.5 7L5.5 10L11.5 4" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          )}
        </div>
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
      {(hov || selected) && !multiSelectMode && <Tag>{job.source}</Tag>}

      {/* Status badge */}
      <StatusBadge status={job.status} />

      {/* Action hint — hidden in multi-select mode */}
      {(hov || selected) && !multiSelectMode && (
        <div style={{ fontSize: 11, fontWeight: 700, color: next.color, whiteSpace: 'nowrap', minWidth: 60, textAlign: 'right' }}>
          {next.label}
        </div>
      )}
    </div>
  )
}
