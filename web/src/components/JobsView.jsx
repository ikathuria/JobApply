import { useState, useMemo, useEffect, useContext } from 'react'
import { ThemeCtx } from './ThemeContext.jsx'
import { DARK, LIGHT } from '../theme.js'
import { Input, Btn, EmptyState, Spinner } from './ui/index.jsx'
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
      <div style={{ padding: '12px 24px', flexShrink: 0, display: 'flex', gap: 10, alignItems: 'center' }}>
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
      </div>

      {/* Job list */}
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
