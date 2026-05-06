export default function Topbar({ screen }) {
  const titles = {
    dashboard: 'Command Center',
    jobs:      'Job Pipeline',
    analytics: 'Analytics',
    settings:  'Settings',
  }
  return (
    <header className="topbar">
      <span className="topbar-title">{titles[screen] ?? screen}</span>
      <span className="route-pill">{screen.toUpperCase()}</span>
    </header>
  )
}
