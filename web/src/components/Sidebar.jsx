import { useContext } from 'react'
import { ThemeCtx } from './ThemeContext.jsx'
import { DARK, LIGHT } from '../theme.js'

export default function Sidebar({ screen, setScreen, dark, setDark, stats }) {
  const T = dark ? DARK : LIGHT

  const navItems = [
    { id: 'jobs',      icon: '⬡', label: 'Jobs',      badge: stats?.ready ?? 0 },
    { id: 'analytics', icon: '◈', label: 'Analytics',  badge: null },
    { id: 'settings',  icon: '◎', label: 'Settings',   badge: null },
  ]

  const pipeline = [
    { label: 'New',       value: stats?.new       ?? 0, color: '#6B7280' },
    { label: 'Ready',     value: stats?.ready     ?? 0, color: '#22C55E' },
    { label: 'Applied',   value: stats?.applied   ?? 0, color: '#3B82F6' },
    { label: 'OA',        value: stats?.oa        ?? 0, color: '#F59E0B' },
    { label: 'Interview', value: stats?.interview  ?? 0, color: '#EC4899' },
    { label: 'Offer',     value: stats?.offer     ?? 0, color: '#10B981' },
  ]

  const total     = stats?.total     ?? 0
  const submitted = (stats?.applied ?? 0) + (stats?.oa ?? 0) + (stats?.interview ?? 0) + (stats?.offer ?? 0)
  const pct = total ? Math.round((submitted / total) * 100) : 0

  return (
    <div style={{
      width: 220, flexShrink: 0, height: '100vh', display: 'flex', flexDirection: 'column',
      background: T.surface, borderRight: `1px solid ${T.border}`,
      position: 'sticky', top: 0,
    }}>
      {/* Logo */}
      <div style={{ padding: '20px 20px 16px', borderBottom: `1px solid ${T.border}` }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 32, height: 32, borderRadius: 8, background: T.accent,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 16, fontWeight: 900, color: '#fff', letterSpacing: -1,
          }}>J</div>
          <div>
            <div style={{ fontWeight: 800, fontSize: 15, color: T.text, letterSpacing: '-0.02em' }}>JobApply</div>
            <div style={{ fontSize: 10, color: T.muted, fontWeight: 500 }}>AI/ML · Summer 2026</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav style={{ padding: '12px 10px', display: 'flex', flexDirection: 'column', gap: 2 }}>
        {navItems.map(item => {
          const active = screen === item.id
          return (
            <button key={item.id} onClick={() => setScreen(item.id)}
              style={{
                display: 'flex', alignItems: 'center', gap: 10, padding: '9px 12px',
                borderRadius: 8, border: 'none', cursor: 'pointer', textAlign: 'left',
                background: active ? T.accentBg : 'transparent',
                color: active ? T.accent : T.muted,
                fontFamily: 'DM Sans, sans-serif', fontSize: 13, fontWeight: active ? 700 : 500,
                transition: 'all 0.15s', width: '100%',
              }}>
              <span style={{ fontSize: 16, width: 18, textAlign: 'center' }}>{item.icon}</span>
              <span style={{ flex: 1 }}>{item.label}</span>
              {item.badge > 0 && (
                <span style={{
                  background: '#22C55E', color: '#fff', fontSize: 10, fontWeight: 800,
                  borderRadius: 10, padding: '1px 7px', minWidth: 20, textAlign: 'center',
                }}>{item.badge}</span>
              )}
            </button>
          )
        })}
      </nav>

      <div style={{ flex: 1 }} />

      {/* Pipeline mini-stats */}
      <div style={{ padding: '16px 20px', borderTop: `1px solid ${T.border}` }}>
        <div style={{ fontSize: 10, fontWeight: 700, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10 }}>
          Pipeline
        </div>
        {pipeline.map(p => (
          <div key={p.label} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
            <div style={{ width: 7, height: 7, borderRadius: '50%', background: p.color, flexShrink: 0 }} />
            <div style={{ fontSize: 12, color: T.muted, flex: 1 }}>{p.label}</div>
            <div style={{ fontSize: 12, fontWeight: 700, color: T.text, fontFamily: 'JetBrains Mono, monospace' }}>{p.value}</div>
          </div>
        ))}

        {/* Progress bar */}
        <div style={{ marginTop: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
            <span style={{ fontSize: 11, color: T.muted }}>Submitted</span>
            <span style={{ fontSize: 11, fontWeight: 700, color: T.text, fontFamily: 'JetBrains Mono, monospace' }}>{pct}%</span>
          </div>
          <div style={{ height: 5, borderRadius: 5, background: dark ? '#252538' : '#E2E2EE', overflow: 'hidden' }}>
            <div style={{ width: `${pct}%`, height: '100%', background: `linear-gradient(90deg, ${T.accent}, #22C55E)`, borderRadius: 5 }} />
          </div>
          <div style={{ fontSize: 10, color: T.muted, marginTop: 4 }}>{submitted} of {total} jobs</div>
        </div>
      </div>

      {/* Theme toggle */}
      <div style={{ padding: '12px 20px', borderTop: `1px solid ${T.border}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: 12, color: T.muted }}>{dark ? 'Dark' : 'Light'} mode</span>
        <button onClick={() => setDark(!dark)} style={{
          width: 36, height: 20, borderRadius: 10, border: 'none', cursor: 'pointer',
          background: dark ? T.accent : '#D1D5DB', position: 'relative', transition: 'background 0.2s',
        }}>
          <div style={{
            width: 14, height: 14, borderRadius: '50%', background: '#fff',
            position: 'absolute', top: 3, left: dark ? 19 : 3, transition: 'left 0.2s',
            boxShadow: '0 1px 3px rgba(0,0,0,0.3)',
          }} />
        </button>
      </div>

      {/* User */}
      <div style={{ padding: '12px 20px', borderTop: `1px solid ${T.border}`, display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{
          width: 28, height: 28, borderRadius: '50%',
          background: `linear-gradient(135deg, ${T.accent}, #EC4899)`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 12, fontWeight: 800, color: '#fff',
        }}>IK</div>
        <div>
          <div style={{ fontSize: 12, fontWeight: 700, color: T.text }}>Ishani Kathuria</div>
          <div style={{ fontSize: 10, color: T.muted }}>Summer 2026</div>
        </div>
      </div>
    </div>
  )
}
