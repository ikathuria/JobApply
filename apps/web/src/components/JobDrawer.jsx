import { useState, useEffect } from 'react'
import { DARK, LIGHT, STATUS_META, ATS_TARGET, alpha, atsColor } from '../theme.js'
import { Btn, StatusBadge, AtsScore, Tag, Textarea, Spinner } from './ui/index.jsx'
import { api } from '../api.js'

const PIPELINE_STATUSES = ['new', 'queued', 'approved', 'applied', 'oa', 'interview', 'offer']

const STATUS_HELP = {
  new: 'Found, not tailored yet',
  queued: 'Tailored and ready to review',
  approved: 'Approved: ready to apply',
  applied: 'Submitted',
  oa: 'Online assessment received',
  interview: 'Interview scheduled',
  offer: 'Offer received',
  rejected: 'Closed out',
  skipped: 'Not pursuing',
}

function fieldBase(T, dark) {
  return {
    width: '100%',
    padding: '8px 10px',
    borderRadius: 2,
    border: `1px solid ${T.border}`,
    background: T.card,
    color: T.text,
    fontSize: 12,
    fontFamily: 'var(--font-text)',
    outline: 'none',
    boxSizing: 'border-box',
  }
}

function Label({ children, T }) {
  return (
    <div style={{
      fontSize: 10,
      fontWeight: 800,
      color: T.muted,
      textTransform: 'uppercase',
      letterSpacing: '0.08em',
      marginBottom: 5,
    }}>
      {children}
    </div>
  )
}

function Field({ label, children, T, style = {} }) {
  return (
    <div style={{ marginBottom: 12, ...style }}>
      <Label T={T}>{label}</Label>
      {children}
    </div>
  )
}

function TextField({ label, value, onChange, T, dark, type = 'text', placeholder = '', style = {} }) {
  return (
    <Field label={label} T={T} style={style}>
      <input
        type={type}
        value={value}
        placeholder={placeholder}
        onChange={e => onChange(e.target.value)}
        style={fieldBase(T, dark)}
      />
    </Field>
  )
}

function FormSection({ title, sub, children, T, dark }) {
  return (
    <section style={{ borderTop: `1px solid ${T.border}`, padding: '12px 0 16px' }}>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 600, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: sub ? 3 : 10 }}>
        {title}
      </div>
      {sub && <div style={{ fontSize: 12, color: T.muted, lineHeight: 1.5, marginBottom: 12 }}>{sub}</div>}
      {children}
    </section>
  )
}

// Same visual shell as FormSection, but the body only renders when `open` —
// keeps the drawer from being one long always-expanded form.
function CollapsibleSection({ title, sub, T, open, onToggle, badge, children }) {
  return (
    <section style={{ borderTop: `1px solid ${T.border}` }}>
      <button onClick={onToggle} aria-expanded={open} style={{
        width: '100%', display: 'flex', alignItems: 'center', gap: 8, minHeight: 44,
        padding: '10px 0', background: 'none', border: 'none', cursor: 'pointer',
        textAlign: 'left', fontFamily: 'var(--font-mono)',
      }}>
        <span style={{ fontSize: 11, fontWeight: 600, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.08em', flex: 1 }}>{title}</span>
        {badge}
        <span aria-hidden="true" style={{ fontSize: 14, color: T.muted, width: 14, textAlign: 'center', flexShrink: 0 }}>{open ? '−' : '+'}</span>
      </button>
      {open && (
        <div style={{ padding: '0 0 16px' }}>
          {sub && <div style={{ fontSize: 12, color: T.muted, lineHeight: 1.5, marginBottom: 12 }}>{sub}</div>}
          {children}
        </div>
      )}
    </section>
  )
}

// Which secondary sections start open, based on the job's current stage —
// avoids re-showing everything every time (Notes and the primary action stay
// outside the accordion since they're used on almost every visit).
function defaultOpenSections(job) {
  const open = new Set()
  if (['applied', 'oa', 'interview', 'offer', 'rejected'].includes(job.status)) open.add('tracking')
  if ((job.description || '').trim() && ['queued', 'approved'].includes(job.status)) open.add('ats')
  return open
}

function ConfirmModal({ job, onConfirm, onCancel, dark }) {
  const T = dark ? DARK : LIGHT
  const [checked, setChecked] = useState(false)
  const score = job.score ?? 0

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'var(--scrim)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', backdropFilter: 'blur(6px)' }}>
      <div style={{ background: T.surface, borderRadius: 4, width: 480, maxWidth: '95vw', border: `1px solid ${T.border}`, boxShadow: 'var(--shadow-float)', overflow: 'hidden' }}>
        <div style={{ padding: '20px 24px', borderBottom: `1px solid ${T.border}`, display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ width: 36, height: 36, borderRadius: 2, background: 'color-mix(in srgb, var(--ok) 13%, transparent)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--ok)', fontWeight: 900 }}>✓</div>
          <div>
            <div style={{ fontSize: 16, fontWeight: 800, color: T.text }}>Mark as manually applied</div>
            <div style={{ fontSize: 12, color: T.muted }}>Use this after you submit the application.</div>
          </div>
          <button onClick={onCancel} style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', color: T.muted, fontSize: 18 }}>x</button>
        </div>

        <div style={{ padding: '20px 24px' }}>
          <div style={{ background: T.card, border: `1px solid ${T.border}`, borderRadius: 2, padding: '14px 16px', marginBottom: 20 }}>
            <div style={{ fontSize: 15, fontWeight: 700, color: T.text, marginBottom: 4 }}>{job.title}</div>
            <div style={{ fontSize: 12, color: T.muted, display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              <span>{job.company}</span>
              {job.location && <span>{job.location}</span>}
              <span style={{ color: 'var(--ok)', fontWeight: 700 }}>{Math.round(score * 100)}% match</span>
            </div>
          </div>

          <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', fontSize: 13, color: T.text, marginBottom: 24 }}>
            <input type="checkbox" onChange={e => setChecked(e.target.checked)}
              style={{ width: 16, height: 16, accentColor: 'var(--ok)' }} />
            I submitted this application to <strong>{job.company}</strong>
          </label>

          <div style={{ display: 'flex', gap: 10 }}>
            <Btn variant="secondary" onClick={onCancel} style={{ flex: 1 }}>Cancel</Btn>
            <Btn variant="primary" disabled={!checked} onClick={onConfirm}
              style={{ flex: 2, background: checked ? 'var(--ok)' : undefined }}>
              Confirm applied
            </Btn>
          </div>
        </div>
      </div>
    </div>
  )
}

function StatusRail({ job, T, dark, disabled, onChange }) {
  const currentIndex = PIPELINE_STATUSES.indexOf(job.status)

  return (
    <div style={{ marginTop: 12 }}>
      <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
        {PIPELINE_STATUSES.map((status, index) => {
          const meta = STATUS_META[status]
          const active = status === job.status
          const passed = currentIndex >= 0 && index < currentIndex
          return (
            <button
              key={status}
              type="button"
              disabled={disabled}
              title={STATUS_HELP[status]}
              onClick={() => onChange(status)}
              style={{
                flex: 1,
                minWidth: 0,
                height: 30,
                border: `1px solid ${active ? meta.color : T.border}`,
                borderRadius: 2,
                background: active ? meta.bg : passed ? `${alpha(meta.color, 9)}` : T.card,
                color: active || passed ? meta.color : T.muted,
                cursor: disabled ? 'not-allowed' : 'pointer',
                fontSize: 10,
                fontWeight: active ? 800 : 700,
                fontFamily: 'var(--font-text)',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                padding: '0 5px',
              }}
            >
              {meta.label}
            </button>
          )
        })}
      </div>
      {['rejected', 'skipped'].includes(job.status) && (
        <div style={{ marginTop: 6 }}>
          <StatusBadge status={job.status} />
        </div>
      )}
    </div>
  )
}

export default function JobDrawer({ job: initialJob, onClose, dark, onRefresh, onReachOut, onPrep }) {
  const T = dark ? DARK : LIGHT
  const [job, setJob] = useState(initialJob)
  const [activeTab, setActiveTab] = useState('overview')
  const [overviewEditing, setOverviewEditing] = useState(false)
  const [notes, setNotes] = useState('')
  const [coverLetter, setCoverLetter] = useState('')
  const [coverLetterMode, setCoverLetterMode] = useState('pdf')
  const [jdExpanded, setJdExpanded] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [tailoring, setTailoring] = useState(false)
  const [tailorMsg, setTailorMsg] = useState('')
  const [updating, setUpdating] = useState(false)
  const [trackingForm, setTrackingForm] = useState(null)
  const [trackingMsg, setTrackingMsg] = useState('')
  const [editForm, setEditForm] = useState(null)
  const [editSaving, setEditSaving] = useState(false)
  const [editMsg, setEditMsg] = useState('')
  const [ats, setAts] = useState(null)
  const [atsLoading, setAtsLoading] = useState(false)
  const [llmAts, setLlmAts] = useState(null)          // on-demand Sonnet ATS report
  const [llmAtsRunning, setLlmAtsRunning] = useState(false)
  const [llmAtsErr, setLlmAtsErr] = useState('')
  const [resumeRev, setResumeRev] = useState(0)        // bumps to reload the PDF iframe
  const [clExists, setClExists] = useState(null)
  const [clGenerating, setClGenerating] = useState(false)
  const [openSections, setOpenSections] = useState(new Set())
  const [moreOpen, setMoreOpen] = useState(false)
  const [narrow, setNarrow] = useState(false)

  // Below ~900px the drawer overlays the screen instead of squeezing the job
  // list down to nothing.
  useEffect(() => {
    const mql = window.matchMedia('(max-width: 900px)')
    const apply = () => setNarrow(mql.matches)
    apply()
    mql.addEventListener('change', apply)
    return () => mql.removeEventListener('change', apply)
  }, [])
  const toggleSection = id => setOpenSections(prev => {
    const next = new Set(prev)
    next.has(id) ? next.delete(id) : next.add(id)
    return next
  })

  // Lazily compute the ATS keyword match when viewing a job with a description.
  useEffect(() => {
    setAts(null)
    if (activeTab !== 'overview' || !job?.id || !(job.description || '').trim()) return
    let cancelled = false
    setAtsLoading(true)
    api.atsMatch(job.id)
      .then(r => { if (!cancelled) setAts(r) })
      .catch(() => { if (!cancelled) setAts(null) })
      .finally(() => { if (!cancelled) setAtsLoading(false) })
    return () => { cancelled = true }
  }, [activeTab, job?.id, job?.description])

  useEffect(() => {
    if (!initialJob) return
    if (initialJob._needsFetch) {
      api.job(initialJob.id).then(j => {
        setJob(j)
        setNotes(j.notes || '')
      }).catch(() => {})
    } else {
      setJob(initialJob)
      setNotes(initialJob.notes || '')
    }
    const openTab = initialJob._openTab || 'overview'
    setActiveTab(openTab === 'edit' ? 'overview' : openTab)
    setOverviewEditing(openTab === 'edit')
    setCoverLetterMode('pdf')
    setTailorMsg('')
    setTrackingMsg('')
    setMoreOpen(false)
  }, [initialJob?.id])

  // Reset which secondary sections are expanded whenever a *different* job is
  // opened (not on every status change — that would collapse things mid-edit).
  useEffect(() => {
    if (!job) return
    setOpenSections(prev => {
      const next = defaultOpenSections(job)
      if (initialJob?._openTab === 'edit') next.add('details')
      return next
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [job?.id])

  useEffect(() => {
    if (!job) return
    setTrackingForm({
      status: job.status || 'new',
      date_applied: job.date_applied ? job.date_applied.slice(0, 10) : '',
      interview_date: job.interview_date ? job.interview_date.slice(0, 10) : '',
      follow_up_date: job.follow_up_date ? job.follow_up_date.slice(0, 10) : '',
      recruiter: job.recruiter || '',
      rejection_stage: job.rejection_stage || '',
    })
  }, [job?.id, job?.status])

  useEffect(() => {
    if (activeTab === 'cover letter' && job?.resume_path) {
      api.coverLetter(job.id)
        .then(t => { setCoverLetter(t); setClExists(true) })
        .catch(() => { setCoverLetter(''); setClExists(false) })
    }
  }, [activeTab, job?.id, job?.resume_path])

  // Show the last stored LLM ATS report (never runs a new check by itself).
  useEffect(() => {
    setLlmAts(null); setLlmAtsErr('')
    if (!job?.id || !job.resume_path) return
    api.atsReport(job.id).then(r => setLlmAts(r && r.score != null ? r : null)).catch(() => {})
  }, [job?.id, job?.resume_path])

  async function runLlmAts() {
    setLlmAtsRunning(true); setLlmAtsErr('')
    try {
      const r = await api.atsScore(job.id)
      setLlmAts(r)
      if (r.improved) setResumeRev(v => v + 1)
      setJob(j => ({ ...j, ats_score: r.score }))
    } catch (e) {
      setLlmAtsErr(e.message)
    } finally {
      setLlmAtsRunning(false)
    }
  }

  async function generateCoverLetter() {
    setClGenerating(true)
    try {
      const r = await api.genCL(job.id)
      setCoverLetter(r.text); setClExists(true)
    } catch (e) {
      setTailorMsg(e.message)
    } finally {
      setClGenerating(false)
    }
  }

  useEffect(() => {
    if (job) {
      setEditForm({
        title: job.title || '',
        company: job.company || '',
        location: job.location || '',
        url: job.url || '',
        status: job.status || 'new',
        score: job.score ?? '',
        date_applied: job.date_applied ? job.date_applied.slice(0, 10) : '',
        recruiter: job.recruiter || '',
        salary_range: job.salary_range || '',
        interview_date: job.interview_date ? job.interview_date.slice(0, 10) : '',
        follow_up_date: job.follow_up_date ? job.follow_up_date.slice(0, 10) : '',
        rejection_stage: job.rejection_stage || '',
        starred: !!job.starred,
      })
      setEditMsg('')
    }
  }, [job?.id])

  if (!job) return (
    <div style={{ width: 480, flexShrink: 0, height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: T.surface, borderLeft: `1px solid ${T.border}` }}>
      <Spinner size={28} />
    </div>
  )

  const score = job.score ?? 0
  const primaryAction = {
    new: { label: 'Tailor with AI', color: T.accent, action: handleTailor },
    queued: { label: 'Approve to apply', color: T.accent, action: () => patchStatus('approved') },
    approved: { label: 'Mark manually applied', color: T.accent, action: () => setShowConfirm(true) },
    applied: { label: 'Move to OA', color: T.accent, action: () => patchStatus('oa') },
    oa: { label: 'Move to interview', color: T.accent, action: () => patchStatus('interview') },
    interview: { label: 'Move to offer', color: T.accent, action: () => patchStatus('offer') },
    offer: { label: 'Offer received', color: T.accent, action: null },
    rejected: null,
    skipped: null,
  }[job.status]

  async function patchStatus(newStatus, extra = {}) {
    setUpdating(true)
    try {
      const payload = { status: newStatus, ...extra }
      if (newStatus === 'applied' && !payload.date_applied && !job.date_applied) {
        payload.date_applied = new Date().toISOString().slice(0, 10)
      }
      const updated = await api.patch(job.id, payload)
      setJob(updated)
      setTrackingMsg('Saved')
      setTimeout(() => setTrackingMsg(''), 1600)
      onRefresh?.()
    } catch (e) {
      alert('Error: ' + e.message)
    } finally {
      setUpdating(false)
    }
  }

  async function handleTailor() {
    setTailoring(true)
    setTailorMsg('')
    try {
      const res = await api.tailor(job.id)
      setTailorMsg(res.message)
      const updated = await api.job(job.id)
      setJob(updated)
      onRefresh?.()
    } catch (e) {
      setTailorMsg(e.message)
    } finally {
      setTailoring(false)
    }
  }

  async function saveNotes() {
    const updated = await api.patch(job.id, { notes })
    setJob(updated)
    onRefresh?.()
  }

  async function saveTracking() {
    if (!trackingForm) return
    setUpdating(true)
    setTrackingMsg('')
    try {
      const payload = {
        status: trackingForm.status,
        date_applied: trackingForm.date_applied || null,
        interview_date: trackingForm.interview_date || null,
        follow_up_date: trackingForm.follow_up_date || null,
        recruiter: trackingForm.recruiter.trim() || null,
        rejection_stage: trackingForm.rejection_stage.trim() || null,
      }
      const updated = await api.patch(job.id, payload)
      setJob(updated)
      setTrackingMsg('Saved')
      setTimeout(() => setTrackingMsg(''), 1600)
      onRefresh?.()
    } catch (e) {
      setTrackingMsg(e.message || 'Save failed')
    } finally {
      setUpdating(false)
    }
  }

  async function saveCoverLetter() {
    await api.saveCL(job.id, coverLetter)
  }

  async function saveEdit() {
    setEditSaving(true)
    setEditMsg('')
    try {
      const payload = {
        title: editForm.title.trim() || undefined,
        company: editForm.company.trim() || undefined,
        location: editForm.location.trim() || undefined,
        url: editForm.url.trim() || undefined,
        status: editForm.status || undefined,
        score: editForm.score !== '' ? parseFloat(editForm.score) : undefined,
        date_applied: editForm.date_applied || null,
        recruiter: editForm.recruiter.trim() || null,
        salary_range: editForm.salary_range.trim() || null,
        interview_date: editForm.interview_date || null,
        follow_up_date: editForm.follow_up_date || null,
        rejection_stage: editForm.rejection_stage.trim() || null,
        starred: editForm.starred ? 1 : 0,
      }
      Object.keys(payload).forEach(k => payload[k] === undefined && delete payload[k])
      const updated = await api.patch(job.id, payload)
      setJob(updated)
      setNotes(updated.notes || '')
      onRefresh?.()
      setEditMsg('Saved')
      setTimeout(() => setEditMsg(''), 2000)
    } catch (e) {
      setEditMsg(e.message || 'Save failed')
    } finally {
      setEditSaving(false)
    }
  }

  const setTracking = (k, v) => setTrackingForm(f => ({ ...f, [k]: v }))
  const setEdit = (k, v) => setEditForm(f => ({ ...f, [k]: v }))
  const input = fieldBase(T, dark)
  const drawerTabs = ['overview', 'resume', 'cover letter']
  const notesRows = Math.min(18, Math.max(4, notes.split('\n').length + Math.ceil(notes.length / 120)))

  // Secondary status moves — one kebab menu instead of a permanent button grid.
  const moreActions = []
  if (job.status === 'new') {
    moreActions.push({ label: 'Skip', onClick: () => patchStatus('skipped') })
    moreActions.push({ label: 'Reject', danger: true, onClick: () => patchStatus('rejected') })
  }
  if (job.status === 'queued') moreActions.push({ label: 'Back to new', onClick: () => patchStatus('new') })
  if (job.status === 'approved') moreActions.push({ label: 'Back to ready', onClick: () => patchStatus('queued') })
  if (['applied', 'oa', 'interview'].includes(job.status)) moreActions.push({ label: 'Mark rejected', danger: true, onClick: () => patchStatus('rejected') })
  if (['rejected', 'skipped'].includes(job.status)) moreActions.push({ label: 'Reopen', onClick: () => patchStatus('new') })

  return (
    <>
      {showConfirm && (
        <ConfirmModal job={job} dark={dark}
          onConfirm={async () => {
            setShowConfirm(false)
            await patchStatus('applied', { date_applied: new Date().toISOString().slice(0, 10) })
            onClose()
          }}
          onCancel={() => setShowConfirm(false)}
        />
      )}

      {narrow && (
        <div onClick={onClose} style={{ position: 'fixed', inset: 0, background: 'var(--scrim)', zIndex: 90 }} />
      )}

      <div style={narrow ? {
        position: 'fixed', inset: 0, zIndex: 91,
        display: 'flex', flexDirection: 'column',
        background: T.surface,
      } : {
        width: 480,
        flexShrink: 0,
        height: '100vh',
        display: 'flex',
        flexDirection: 'column',
        background: T.surface,
        borderLeft: `1px solid ${T.border}`,
        position: 'sticky',
        top: 0,
      }}>
        <div style={{ padding: '16px 20px', borderBottom: `1px solid ${T.border}`, flexShrink: 0 }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div className="mono" style={{ fontSize: 11, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>#{job.id}</div>
              <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 24, fontWeight: 700, color: T.text, lineHeight: 1.15, margin: '0 0 6px' }}>
                {job.starred ? <span style={{ color: 'var(--warn)', marginRight: 5 }}>★</span> : null}
                {job.title}
              </h2>
              <div style={{ fontSize: 13, color: T.muted, display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
                <span style={{ fontWeight: 600, color: T.text }}>{job.company || 'Unknown company'}</span>
                {job.known_sponsor && (
                  <span title="Known H-1B sponsor" style={{
                    fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700, color: T.success,
                    border: '1px solid currentColor', padding: '0 5px',
                  }}>H-1B SPONSOR</span>
                )}
                {job.location && <><span>·</span><span>{job.location}</span></>}
                {job.source && <><span>·</span><Tag>{job.source}</Tag></>}
              </div>
            </div>
            <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexShrink: 0, position: 'relative' }}>
              <button
                onClick={() => patchStatus(job.status, { starred: job.starred ? 0 : 1 })}
                aria-label={job.starred ? 'Unstar' : 'Star'}
                title={job.starred ? 'Unstar' : 'Star'}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: job.starred ? 'var(--warn)' : T.muted, fontSize: 17, padding: 4, minWidth: 32, minHeight: 32 }}>
                {job.starred ? '★' : '☆'}
              </button>
              {moreActions.length > 0 && (
                <button
                  onClick={() => setMoreOpen(o => !o)}
                  aria-label="More actions" aria-expanded={moreOpen} title="More actions"
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: T.muted, fontSize: 16, padding: 4, lineHeight: 1, minWidth: 32, minHeight: 32 }}>
                  ⋮
                </button>
              )}
              {moreOpen && (
                <div onClick={() => setMoreOpen(false)} style={{ position: 'fixed', inset: 0, zIndex: 19 }} />
              )}
              {moreOpen && (
                <div style={{
                  position: 'absolute', top: '100%', right: 20, marginTop: 4, zIndex: 20,
                  background: T.card, border: `1px solid ${T.border}`, borderRadius: 2,
                  boxShadow: 'var(--shadow-float)', minWidth: 150, overflow: 'hidden',
                }}>
                  {moreActions.map(a => (
                    <button key={a.label}
                      onClick={() => { setMoreOpen(false); a.onClick() }}
                      style={{
                        display: 'block', width: '100%', textAlign: 'left', padding: '9px 14px',
                        background: 'none', border: 'none', cursor: 'pointer',
                        fontFamily: 'var(--font-text)', fontSize: 12, fontWeight: 600,
                        color: a.danger ? T.danger : T.text,
                      }}>
                      {a.label}
                    </button>
                  ))}
                </div>
              )}
              <button onClick={onClose} aria-label="Close" style={{ background: 'none', border: 'none', cursor: 'pointer', color: T.muted, fontSize: 18, padding: 4, minWidth: 32, minHeight: 32 }}>×</button>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginTop: 12, flexWrap: 'wrap' }}>
            <StatusBadge status={job.status} size="md" />
            <span className="mono tabular" style={{ fontSize: 12, color: T.muted }}>
              match <b style={{ color: T.text, fontSize: 14 }}>{Math.round(score * 100)}</b>
            </span>
            <span className="mono" style={{ fontSize: 12, color: T.muted, display: 'inline-flex', alignItems: 'center', gap: 8 }}>
              ATS <AtsScore score={job.ats_score} width={110} />
            </span>
          </div>

          <StatusRail job={job} T={T} dark={dark} disabled={updating || tailoring} onChange={patchStatus} />

          <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
            {primaryAction && (
              <button
                onClick={tailoring || updating ? undefined : primaryAction.action}
                disabled={tailoring || updating || !primaryAction.action}
                style={{
                  flex: 1,
                  padding: '10px 0',
                  borderRadius: 2,
                  border: 'none',
                  cursor: tailoring || updating ? 'not-allowed' : 'pointer',
                  minHeight: 40,
                  background: primaryAction.color,
                  color: 'var(--on-accent)',
                  fontSize: 13,
                  fontWeight: 600,
                  fontFamily: 'var(--font-text)',
                  opacity: tailoring || updating ? 0.7 : 1,
                }}>
                {tailoring ? 'Tailoring...' : primaryAction.label}
              </button>
            )}
            {job.url && !job.url.startsWith('manual://') && (
              <Btn variant="secondary" size="sm" onClick={() => window.open(job.url, '_blank')}>Posting</Btn>
            )}
            {onReachOut && (
              <Btn variant="secondary" size="sm" onClick={() => onReachOut(job)}>Reach out</Btn>
            )}
            {onPrep && ['oa', 'interview'].includes(job.status) && (
              <Btn variant="secondary" size="sm" onClick={() => onPrep(job)}>Prep</Btn>
            )}
          </div>
          {tailorMsg && <div style={{ fontSize: 11, color: T.muted, marginTop: 6 }}>{tailorMsg}</div>}
        </div>

        <div style={{ display: 'flex', borderBottom: `1px solid ${T.border}`, flexShrink: 0 }}>
          {drawerTabs.map(t => (
            <button key={t} onClick={() => {
              setOverviewEditing(false)
              setActiveTab(t)
            }}
              style={{
                flex: 1,
                minHeight: 40,
                padding: '9px 4px',
                border: 'none',
                cursor: 'pointer',
                background: 'transparent',
                fontFamily: 'var(--font-text)',
                fontSize: 13,
                fontWeight: activeTab === t ? 600 : 500,
                color: activeTab === t ? T.text : T.muted,
                borderBottom: activeTab === t ? `3px solid ${T.accent}` : '3px solid transparent',
                textTransform: 'capitalize',
              }}>{t}</button>
          ))}
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: '16px 20px' }}>
          {activeTab === 'overview' && trackingForm && (
            <div>
              {job.resume_path && (
                <AtsScorePanel report={llmAts} running={llmAtsRunning} error={llmAtsErr}
                  onRun={runLlmAts} T={T} />
              )}
              {job.status === 'approved' && (
                <div style={{ background: 'var(--accent-soft)', border: '1px solid color-mix(in srgb, var(--accent) 30%, transparent)', borderRadius: 2, padding: '12px 14px', marginBottom: 14 }}>
                  <div style={{ fontSize: 12, fontWeight: 800, color: 'var(--accent)', marginBottom: 3 }}>Approved</div>
                  <div style={{ fontSize: 11, color: T.muted, lineHeight: 1.5 }}>
                    Open the posting and apply, then use “Mark manually applied”.
                  </div>
                </div>
              )}

              {editForm && (
                <CollapsibleSection
                  title={overviewEditing ? 'Edit this job' : 'Role details'}
                  sub={overviewEditing ? 'You are editing directly in Overview. Save here when the scrape or import needs cleanup.' : 'Core job information and metadata.'}
                  T={T}
                  open={openSections.has('details') || overviewEditing}
                  onToggle={() => toggleSection('details')}
                >
                  {overviewEditing ? (
                    <>
                      <TextField label="Title" value={editForm.title} onChange={v => setEdit('title', v)} T={T} dark={dark} />
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 10px' }}>
                        <TextField label="Company" value={editForm.company} onChange={v => setEdit('company', v)} T={T} dark={dark} />
                        <TextField label="Location" value={editForm.location} onChange={v => setEdit('location', v)} T={T} dark={dark} />
                        <TextField label="Score" type="number" value={editForm.score} onChange={v => setEdit('score', v)} T={T} dark={dark} />
                        <TextField label="Salary range" value={editForm.salary_range} onChange={v => setEdit('salary_range', v)} placeholder="$40-50/hr" T={T} dark={dark} />
                      </div>
                      <TextField label="Job URL" value={editForm.url} onChange={v => setEdit('url', v)} T={T} dark={dark} />
                      <Field label="Starred" T={T}>
                        <label style={{ ...input, display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                          <input type="checkbox" checked={editForm.starred} onChange={e => setEdit('starred', e.target.checked)} style={{ accentColor: 'var(--warn)' }} />
                          Keep near the top
                        </label>
                      </Field>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
                        <Btn variant="primary" size="sm" onClick={saveEdit} disabled={editSaving}>{editSaving ? 'Saving...' : 'Save changes'}</Btn>
                        <Btn variant="secondary" size="sm" onClick={() => setOverviewEditing(false)}>Done</Btn>
                        {editMsg && <span style={{ fontSize: 12, color: editMsg === 'Saved' ? T.success : T.danger }}>{editMsg}</span>}
                      </div>
                    </>
                  ) : (
                    <>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 10px' }}>
                        <Field label="Title" T={T}><div style={{ ...input, minHeight: 34 }}>{job.title || 'Untitled job'}</div></Field>
                        <Field label="Company" T={T}><div style={{ ...input, minHeight: 34 }}>{job.company || 'Unknown company'}</div></Field>
                        <Field label="Location" T={T}><div style={{ ...input, minHeight: 34 }}>{job.location || 'Not set'}</div></Field>
                        <Field label="Score" T={T}><div style={{ ...input, minHeight: 34 }}>{job.score != null ? job.score : 'Not set'}</div></Field>
                        <Field label="Salary range" T={T}><div style={{ ...input, minHeight: 34 }}>{job.salary_range || 'Not set'}</div></Field>
                        <Field label="Starred" T={T}><div style={{ ...input, minHeight: 34 }}>{job.starred ? 'Yes' : 'No'}</div></Field>
                      </div>
                      <Field label="Job URL" T={T}>
                        <div style={{ ...input, minHeight: 34, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{job.url || 'Not set'}</div>
                      </Field>
                      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
                        <Btn variant="secondary" size="sm" onClick={() => { setOverviewEditing(true); setOpenSections(prev => new Set(prev).add('details')) }}>Edit details</Btn>
                      </div>
                    </>
                  )}
                </CollapsibleSection>
              )}

              <FormSection title="Notes" T={T} dark={dark}>
                <Textarea value={notes} onChange={setNotes} placeholder="Referral notes, next step, application quirks..." rows={notesRows} style={{ lineHeight: 1.6 }} />
                {notes !== (job.notes || '') && (
                  <button onClick={saveNotes} style={{ marginTop: 7, minHeight: 32, background: 'none', border: 'none', cursor: 'pointer', color: T.accent, fontSize: 12, fontWeight: 600, padding: 0 }}>
                    Save notes
                  </button>
                )}
              </FormSection>

              <CollapsibleSection title="Tracking" sub="The fields you are most likely to touch after every job-search session."
                T={T} open={openSections.has('tracking')} onToggle={() => toggleSection('tracking')}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 10px' }}>
                  <TextField label="Date applied" type="date" value={trackingForm.date_applied} onChange={v => setTracking('date_applied', v)} T={T} dark={dark} />
                  <TextField label="Interview date" type="date" value={trackingForm.interview_date} onChange={v => setTracking('interview_date', v)} T={T} dark={dark} />
                  <TextField label="Follow-up date" type="date" value={trackingForm.follow_up_date} onChange={v => setTracking('follow_up_date', v)} T={T} dark={dark} />
                  <TextField label="Recruiter" value={trackingForm.recruiter} onChange={v => setTracking('recruiter', v)} placeholder="Name or email" T={T} dark={dark} style={{ gridColumn: '1/-1' }} />
                  <TextField label="Rejection stage" value={trackingForm.rejection_stage} onChange={v => setTracking('rejection_stage', v)} placeholder="Resume screen, OA, phone screen..." T={T} dark={dark} style={{ gridColumn: '1/-1' }} />
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
                  <Btn variant="primary" size="sm" onClick={saveTracking} disabled={updating}>Save tracking</Btn>
                  {trackingMsg && <span style={{ fontSize: 12, color: trackingMsg === 'Saved' ? T.success : T.danger }}>{trackingMsg}</span>}
                </div>
              </CollapsibleSection>

              <CollapsibleSection title="Job description" T={T} open={openSections.has('jd')} onToggle={() => toggleSection('jd')}>
                <div style={{ fontSize: 12, color: T.text, lineHeight: 1.7, whiteSpace: 'pre-wrap', maxHeight: jdExpanded ? 'none' : 140, overflow: 'hidden' }}>
                  {job.description || 'No description available.'}
                </div>
                <button onClick={() => setJdExpanded(!jdExpanded)}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: T.accent, fontSize: 11, fontWeight: 800, padding: '5px 0', marginTop: 4 }}>
                  {jdExpanded ? 'Show less' : 'Show more'}
                </button>
              </CollapsibleSection>

              {(job.description || '').trim() && (
                <CollapsibleSection title="ATS keyword match"
                  sub="JD skill keywords found in your materials — add the missing ones before applying"
                  T={T} open={openSections.has('ats')} onToggle={() => toggleSection('ats')}
                  badge={ats && ats.score != null ? (
                    <span style={{
                      fontSize: 10, fontWeight: 800, fontFamily: 'var(--font-mono)',
                      color: ats.score >= 0.7 ? 'var(--ok)' : ats.score >= 0.4 ? 'var(--warn)' : 'var(--bad)',
                    }}>{Math.round(ats.score * 100)}%</span>
                  ) : null}
                >
                  {atsLoading && <div style={{ fontSize: 12, color: T.muted }}>Analyzing…</div>}
                  {ats && ats.score != null && (() => {
                    const pct = Math.round(ats.score * 100)
                    const col = pct >= 70 ? 'var(--ok)' : pct >= 40 ? 'var(--warn)' : 'var(--bad)'
                    return (
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
                          <div style={{ flex: 1, height: 8, background: T.border, borderRadius: 2, overflow: 'hidden' }}>
                            <div style={{ width: `${pct}%`, height: '100%', background: col, borderRadius: 2 }} />
                          </div>
                          <span style={{ fontSize: 13, fontWeight: 800, color: col, fontFamily: 'var(--font-mono)' }}>{pct}%</span>
                        </div>
                        <div style={{ fontSize: 11, color: T.muted, marginBottom: 6 }}>
                          {ats.matched.length}/{ats.jd_keywords.length} keywords matched
                        </div>
                        {ats.missing.length > 0 && (
                          <div>
                            <div style={{ fontSize: 11, fontWeight: 700, color: T.text, marginBottom: 5 }}>Missing:</div>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
                              {ats.missing.map(k => (
                                <span key={k} style={{ fontSize: 10, fontWeight: 700, color: 'var(--bad)', background: dark ? 'var(--bad-soft)' : 'var(--bad-soft)', border: `1px solid ${dark ? 'color-mix(in srgb, var(--bad) 35%, transparent)' : 'color-mix(in srgb, var(--bad) 35%, transparent)'}`, borderRadius: 2, padding: '2px 7px' }}>{k}</span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )
                  })()}
                  {ats && ats.score == null && (
                    <div style={{ fontSize: 11, color: T.muted }}>{ats.note || 'No keywords detected in the description.'}</div>
                  )}
                </CollapsibleSection>
              )}
            </div>
          )}

          {activeTab === 'resume' && (
            <div>
              {job.status === 'new' || !job.resume_path ? (
                <div style={{ textAlign: 'center', padding: '40px 0', color: T.muted }}>
                  <div style={{ fontWeight: 700, marginBottom: 6, color: T.text }}>No resume yet</div>
                  <div style={{ fontSize: 12, marginBottom: 20 }}>Tailor this job to generate a customized resume.</div>
                  <Btn variant="primary" onClick={handleTailor} disabled={tailoring}>
                    {tailoring ? 'Tailoring...' : 'Tailor now'}
                  </Btn>
                </div>
              ) : (
                <div style={{ textAlign: 'center' }}>
                  <iframe
                    key={resumeRev}
                    src={api.resumeUrl(job.id) + (resumeRev ? `?v=${resumeRev}` : '')}
                    style={{ width: '100%', height: 500, border: 'none', borderRadius: 2 }}
                    title="Resume PDF"
                  />
                  <a href={api.resumeUrl(job.id)} target="_blank" rel="noopener noreferrer"
                    style={{ display: 'inline-block', marginTop: 10, fontSize: 12, color: T.accent }}>
                    Download PDF
                  </a>
                </div>
              )}
            </div>
          )}

          {activeTab === 'cover letter' && (
            <div>
              {!job.resume_path ? (
                <div style={{ textAlign: 'center', padding: '40px 0', color: T.muted }}>
                  <div style={{ fontWeight: 700, marginBottom: 6, color: T.text }}>No cover letter yet</div>
                  <div style={{ fontSize: 12, marginBottom: 20 }}>Tailor the resume first; cover letters are generated on demand.</div>
                  <Btn variant="primary" onClick={handleTailor} disabled={tailoring}>Tailor now</Btn>
                </div>
              ) : clExists === false ? (
                <div style={{ textAlign: 'center', padding: '40px 0', color: T.muted }}>
                  <div style={{ fontWeight: 700, marginBottom: 6, color: T.text }}>No cover letter yet</div>
                  <div style={{ fontSize: 12, marginBottom: 20 }}>Only generate one if the application asks for it.</div>
                  <Btn variant="primary" onClick={generateCoverLetter} disabled={clGenerating}>
                    {clGenerating ? 'Writing…' : 'Generate cover letter'}
                  </Btn>
                </div>
              ) : (
                <>
                  <div style={{ display: 'flex', gap: 4, background: T.surface, borderRadius: 2, padding: 4, marginBottom: 12 }}>
                    {['pdf', 'text'].map(mode => (
                      <button
                        key={mode}
                        onClick={() => setCoverLetterMode(mode)}
                        style={{
                          flex: 1,
                          padding: '7px 10px',
                          border: 'none',
                          borderRadius: 2,
                          cursor: 'pointer',
                          background: coverLetterMode === mode ? T.accent : 'transparent',
                          color: coverLetterMode === mode ? 'var(--on-accent)' : T.muted,
                          fontSize: 12,
                          fontWeight: 800,
                          fontFamily: 'var(--font-text)',
                          textTransform: 'capitalize',
                        }}
                      >
                        {mode}
                      </button>
                    ))}
                  </div>
                  {coverLetterMode === 'pdf' ? (
                    <div style={{ textAlign: 'center' }}>
                      <iframe
                        src={api.coverLetterPdfUrl(job.id)}
                        style={{ width: '100%', height: 500, border: 'none', borderRadius: 2 }}
                        title="Cover letter PDF"
                      />
                    </div>
                  ) : (
                    <Textarea value={coverLetter} onChange={setCoverLetter} rows={18} style={{ fontSize: 12, lineHeight: 1.7 }} />
                  )}
                  <div style={{ marginTop: 10, display: 'flex', gap: 8 }}>
                    {coverLetterMode === 'text' && <Btn variant="secondary" size="sm" onClick={saveCoverLetter}>Save edits</Btn>}
                    <a href={api.coverLetterPdfUrl(job.id)} target="_blank" rel="noopener noreferrer">
                      <Btn variant="ghost" size="sm">Download PDF</Btn>
                    </a>
                  </div>
                </>
              )}
            </div>
          )}

        </div>
      </div>
    </>
  )
}


// On-demand LLM ATS check (Sonnet). Below 90 the backend re-tailors with the
// feedback and keeps the best version; unsupported keywords are real gaps it
// will not add. Layout: BRAND.md signature move 3 (score + target gauge).
const ATS_PARTS = [
  ['keywords', 'Keywords', 40], ['required', 'Required quals', 25], ['alignment', 'Role alignment', 15],
  ['preferred', 'Preferred quals', 10], ['impact', 'Quantified impact', 10],
]

function AtsScorePanel({ report, running, error, onRun, T }) {
  const score = report?.score
  const target = report?.target ?? ATS_TARGET
  const col = score == null ? T.muted : atsColor(score)
  const head = { fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 600, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.08em', margin: '14px 0 6px' }
  const chip = (k, kind) => (
    <span key={k} style={{
      fontFamily: 'var(--font-mono)', fontSize: 11, borderRadius: 2, padding: '2px 7px',
      color: kind === 'gap' ? 'var(--bad)' : T.text2,
      background: kind === 'ok' ? 'var(--band)' : T.surface,
      border: kind === 'gap' ? '1px dashed var(--bad)' : `1px solid ${T.border}`,
    }}>{k}</span>
  )
  const missing = (report?.missing_keywords || []).filter(k => !(report?.unsupported || []).includes(k))
  return (
    <section aria-label="ATS score" style={{ textAlign: 'left', paddingBottom: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{ ...head, margin: 0, flex: 1 }}>ATS score · Sonnet</span>
        <Btn variant={score == null ? 'primary' : 'secondary'} size="sm" onClick={onRun} disabled={running}>
          {running ? 'Scoring… (up to ~1 min)' : score == null ? 'Run ATS check' : 'Re-run'}
        </Btn>
      </div>
      {error && <div style={{ fontSize: 12, color: 'var(--bad)', marginTop: 6 }}>{error}</div>}
      {score == null && !running && (
        <p style={{ fontSize: 13, color: T.muted, margin: '8px 0 0' }}>
          Not scored yet. Below {target}, it re-tailors with the feedback (max 2 rounds) and keeps the best resume.
        </p>
      )}
      {score != null && (<>
        <div style={{ display: 'flex', alignItems: 'center', gap: 18, marginTop: 10 }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 2 }}>
            <span className="mono tabular" style={{ fontSize: 'var(--fs-num)', fontWeight: 700, lineHeight: 1, color: col }}>{score}</span>
            <span className="mono" style={{ fontSize: 14, color: T.muted }}>/100</span>
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ position: 'relative', height: 8, background: T.border }}>
              <div className="gb-fill" style={{ position: 'absolute', inset: 0, width: `${score}%`, background: col }} />
              <div title={`Target ${target}`} style={{ position: 'absolute', left: `${target}%`, top: -5, bottom: -5, width: 2, background: T.text }} />
            </div>
            <p style={{ fontSize: 12, color: T.muted, margin: '10px 0 0', lineHeight: 1.45 }}>
              {score >= target
                ? `Meets the ${target} target.`
                : `${target - score} points under the ${target} target${report.history?.length > 1 ? ` after ${report.history.length - 1} re-tailor round${report.history.length > 2 ? 's' : ''}` : ''}.`}
              {report.history?.length > 1 && <> <span className="mono">{report.history.join(' → ')}</span>{report.improved ? ', resume updated.' : '.'}</>}
            </p>
          </div>
        </div>
        {report.breakdown && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 14 }}>
            {ATS_PARTS.filter(([k]) => report.breakdown[k] != null).map(([k, label, max]) => (
              <div key={k} style={{ display: 'grid', gridTemplateColumns: '120px 1fr 44px', gap: 10, alignItems: 'center', fontSize: 12, color: T.text2 }}>
                <span>{label}</span>
                <div style={{ height: 6, background: T.border }}>
                  <div className="gb-fill" style={{ width: `${Math.min(100, report.breakdown[k] / max * 100)}%`, height: '100%', background: T.accent }} />
                </div>
                <span className="mono tabular" style={{ textAlign: 'right' }}>{report.breakdown[k]}/{max}</span>
              </div>
            ))}
          </div>
        )}
        {report.matched_keywords?.length > 0 && (<>
          <div style={head}>Matched <span style={{ color: T.text }}>{report.matched_keywords.length}</span></div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>{report.matched_keywords.map(k => chip(k, 'ok'))}</div>
        </>)}
        {missing.length > 0 && (<>
          <div style={head}>Missing, can add <span style={{ color: T.text }}>{missing.length}</span></div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>{missing.map(k => chip(k))}</div>
        </>)}
        {report.unsupported?.length > 0 && (<>
          <div style={head}>Real gaps, not added <span style={{ color: T.text }}>{report.unsupported.length}</span></div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>{report.unsupported.map(k => chip(k, 'gap'))}</div>
        </>)}
        {report.suggestions?.length > 0 && score < target && (<>
          <div style={head}>Fixes</div>
          <ol style={{ fontSize: 13, color: T.text2, margin: 0, paddingLeft: 18, display: 'flex', flexDirection: 'column', gap: 4, lineHeight: 1.45 }}>
            {report.suggestions.slice(0, 3).map((t, i) => <li key={i}>{t}</li>)}
          </ol>
        </>)}
      </>)}
    </section>
  )
}
