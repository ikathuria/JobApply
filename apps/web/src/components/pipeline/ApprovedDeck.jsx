import { useState, useEffect } from 'react'
import { DARK, LIGHT } from '../../theme.js'
import { EmptyState, Spinner, StatusBadge, Tag } from '../ui/index.jsx'
import { api } from '../../api.js'

function safeFilePart(value) {
  return (value || 'job').toString().replace(/[^a-z0-9_-]+/gi, '_').replace(/^_+|_+$/g, '') || 'job'
}

async function downloadFile(url, filename) {
  const res = await fetch(url)
  if (!res.ok) {
    const message = await res.text().catch(() => res.statusText)
    throw new Error(message || res.statusText)
  }
  const blob = await res.blob()
  const objectUrl = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = objectUrl
  a.download = filename
  a.style.display = 'none'
  document.body.appendChild(a)
  a.click()
  a.remove()
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000)
}

export default function ApprovedDeck({ jobs, loading, dark, onOpenJob, onDecision }) {
  const T = dark ? DARK : LIGHT
  const [busy, setBusy] = useState(false)
  const [openedIds, setOpenedIds] = useState(new Set())
  const topJob = jobs[0]
  const nextJob = jobs[1]

  async function downloadPacket(job) {
    const prefix = `${safeFilePart(job.company)}_${job.id}`
    await Promise.all([
      downloadFile(api.resumeUrl(job.id), `${prefix}_resume.pdf`),
      downloadFile(api.coverLetterPdfUrl(job.id), `${prefix}_cover_letter.pdf`),
    ])
  }

  async function openPosting(job) {
    if (!job) return
    const hasPosting = job.url && !job.url.startsWith('manual://')
    if (hasPosting) {
      window.open(job.url, '_blank', 'noopener,noreferrer')
    }
    setOpenedIds(prev => new Set(prev).add(job.id))
    try {
      await downloadPacket(job)
    } catch (e) {
      alert(`Could not download both documents: ${e.message}`)
    }
    if (!hasPosting) {
      onOpenJob(job)
    }
  }

  async function decide(status) {
    if (!topJob || busy) return
    setBusy(true)
    try {
      await onDecision(topJob, status)
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => {
    const handler = e => {
      if (!topJob) return
      const tag = e.target?.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
      if (e.key === 'Enter') {
        e.preventDefault()
        openPosting(topJob)
      }
      if (e.key === 'ArrowRight') {
        e.preventDefault()
        decide('applied')
      }
      if (e.key === 'ArrowLeft') {
        e.preventDefault()
        decide('skipped')
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
    return text.replace(/\s+/g, ' ').slice(0, 300)
  })()
  const skills = (topJob?.matched_skills || topJob?.keywords || '')
    .toString()
    .split(',')
    .map(s => s.trim())
    .filter(Boolean)
    .slice(0, 6)
  const hasLink = !!(topJob?.url && !topJob.url.startsWith('manual://'))
  const opened = topJob ? openedIds.has(topJob.id) : false

  return (
    <div style={{ flex: 1, overflow: 'auto', padding: '18px 24px 28px' }}>
      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}>
          <Spinner size={28} />
        </div>
      ) : !topJob ? (
        <EmptyState icon="OK" title="Approved queue cleared" sub="No approved jobs are waiting to be opened." />
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
                minHeight: 500,
                borderRadius: 20,
                border: `1px solid ${opened ? '#22C55E60' : T.border}`,
                background: T.card,
                boxShadow: dark ? '0 24px 80px rgba(0,0,0,0.35)' : '0 24px 70px rgba(42,42,80,0.15)',
                padding: 24,
                position: 'relative',
                overflow: 'hidden',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 18 }}>
                  <StatusBadge status={topJob.status} />
                  {opened && <Tag style={{ color: '#22C55E' }}>opened</Tag>}
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
                  Approved application
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
                  padding: '16px 0',
                  marginBottom: 18,
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr',
                  gap: 14,
                }}>
                  <div>
                    <div style={{ fontSize: 10, color: T.muted, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 5 }}>Application link</div>
                    <div style={{ fontSize: 13, color: T.text, lineHeight: 1.45 }}>
                      {hasLink ? 'Opening this link downloads the resume and cover letter.' : 'No posting URL is stored for this job.'}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: 10, color: T.muted, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 5 }}>Documents</div>
                    <div style={{ fontSize: 13, color: T.text, lineHeight: 1.45 }}>Resume PDF and cover letter PDF</div>
                  </div>
                </div>

                <div style={{ marginBottom: 14 }}>
                  <div style={{ fontSize: 10, color: T.muted, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 7 }}>
                    Fit notes
                  </div>
                  <div style={{ minHeight: 84, fontSize: 13, color: T.text, lineHeight: 1.7, overflow: 'hidden' }}>
                    {whyFit || 'No fit summary yet. Open details if you want to inspect notes before applying.'}
                    {whyFit && whyFit.length >= 300 ? '...' : ''}
                  </div>
                </div>

                <div style={{ display: 'flex', gap: 7, flexWrap: 'wrap', marginTop: 18 }}>
                  {skills.length ? skills.map(skill => <Tag key={skill}>{skill}</Tag>) : (
                    <span style={{ fontSize: 12, color: T.muted }}>No extracted skill tags yet.</span>
                  )}
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.4fr 1fr', gap: 10, marginTop: 14 }}>
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
                }}>Skip</button>
                <button onClick={() => openPosting(topJob)} disabled={busy} style={{
                  height: 46,
                  borderRadius: 12,
                  border: '1px solid rgba(139,123,184,0.28)',
                  background: T.accent,
                  color: '#fff',
                  fontSize: 13,
                  fontWeight: 900,
                  fontFamily: 'Inter, system-ui, sans-serif',
                  cursor: busy ? 'wait' : 'pointer',
                }}>{hasLink ? 'Open link + download docs' : 'Download docs + details'}</button>
                <button onClick={() => decide('applied')} disabled={busy} style={{
                  height: 46,
                  borderRadius: 12,
                  border: '1px solid #22C55E40',
                  background: '#22C55E',
                  color: '#fff',
                  fontSize: 13,
                  fontWeight: 900,
                  fontFamily: 'Inter, system-ui, sans-serif',
                  cursor: busy ? 'wait' : 'pointer',
                }}>Mark applied</button>
              </div>
            </div>

            <aside style={{
              border: `1px solid ${T.border}`,
              borderRadius: 14,
              background: T.surface,
              padding: 16,
            }}>
              <div style={{ fontSize: 12, color: T.muted, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10 }}>
                Apply queue
              </div>
              <div style={{ fontSize: 34, fontWeight: 900, color: T.text, lineHeight: 1 }}>{jobs.length}</div>
              <div style={{ fontSize: 12, color: T.muted, marginTop: 5, marginBottom: 16 }}>approved jobs left</div>
              <div style={{ display: 'grid', gap: 8, fontSize: 12, color: T.text }}>
                <div><strong>Enter</strong> opens the posting and downloads docs.</div>
                <div><strong>Arrow right</strong> marks the job applied.</div>
                <div><strong>Arrow left</strong> skips it.</div>
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
