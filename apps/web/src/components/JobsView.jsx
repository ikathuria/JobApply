import { useState, useMemo, useEffect, useContext } from 'react'
import { ThemeCtx } from './ThemeContext.jsx'
import { DARK, LIGHT, alpha } from '../theme.js'
import { EmptyState, Spinner } from './ui/index.jsx'
import JobRow, { JobListHeader } from './JobRow.jsx'
import { api } from '../api.js'
import ImportModal from './pipeline/ImportModal.jsx'
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
      {/* Tab bar */}
      <div className="pipe-controls">
        <div className="pipe-tabs">
        {TABS.map(t => {
          const active = tab === t.id
          const count  = tabCount(t.id)
          return (
            <button key={t.id} aria-pressed={active} onClick={() => setTab(t.id)}
              style={{
                minHeight: 42, padding: '10px 12px', border: 'none', cursor: 'pointer',
                borderRadius: 0, background: 'transparent',
                fontFamily: 'var(--font-text)', fontSize: 13,
                fontWeight: active ? 600 : 500,
                color: active ? T.text : T.muted,
                borderBottom: active ? `3px solid ${T.accent}` : '3px solid transparent',
                display: 'flex', alignItems: 'center', gap: 6, whiteSpace: 'nowrap',
                transition: 'color var(--dur-1) var(--ease)',
              }}>
              {t.label}
              {count > 0 && (
                <span style={{
                  fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 500,
                  color: active ? T.accent : T.muted, fontVariantNumeric: 'tabular-nums',
                }}>{count}</span>
              )}
            </button>
          )
        })}
        </div>
        <div className="pipe-tools">
          <div className="filter-search">
            <span className="filter-search-icon">⌕</span>
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder={`Search ${TABS.find(t => t.id === tab)?.label ?? tab} jobs…`}
            />
          </div>
          <span className="filter-count">{filteredJobs.length} {filteredJobs.length === 1 ? 'job' : 'jobs'}</span>
          <button
            onClick={() => setShowFilters(v => !v)}
            aria-expanded={showFilters}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              minHeight: 34, padding: '6px 12px', borderRadius: 2,
              border: `1px solid ${showFilters || advancedFilterCount > 0 ? T.accent : T.border}`,
              background: showFilters ? T.accentBg : T.surface,
              color: showFilters || advancedFilterCount > 0 ? T.accent : T.text2,
              fontSize: 12, fontWeight: 600, cursor: 'pointer',
              fontFamily: 'var(--font-text)',
            }}>
            Filters
            {advancedFilterCount > 0 && (
              <span style={{
                background: T.accent, color: 'var(--on-accent)', fontSize: 10, fontWeight: 800,
                borderRadius: 2, padding: '0 6px', lineHeight: '15px',
              }}>{advancedFilterCount}</span>
            )}
          </button>
          {(tab === 'ready' || tab === 'approved') && (
            <div style={{ display: 'flex', border: `1px solid ${T.border}`, borderRadius: 2 }}>
              {['deck', 'list'].map(mode => (
                <button key={mode} onClick={() => setReviewMode(mode)} aria-pressed={reviewMode === mode} style={{
                  minHeight: 32, padding: '6px 12px', border: 'none', borderRadius: 0, cursor: 'pointer',
                  background: reviewMode === mode ? T.accent : T.surface,
                  color: reviewMode === mode ? 'var(--on-accent)' : T.text2,
                  fontSize: 12, fontWeight: 600, fontFamily: 'var(--font-text)',
                }}>
                  {mode === 'deck' ? (tab === 'approved' ? 'Apply deck' : 'Review deck') : 'List'}
                </button>
              ))}
            </div>
          )}
          <button onClick={() => setShowImport(true)} style={{
            minHeight: 34, padding: '6px 12px', borderRadius: 2, border: `1px solid ${T.border}`,
            background: T.surface, color: T.text2, fontSize: 12, fontWeight: 600,
            cursor: 'pointer', fontFamily: 'var(--font-text)',
          }}>+ Import</button>
        </div>
      </div>

      {/* Advanced filters: sort + score + location + source + dates + clear */}
      {showFilters && (
        <div className="filter-bar">
          <div className="filter-row">
            <select className="filter-select" value={sort} onChange={e => setSort(e.target.value)}>
              <option value="score">Match ↓</option>
              <option value="ats">ATS ↓</option>
              <option value="company">Company A–Z</option>
              <option value="starred">Starred first</option>
            </select>

            <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
              <span style={{ fontSize: 11, color: T.muted, whiteSpace: 'nowrap' }}>Score ≥</span>
              <input type="range" min={0} max={1} step={0.05} value={minScore}
                onChange={e => setMinScore(parseFloat(e.target.value))}
                style={{ width: 72, accentColor: T.accent }} />
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: T.text, width: 30 }}>
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
                borderRadius: 2, cursor: 'pointer', fontSize: 11, fontWeight: 700,
                fontFamily: 'var(--font-text)',
                border: `1px solid ${sponsorsOnly ? T.success : T.border}`,
                background: sponsorsOnly ? `${alpha(T.success, 10)}` : 'transparent',
                color: sponsorsOnly ? T.success : T.muted,
              }}>
              {sponsorsOnly ? '✓ ' : ''}H-1B sponsors only
            </button>

            {hasFilters && (
              <button className="filter-clear" onClick={clearFilters}>Clear</button>
            )}
          </div>
        </div>
      )}

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
      <div className="gb-list" style={{ flex: 1, overflowY: 'auto', padding: '0 16px 24px', position: 'relative' }}>
        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}>
            <Spinner size={16} />
          </div>
        ) : filteredJobs.length === 0 ? (
          <EmptyState title="No jobs match these filters." sub="Lower the match slider or clear the search." />
        ) : (
          [<JobListHeader key="_h" />, ...filteredJobs.map(job => (
            <JobRow
              key={job.id}
              job={job}
              onSelect={onSelectJob}
              selected={selectedJob?.id === job.id}
              checked={selectedIds.has(job.id)}
              onCheck={toggleSelect}
              multiSelectMode={multiSelectMode}
            />
          ))]
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
          boxShadow: 'var(--shadow-float)',
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
              background: 'none', border: `1px solid ${T.border}`, borderRadius: 2,
              padding: '5px 10px', fontSize: 11, fontWeight: 600, color: T.muted,
              cursor: 'pointer', fontFamily: 'var(--font-text)',
            }}>
              Select all {filteredJobs.length}
            </button>
          )}

          <div style={{ flex: 1 }} />

          {/* Tab-contextual primary actions */}
          {tab === 'ready' && (
            <button onClick={() => bulkApply('approved')} disabled={bulkLoading}
              style={{ background: 'var(--accent)', color: 'var(--on-accent)', border: 'none', borderRadius: 2, padding: '8px 16px', fontSize: 12, fontWeight: 700, cursor: bulkLoading ? 'not-allowed' : 'pointer', fontFamily: 'var(--font-text)', opacity: bulkLoading ? 0.7 : 1 }}>
              {bulkLoading ? '…' : `✓ Approve (${selectedIds.size})`}
            </button>
          )}
          {tab === 'approved' && (
            <button onClick={() => bulkApply('applied')} disabled={bulkLoading}
              style={{ background: 'var(--ok)', color: 'var(--on-accent)', border: 'none', borderRadius: 2, padding: '8px 16px', fontSize: 12, fontWeight: 700, cursor: bulkLoading ? 'not-allowed' : 'pointer', fontFamily: 'var(--font-text)', opacity: bulkLoading ? 0.7 : 1 }}>
              {bulkLoading ? '…' : `✓ Mark Applied (${selectedIds.size})`}
            </button>
          )}
          {tab === 'new' && (
            <button onClick={() => bulkApply('queued')} disabled={bulkLoading}
              style={{ background: T.accent, color: 'var(--on-accent)', border: 'none', borderRadius: 2, padding: '8px 16px', fontSize: 12, fontWeight: 700, cursor: bulkLoading ? 'not-allowed' : 'pointer', fontFamily: 'var(--font-text)', opacity: bulkLoading ? 0.7 : 1 }}>
              {bulkLoading ? '…' : `Tailor ${selectedIds.size} jobs`}
            </button>
          )}

          {/* Always available: skip + reject */}
          {['new', 'ready', 'approved', 'all'].includes(tab) && (
            <button onClick={() => bulkApply('skipped')} disabled={bulkLoading}
              style={{ background: 'none', border: `1px solid ${T.border}`, borderRadius: 2, padding: '8px 12px', fontSize: 12, fontWeight: 600, color: T.muted, cursor: bulkLoading ? 'not-allowed' : 'pointer', fontFamily: 'var(--font-text)' }}>
              ⏭ Skip
            </button>
          )}
          <button onClick={() => bulkApply('rejected')} disabled={bulkLoading}
            style={{ background: 'none', border: '1px solid color-mix(in srgb, var(--bad) 25%, transparent)', borderRadius: 2, padding: '8px 12px', fontSize: 12, fontWeight: 600, color: 'var(--bad)', cursor: bulkLoading ? 'not-allowed' : 'pointer', fontFamily: 'var(--font-text)' }}>
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
