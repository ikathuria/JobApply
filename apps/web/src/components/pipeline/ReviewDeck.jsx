import { useState, useEffect, useRef } from 'react'
import { DARK, LIGHT } from '../../theme.js'
import { EmptyState, Spinner, StatusBadge, Tag } from '../ui/index.jsx'

export default function ReviewDeck({ jobs, loading, dark, onOpenJob, onDecision }) {
  const T = dark ? DARK : LIGHT
  const [drag, setDrag] = useState({ active: false, startX: 0, x: 0 })
  const [busy, setBusy] = useState(false)
  const pointerId = useRef(null)
  const topJob = jobs[0]
  const nextJob = jobs[1]
  const dx = drag.x
  const intent = dx > 42 ? 'approve' : dx < -42 ? 'skip' : null

  async function decide(status) {
    if (!topJob || busy) return
    setBusy(true)
    setDrag({ active: false, startX: 0, x: status === 'approved' ? 520 : -520 })
    try {
      await onDecision(topJob, status)
    } finally {
      setTimeout(() => {
        setDrag({ active: false, startX: 0, x: 0 })
        setBusy(false)
      }, 160)
    }
  }

  useEffect(() => {
    const handler = e => {
      if (!topJob) return
      const tag = e.target?.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
      if (e.key === 'ArrowLeft') {
        e.preventDefault()
        decide('skipped')
      }
      if (e.key === 'ArrowRight') {
        e.preventDefault()
        decide('approved')
      }
      if (e.key === 'Enter') {
        e.preventDefault()
        onOpenJob(topJob)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [topJob?.id, busy])

  const score = topJob?.score ?? 0
  const pct = Math.round(score * 100)
  const whyFit = (() => {
    const raw = (topJob?.notes || '').trim()
    const match = raw.match(/why[_\s-]?fit\s*:\s*([\s\S]*)/i)
    const text = (match ? match[1] : raw || topJob?.description || '').trim()
    return text.replace(/\s+/g, ' ').slice(0, 340)
  })()
  const salary = topJob?.salary_range?.trim?.() || topJob?.salary_range || 'Not listed'
  const skills = (topJob?.matched_skills || topJob?.keywords || '')
    .toString()
    .split(',')
    .map(s => s.trim())
    .filter(Boolean)
    .slice(0, 6)

  return (
    <div style={{ flex: 1, overflow: 'auto', padding: '18px 24px 28px' }}>
      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}>
          <Spinner size={28} />
        </div>
      ) : !topJob ? (
        <EmptyState icon="OK" title="Ready queue cleared" sub="Everything here has been approved or removed from the review list." />
      ) : (
        <div style={{ maxWidth: 880, margin: '0 auto' }}>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'minmax(0, 1fr) 220px',
            gap: 22,
            alignItems: 'start',
          }}>
            <div style={{ minWidth: 0 }}>
              <div style={{
                height: 520,
                position: 'relative',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}>
                {nextJob && (
                  <div style={{
                    position: 'absolute',
                    inset: '34px 30px 10px',
                    borderRadius: 18,
                    border: `1px solid ${T.border}`,
                    background: T.surface,
                    opacity: 0.55,
                    transform: 'scale(0.96) translateY(16px)',
                  }} />
                )}

                <div
                  onPointerDown={e => {
                    if (busy) return
                    pointerId.current = e.pointerId
                    e.currentTarget.setPointerCapture(e.pointerId)
                    setDrag({ active: true, startX: e.clientX, x: 0 })
                  }}
                  onPointerMove={e => {
                    if (!drag.active || pointerId.current !== e.pointerId) return
                    setDrag(d => ({ ...d, x: e.clientX - d.startX }))
                  }}
                  onPointerUp={e => {
                    if (pointerId.current === e.pointerId) pointerId.current = null
                    if (dx > 110) decide('approved')
                    else if (dx < -110) decide('skipped')
                    else setDrag({ active: false, startX: 0, x: 0 })
                  }}
                  style={{
                    position: 'absolute',
                    inset: 0,
                    borderRadius: 20,
                    border: `1px solid ${intent === 'approve' ? '#22C55E' : intent === 'skip' ? '#EF4444' : T.border}`,
                    background: T.card,
                    boxShadow: dark ? '0 24px 80px rgba(0,0,0,0.35)' : '0 24px 70px rgba(42,42,80,0.15)',
                    padding: 24,
                    cursor: busy ? 'wait' : drag.active ? 'grabbing' : 'grab',
                    touchAction: 'pan-y',
                    transform: `translateX(${dx}px) rotate(${dx / 22}deg)`,
                    transition: drag.active ? 'none' : 'transform 0.18s ease, border-color 0.18s ease',
                    userSelect: 'none',
                    overflow: 'hidden',
                  }}
                >
                  <div style={{
                    position: 'absolute',
                    top: 18,
                    left: 18,
                    border: '2px solid #EF4444',
                    color: '#EF4444',
                    borderRadius: 10,
                    padding: '7px 12px',
                    fontSize: 12,
                    fontWeight: 900,
                    opacity: intent === 'skip' ? 1 : 0,
                    transform: 'rotate(-10deg)',
                    transition: 'opacity 0.12s',
                  }}>
                    REMOVE
                  </div>
                  <div style={{
                    position: 'absolute',
                    top: 18,
                    right: 18,
                    border: '2px solid #22C55E',
                    color: '#22C55E',
                    borderRadius: 10,
                    padding: '7px 12px',
                    fontSize: 12,
                    fontWeight: 900,
                    opacity: intent === 'approve' ? 1 : 0,
                    transform: 'rotate(10deg)',
                    transition: 'opacity 0.12s',
                  }}>
                    APPROVE
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 18 }}>
                    <StatusBadge status={topJob.status} />
                    <div style={{ flex: 1 }} />
                    <div style={{
                      width: 58,
                      height: 58,
                      borderRadius: 16,
                      background: score >= 0.75 ? '#22C55E18' : score >= 0.55 ? '#F59E0B18' : '#EF444418',
                      border: `1px solid ${score >= 0.75 ? '#22C55E40' : score >= 0.55 ? '#F59E0B40' : '#EF444440'}`,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexDirection: 'column',
                    }}>
                      <div style={{ fontSize: 18, fontWeight: 900, color: score >= 0.75 ? T.success : score >= 0.55 ? T.warning : T.danger }}>{pct}</div>
                      <div style={{ fontSize: 9, fontWeight: 800, color: T.muted, textTransform: 'uppercase' }}>match</div>
                    </div>
                  </div>

                  <div style={{ fontSize: 11, color: T.muted, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>
                    Role
                  </div>
                  <div style={{ fontSize: 28, lineHeight: 1.12, fontWeight: 900, color: T.text, marginBottom: 10 }}>
                    {topJob.title}
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center', color: T.muted, fontSize: 13, marginBottom: 22 }}>
                    <span style={{ color: T.text, fontWeight: 800 }}>{topJob.company || 'Unknown company'}</span>
                    {topJob.location && <span>{topJob.location}</span>}
                    {topJob.source && <Tag>{topJob.source}</Tag>}
                  </div>

                  <div style={{
                    borderTop: `1px solid ${T.border}`,
                    borderBottom: `1px solid ${T.border}`,
                    padding: '16px 0 6px',
                    marginBottom: 18,
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr',
                    gap: 14,
                  }}>
                    <div>
                      <div style={{ fontSize: 10, color: T.muted, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 5 }}>Job link</div>
                      {topJob.url && !topJob.url.startsWith('manual://') ? (
                        <a
                          href={topJob.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          onPointerDown={e => e.stopPropagation()}
                          onClick={e => e.stopPropagation()}
                          style={{ fontSize: 13, color: T.accent, fontWeight: 700, textDecoration: 'none' }}
                        >
                          Open posting
                        </a>
                      ) : (
                        <div style={{ fontSize: 13, color: T.text, lineHeight: 1.45 }}>Not available</div>
                      )}
                    </div>
                    <div>
                      <div style={{ fontSize: 10, color: T.muted, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 5 }}>Salary range</div>
                      <div style={{ fontSize: 13, color: T.text, lineHeight: 1.45 }}>{salary}</div>
                    </div>
                  </div>

                  <div style={{ marginBottom: 14 }}>
                    <div style={{ fontSize: 10, color: T.muted, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 7 }}>
                      Why fit
                    </div>
                    <div style={{ minHeight: 96, fontSize: 13, color: T.text, lineHeight: 1.7, overflow: 'hidden' }}>
                      {whyFit || 'No fit summary yet. Open details to inspect the job and notes before deciding.'}
                      {whyFit && whyFit.length >= 340 ? '...' : ''}
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: 7, flexWrap: 'wrap', marginTop: 18 }}>
                    {skills.length ? skills.map(skill => <Tag key={skill}>{skill}</Tag>) : (
                      <span style={{ fontSize: 12, color: T.muted }}>No extracted skill tags yet.</span>
                    )}
                  </div>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginTop: 14 }}>
                <button onClick={() => decide('skipped')} disabled={busy} style={{
                  height: 46,
                  borderRadius: 12,
                  border: '1px solid #EF444440',
                  background: T.danger + '14',
                  color: '#EF4444',
                  fontSize: 13,
                  fontWeight: 900,
                  fontFamily: 'Inter, system-ui, sans-serif',
                  cursor: busy ? 'wait' : 'pointer',
                }}>Remove</button>
                <button onClick={() => onOpenJob({ ...topJob, _openTab: 'edit' })} style={{
                  height: 46,
                  borderRadius: 12,
                  border: `1px solid ${T.border}`,
                  background: T.card,
                  color: T.text,
                  fontSize: 13,
                  fontWeight: 800,
                  fontFamily: 'Inter, system-ui, sans-serif',
                  cursor: 'pointer',
                }}>Edit details</button>
                <button onClick={() => decide('approved')} disabled={busy} style={{
                  height: 46,
                  borderRadius: 12,
                  border: '1px solid #22C55E40',
                  background: '#22C55E',
                  color: '#fff',
                  fontSize: 13,
                  fontWeight: 900,
                  fontFamily: 'Inter, system-ui, sans-serif',
                  cursor: busy ? 'wait' : 'pointer',
                }}>Approve</button>
              </div>
            </div>

            <aside style={{
              border: `1px solid ${T.border}`,
              borderRadius: 14,
              background: T.surface,
              padding: 16,
            }}>
              <div style={{ fontSize: 12, color: T.muted, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10 }}>
                Review queue
              </div>
              <div style={{ fontSize: 34, fontWeight: 900, color: T.text, lineHeight: 1 }}>{jobs.length}</div>
              <div style={{ fontSize: 12, color: T.muted, marginTop: 5, marginBottom: 16 }}>ready jobs left</div>
              <div style={{ display: 'grid', gap: 8, fontSize: 12, color: T.text }}>
                <div><strong>Swipe left</strong> removes from this list.</div>
                <div><strong>Swipe right</strong> moves to Approved.</div>
                <div><strong>Enter</strong> opens details.</div>
              </div>
              <div style={{ borderTop: `1px solid ${T.border}`, margin: '16px 0', paddingTop: 14 }}>
                <button onClick={() => onOpenJob(topJob)} style={{
                  width: '100%',
                  padding: '9px 10px',
                  borderRadius: 10,
                  border: `1px solid ${T.border}`,
                  background: 'transparent',
                  color: T.accent,
                  fontSize: 12,
                  fontWeight: 800,
                  fontFamily: 'Inter, system-ui, sans-serif',
                  cursor: 'pointer',
                }}>Open full details</button>
              </div>
              {nextJob && (
                <div>
                  <div style={{ fontSize: 10, color: T.muted, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 7 }}>Up next</div>
                  <div style={{ fontSize: 13, color: T.text, fontWeight: 800, lineHeight: 1.3 }}>{nextJob.title}</div>
                  <div style={{ fontSize: 11, color: T.muted, marginTop: 4 }}>{nextJob.company}</div>
                </div>
              )}
            </aside>
          </div>
        </div>
      )}
    </div>
  )
}
