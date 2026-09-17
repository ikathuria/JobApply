import { useState } from 'react'
import { DARK, LIGHT } from '../../theme.js'
import { Btn } from '../ui/index.jsx'
import { api } from '../../api.js'

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

export default function ImportModal({ dark, onClose, onSuccess }) {
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
  const inp     = { width:'100%', padding:'8px 12px', borderRadius:8, border:`1px solid ${T.border}`, background: T.card, color:T.text, fontSize:13, fontFamily:'Inter, system-ui, sans-serif', outline:'none', boxSizing:'border-box' }
  const tabBtn  = active => ({ padding:'6px 16px', borderRadius:6, border:'none', cursor:'pointer', fontFamily:'Inter, system-ui, sans-serif', fontSize:12, fontWeight: active ? 700 : 500, background: active ? T.accent : 'transparent', color: active ? '#fff' : T.muted, transition:'all 0.12s' })

  return (
    <div style={overlay} onClick={e => e.target === e.currentTarget && onClose()}>
      <div style={modal}>
        {/* Header */}
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:18 }}>
          <div style={{ fontSize:16, fontWeight:800, color:T.text }}>Import Job</div>
          <button onClick={onClose} style={{ background:'none', border:'none', color:T.muted, fontSize:20, cursor:'pointer', lineHeight:1 }}>×</button>
        </div>

        {/* Tab switcher */}
        <div style={{ display:'flex', gap:4, marginBottom:20, background: T.surface, borderRadius:8, padding:4 }}>
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
          <div style={{ background: T.surface, border:`1px solid ${T.border}`, borderRadius:8, padding:'12px 14px', marginBottom:16, fontSize:12, color:T.muted, lineHeight:1.6 }}>
            Expected columns: <code style={{ color:T.text }}>{CSV_COLUMNS.join(', ')}</code><br/>
            Only <strong>title</strong> and <strong>company</strong> are required.{' '}
            <span style={{ color:T.accent, cursor:'pointer', textDecoration:'underline' }} onClick={downloadTemplate}>Download template ↓</span>
          </div>

          {/* File picker */}
          <div style={{ marginBottom:14 }}>
            <div style={lbl}>Select CSV file</div>
            <input type="file" accept=".csv,text/csv" onChange={onFileChange}
              style={{ fontSize:12, color:T.text, fontFamily:'Inter, system-ui, sans-serif' }} />
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
