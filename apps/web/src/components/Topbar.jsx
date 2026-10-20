const TITLES = {
  pipeline:  'Pipeline',
  outreach:  'Outreach',
  timeline:  'Recruiting timeline',
  prep:      'Interview prep',
  analytics: 'Analytics',
  settings:  'Settings',
}

export default function Topbar({ screen, stats }) {
  const applied = stats
    ? (stats.applied ?? 0) + (stats.oa ?? 0) + (stats.interview ?? 0) + (stats.offer ?? 0) + (stats.rejected ?? 0)
    : null
  const kpis = stats ? [
    ['new', stats.new], ['ready', stats.ready], ['applied', applied],
    ['OA', stats.oa], ['interview', stats.interview],
  ] : []
  const today = new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })
  return (
    <header className="topbar">
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, minWidth: 0 }}>
        <h1 className="topbar-title">{TITLES[screen] ?? screen}</h1>
        <span className="route-pill">{today}</span>
      </div>
      {screen === 'pipeline' && kpis.length > 0 && (
        <dl className="topbar-kpis">
          {kpis.map(([label, value]) => (
            <div key={label}><dd>{value ?? 0}</dd><dt>{label}</dt></div>
          ))}
        </dl>
      )}
    </header>
  )
}
