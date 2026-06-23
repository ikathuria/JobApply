import { useState, useEffect, useCallback, useContext } from 'react'
import { ThemeCtx } from './ThemeContext.jsx'
import { DARK, LIGHT } from '../theme.js'
import { api } from '../api.js'
import { Card, Btn, Input, Textarea, EmptyState, Spinner, SectionLabel, Divider } from './ui/index.jsx'

const OUTREACH_STATUSES = ['draft', 'sent', 'replied', 'bounced', 'ignored']
const STATUS_COLOR = {
  draft:   '#8A847A',
  sent:    '#5B88B5',
  replied: '#5B8C44',
  bounced: '#B4452C',
  ignored: '#B5AFA3',
}

function fmtDate(s) {
  if (!s) return ''
  return String(s).slice(0, 10)
}

export default function OutreachView({ reachOutJob, clearReachOut }) {
  const { dark } = useContext(ThemeCtx)
  const T = dark ? DARK : LIGHT

  const [recruiters, setRecruiters] = useState(null)
  const [selectedId, setSelectedId] = useState(null)
  const [outreach, setOutreach] = useState([])
  const [loadingOutreach, setLoadingOutreach] = useState(false)
  const [followups, setFollowups] = useState([])
  const [toast, setToast] = useState(null)

  // add-recruiter form
  const [addOpen, setAddOpen] = useState(false)
  const [form, setForm] = useState({ name: '', email: '', company: '', title: '', notes: '' })
  const [adding, setAdding] = useState(false)

  // composer
  const [composer, setComposer] = useState(null)  // { id, type, subject, body }
  const [generating, setGenerating] = useState(false)
  const [sending, setSending] = useState(false)

  const flash = (msg, kind = 'ok') => {
    setToast({ msg, kind })
    setTimeout(() => setToast(null), 3200)
  }

  const loadRecruiters = useCallback(() => {
    api.recruiters().then(setRecruiters).catch(() => setRecruiters([]))
  }, [])
  const loadFollowups = useCallback(() => {
    api.followups().then(setFollowups).catch(() => setFollowups([]))
  }, [])

  useEffect(() => { loadRecruiters(); loadFollowups() }, [loadRecruiters, loadFollowups])

  // When arriving from a job's "Reach Out", prefill the add form with the company.
  useEffect(() => {
    if (reachOutJob) {
      setAddOpen(true)
      setForm(f => ({ ...f, company: reachOutJob.company || '' }))
    }
  }, [reachOutJob])

  const selectRecruiter = (id) => {
    setSelectedId(id)
    setComposer(null)
    setLoadingOutreach(true)
    api.recruiterOutreach(id)
      .then(setOutreach)
      .catch(() => setOutreach([]))
      .finally(() => setLoadingOutreach(false))
  }

  const submitAdd = async () => {
    if (!form.name.trim()) { flash('Name is required', 'err'); return }
    setAdding(true)
    try {
      const r = await api.addRecruiter({
        name: form.name.trim(),
        email: form.email.trim() || null,
        company: form.company.trim() || null,
        title: form.title.trim() || null,
        notes: form.notes.trim() || null,
      })
      setForm({ name: '', email: '', company: '', title: '', notes: '' })
      setAddOpen(false)
      loadRecruiters()
      selectRecruiter(r.id)
      flash(`Added ${r.name}`)
    } catch (e) {
      flash(e.message || 'Could not add recruiter', 'err')
    } finally {
      setAdding(false)
    }
  }

  const startCompose = async (type) => {
    if (!selectedId) return
    setGenerating(true)
    setComposer(null)
    try {
      const draft = await api.draftOutreach({
        recruiter_id: selectedId,
        type,
        job_id: reachOutJob ? reachOutJob.id : null,
      })
      setComposer({ id: draft.id, type, subject: draft.subject || '', body: draft.body || '' })
      loadOutreachQuiet()
    } catch (e) {
      flash(e.message || 'Draft generation failed', 'err')
    } finally {
      setGenerating(false)
    }
  }

  const loadOutreachQuiet = () => {
    if (!selectedId) return
    api.recruiterOutreach(selectedId).then(setOutreach).catch(() => {})
  }

  const sendComposer = async () => {
    if (!composer) return
    setSending(true)
    try {
      // persist any edits to the draft, then send
      await api.patchOutreach(composer.id, { subject: composer.subject, body: composer.body })
      await api.sendOutreach(composer.id)
      const r = recruiters?.find(x => x.id === selectedId)
      flash(`Email sent to ${r ? r.name : 'recruiter'}`)
      setComposer(null)
      loadOutreachQuiet()
      loadRecruiters()
      loadFollowups()
      if (reachOutJob) clearReachOut()
    } catch (e) {
      flash(e.message || 'Send failed — check Gmail credentials', 'err')
    } finally {
      setSending(false)
    }
  }

  const changeStatus = async (oid, status) => {
    try {
      await api.patchOutreach(oid, { status })
      loadOutreachQuiet()
      loadRecruiters()
      loadFollowups()
    } catch (e) {
      flash(e.message || 'Could not update status', 'err')
    }
  }

  const selected = recruiters?.find(r => r.id === selectedId)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Follow-up reminder banner */}
      {followups.length > 0 && (
        <div style={{
          margin: '14px 20px 0', padding: '10px 16px', borderRadius: 10,
          background: 'rgba(196,152,64,0.14)', border: `1px solid ${T.warning}50`,
          color: T.text, fontSize: 13, display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap',
        }}>
          <span style={{ fontSize: 16 }}>⏰</span>
          <span style={{ fontWeight: 700 }}>{followups.length} follow-up{followups.length !== 1 ? 's' : ''} due:</span>
          {followups.map(f => (
            <button key={f.id}
              onClick={() => selectRecruiter(f.recruiter_id)}
              style={{
                background: 'transparent', border: `1px solid ${T.warning}55`, borderRadius: 14,
                padding: '2px 10px', fontSize: 12, color: T.text, cursor: 'pointer',
              }}>
              {f.recruiter_name}{f.company ? ` · ${f.company}` : ''} ({fmtDate(f.follow_up_date)})
            </button>
          ))}
        </div>
      )}

      {/* Reach-out context banner */}
      {reachOutJob && (
        <div style={{
          margin: '14px 20px 0', padding: '10px 16px', borderRadius: 10,
          background: T.accentBg, border: `1px solid ${T.accent}40`,
          color: T.text, fontSize: 13, display: 'flex', alignItems: 'center', gap: 10,
        }}>
          <span>✉️ Reaching out about <b>{reachOutJob.title}</b>{reachOutJob.company ? ` @ ${reachOutJob.company}` : ''}</span>
          <span style={{ flex: 1 }} />
          <button onClick={clearReachOut} style={{ background: 'transparent', border: 'none', color: T.muted, cursor: 'pointer', fontSize: 16 }}>×</button>
        </div>
      )}

      <div style={{ flex: 1, display: 'flex', gap: 18, padding: 20, overflow: 'hidden' }}>
        {/* ── Left: recruiter list ── */}
        <div style={{ width: 320, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <SectionLabel style={{ marginBottom: 0 }}>Recruiters</SectionLabel>
            <Btn size="sm" variant={addOpen ? 'secondary' : 'primary'} onClick={() => setAddOpen(o => !o)}>
              {addOpen ? 'Cancel' : '+ Add'}
            </Btn>
          </div>

          {addOpen && (
            <Card style={{ marginBottom: 12 }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <Input value={form.name} onChange={v => setForm({ ...form, name: v })} placeholder="Name *" />
                <Input value={form.email} onChange={v => setForm({ ...form, email: v })} placeholder="Email" />
                <Input value={form.company} onChange={v => setForm({ ...form, company: v })} placeholder="Company" />
                <Input value={form.title} onChange={v => setForm({ ...form, title: v })} placeholder="Title" />
                <Textarea value={form.notes} onChange={v => setForm({ ...form, notes: v })} placeholder="Notes" rows={2} />
                <Btn onClick={submitAdd} disabled={adding}>
                  {adding ? <Spinner size={14} color="#fff" /> : 'Save recruiter'}
                </Btn>
              </div>
            </Card>
          )}

          <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8 }}>
            {recruiters === null && <div style={{ padding: 20, textAlign: 'center' }}><Spinner /></div>}
            {recruiters?.length === 0 && !addOpen && (
              <EmptyState icon="✉" title="No recruiters yet" sub="Add a recruiter to start outreach." />
            )}
            {recruiters?.map(r => (
              <Card key={r.id} onClick={() => selectRecruiter(r.id)}
                style={selectedId === r.id ? { borderColor: T.accent, boxShadow: `0 0 0 3px ${T.accent}18` } : {}}>
                <div style={{ fontWeight: 700, fontSize: 14, color: T.text }}>{r.name}</div>
                <div style={{ fontSize: 12, color: T.muted, marginTop: 2 }}>
                  {[r.title, r.company].filter(Boolean).join(' · ') || '—'}
                </div>
                <div style={{ fontSize: 11.5, color: T.muted, marginTop: 4, display: 'flex', justifyContent: 'space-between' }}>
                  <span>{r.email || 'no email'}</span>
                  <span>{r.sent_count || 0} sent</span>
                </div>
              </Card>
            ))}
          </div>
        </div>

        {/* ── Right: detail ── */}
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {!selected && (
            <EmptyState icon="◌" title="Select a recruiter" sub="Pick someone on the left to view outreach and compose an email." />
          )}

          {selected && (
            <div>
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
                <div>
                  <div style={{ fontSize: 20, fontWeight: 800, color: T.text }}>{selected.name}</div>
                  <div style={{ fontSize: 13, color: T.muted, marginTop: 2 }}>
                    {[selected.title, selected.company].filter(Boolean).join(' · ') || '—'}
                  </div>
                  <div style={{ fontSize: 12.5, color: T.muted, marginTop: 2 }}>{selected.email || 'no email on file'}</div>
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <Btn size="sm" variant="primary" onClick={() => startCompose('cold')} disabled={generating || sending}>New Email</Btn>
                  <Btn size="sm" variant="secondary" onClick={() => startCompose('referral')} disabled={generating || sending}>Request Referral</Btn>
                </div>
              </div>

              {!selected.email && (
                <div style={{ marginTop: 10, fontSize: 12, color: T.warning }}>
                  ⚠ Add an email for this recruiter before sending.
                </div>
              )}

              {/* Composer */}
              {generating && (
                <Card style={{ marginTop: 16, display: 'flex', alignItems: 'center', gap: 10 }}>
                  <Spinner size={16} /> <span style={{ color: T.muted, fontSize: 13 }}>Generating draft…</span>
                </Card>
              )}

              {composer && (
                <Card style={{ marginTop: 16 }}>
                  <SectionLabel>{composer.type === 'referral' ? 'Referral request' : 'Cold email'} — review &amp; send</SectionLabel>
                  <Input value={composer.subject} onChange={v => setComposer({ ...composer, subject: v })} placeholder="Subject" style={{ marginBottom: 8 }} />
                  <Textarea value={composer.body} onChange={v => setComposer({ ...composer, body: v })} rows={12} />
                  <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
                    <Btn variant="success" onClick={sendComposer} disabled={sending || !selected.email}>
                      {sending ? <Spinner size={14} color="#fff" /> : 'Send email'}
                    </Btn>
                    <Btn variant="ghost" onClick={() => setComposer(null)} disabled={sending}>Discard</Btn>
                  </div>
                </Card>
              )}

              <Divider style={{ margin: '20px 0 12px' }} />
              <SectionLabel>Outreach history</SectionLabel>

              {loadingOutreach && <div style={{ padding: 16 }}><Spinner /></div>}
              {!loadingOutreach && outreach.length === 0 && (
                <div style={{ fontSize: 13, color: T.muted, padding: '8px 2px' }}>No emails yet.</div>
              )}

              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {outreach.map(o => (
                  <Card key={o.id}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10 }}>
                      <div style={{ minWidth: 0 }}>
                        <div style={{ fontWeight: 700, fontSize: 13.5, color: T.text, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {o.subject || '(no subject)'}
                        </div>
                        <div style={{ fontSize: 11.5, color: T.muted, marginTop: 3 }}>
                          {o.type === 'referral' ? 'Referral' : 'Cold'}
                          {o.sent_at ? ` · sent ${fmtDate(o.sent_at)}` : ''}
                          {o.follow_up_date ? ` · follow up ${fmtDate(o.follow_up_date)}` : ''}
                        </div>
                      </div>
                      <select
                        value={o.status}
                        onChange={e => changeStatus(o.id, e.target.value)}
                        style={{
                          background: T.card, color: STATUS_COLOR[o.status] || T.text,
                          border: `1px solid ${T.border}`, borderRadius: 8, padding: '5px 8px',
                          fontSize: 12, fontWeight: 700, cursor: 'pointer', outline: 'none',
                        }}>
                        {OUTREACH_STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
                      </select>
                    </div>
                    {o.body && (
                      <div style={{ fontSize: 12.5, color: T.muted, marginTop: 8, whiteSpace: 'pre-wrap', maxHeight: 88, overflow: 'hidden' }}>
                        {o.body}
                      </div>
                    )}
                  </Card>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Toast */}
      {toast && (
        <div style={{
          position: 'fixed', bottom: 24, right: 24, zIndex: 1000,
          padding: '12px 18px', borderRadius: 10, fontSize: 13, fontWeight: 600, color: '#fff',
          background: toast.kind === 'err' ? T.danger : T.success,
          boxShadow: '0 6px 24px rgba(0,0,0,0.25)',
        }}>
          {toast.msg}
        </div>
      )}
    </div>
  )
}
