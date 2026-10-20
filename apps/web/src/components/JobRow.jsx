import { useState } from 'react'
import { NEXT_ACTION } from '../theme.js'
import { StatusBadge, Tag, AtsScore } from './ui/index.jsx'

// Columns (.gb-grid in index.css): match/checkbox · role · ATS · status · next action

const matchColor = score => score >= 0.75 ? 'var(--ok)' : score >= 0.55 ? 'var(--warn)' : 'var(--bad)'

export function JobListHeader() {
  const head = {
    fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 600, color: 'var(--muted)',
    textTransform: 'uppercase', letterSpacing: '0.07em',
  }
  return (
    <div className="gb-grid" style={{ ...head, padding: '10px 12px 8px', borderBottom: '1px solid var(--line-strong)', position: 'sticky', top: 0, background: 'var(--bg)', zIndex: 1 }}>
      <span style={{ textAlign: 'center' }}>Match</span>
      <span>Role</span>
      <span>ATS</span>
      <span className="gb-col-status" style={{ textAlign: 'center' }}>Status</span>
      <span className="gb-col-next" />
    </div>
  )
}

export default function JobRow({ job, onSelect, selected, checked, onCheck, multiSelectMode }) {
  const [hov, setHov] = useState(false)

  const score = job.score ?? 0
  const pct   = Math.round(score * 100)
  const next  = NEXT_ACTION[job.status] || { label: 'View →', color: 'var(--muted)' }

  // Checkbox replaces the match number when hovering or in multi-select mode
  const showCheck = multiSelectMode || hov || checked

  return (
    <div
      className={`gb-row gb-grid${selected || checked ? ' is-selected' : ''}`}
      role="button" tabIndex={0}
      onClick={() => multiSelectMode ? onCheck(job.id) : onSelect(job)}
      onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), multiSelectMode ? onCheck(job.id) : onSelect(job))}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        padding: '10px 12px', cursor: 'pointer',
        borderLeft: `3px solid ${selected || checked ? 'var(--accent)' : 'transparent'}`,
      }}
    >
      {/* Match score — doubles as checkbox in multi-select mode */}
      <span
        aria-hidden="true"
        title={checked ? 'Deselect' : 'Select'}
        onClick={e => { e.stopPropagation(); onCheck?.(job.id) }}
        style={{
          height: 30, padding: 0, borderRadius: 2, cursor: onCheck ? 'pointer' : 'default',
          fontFamily: 'var(--font-mono)', fontSize: 14, fontWeight: 600, fontVariantNumeric: 'tabular-nums',
          display: 'grid', placeItems: 'center',
          background: checked ? 'var(--accent)' : 'var(--surface)',
          border: `1px solid ${checked ? 'var(--accent)' : 'var(--line)'}`,
          color: checked ? 'var(--on-accent)' : showCheck ? 'var(--muted)' : matchColor(score),
        }}
      >
        {checked ? (
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
            <path d="M2.5 7L5.5 10L11.5 4" stroke="currentColor" strokeWidth="2" strokeLinecap="square" />
          </svg>
        ) : showCheck ? '☐' : pct}
      </span>

      {/* Title + company */}
      <div style={{ minWidth: 0 }}>
        <div style={{
          fontSize: 14, fontWeight: 600, color: 'var(--ink)',
          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
        }}>
          {job.starred ? <span aria-label="Starred" style={{ color: 'var(--warn)', marginRight: 6 }}>★</span> : null}
          {job.title}
        </div>
        <div style={{ fontSize: 12, color: 'var(--muted)', display: 'flex', alignItems: 'center', gap: 8, marginTop: 2, whiteSpace: 'nowrap', overflow: 'hidden' }}>
          <span style={{ fontWeight: 600, color: 'var(--ink-2)' }}>{job.company}</span>
          {job.known_sponsor && (
            <span title="Known H-1B sponsor" style={{
              fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700, color: 'var(--ok)',
              border: '1px solid currentColor', padding: '0 5px', flexShrink: 0,
            }}>H-1B</span>
          )}
          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{job.location}</span>
          {job.interview_date && (
            <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--info)', fontWeight: 600, flexShrink: 0 }}>
              interview {job.interview_date.slice(0, 10)}
            </span>
          )}
          {(hov || selected) && !multiSelectMode && job.source && <Tag>{job.source}</Tag>}
        </div>
      </div>

      <AtsScore score={job.ats_score} />

      <div className="gb-col-status" style={{ display: 'flex', justifyContent: 'center' }}><StatusBadge status={job.status} /></div>

      {/* Action hint — hidden in multi-select mode */}
      <div className="gb-col-next" style={{
        fontSize: 12, fontWeight: 600, color: next.color, whiteSpace: 'nowrap', textAlign: 'right',
        opacity: (hov || selected) && !multiSelectMode ? 1 : 0, transition: 'opacity var(--dur-1) var(--ease)',
      }}>
        {next.label}
      </div>
    </div>
  )
}
