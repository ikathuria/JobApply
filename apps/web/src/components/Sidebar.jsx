// Sidebar — warm paper redesign, CSS-var based

function IconLayers() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 5.5L8 2.5L14 5.5L8 8.5L2 5.5Z" />
      <path d="M2 9L8 12L14 9" />
      <path d="M2 11.5L8 14.5L14 11.5" />
    </svg>
  )
}
function IconChart() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
      <rect x="2"  y="8.5" width="2.5" height="5" rx="1" opacity="0.85" />
      <rect x="6.75" y="5.5" width="2.5" height="8" rx="1" />
      <rect x="11.5" y="3"   width="2.5" height="10.5" rx="1" opacity="0.85" />
    </svg>
  )
}
function IconGear() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <circle cx="8" cy="8" r="2.4" />
      <path d="M8 1.5V3M8 13V14.5M1.5 8H3M13 8H14.5M3.4 3.4L4.5 4.5M11.5 11.5L12.6 12.6M11.5 3.4L10.4 4.5M4.5 11.5L3.4 12.6" />
    </svg>
  )
}
function IconMail() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <rect x="1.5" y="3" width="13" height="10" rx="1.5" />
      <path d="M2 4L8 8.5L14 4" />
    </svg>
  )
}
function IconCalendar() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="3" width="12" height="11" rx="1.5" />
      <path d="M2 6.5H14M5.5 1.5V4M10.5 1.5V4" />
    </svg>
  )
}
function IconPrep() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M8 1.8A4.2 4.2 0 0 0 5.4 9.2c0.5 0.5 0.85 1 0.95 1.8h3.3c0.1-0.8 0.45-1.3 0.95-1.8A4.2 4.2 0 0 0 8 1.8Z" />
      <path d="M6.3 13h3.4M6.8 14.5h2.4" />
    </svg>
  )
}

// Two-tier nav (M28): the daily apply-loop screens sit in the prominent
// "Workspace" group; everything else demotes to a lighter "Tools" group.
const PRIMARY_NAV = [
  { id: 'pipeline', label: 'Pipeline', Icon: IconLayers, hasBadge: true },
]
const TOOLS_NAV = [
  { id: 'outreach',  label: 'Outreach',       Icon: IconMail },
  { id: 'timeline',  label: 'Timeline',       Icon: IconCalendar },
  { id: 'prep',      label: 'Interview prep',  Icon: IconPrep },
  { id: 'analytics', label: 'Analytics',      Icon: IconChart },
  { id: 'settings',  label: 'Settings',       Icon: IconGear },
]

const STATUS_ROWS = [
  { key: 'new',       label: 'New' },
  { key: 'ready',     label: 'Ready' },
  { key: 'approved',  label: 'Approved' },
  { key: 'applied',   label: 'Applied' },
  { key: 'oa',        label: 'OA' },
  { key: 'interview', label: 'Interview' },
  { key: 'offer',     label: 'Offer' },
]

function NavButton({ item, active, collapsed, badge, onClick }) {
  const { label, Icon } = item
  return (
    <button className={`nav-item${active ? ' active' : ''}`} onClick={onClick}
      title={collapsed ? label : undefined} aria-label={label} aria-current={active ? 'page' : undefined}>
      <div className="nav-icon"><Icon /></div>
      {!collapsed && <span style={{ flex: 1 }}>{label}</span>}
      {!collapsed && badge > 0 && <span className="nav-count">{badge}</span>}
    </button>
  )
}

export default function Sidebar({ screen, setScreen, dark, setDark, stats, collapsed, onToggleCollapsed }) {
  const goTo = (id) => setScreen(id)

  const totalApplied = stats
    ? ((stats.applied ?? 0) + (stats.oa ?? 0) + (stats.interview ?? 0) + (stats.offer ?? 0) + (stats.rejected ?? 0))
    : 0
  const pct = stats?.total ? Math.round((totalApplied / stats.total) * 100) : 0

  return (
    <aside className={`sidebar${collapsed ? ' collapsed' : ''}`}>
      {/* Logo */}
      <div className="sidebar-logo">
        <div className="sidebar-logo-mark">J</div>
        {!collapsed && (
          <div className="col" style={{ lineHeight: 1.15 }}>
            <span style={{ fontFamily: 'var(--font-display)', fontSize: 17, fontWeight: 700, color: 'var(--side-ink)' }}>JobApply</span>
            <span className="mono" style={{ fontSize: 11, color: 'var(--side-muted)' }}>ledger · 2026–27</span>
          </div>
        )}
      </div>

      {/* Primary nav — the daily apply loop */}
      {!collapsed && <div className="eyebrow">Workspace</div>}
      <div className="col gap-1 side-nav">
        {PRIMARY_NAV.map(item => (
          <NavButton
            key={item.id}
            item={item}
            active={screen === item.id}
            collapsed={collapsed}
            badge={item.hasBadge ? (stats?.ready ?? 0) : 0}
            onClick={() => goTo(item.id)}
          />
        ))}
      </div>

      {/* Secondary nav — occasional tools */}
      {!collapsed
        ? <div className="eyebrow" style={{ marginTop: 14 }}>Tools</div>
        : <div className="sidebar-divider" style={{ margin: '8px 0' }} />}
      <div className="col gap-1 side-nav">
        {TOOLS_NAV.map(item => (
          <NavButton
            key={item.id}
            item={item}
            active={screen === item.id}
            collapsed={collapsed}
            badge={0}
            onClick={() => goTo(item.id)}
          />
        ))}
      </div>

      {/* Pipeline stats */}
      {!collapsed && (<>
        <div className="sidebar-section-gap" />
        <div className="eyebrow">Funnel</div>
        <div className="col">
          {STATUS_ROWS.map(({ key, label }) => (
            <div key={key} className="status-row">
              <span>{label}</span>
              <span className="mono tabular" style={{ fontSize: 12, color: 'var(--side-ink)' }}>
                {stats?.[key] ?? 0}
              </span>
            </div>
          ))}

          {/* Progress bar */}
          {stats && (
            <div style={{ margin: '8px 10px 0', paddingTop: 10, borderTop: '1px solid var(--side-line)' }}>
              <div className="row" style={{ justifyContent: 'space-between', marginBottom: 6, fontSize: 12 }}>
                <span style={{ color: 'var(--side-muted)' }}>Submitted</span>
                <span className="mono tabular" style={{ color: 'var(--side-ink)' }}>{totalApplied} / {(stats.total ?? 0).toLocaleString()}</span>
              </div>
              <div style={{ height: 4, background: 'var(--side-line)' }}>
                <div className="gb-fill" style={{ width: `${pct}%`, height: '100%', background: 'var(--accent)' }} />
              </div>
            </div>
          )}
        </div>
      </>)}

      <div className="grow" />

      {/* Footer */}
      <div className="sidebar-divider" />

      {/* Collapse toggle */}
      <button
        onClick={onToggleCollapsed}
        aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        className="nav-item side-collapse"
        style={{ justifyContent: collapsed ? 'center' : 'flex-start' }}
      >
        <span style={{ fontSize: 13 }}>{collapsed ? '»' : '« Collapse'}</span>
      </button>

      {/* Theme toggle */}
      <div className="row side-theme" style={{ padding: '4px 6px 8px', justifyContent: collapsed ? 'center' : 'space-between' }}>
        {!collapsed && <span style={{ fontSize: 12, color: 'var(--side-muted)' }}>{dark ? 'Dark' : 'Light'} mode</span>}
        <button
          onClick={() => setDark(!dark)}
          className="theme-toggle"
          aria-label={dark ? 'Switch to light mode' : 'Switch to dark mode'}
          style={{ background: dark ? 'var(--side-active)' : 'var(--side-line)' }}
        >
          <div className="theme-knob" style={{ left: dark ? 19 : 3 }} />
        </button>
      </div>

      {/* User */}
      <div className="user-chip">
        <div className="user-avatar">IK</div>
        {!collapsed && (
          <div className="col" style={{ lineHeight: 1.2, minWidth: 0 }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--side-ink)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>Ishani Kathuria</span>
            <span className="mono" style={{ fontSize: 11, color: 'var(--side-muted)' }}>new grad · May 2027</span>
          </div>
        )}
      </div>
    </aside>
  )
}
