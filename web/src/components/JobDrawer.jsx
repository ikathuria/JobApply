import { useState, useEffect } from 'react'
import { DARK, LIGHT, STATUS_META } from '../theme.js'
import { Btn, StatusBadge, ScoreBar, Tag, Textarea, Divider, Spinner } from './ui/index.jsx'
import { api } from '../api.js'

const STATUS_OPTS = ['new', 'queued', 'approved', 'applied', 'oa', 'interview', 'offer', 'rejected', 'skipped']
const PIPELINE_STATUSES = ['new', 'queued', 'approved', 'applied', 'oa', 'interview', 'offer']

const STATUS_HELP = {
  new: 'Found, not tailored yet',
  queued: 'Tailored and ready to review',
  approved: 'Approved for the apply bot',
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
    borderRadius: 7,
    border: `1px solid ${T.border}`,
    background: T.card,
    color: T.text,
    fontSize: 12,
    fontFamily: 'Inter, system-ui, sans-serif',
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

function SelectField({ label, value, onChange, T, dark, options, style = {} }) {
  return (
    <Field label={label} T={T} style={style}>
      <select value={value} onChange={e => onChange(e.target.value)} style={fieldBase(T, dark)}>
        {options.map(s => (
          <option key={s} value={s}>{STATUS_META[s]?.label || s}</option>
        ))}
      </select>
    </Field>
  )
}

function FormSection({ title, sub, children, T, dark }) {
  return (
    <div style={{
      background: T.card,
      border: `1px solid ${T.border}`,
      borderRadius: 10,
      padding: '14px 14px 2px',
      marginBottom: 14,
    }}>
      <div style={{ fontSize: 13, fontWeight: 800, color: T.text, marginBottom: sub ? 3 : 12 }}>
        {title}
      </div>
      {sub && <div style={{ fontSize: 11, color: T.muted, lineHeight: 1.5, marginBottom: 12 }}>{sub}</div>}
      {children}
    </div>
  )
}

function ConfirmModal({ job, onConfirm, onCancel, dark }) {
  const T = dark ? DARK : LIGHT
  const [checked, setChecked] = useState(false)
  const score = job.score ?? 0

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', backdropFilter: 'blur(6px)' }}>
      <div style={{ background: T.surface, borderRadius: 14, width: 480, border: `1px solid ${T.border}`, boxShadow: '0 32px 80px rgba(0,0,0,0.4)', overflow: 'hidden' }}>
        <div style={{ padding: '20px 24px', borderBottom: `1px solid ${T.border}`, display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ width: 36, height: 36, borderRadius: 8, background: '#22C55E20', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#22C55E', fontWeight: 900 }}>✓</div>
          <div>
            <div style={{ fontSize: 16, fontWeight: 800, color: T.text }}>Mark as manually applied</div>
            <div style={{ fontSize: 12, color: T.muted }}>Use this after submitting outside the apply bot.</div>
          </div>
          <button onClick={onCancel} style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', color: T.muted, fontSize: 18 }}>x</button>
        </div>

        <div style={{ padding: '20px 24px' }}>
          <div style={{ background: T.card, border: `1px solid ${T.border}`, borderRadius: 10, padding: '14px 16px', marginBottom: 20 }}>
            <div style={{ fontSize: 15, fontWeight: 700, color: T.text, marginBottom: 4 }}>{job.title}</div>
            <div style={{ fontSize: 12, color: T.muted, display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              <span>{job.company}</span>
              {job.location && <span>{job.location}</span>}
              <span style={{ color: '#22C55E', fontWeight: 700 }}>{Math.round(score * 100)}% match</span>
            </div>
          </div>

          <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', fontSize: 13, color: T.text, marginBottom: 24 }}>
            <input type="checkbox" onChange={e => setChecked(e.target.checked)}
              style={{ width: 16, height: 16, accentColor: '#22C55E' }} />
            I submitted this application to <strong>{job.company}</strong>
          </label>

          <div style={{ display: 'flex', gap: 10 }}>
            <Btn variant="secondary" onClick={onCancel} style={{ flex: 1 }}>Cancel</Btn>
            <Btn variant="primary" disabled={!checked} onClick={onConfirm}
              style={{ flex: 2, background: checked ? '#22C55E' : undefined }}>
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
                borderRadius: 7,
                background: active ? meta.bg : passed ? `${meta.color}18` : T.card,
                color: active || passed ? meta.color : T.muted,
                cursor: disabled ? 'not-allowed' : 'pointer',
                fontSize: 10,
                fontWeight: active ? 800 : 700,
                fontFamily: 'Inter, system-ui, sans-serif',
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

export default function JobDrawer({ job: initialJob, onClose, dark, onRefresh }) {
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
  }, [initialJob?.id])

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
      api.coverLetter(job.id).then(setCoverLetter).catch(() => setCoverLetter(''))
    }
  }, [activeTab, job?.id, job?.resume_path])

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
    queued: { label: 'Approve for apply bot', color: '#8B7BB8', action: () => patchStatus('approved') },
    approved: { label: 'Mark manually applied', color: '#22C55E', action: () => setShowConfirm(true) },
    applied: { label: 'Move to OA', color: '#F59E0B', action: () => patchStatus('oa') },
    oa: { label: 'Move to interview', color: '#EC4899', action: () => patchStatus('interview') },
    interview: { label: 'Move to offer', color: '#10B981', action: () => patchStatus('offer') },
    offer: { label: 'Offer received', color: '#10B981', action: null },
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
  const notesRows = Math.min(18, Math.max(8, notes.split('\n').length + Math.ceil(notes.length / 120)))

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

      <div style={{
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
              <div style={{ fontSize: 15, fontWeight: 800, color: T.text, lineHeight: 1.3, marginBottom: 5 }}>
                {job.starred ? <span style={{ color: '#F59E0B', marginRight: 5 }}>★</span> : null}
                {job.title}
              </div>
              <div style={{ fontSize: 12, color: T.muted, display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
                <span style={{ fontWeight: 700, color: T.text }}>{job.company || 'Unknown company'}</span>
                {job.location && <><span>·</span><span>{job.location}</span></>}
                {job.source && <><span>·</span><Tag>{job.source}</Tag></>}
              </div>
            </div>
            <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexShrink: 0 }}>
              <button
                onClick={() => patchStatus(job.status, { starred: job.starred ? 0 : 1 })}
                title={job.starred ? 'Unstar' : 'Star'}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: job.starred ? '#F59E0B' : T.muted, fontSize: 17, padding: 4 }}>
                {job.starred ? '★' : '☆'}
              </button>
              <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: T.muted, fontSize: 18, padding: 4 }}>x</button>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 12 }}>
            <StatusBadge status={job.status} size="md" />
            <div style={{ flex: 1 }}><ScoreBar score={score} height={5} showLabel /></div>
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
                  borderRadius: 8,
                  border: 'none',
                  cursor: tailoring || updating ? 'not-allowed' : 'pointer',
                  background: primaryAction.color,
                  color: '#fff',
                  fontSize: 12,
                  fontWeight: 800,
                  fontFamily: 'Inter, system-ui, sans-serif',
                  opacity: tailoring || updating ? 0.7 : 1,
                }}>
                {tailoring ? 'Tailoring...' : primaryAction.label}
              </button>
            )}
            {job.url && !job.url.startsWith('manual://') && (
              <Btn variant="secondary" size="sm" onClick={() => window.open(job.url, '_blank')}>Posting</Btn>
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
                padding: '9px 4px',
                border: 'none',
                cursor: 'pointer',
                background: 'transparent',
                fontFamily: 'Inter, system-ui, sans-serif',
                fontSize: 11,
                fontWeight: activeTab === t ? 800 : 600,
                color: activeTab === t ? T.accent : T.muted,
                borderBottom: activeTab === t ? `2px solid ${T.accent}` : '2px solid transparent',
                textTransform: 'capitalize',
              }}>{t}</button>
          ))}
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: '16px 20px' }}>
          {activeTab === 'overview' && trackingForm && (
            <div>
              {job.status === 'approved' && (
                <div style={{ background: 'rgba(139,123,184,0.10)', border: '1px solid rgba(139,123,184,0.30)', borderRadius: 10, padding: '12px 14px', marginBottom: 14 }}>
                  <div style={{ fontSize: 12, fontWeight: 800, color: '#8B7BB8', marginBottom: 3 }}>Auto-apply queued</div>
                  <div style={{ fontSize: 11, color: T.muted, lineHeight: 1.5 }}>
                    The apply bot will pick this up on the next scheduled run. Use “Mark manually applied” if you submit it yourself.
                  </div>
                </div>
              )}

              {editForm && (
                <FormSection
                  title={overviewEditing ? 'Edit this job' : 'Role details'}
                  sub={overviewEditing ? 'You are editing directly in Overview. Save here when the scrape or import needs cleanup.' : 'Core job information and metadata.'}
                  T={T}
                  dark={dark}
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
                          <input type="checkbox" checked={editForm.starred} onChange={e => setEdit('starred', e.target.checked)} style={{ accentColor: '#F59E0B' }} />
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
                        <Btn variant="secondary" size="sm" onClick={() => setOverviewEditing(true)}>Edit details</Btn>
                      </div>
                    </>
                  )}
                </FormSection>
              )}

              <FormSection title="Update this application" sub="The fields you are most likely to touch after every job-search session." T={T} dark={dark}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 10px' }}>
                  <SelectField label="Status" value={trackingForm.status} onChange={v => setTracking('status', v)} options={STATUS_OPTS} T={T} dark={dark} />
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
              </FormSection>

              <FormSection title="Notes" T={T} dark={dark}>
                <Textarea value={notes} onChange={setNotes} placeholder="Referral notes, next step, application quirks..." rows={notesRows} style={{ lineHeight: 1.6 }} />
                {notes !== (job.notes || '') && (
                  <button onClick={saveNotes} style={{ marginTop: 7, background: 'none', border: 'none', cursor: 'pointer', color: T.accent, fontSize: 11, fontWeight: 800 }}>
                    Save notes
                  </button>
                )}
              </FormSection>

              <FormSection title="Job description" T={T} dark={dark}>
                <div style={{ fontSize: 12, color: T.text, lineHeight: 1.7, whiteSpace: 'pre-wrap', maxHeight: jdExpanded ? 'none' : 140, overflow: 'hidden' }}>
                  {job.description || 'No description available.'}
                </div>
                <button onClick={() => setJdExpanded(!jdExpanded)}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: T.accent, fontSize: 11, fontWeight: 800, padding: '5px 0', marginTop: 4 }}>
                  {jdExpanded ? 'Show less' : 'Show more'}
                </button>
              </FormSection>

              <Divider />

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                {job.status === 'new' && <Btn variant="ghost" size="sm" onClick={() => patchStatus('skipped')} style={{ width: '100%' }}>Skip</Btn>}
                {job.status === 'new' && <Btn variant="ghost" size="sm" onClick={() => patchStatus('rejected')} style={{ width: '100%', color: T.danger }}>Reject</Btn>}
                {job.status === 'queued' && <Btn variant="ghost" size="sm" onClick={() => patchStatus('new')} style={{ width: '100%' }}>Back to new</Btn>}
                {job.status === 'approved' && <Btn variant="ghost" size="sm" onClick={() => patchStatus('queued')} style={{ width: '100%' }}>Back to ready</Btn>}
                {['applied', 'oa', 'interview'].includes(job.status) && <Btn variant="ghost" size="sm" onClick={() => patchStatus('rejected')} style={{ width: '100%', color: T.danger }}>Mark rejected</Btn>}
                {['rejected', 'skipped'].includes(job.status) && <Btn variant="ghost" size="sm" onClick={() => patchStatus('new')} style={{ width: '100%' }}>Reopen</Btn>}
              </div>
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
                    src={api.resumeUrl(job.id)}
                    style={{ width: '100%', height: 500, border: 'none', borderRadius: 8 }}
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
                  <div style={{ fontSize: 12, marginBottom: 20 }}>Generated automatically when you tailor this job.</div>
                  <Btn variant="primary" onClick={handleTailor} disabled={tailoring}>Tailor now</Btn>
                </div>
              ) : (
                <>
                  <div style={{ display: 'flex', gap: 4, background: T.surface, borderRadius: 8, padding: 4, marginBottom: 12 }}>
                    {['pdf', 'text'].map(mode => (
                      <button
                        key={mode}
                        onClick={() => setCoverLetterMode(mode)}
                        style={{
                          flex: 1,
                          padding: '7px 10px',
                          border: 'none',
                          borderRadius: 6,
                          cursor: 'pointer',
                          background: coverLetterMode === mode ? T.accent : 'transparent',
                          color: coverLetterMode === mode ? '#fff' : T.muted,
                          fontSize: 12,
                          fontWeight: 800,
                          fontFamily: 'Inter, system-ui, sans-serif',
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
                        style={{ width: '100%', height: 500, border: 'none', borderRadius: 8 }}
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
