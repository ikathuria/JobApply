import { useState, useMemo, useEffect, useContext, useRef } from 'react'
import { ThemeCtx } from './ThemeContext.jsx'
import { DARK, LIGHT } from '../theme.js'
import { Input, Btn, EmptyState, Spinner, StatusBadge, Tag } from './ui/index.jsx'
import JobRow from './JobRow.jsx'
import { api } from '../api.js'

// ── Import modal ─────────────────────────────────────────────────────────────
const STATUS_OPTIONS = ['new','queued','approved','applied','oa','interview','offer','rejected','skipped']
const BLANK = { title:'', company:'', url:'', status:'applied', date_applied:'', location:'', notes:'' }
const CSV_COLUMNS = ['title','company','url','status','date_applied','location','notes']
const CSV_TEMPLATE = CSV_COLUMNS.join(',') + '\n' +
  'ML Engineer Intern,Acme AI,https://jobs.acme.ai/123,applied,2026-04-21,Remote,Referral from Jane\n' +
  'Research Intern,DeepMind,,new,,,\n'

// Minimal CSV parser (handles quoted fields with commas/newlines)
function parseCSV(text) {
  const rows = []
  const lines = text.trim().split(/\r?\n/)
  const headers = lines[0].split(',').map(h => h.trim().toLowerCase())
  for (let i = 1; i < lines.length; i++) {
    if (!lines[i].trim()) continue
    const vals = []
    let cur = '', inQ = false
    for (const ch of lines[i]) {
      if (ch === '"') { inQ = !inQ }
      else if (ch === ',' && !inQ) { vals.push(cur.trim()); cur = '' }
      else cur += ch
    }
    vals.push(cur.trim())
    const row = {}
    headers.forEach((h, idx) => { row[h] = vals[idx] || '' })
    rows.push(row)
  }
  return { headers, rows }
}

function ImportModal({ dark, onClose, onSuccess }) {
  const T = dark ? DARK : LIGHT
  const [tab, setTab]       = useState('manual')   // 'manual' | 'csv'

  // ── Manual tab state ──
  const [form, setForm]     = useState({ ...BLANK, date_applied: new Date().toISOString().slice(0,10) })
  const [saving, setSaving] = useState(false)
  const [error, setError]   = useState('')
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const submitManual = async () => {
    if (!form.title.trim() || !form.company.trim()) { setError('Title and Company are required.'); return }
    setSaving(true); setError('')
    try {
      await api.import({ title: form.title.trim(), company: form.company.trim(),
        url: form.url.trim(), status: form.status,
        date_applied: form.date_applied || null,
        location: form.location.trim(), notes: form.notes.trim() })
      onSuccess(); onClose()
    } catch (e) { setError(e.message || 'Import failed'); setSaving(false) }
  }

  // ── CSV tab state ──
  const [csvRows, setCsvRows]     = useState([])
  const [csvError, setCsvError]   = useState('')
  const [csvStatus, setCsvStatus] = useState('')   // progress message
  const [importing, setImporting] = useState(false)

  const onFileChange = e => {
    const file = e.target.files?.[0]
    if (!file) return
    setCsvError(''); setCsvRows([]); setCsvStatus('')
    const reader = new FileReader()
    reader.onload = ev => {
      try {
        const { rows } = parseCSV(ev.target.result)
        const valid = rows.filter(r => r.title && r.company)
        if (!valid.length) { setCsvError('No valid rows found. Columns "title" and "company" are required.'); return }
        setCsvRows(valid)
      } catch { setCsvError('Could not parse CSV — check the format.') }
    }
    reader.readAsText(file)
  }

  const submitCSV = async () => {
    if (!csvRows.length) return
    setImporting(true); setCsvError(''); setCsvStatus('')
    let ok = 0, fail = 0
    for (let i = 0; i < csvRows.length; i++) {
      const r = csvRows[i]
      setCsvStatus(`Importing ${i + 1} / ${csvRows.length}…`)
      try {
        await api.import({
          title:        r.title?.trim(),
          company:      r.company?.trim(),
          url:          r.url?.trim() || '',
          status:       r.status?.trim() || 'applied',
          date_applied: r.date_applied?.trim() || null,
          location:     r.location?.trim() || '',
          notes:        r.notes?.trim() || '',
        })
        ok++
      } catch { fail++ }
    }
    setCsvStatus(`Done — ${ok} imported${fail ? `, ${fail} failed` : ''}.`)
    setImporting(false)
    if (ok) onSuccess()
  }

  const downloadTemplate = () => {
    const blob = new Blob([CSV_TEMPLATE], { type: 'text/csv' })
    const a = Object.assign(document.createElement('a'), { href: URL.createObjectURL(blob), download: 'jobapply_import.csv' })
    a.click()
  }

  // ── Shared styles ──
  const overlay = { position:'fixed', inset:0, zIndex:1000, background:'rgba(0,0,0,0.55)', backdropFilter:'blur(4px)', display:'flex', alignItems:'center', justifyContent:'center' }
  const modal   = { background: T.card, border: `1px solid ${T.border}`, borderRadius:14, padding:'28px 32px', width:560, maxWidth:'95vw', boxShadow:'0 24px 64px rgba(0,0,0,0.4)' }
  const lbl     = { fontSize:11, fontWeight:700, color:T.muted, textTransform:'uppercase', letterSpacing:'0.07em', marginBottom:5 }
  const inp     = { width:'100%', padding:'8px 12px', borderRadius:8, border:`1px solid ${T.border}`, background: dark ? '#1A1A28' : '#FAFAFA', color:T.text, fontSize:13, fontFamily:'DM Sans, sans-serif', outline:'none', boxSizing:'border-box' }
  const tabBtn  = active => ({ padding:'6px 16px', borderRadius:6, border:'none', cursor:'pointer', fontFamily:'DM Sans, sans-serif', fontSize:12, fontWeight: active ? 700 : 500, background: active ? T.accent : 'transparent', color: active ? '#fff' : T.muted, transition:'all 0.12s' })

  return (
    <div style={overlay} onClick={e => e.target === e.currentTarget && onClose()}>
      <div style={modal}>
        {/* Header */}
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:18 }}>
          <div style={{ fontSize:16, fontWeight:800, color:T.text }}>Import Job</div>
          <button onClick={onClose} style={{ background:'none', border:'none', color:T.muted, fontSize:20, cursor:'pointer', lineHeight:1 }}>×</button>
        </div>

        {/* Tab switcher */}
        <div style={{ display:'flex', gap:4, marginBottom:20, background: dark ? '#13131F' : '#F0F0F8', borderRadius:8, padding:4 }}>
          <button style={tabBtn(tab === 'manual')} onClick={() => { setTab('manual'); setError('') }}>Single Job</button>
          <button style={tabBtn(tab === 'csv')}   onClick={() => { setTab('csv');   setCsvError('') }}>CSV Bulk</button>
        </div>

        {/* ── Manual tab ── */}
        {tab === 'manual' && (<>
          <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'14px 16px' }}>
            <div style={{ gridColumn:'1/-1' }}>
              <div style={lbl}>Job Title *</div>
              <input style={inp} value={form.title} onChange={e => set('title', e.target.value)} placeholder="ML Engineer Intern" />
            </div>
            <div>
              <div style={lbl}>Company *</div>
              <input style={inp} value={form.company} onChange={e => set('company', e.target.value)} placeholder="Acme AI" />
            </div>
            <div>
              <div style={lbl}>Status</div>
              <select style={inp} value={form.status} onChange={e => set('status', e.target.value)}>
                {STATUS_OPTIONS.map(s => <option key={s} value={s}>{s.charAt(0).toUpperCase()+s.slice(1)}</option>)}
              </select>
            </div>
            <div style={{ gridColumn:'1/-1' }}>
              <div style={lbl}>Job URL</div>
              <input style={inp} value={form.url} onChange={e => set('url', e.target.value)} placeholder="https://jobs.example.com/..." />
            </div>
            <div>
              <div style={lbl}>Date Applied</div>
              <input type="date" style={inp} value={form.date_applied} onChange={e => set('date_applied', e.target.value)} />
            </div>
            <div>
              <div style={lbl}>Location</div>
              <input style={inp} value={form.location} onChange={e => set('location', e.target.value)} placeholder="Remote / NYC" />
            </div>
            <div style={{ gridColumn:'1/-1' }}>
              <div style={lbl}>Notes</div>
              <textarea style={{ ...inp, resize:'vertical', minHeight:64 }} value={form.notes} onChange={e => set('notes', e.target.value)} placeholder="Referral from Jane, apply before May 1…" />
            </div>
          </div>
          {error && <div style={{ marginTop:10, fontSize:12, color:'#EF4444' }}>{error}</div>}
          <div style={{ display:'flex', gap:10, marginTop:20 }}>
            <Btn variant="primary" onClick={submitManual} disabled={saving}>{saving ? 'Importing…' : 'Import Job'}</Btn>
            <Btn variant="secondary" onClick={onClose}>Cancel</Btn>
          </div>
        </>)}

        {/* ── CSV tab ── */}
        {tab === 'csv' && (<>
          {/* Template download */}
          <div style={{ background: dark ? '#13131F' : '#F4F4FC', border:`1px solid ${T.border}`, borderRadius:8, padding:'12px 14px', marginBottom:16, fontSize:12, color:T.muted, lineHeight:1.6 }}>
            Expected columns: <code style={{ color:T.text }}>{CSV_COLUMNS.join(', ')}</code><br/>
            Only <strong>title</strong> and <strong>company</strong> are required.{' '}
            <span style={{ color:T.accent, cursor:'pointer', textDecoration:'underline' }} onClick={downloadTemplate}>Download template ↓</span>
          </div>

          {/* File picker */}
          <div style={{ marginBottom:14 }}>
            <div style={lbl}>Select CSV file</div>
            <input type="file" accept=".csv,text/csv" onChange={onFileChange}
              style={{ fontSize:12, color:T.text, fontFamily:'DM Sans, sans-serif' }} />
          </div>

          {/* Preview table */}
          {csvRows.length > 0 && (
            <div style={{ marginBottom:14 }}>
              <div style={{ fontSize:11, color:T.muted, marginBottom:6 }}>{csvRows.length} row{csvRows.length !== 1 ? 's' : ''} ready to import</div>
              <div style={{ maxHeight:160, overflowY:'auto', border:`1px solid ${T.border}`, borderRadius:8 }}>
                <table style={{ width:'100%', borderCollapse:'collapse', fontSize:11 }}>
                  <thead>
                    <tr style={{ background: dark ? '#1A1A28' : '#F0F0F8' }}>
                      {['title','company','status','date_applied'].map(h => (
                        <th key={h} style={{ padding:'6px 10px', textAlign:'left', color:T.muted, fontWeight:700, textTransform:'uppercase', letterSpacing:'0.06em', borderBottom:`1px solid ${T.border}` }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {csvRows.slice(0, 50).map((r, i) => (
                      <tr key={i} style={{ borderBottom:`1px solid ${T.border}20` }}>
                        <td style={{ padding:'5px 10px', color:T.text, maxWidth:160, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>{r.title}</td>
                        <td style={{ padding:'5px 10px', color:T.text }}>{r.company}</td>
                        <td style={{ padding:'5px 10px', color:T.muted }}>{r.status || 'applied'}</td>
                        <td style={{ padding:'5px 10px', color:T.muted, fontFamily:'JetBrains Mono, monospace' }}>{r.date_applied || '—'}</td>
                      </tr>
                    ))}
                    {csvRows.length > 50 && (
                      <tr><td colSpan={4} style={{ padding:'6px 10px', color:T.muted, fontSize:11 }}>…and {csvRows.length - 50} more</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {csvError  && <div style={{ marginBottom:10, fontSize:12, color:'#EF4444' }}>{csvError}</div>}
          {csvStatus && <div style={{ marginBottom:10, fontSize:12, color: csvStatus.startsWith('Done') ? '#22C55E' : T.muted }}>{csvStatus}</div>}

          <div style={{ display:'flex', gap:10, marginTop:4 }}>
            <Btn variant="primary" onClick={submitCSV} disabled={!csvRows.length || importing}>
              {importing ? csvStatus : `Import ${csvRows.length || ''} Job${csvRows.length !== 1 ? 's' : ''}`}
            </Btn>
            <Btn variant="secondary" onClick={onClose}>Close</Btn>
          </div>
        </>)}
      </div>
    </div>
  )
}

// ── Focus queue ───────────────────────────────────────────────────────────────
function FocusQueue({ focus, onSelectJob, setTab, dark }) {
  const T = dark ? DARK : LIGHT
  if (!focus?.length) return null
  return (
    <div style={{ marginBottom: 24 }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10 }}>
        Today's Focus
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 10 }}>
        {focus.map(item => (
          <div key={item.id}
            onClick={() => {
              if (item.jobId) onSelectJob({ id: item.jobId, _needsFetch: true })
              else setTab(item.tab)
            }}
            style={{
              background: T.card, border: `1px solid ${T.border}`,
              borderLeft: `3px solid ${item.color}`,
              borderRadius: 10, padding: '12px 14px', cursor: 'pointer',
              transition: 'all 0.15s',
              display: 'flex', flexDirection: 'column', gap: 6,
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = item.color; e.currentTarget.style.boxShadow = `0 0 0 3px ${item.color}18` }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = T.border; e.currentTarget.style.borderLeftColor = item.color; e.currentTarget.style.boxShadow = 'none' }}
          >
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
              <span style={{ fontSize: 16, lineHeight: 1.2 }}>{item.icon}</span>
              <span style={{ fontSize: 12, color: T.text, fontWeight: 500, flex: 1, lineHeight: 1.4 }}>{item.label}</span>
            </div>
            <span style={{ fontSize: 11, fontWeight: 700, color: item.color, alignSelf: 'flex-start' }}>{item.cta} →</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Tab definitions ───────────────────────────────────────────────────────────
function ReviewDeck({ jobs, loading, dark, onOpenJob, onDecision }) {
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
                    background: dark ? '#151522' : '#FFFFFF',
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
                    background: dark ? '#171724' : '#FFFFFF',
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
                  background: dark ? '#251719' : '#FFF4F4',
                  color: '#EF4444',
                  fontSize: 13,
                  fontWeight: 900,
                  fontFamily: 'DM Sans, sans-serif',
                  cursor: busy ? 'wait' : 'pointer',
                }}>Remove</button>
                <button onClick={() => onOpenJob({ ...topJob, _openTab: 'edit' })} style={{
                  height: 46,
                  borderRadius: 12,
                  border: `1px solid ${T.border}`,
                  background: dark ? '#1A1A28' : '#FAFAFA',
                  color: T.text,
                  fontSize: 13,
                  fontWeight: 800,
                  fontFamily: 'DM Sans, sans-serif',
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
                  fontFamily: 'DM Sans, sans-serif',
                  cursor: busy ? 'wait' : 'pointer',
                }}>Approve</button>
              </div>
            </div>

            <aside style={{
              border: `1px solid ${T.border}`,
              borderRadius: 14,
              background: dark ? '#151522' : '#FFFFFF',
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
                  fontFamily: 'DM Sans, sans-serif',
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

function ApprovedDeck({ jobs, loading, dark, onOpenJob, onDecision }) {
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
                background: dark ? '#171724' : '#FFFFFF',
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
                  background: dark ? '#251719' : '#FFF4F4',
                  color: '#EF4444',
                  fontSize: 13,
                  fontWeight: 900,
                  fontFamily: 'DM Sans, sans-serif',
                  cursor: busy ? 'wait' : 'pointer',
                }}>Skip</button>
                <button onClick={() => openPosting(topJob)} disabled={busy} style={{
                  height: 46,
                  borderRadius: 12,
                  border: '1px solid #8B5CF640',
                  background: T.accent,
                  color: '#fff',
                  fontSize: 13,
                  fontWeight: 900,
                  fontFamily: 'DM Sans, sans-serif',
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
                  fontFamily: 'DM Sans, sans-serif',
                  cursor: busy ? 'wait' : 'pointer',
                }}>Mark applied</button>
              </div>
            </div>

            <aside style={{
              border: `1px solid ${T.border}`,
              borderRadius: 14,
              background: dark ? '#151522' : '#FFFFFF',
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
                  fontFamily: 'DM Sans, sans-serif',
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

const TABS = [
  { id: 'new',      label: 'New',      statusFilter: 'new' },
  { id: 'ready',    label: 'Ready',    statusFilter: 'queued' },
  { id: 'approved', label: 'Approved', statusFilter: 'approved' },
  { id: 'applied',  label: 'Applied',  statusFilter: null },   // applied+oa+interview
  { id: 'all',      label: 'All',      statusFilter: null },
]

export default function JobsView({ onSelectJob, selectedJob, tab, setTab, stats, onRefresh, triggerRefresh }) {
  const { dark } = useContext(ThemeCtx)
  const T = dark ? DARK : LIGHT

  const [search, setSearch]       = useState('')
  const [sort, setSort]           = useState('score')
  const [reviewMode, setReviewMode] = useState('deck')
  const [minScore, setMinScore]   = useState(0)
  const [jobs, setJobs]           = useState([])
  const [focus, setFocus]         = useState([])
  const [loading, setLoading]     = useState(true)
  const [showImport, setShowImport] = useState(false)
  const [selectedIds, setSelectedIds] = useState(new Set())
  const [bulkLoading, setBulkLoading] = useState(false)

  const multiSelectMode = selectedIds.size > 0

  function toggleSelect(id) {
    setSelectedIds(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  function selectAll() {
    setSelectedIds(new Set(filteredJobs.map(j => j.id)))
  }

  function clearSelection() {
    setSelectedIds(new Set())
  }

  async function bulkApply(status) {
    const ids = [...selectedIds]
    if (!ids.length) return
    setBulkLoading(true)
    try {
      await api.bulk(ids, status)
      clearSelection()
      triggerRefresh?.()
    } catch (e) {
      alert('Bulk update failed: ' + e.message)
    } finally {
      setBulkLoading(false)
    }
  }

  async function handleReviewDecision(job, status) {
    await api.patch(job.id, { status })
    setJobs(prev => prev.filter(j => j.id !== job.id))
    if (selectedJob?.id === job.id) onSelectJob(null)
    triggerRefresh?.()
  }

  // Fetch jobs when tab or filters change
  useEffect(() => {
    setLoading(true)
    clearSelection()
    const tabDef = TABS.find(t => t.id === tab)
    const params = { min_score: minScore, sort, limit: 500 }

    if (tab === 'applied') {
      // fetch all post-application statuses (applied includes later-rejected)
      Promise.all(['applied','oa','interview','offer','rejected'].map(s =>
        api.jobs({ ...params, status: s, limit: 500 })
      )).then(results => {
        setJobs(results.flatMap(r => r.jobs))
        setLoading(false)
      }).catch(() => setLoading(false))
    } else {
      if (tabDef?.statusFilter) params.status = tabDef.statusFilter
      api.jobs(params).then(r => { setJobs(r.jobs); setLoading(false) }).catch(() => setLoading(false))
    }
  }, [tab, minScore, sort, onRefresh])

  // Fetch focus items once
  useEffect(() => {
    api.focus().then(setFocus).catch(() => {})
  }, [onRefresh])

  // Client-side search filter
  const filteredJobs = useMemo(() => {
    if (!search) return jobs
    const q = search.toLowerCase()
    return jobs.filter(j =>
      (j.title    || '').toLowerCase().includes(q) ||
      (j.company  || '').toLowerCase().includes(q) ||
      (j.location || '').toLowerCase().includes(q)
    )
  }, [jobs, search])

  useEffect(() => {
    setReviewMode(tab === 'ready' || tab === 'approved' ? 'deck' : 'list')
  }, [tab])

  const tabCount = (tabId) => {
    if (!stats) return 0
    if (tabId === 'new')      return stats.new
    if (tabId === 'ready')    return stats.ready
    if (tabId === 'approved') return stats.approved
    if (tabId === 'applied')  return (stats.total_applied ?? (stats.applied + stats.oa + stats.interview + stats.offer + stats.rejected))
    if (tabId === 'all')      return stats.total
    return 0
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden', position: 'relative' }}>
      {/* Focus queue */}
      <div style={{ padding: '20px 24px 0', flexShrink: 0 }}>
        <FocusQueue focus={focus} onSelectJob={onSelectJob} setTab={setTab} dark={dark} />
      </div>

      {/* Tab bar */}
      <div style={{ padding: '0 24px', flexShrink: 0, borderBottom: `1px solid ${T.border}`, display: 'flex', alignItems: 'center', gap: 2 }}>
        {TABS.map(t => {
          const active = tab === t.id
          const count  = tabCount(t.id)
          return (
            <button key={t.id} onClick={() => setTab(t.id)}
              style={{
                padding: '10px 14px', border: 'none', cursor: 'pointer',
                borderRadius: '8px 8px 0 0', background: 'transparent',
                fontFamily: 'DM Sans, sans-serif', fontSize: 12,
                fontWeight: active ? 700 : 500,
                color: active ? T.accent : T.muted,
                borderBottom: active ? `2px solid ${T.accent}` : '2px solid transparent',
                display: 'flex', alignItems: 'center', gap: 6, transition: 'all 0.12s',
              }}>
              {t.label}
              {count > 0 && (
                <span style={{
                  background: active ? T.accent : (dark ? '#252538' : '#E2E2EE'),
                  color: active ? '#fff' : T.muted,
                  fontSize: 10, fontWeight: 800, borderRadius: 10, padding: '1px 6px',
                }}>{count}</span>
              )}
            </button>
          )
        })}
        <div style={{ flex: 1 }} />
        <button style={{
          padding: '6px 12px', borderRadius: 6, border: `1px solid ${T.border}`,
          background: 'transparent', color: T.muted, fontSize: 11, fontWeight: 600,
          cursor: 'pointer', fontFamily: 'DM Sans, sans-serif', marginBottom: 2,
        }} onClick={() => setShowImport(true)}>+ Import</button>
      </div>

      {/* Filter bar */}
      <div style={{ padding: '12px 24px', flexShrink: 0, display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
        <Input value={search} onChange={setSearch} placeholder="Search title, company, location…" icon="⌕" style={{ flex: 1, maxWidth: 360 }} />

        <select value={sort} onChange={e => setSort(e.target.value)}
          style={{
            padding: '8px 12px', borderRadius: 8, border: `1px solid ${T.border}`,
            background: dark ? '#1A1A28' : '#FAFAFA', color: T.text,
            fontSize: 12, fontFamily: 'DM Sans, sans-serif', cursor: 'pointer', outline: 'none',
          }}>
          <option value="score">Score ↓</option>
          <option value="company">Company A–Z</option>
          <option value="starred">Starred first</option>
        </select>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 11, color: T.muted, whiteSpace: 'nowrap' }}>Min score</span>
          <input type="range" min={0} max={1} step={0.05} value={minScore}
            onChange={e => setMinScore(parseFloat(e.target.value))}
            style={{ width: 80, accentColor: T.accent }}
          />
          <span style={{ fontSize: 11, color: T.text, fontFamily: 'JetBrains Mono, monospace', width: 32 }}>
            {Math.round(minScore * 100)}%
          </span>
        </div>

        <div style={{ fontSize: 11, color: T.muted, whiteSpace: 'nowrap' }}>
          {filteredJobs.length} jobs
        </div>
        {(tab === 'ready' || tab === 'approved') && (
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 4, background: dark ? '#13131F' : '#EEF0F7', borderRadius: 8, padding: 4 }}>
            {['deck', 'list'].map(mode => (
              <button
                key={mode}
                onClick={() => setReviewMode(mode)}
                style={{
                  padding: '7px 12px',
                  border: 'none',
                  borderRadius: 6,
                  cursor: 'pointer',
                  background: reviewMode === mode ? T.accent : 'transparent',
                  color: reviewMode === mode ? '#fff' : T.muted,
                  fontSize: 12,
                  fontWeight: 800,
                  fontFamily: 'DM Sans, sans-serif',
                }}
              >
                {mode === 'deck' ? (tab === 'approved' ? 'Apply deck' : 'Review deck') : 'List'}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Job list */}
      {tab === 'ready' && reviewMode === 'deck' ? (
        <ReviewDeck
          jobs={filteredJobs}
          loading={loading}
          dark={dark}
          onOpenJob={onSelectJob}
          onDecision={handleReviewDecision}
        />
      ) : tab === 'approved' && reviewMode === 'deck' ? (
        <ApprovedDeck
          jobs={filteredJobs}
          loading={loading}
          dark={dark}
          onOpenJob={onSelectJob}
          onDecision={handleReviewDecision}
        />
      ) : (
      <div style={{ flex: 1, overflowY: 'auto', padding: '0 12px 24px', position: 'relative' }}>
        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}>
            <Spinner size={28} />
          </div>
        ) : filteredJobs.length === 0 ? (
          <EmptyState icon="◌" title="No jobs match these filters" sub="Try adjusting the score slider or search term" />
        ) : (
          filteredJobs.map(job => (
            <JobRow
              key={job.id}
              job={job}
              onSelect={onSelectJob}
              selected={selectedJob?.id === job.id}
              checked={selectedIds.has(job.id)}
              onCheck={toggleSelect}
              multiSelectMode={multiSelectMode}
            />
          ))
        )}
      </div>
      )}

      {/* Bulk action bar */}
      {selectedIds.size > 0 && (
        <div style={{
          position: 'absolute', bottom: 0, left: 0, right: 0,
          background: dark ? '#1A1A28' : '#fff',
          borderTop: `2px solid #8B5CF6`,
          padding: '12px 20px',
          display: 'flex', alignItems: 'center', gap: 10,
          boxShadow: '0 -8px 24px rgba(0,0,0,0.15)',
          zIndex: 50, flexWrap: 'wrap',
        }}>
          {/* Clear + count */}
          <button onClick={clearSelection} style={{ background: 'none', border: 'none', cursor: 'pointer', color: T.muted, fontSize: 16, lineHeight: 1, padding: 2 }}>✕</button>
          <span style={{ fontSize: 13, fontWeight: 700, color: T.text, minWidth: 80 }}>
            {selectedIds.size} selected
          </span>

          {/* Select all */}
          {selectedIds.size < filteredJobs.length && (
            <button onClick={selectAll} style={{
              background: 'none', border: `1px solid ${T.border}`, borderRadius: 6,
              padding: '5px 10px', fontSize: 11, fontWeight: 600, color: T.muted,
              cursor: 'pointer', fontFamily: 'DM Sans, sans-serif',
            }}>
              Select all {filteredJobs.length}
            </button>
          )}

          <div style={{ flex: 1 }} />

          {/* Tab-contextual primary actions */}
          {tab === 'ready' && (
            <button onClick={() => bulkApply('approved')} disabled={bulkLoading}
              style={{ background: '#8B5CF6', color: '#fff', border: 'none', borderRadius: 8, padding: '8px 16px', fontSize: 12, fontWeight: 700, cursor: bulkLoading ? 'not-allowed' : 'pointer', fontFamily: 'DM Sans, sans-serif', opacity: bulkLoading ? 0.7 : 1 }}>
              {bulkLoading ? '…' : `✓ Approve (${selectedIds.size})`}
            </button>
          )}
          {tab === 'approved' && (
            <button onClick={() => bulkApply('applied')} disabled={bulkLoading}
              style={{ background: '#22C55E', color: '#fff', border: 'none', borderRadius: 8, padding: '8px 16px', fontSize: 12, fontWeight: 700, cursor: bulkLoading ? 'not-allowed' : 'pointer', fontFamily: 'DM Sans, sans-serif', opacity: bulkLoading ? 0.7 : 1 }}>
              {bulkLoading ? '…' : `✓ Mark Applied (${selectedIds.size})`}
            </button>
          )}
          {tab === 'new' && (
            <button onClick={() => bulkApply('queued')} disabled={bulkLoading}
              style={{ background: T.accent, color: '#fff', border: 'none', borderRadius: 8, padding: '8px 16px', fontSize: 12, fontWeight: 700, cursor: bulkLoading ? 'not-allowed' : 'pointer', fontFamily: 'DM Sans, sans-serif', opacity: bulkLoading ? 0.7 : 1 }}>
              {bulkLoading ? '…' : `✦ Tailor Queue (${selectedIds.size})`}
            </button>
          )}

          {/* Always available: skip + reject */}
          {['new', 'ready', 'approved', 'all'].includes(tab) && (
            <button onClick={() => bulkApply('skipped')} disabled={bulkLoading}
              style={{ background: 'none', border: `1px solid ${T.border}`, borderRadius: 8, padding: '8px 12px', fontSize: 12, fontWeight: 600, color: T.muted, cursor: bulkLoading ? 'not-allowed' : 'pointer', fontFamily: 'DM Sans, sans-serif' }}>
              ⏭ Skip
            </button>
          )}
          <button onClick={() => bulkApply('rejected')} disabled={bulkLoading}
            style={{ background: 'none', border: '1px solid #EF444440', borderRadius: 8, padding: '8px 12px', fontSize: 12, fontWeight: 600, color: '#EF4444', cursor: bulkLoading ? 'not-allowed' : 'pointer', fontFamily: 'DM Sans, sans-serif' }}>
            ✕ Reject
          </button>
        </div>
      )}

      {showImport && (
        <ImportModal
          dark={dark}
          onClose={() => setShowImport(false)}
          onSuccess={() => triggerRefresh?.()}
        />
      )}
    </div>
  )
}
