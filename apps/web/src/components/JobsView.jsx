import { useState, useMemo, useEffect, useContext } from 'react'
import { ThemeCtx } from './ThemeContext.jsx'
import { DARK, LIGHT } from '../theme.js'
import { EmptyState, Spinner } from './ui/index.jsx'
import JobRow from './JobRow.jsx'
import { api } from '../api.js'
import ImportModal from './pipeline/ImportModal.jsx'
import FocusQueue from './pipeline/FocusQueue.jsx'
import ReviewDeck from './pipeline/ReviewDeck.jsx'
import ApprovedDeck from './pipeline/ApprovedDeck.jsx'
import { TABS, normalizeLocation } from './pipeline/constants.js'
export default function JobsView({ onSelectJob, selectedJob, tab, setTab, stats, onRefresh, triggerRefresh, initialSearch }) {
  const { dark } = useContext(ThemeCtx)
  const T = dark ? DARK : LIGHT

  const [search, setSearch]         = useState('')
  const [sort, setSort]             = useState('score')
  const [reviewMode, setReviewMode] = useState('deck')
  const [minScore, setMinScore]     = useState(0)
  const [locationFilter, setLocationFilter] = useState('')
  const [sourceFilter, setSourceFilter]     = useState('')
  const [dateFrom, setDateFrom]             = useState('')
  const [dateTo, setDateTo]                 = useState('')
  const [sponsorsOnly, setSponsorsOnly]     = useState(false)
  const [jobs, setJobs]             = useState([])
  const [focus, setFocus]           = useState([])
  const [focusOpen, setFocusOpen]   = useState(false)
  const [showFilters, setShowFilters] = useState(false)
  const [loading, setLoading]       = useState(true)
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

  // Client-side filter (search + location + source + date range)
  const filteredJobs = useMemo(() => {
    return jobs.filter(j => {
      if (search) {
        const q = search.toLowerCase()
        const hit = (j.title || '').toLowerCase().includes(q) ||
          (j.company || '').toLowerCase().includes(q) ||
          (j.location || '').toLowerCase().includes(q)
        if (!hit) return false
      }
      if (locationFilter && normalizeLocation(j.location) !== locationFilter) return false
      if (sourceFilter && j.source !== sourceFilter) return false
      if (dateFrom && j.date_applied && j.date_applied < dateFrom) return false
      if (dateTo && j.date_applied && j.date_applied > dateTo) return false
      if (sponsorsOnly && !j.known_sponsor) return false
      return true
    })
  }, [jobs, search, locationFilter, sourceFilter, dateFrom, dateTo, sponsorsOnly])

  useEffect(() => {
    setReviewMode(tab === 'ready' || tab === 'approved' ? 'deck' : 'list')
  }, [tab])

  // Reset all filters when switching tabs
  useEffect(() => {
    setSearch('')
    setLocationFilter('')
    setSourceFilter('')
    setDateFrom('')
    setDateTo('')
    setSponsorsOnly(false)
  }, [tab])

  // Deep-link from the Timeline view: seed the search with a company name.
  // Defined after the tab-reset effect so it wins when both fire on the same
  // navigation. Empty values are ignored so normal navigation isn't clobbered.
  useEffect(() => {
    if (initialSearch) setSearch(initialSearch)
  }, [initialSearch])

  // Unique sorted location options derived from current tab's jobs
  const locationOptions = useMemo(() => {
    const seen = new Set()
    const opts = []
    for (const j of jobs) {
      const n = normalizeLocation(j.location)
      if (n && !seen.has(n)) { seen.add(n); opts.push(n) }
    }
    return opts.sort()
  }, [jobs])

  // Unique sorted source options derived from current tab's jobs
  const sourceOptions = useMemo(() => {
    const seen = new Set()
    const opts = []
    for (const j of jobs) {
      if (j.source && !seen.has(j.source)) { seen.add(j.source); opts.push(j.source) }
    }
    return opts.sort()
  }, [jobs])

  const hasFilters = !!(search || locationFilter || sourceFilter || dateFrom || dateTo || minScore > 0 || sponsorsOnly)
  // Only the "advanced" fields (row 2) count toward the Filters-button badge —
  // search lives in the always-visible row and isn't part of that disclosure.
  const advancedFilterCount = [minScore > 0, !!locationFilter, !!sourceFilter, !!dateFrom, !!dateTo, sponsorsOnly].filter(Boolean).length
  function clearFilters() {
    setSearch('')
    setLocationFilter('')
    setSourceFilter('')
    setDateFrom('')
    setDateTo('')
    setMinScore(0)
    setSponsorsOnly(false)
  }

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
        <FocusQueue focus={focus} onSelectJob={onSelectJob} setTab={setTab} dark={dark}
          open={focusOpen} onToggle={() => setFocusOpen(o => !o)} />
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
                fontFamily: 'Inter, system-ui, sans-serif', fontSize: 12,
                fontWeight: active ? 700 : 500,
                color: active ? T.accent : T.muted,
                borderBottom: active ? `2px solid ${T.accent}` : '2px solid transparent',
                display: 'flex', alignItems: 'center', gap: 6, transition: 'all 0.12s',
              }}>
              {t.label}
              {count > 0 && (
                <span style={{
                  background: active ? T.accent : T.border,
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
          cursor: 'pointer', fontFamily: 'Inter, system-ui, sans-serif', marginBottom: 2,
        }} onClick={() => setShowImport(true)}>+ Import</button>
      </div>

      {/* Filter bar */}
      <div className="filter-bar">
        {/* Row 1: search + scope tag + count + deck toggle */}
        <div className="filter-row">
          <div className="filter-search">
            <span className="filter-search-icon">⌕</span>
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder={`Search ${TABS.find(t => t.id === tab)?.label ?? tab} jobs…`}
            />
          </div>
          <span className="filter-scope-tag">{TABS.find(t => t.id === tab)?.label ?? tab}</span>
          <span className="filter-count">{filteredJobs.length} {filteredJobs.length === 1 ? 'job' : 'jobs'}</span>
          <button
            onClick={() => setShowFilters(v => !v)}
            aria-expanded={showFilters}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '6px 12px', borderRadius: 6,
              border: `1px solid ${showFilters || advancedFilterCount > 0 ? T.accent : T.border}`,
              background: showFilters ? T.accentBg : 'transparent',
              color: showFilters || advancedFilterCount > 0 ? T.accent : T.muted,
              fontSize: 11, fontWeight: 700, cursor: 'pointer',
              fontFamily: 'Inter, system-ui, sans-serif',
            }}>
            Filters
            {advancedFilterCount > 0 && (
              <span style={{
                background: T.accent, color: '#fff', fontSize: 10, fontWeight: 800,
                borderRadius: 10, padding: '0 6px', lineHeight: '15px',
              }}>{advancedFilterCount}</span>
            )}
          </button>
          {(tab === 'ready' || tab === 'approved') && (
            <div style={{ marginLeft: 'auto', display: 'flex', gap: 4, background: T.surface, borderRadius: 8, padding: 4 }}>
              {['deck', 'list'].map(mode => (
                <button key={mode} onClick={() => setReviewMode(mode)} style={{
                  padding: '7px 12px', border: 'none', borderRadius: 6, cursor: 'pointer',
                  background: reviewMode === mode ? T.accent : 'transparent',
                  color: reviewMode === mode ? '#fff' : T.muted,
                  fontSize: 12, fontWeight: 800, fontFamily: 'Inter, system-ui, sans-serif',
                }}>
                  {mode === 'deck' ? (tab === 'approved' ? 'Apply deck' : 'Review deck') : 'List'}
                </button>
              ))}
            </div>
          )}
        </div>
        {/* Row 2: sort + score + location + source + dates + clear — behind "Filters" */}
        {showFilters && (
          <div className="filter-row">
            <select className="filter-select" value={sort} onChange={e => setSort(e.target.value)}>
              <option value="score">Score ↓</option>
              <option value="company">Company A–Z</option>
              <option value="starred">Starred first</option>
            </select>

            <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
              <span style={{ fontSize: 11, color: T.muted, whiteSpace: 'nowrap' }}>Score ≥</span>
              <input type="range" min={0} max={1} step={0.05} value={minScore}
                onChange={e => setMinScore(parseFloat(e.target.value))}
                style={{ width: 72, accentColor: T.accent }} />
              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: T.text, width: 30 }}>
                {Math.round(minScore * 100)}%
              </span>
            </div>

            {locationOptions.length > 0 && (
              <select className="filter-select" value={locationFilter} onChange={e => setLocationFilter(e.target.value)}>
                <option value="">All locations</option>
                {locationOptions.map(loc => <option key={loc} value={loc}>{loc}</option>)}
              </select>
            )}

            {sourceOptions.length > 1 && (
              <select className="filter-select" value={sourceFilter} onChange={e => setSourceFilter(e.target.value)}>
                <option value="">All sources</option>
                {sourceOptions.map(src => <option key={src} value={src}>{src}</option>)}
              </select>
            )}

            {(tab === 'applied' || tab === 'all') && (<>
              <input type="date" className="filter-date" value={dateFrom}
                onChange={e => setDateFrom(e.target.value)} title="Applied from" />
              <input type="date" className="filter-date" value={dateTo}
                onChange={e => setDateTo(e.target.value)} title="Applied to" />
            </>)}

            <button
              onClick={() => setSponsorsOnly(v => !v)}
              aria-pressed={sponsorsOnly}
              title="Show only companies that are known H-1B sponsors"
              style={{
                display: 'flex', alignItems: 'center', gap: 6, padding: '6px 12px',
                borderRadius: 6, cursor: 'pointer', fontSize: 11, fontWeight: 700,
                fontFamily: 'Inter, system-ui, sans-serif',
                border: `1px solid ${sponsorsOnly ? T.success : T.border}`,
                background: sponsorsOnly ? `${T.success}1A` : 'transparent',
                color: sponsorsOnly ? T.success : T.muted,
              }}>
              {sponsorsOnly ? '✓ ' : ''}H-1B sponsors only
            </button>

            {hasFilters && (
              <button className="filter-clear" onClick={clearFilters}>Clear</button>
            )}
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
          background: T.card,
          borderTop: `2px solid ${T.accent}`,
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
              cursor: 'pointer', fontFamily: 'Inter, system-ui, sans-serif',
            }}>
              Select all {filteredJobs.length}
            </button>
          )}

          <div style={{ flex: 1 }} />

          {/* Tab-contextual primary actions */}
          {tab === 'ready' && (
            <button onClick={() => bulkApply('approved')} disabled={bulkLoading}
              style={{ background: '#8B7BB8', color: '#fff', border: 'none', borderRadius: 8, padding: '8px 16px', fontSize: 12, fontWeight: 700, cursor: bulkLoading ? 'not-allowed' : 'pointer', fontFamily: 'Inter, system-ui, sans-serif', opacity: bulkLoading ? 0.7 : 1 }}>
              {bulkLoading ? '…' : `✓ Approve (${selectedIds.size})`}
            </button>
          )}
          {tab === 'approved' && (
            <button onClick={() => bulkApply('applied')} disabled={bulkLoading}
              style={{ background: '#22C55E', color: '#fff', border: 'none', borderRadius: 8, padding: '8px 16px', fontSize: 12, fontWeight: 700, cursor: bulkLoading ? 'not-allowed' : 'pointer', fontFamily: 'Inter, system-ui, sans-serif', opacity: bulkLoading ? 0.7 : 1 }}>
              {bulkLoading ? '…' : `✓ Mark Applied (${selectedIds.size})`}
            </button>
          )}
          {tab === 'new' && (
            <button onClick={() => bulkApply('queued')} disabled={bulkLoading}
              style={{ background: T.accent, color: '#fff', border: 'none', borderRadius: 8, padding: '8px 16px', fontSize: 12, fontWeight: 700, cursor: bulkLoading ? 'not-allowed' : 'pointer', fontFamily: 'Inter, system-ui, sans-serif', opacity: bulkLoading ? 0.7 : 1 }}>
              {bulkLoading ? '…' : `✦ Tailor Queue (${selectedIds.size})`}
            </button>
          )}

          {/* Always available: skip + reject */}
          {['new', 'ready', 'approved', 'all'].includes(tab) && (
            <button onClick={() => bulkApply('skipped')} disabled={bulkLoading}
              style={{ background: 'none', border: `1px solid ${T.border}`, borderRadius: 8, padding: '8px 12px', fontSize: 12, fontWeight: 600, color: T.muted, cursor: bulkLoading ? 'not-allowed' : 'pointer', fontFamily: 'Inter, system-ui, sans-serif' }}>
              ⏭ Skip
            </button>
          )}
          <button onClick={() => bulkApply('rejected')} disabled={bulkLoading}
            style={{ background: 'none', border: '1px solid #EF444440', borderRadius: 8, padding: '8px 12px', fontSize: 12, fontWeight: 600, color: '#EF4444', cursor: bulkLoading ? 'not-allowed' : 'pointer', fontFamily: 'Inter, system-ui, sans-serif' }}>
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
