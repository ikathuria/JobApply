// Sidebar — warm paper redesign, CSS-var based

function IconHome() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
      <path d="M8 1.5L1.5 6.8V14.5H5.5V9.5H10.5V14.5H14.5V6.8L8 1.5Z" />
    </svg>
  )
}
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

const NAV = [
  { id: 'dashboard', label: 'Dashboard',  Icon: IconHome,   tone: 'blue'   },
  { id: 'jobs',      label: 'Jobs',       Icon: IconLayers, tone: 'purple', hasBadge: true },
  { id: 'analytics', label: 'Analytics',  Icon: IconChart,  tone: 'teal'   },
  { id: 'settings',  label: 'Settings',   Icon: IconGear,   tone: null     },
]

const STATUS_ROWS = [
  { key: 'new',       label: 'New',       color: '#5B88B5' },
  { key: 'ready',     label: 'Ready',     color: '#6A9068' },
  { key: 'approved',  label: 'Approved',  color: '#8B7BB8' },
  { key: 'applied',   label: 'Applied',   color: '#D17847' },
  { key: 'interview', label: 'Interview', color: '#C28098' },
  { key: 'offer',     label: 'Offer',     color: '#5A9DA8' },
]

export default function Sidebar({ screen, setScreen, dark, setDark, stats }) {
  const goTo = (id) => setScreen(id)

  const totalApplied = stats
    ? ((stats.applied ?? 0) + (stats.oa ?? 0) + (stats.interview ?? 0) + (stats.offer ?? 0) + (stats.rejected ?? 0))
    : 0
  const pct = stats?.total ? Math.round((totalApplied / stats.total) * 100) : 0

  return (
    <aside className="sidebar">
      {/* Logo */}
      <div className="sidebar-logo">
        <div className="sidebar-logo-mark">J</div>
        <div className="col" style={{ lineHeight: 1.15 }}>
          <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--ink)', letterSpacing: '-0.02em' }}>JobApply</span>
          <span className="mono" style={{ fontSize: 9.5, color: 'var(--ink-3)', letterSpacing: '0.13em', textTransform: 'uppercase' }}>AI · 2026</span>
        </div>
      </div>

      {/* Nav */}
      <div className="eyebrow">Workspace</div>
      <div className="col gap-1">
        {NAV.map(({ id, label, Icon, tone, hasBadge }) => {
          const active = screen === id
          const badge = hasBadge ? (stats?.ready ?? 0) : null
          const toneColor  = tone ? `var(--${tone})`      : 'var(--paper-3)'
          const toneInk    = tone ? `var(--${tone}-ink)`  : 'var(--ink-3)'
          return (
            <button key={id} className={`nav-item${active ? ' active' : ''}`} onClick={() => goTo(id)}>
              <div
                className="nav-icon"
                style={{
                  background: active ? toneColor : 'var(--paper-3)',
                  color:      active ? toneInk   : 'var(--ink-3)',
                }}
              >
                <Icon />
              </div>
              <span style={{ flex: 1 }}>{label}</span>
              {badge > 0 && (
                <span
                  className="nav-count"
                  style={{
                    background: active ? toneColor        : 'var(--paper-3)',
                    color:      active ? toneInk          : 'var(--ink-3)',
                  }}
                >
                  {badge}
                </span>
              )}
            </button>
          )
        })}
      </div>

      {/* Pipeline stats */}
      <div className="sidebar-section-gap" />
      <div className="eyebrow">Pipeline</div>
      <div className="col">
        {STATUS_ROWS.map(({ key, label, color }) => (
          <div key={key} className="status-row">
            <div className="row gap-2">
              <div
                className="status-dot"
                style={{ background: color, borderColor: color }}
              />
              <span>{label}</span>
            </div>
            <span className="mono tabular" style={{ fontSize: 11, color: 'var(--ink-3)' }}>
              {stats?.[key] ?? 0}
            </span>
          </div>
        ))}

        {/* Progress bar */}
        {stats && (
          <div style={{ padding: '10px 10px 4px' }}>
            <div className="row" style={{ justifyContent: 'space-between', marginBottom: 5 }}>
              <span style={{ fontSize: 11, color: 'var(--ink-3)' }}>Submitted</span>
              <span className="mono tabular" style={{ fontSize: 11, color: 'var(--ink-2)', fontWeight: 700 }}>{pct}%</span>
            </div>
            <div style={{ height: 5, borderRadius: 5, background: 'var(--paper-3)', overflow: 'hidden' }}>
              <div style={{
                width: `${pct}%`, height: '100%', borderRadius: 5,
                background: `linear-gradient(90deg, var(--accent), var(--ok))`,
                transition: 'width 0.5s ease',
              }} />
            </div>
            <div style={{ fontSize: 10, color: 'var(--ink-3)', marginTop: 4 }}>
              {totalApplied} of {stats.total ?? 0} jobs
            </div>
          </div>
        )}
      </div>

      <div className="grow" />

      {/* Footer */}
      <div className="sidebar-divider" />

      {/* Theme toggle */}
      <div className="row" style={{ padding: '4px 6px 8px', justifyContent: 'space-between' }}>
        <span style={{ fontSize: 11.5, color: 'var(--ink-3)' }}>{dark ? 'Dark' : 'Light'} mode</span>
        <button
          onClick={() => setDark(!dark)}
          className="theme-toggle"
          style={{ background: dark ? 'var(--accent)' : 'var(--paper-4)' }}
        >
          <div className="theme-knob" style={{ left: dark ? 19 : 3 }} />
        </button>
      </div>

      {/* User */}
      <div className="user-chip">
        <div className="user-avatar">IK</div>
        <div className="col" style={{ lineHeight: 1.2, minWidth: 0 }}>
          <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--ink)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>Ishani Kathuria</span>
          <span style={{ fontSize: 10, color: 'var(--ink-3)' }}>Summer 2026</span>
        </div>
      </div>
    </aside>
  )
}
