import { useContext } from 'react'
import { ThemeCtx } from './ThemeContext.jsx'
import { DARK, LIGHT } from '../theme.js'

export default function AnalyticsView({ stats }) {
  const { dark } = useContext(ThemeCtx)
  const T = dark ? DARK : LIGHT
  const s = stats || {}

  const funnel = [
    { label: 'Discovered',  value: s.total     ?? 0, color: '#6366F1' },
    { label: 'New',         value: s.new       ?? 0, color: '#6B7280' },
    { label: 'Tailored',    value: s.ready     ?? 0, color: '#22C55E' },
    { label: 'Applied',     value: s.applied   ?? 0, color: '#3B82F6' },
    { label: 'OA',          value: s.oa        ?? 0, color: '#F59E0B' },
    { label: 'Interview',   value: s.interview ?? 0, color: '#EC4899' },
    { label: 'Offer',       value: s.offer     ?? 0, color: '#10B981' },
  ]
  const maxVal = funnel[0].value || 1

  const safe = n => Math.max(n, 1)
  const conversionRows = [
    { from: 'Discovered → Applied', rate: ((s.applied / safe(s.total)) * 100).toFixed(1), color: '#3B82F6' },
    { from: 'Applied → OA',         rate: ((s.oa / safe(s.applied)) * 100).toFixed(1), color: '#F59E0B' },
    { from: 'OA → Interview',       rate: ((s.interview / safe(s.oa)) * 100).toFixed(1), color: '#EC4899' },
    { from: 'Interview → Offer',    rate: ((s.offer / safe(s.interview)) * 100).toFixed(1), color: '#10B981' },
  ]

  return (
    <div style={{ padding: '28px 32px', overflowY: 'auto', height: '100%' }}>
      <div style={{ fontSize: 20, fontWeight: 800, color: T.text, marginBottom: 4 }}>Pipeline Analytics</div>
      <div style={{ fontSize: 13, color: T.muted, marginBottom: 28 }}>Summer 2026 AI/ML Internship Search</div>

      {/* Top stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14, marginBottom: 28 }}>
        {[
          { label: 'Total Discovered', value: s.total     ?? 0, color: T.accent },
          { label: 'Applied',          value: s.applied   ?? 0, color: '#3B82F6' },
          { label: 'In Pipeline',      value: (s.oa ?? 0) + (s.interview ?? 0), color: '#EC4899' },
          { label: 'Offers',           value: s.offer     ?? 0, color: '#10B981' },
        ].map(st => (
          <div key={st.label} style={{ background: T.card, border: `1px solid ${T.border}`, borderRadius: 12, padding: '16px 20px' }}>
            <div style={{ fontSize: 28, fontWeight: 800, color: st.color, letterSpacing: '-0.03em' }}>{st.value}</div>
            <div style={{ fontSize: 11, fontWeight: 700, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.07em', marginTop: 4 }}>{st.label}</div>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 20, marginBottom: 20 }}>
        {/* Funnel */}
        <div style={{ background: T.card, border: `1px solid ${T.border}`, borderRadius: 12, padding: '20px 24px' }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: T.text, marginBottom: 20 }}>Application Funnel</div>
          {funnel.map((stage, i) => {
            const width = (stage.value / maxVal) * 100
            const prevVal = i > 0 ? funnel[i - 1].value : stage.value
            const dropPct = prevVal > 0 ? Math.round((1 - stage.value / prevVal) * 100) : 0
            return (
              <div key={stage.label} style={{ marginBottom: 10 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
                  <div style={{ fontSize: 11, color: T.muted, width: 76, flexShrink: 0 }}>{stage.label}</div>
                  <div style={{ flex: 1, height: 22, background: dark ? '#252538' : '#E8E8F4', borderRadius: 4, overflow: 'hidden' }}>
                    <div style={{ width: `${width}%`, height: '100%', background: stage.color, borderRadius: 4, display: 'flex', alignItems: 'center', paddingLeft: 8, transition: 'width 0.6s ease', minWidth: stage.value > 0 ? 28 : 0 }}>
                      <span style={{ fontSize: 10, fontWeight: 800, color: '#fff', fontFamily: 'JetBrains Mono, monospace' }}>{stage.value}</span>
                    </div>
                  </div>
                  {i > 0 && dropPct > 0 && (
                    <div style={{ fontSize: 10, color: T.muted, width: 44, textAlign: 'right', flexShrink: 0 }}>-{dropPct}%</div>
                  )}
                </div>
              </div>
            )
          })}
        </div>

        {/* Conversion rates + source breakdown */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div style={{ background: T.card, border: `1px solid ${T.border}`, borderRadius: 12, padding: '18px 20px' }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: T.text, marginBottom: 14 }}>Conversion Rates</div>
            {conversionRows.map(row => (
              <div key={row.from} style={{ marginBottom: 10 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <span style={{ fontSize: 11, color: T.muted }}>{row.from}</span>
                  <span style={{ fontSize: 11, fontWeight: 800, color: row.color, fontFamily: 'JetBrains Mono, monospace' }}>{row.rate}%</span>
                </div>
                <div style={{ height: 4, background: dark ? '#252538' : '#E8E8F4', borderRadius: 4, overflow: 'hidden' }}>
                  <div style={{ width: `${Math.min(parseFloat(row.rate), 100)}%`, height: '100%', background: row.color, borderRadius: 4 }} />
                </div>
              </div>
            ))}
          </div>

          <div style={{ background: T.card, border: `1px solid ${T.border}`, borderRadius: 12, padding: '18px 20px' }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: T.text, marginBottom: 14 }}>Rejected</div>
            <div style={{ fontSize: 24, fontWeight: 800, color: '#EF4444', letterSpacing: '-0.03em' }}>{s.rejected ?? 0}</div>
            <div style={{ fontSize: 11, color: T.muted, marginTop: 4 }}>
              Skipped: {s.skipped ?? 0}
            </div>
          </div>
        </div>
      </div>

      {/* Pipeline flow SVG */}
      <div style={{ background: T.card, border: `1px solid ${T.border}`, borderRadius: 12, padding: '20px 24px' }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: T.text, marginBottom: 6 }}>Pipeline Flow</div>
        <div style={{ fontSize: 11, color: T.muted, marginBottom: 20 }}>Where jobs end up after discovery</div>
        <svg viewBox="0 0 700 160" style={{ width: '100%', height: 160 }}>
          <path d="M 0,20 C 120,20 120,60 240,60 L 240,100 C 120,100 120,60 0,60 Z" fill="#3B82F630" />
          <path d="M 0,65 C 120,65 120,130 240,130 L 240,155 C 120,155 120,140 0,100 Z" fill="#EF444420" />
          <path d="M 240,62 C 360,62 360,70 480,70 L 480,82 C 360,82 360,74 240,74 Z" fill="#F59E0B40" />
          <path d="M 240,78 C 360,78 360,110 480,110 L 480,125 C 360,125 360,95 240,100 Z" fill="#6B728030" />
          <path d="M 480,71 C 580,71 580,76 680,76 L 680,82 C 580,82 580,78 480,80 Z" fill="#EC489940" />
          <path d="M 480,83 C 580,83 580,105 680,105 L 680,118 C 580,118 580,98 480,98 Z" fill="#EF444430" />

          {[
            { x: 0,   y: 10, label: String(s.total     ?? 0), sub: 'Discovered', color: '#6366F1' },
            { x: 240, y: 52, label: String(s.applied   ?? 0), sub: 'Applied',    color: '#3B82F6' },
            { x: 480, y: 62, label: String(s.oa        ?? 0), sub: 'OA',         color: '#F59E0B' },
            { x: 680, y: 68, label: String(s.interview ?? 0), sub: 'Interview',  color: '#EC4899' },
          ].map(n => (
            <g key={n.sub}>
              <text x={n.x + 4} y={n.y} fontFamily="JetBrains Mono" fontSize="13" fontWeight="800" fill={n.color}>{n.label}</text>
              <text x={n.x + 4} y={n.y + 13} fontFamily="DM Sans" fontSize="9" fill="#8888A0">{n.sub}</text>
            </g>
          ))}
          <text x={100} y={148} fontFamily="DM Sans" fontSize="9" fill="#EF4444">{(s.rejected ?? 0) + (s.skipped ?? 0)} skipped/rejected</text>
          <text x={340} y={130} fontFamily="DM Sans" fontSize="9" fill="#6B7280">{s.applied ?? 0} applied</text>
          <text x={580} y={125} fontFamily="DM Sans" fontSize="9" fill="#EF4444">{s.rejected ?? 0} rejected</text>
        </svg>
      </div>
    </div>
  )
}
