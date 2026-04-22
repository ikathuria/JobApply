import { useContext } from 'react'
import { ThemeCtx } from './ThemeContext.jsx'
import { DARK, LIGHT } from '../theme.js'

export default function AnalyticsView({ stats }) {
  const { dark } = useContext(ThemeCtx)
  const T = dark ? DARK : LIGHT
  const s = stats || {}

  // "Applied" = everyone who actually submitted — includes later rejected/OA/interview/offer
  const totalApplied = (s.total_applied ?? 0) ||
    ((s.applied ?? 0) + (s.oa ?? 0) + (s.interview ?? 0) + (s.offer ?? 0) + (s.rejected ?? 0))

  const funnel = [
    { label: 'Discovered',  value: s.total        ?? 0, color: '#6366F1' },
    { label: 'Applied',     value: totalApplied,          color: '#3B82F6' },
    { label: 'OA',          value: s.oa           ?? 0, color: '#F59E0B' },
    { label: 'Interview',   value: s.interview    ?? 0, color: '#EC4899' },
    { label: 'Offer',       value: s.offer        ?? 0, color: '#10B981' },
  ]
  const maxVal = funnel[0].value || 1

  const safe = n => Math.max(n, 1)
  const conversionRows = [
    { from: 'Discovered → Applied', rate: ((totalApplied / safe(s.total)) * 100).toFixed(1),       color: '#3B82F6' },
    { from: 'Applied → OA',         rate: (((s.oa??0) / safe(totalApplied)) * 100).toFixed(1),     color: '#F59E0B' },
    { from: 'OA → Interview',       rate: (((s.interview??0) / safe(s.oa??0)) * 100).toFixed(1),  color: '#EC4899' },
    { from: 'Interview → Offer',    rate: (((s.offer??0) / safe(s.interview??0)) * 100).toFixed(1), color: '#10B981' },
  ]

  // ── Data-driven Sankey SVG ────────────────────────────────────────────────
  const SVG_W = 700, SVG_H = 160
  const H = 130, TOP = 10           // usable band height, starting y
  const base = Math.max(s.total ?? 0, 1)
  const sc  = n => Math.max((n / base) * H, 0)
  const oaPlus  = (s.oa ?? 0) + (s.interview ?? 0) + (s.offer ?? 0)
  const intPlus = (s.interview ?? 0) + (s.offer ?? 0)

  // Heights at each stage column
  const h0 = H                 // all discovered
  const h1 = sc(totalApplied)  // applied (including later-rejected/OA/interview/offer)
  const h2 = sc(oaPlus)        // OA+
  const h3 = sc(intPlus)       // Interview+

  // Column x positions for 4 transitions
  const X = [0, 210, 420, 700]
  const mx = (a, b) => (a + b) / 2

  // Main flow band: top=TOP, bottom narrows from ha to hb across x1→x2
  const flowPath = (x1, ha, x2, hb, color, alpha = 0.38) => {
    const m = mx(x1, x2)
    return (
      <path
        key={`flow-${x1}`}
        d={`M${x1},${TOP} L${x2},${TOP} L${x2},${TOP + hb} C${m},${TOP + hb} ${m},${TOP + ha} ${x1},${TOP + ha} Z`}
        fill={color}
        fillOpacity={alpha}
      />
    )
  }

  // Drop band: the portion that "falls off" between x1 and x2
  // At x1: drop occupies from (TOP+hNext) to (TOP+hCur) — wedge starting thin on left
  // Fans to the bottom of the SVG on the right
  const dropPath = (x1, hCur, hNext, x2, color, alpha = 0.18) => {
    const m = mx(x1, x2)
    const BOT = SVG_H - 2
    // Top edge of drop: bezier from (x1, TOP+hCur) to (x2, TOP+hNext)
    // But at x1 the drop is zero-width (since it's within hCur). The drop "appears" as we move right.
    // We show it as: top bezier from (x1,TOP+hNext) to (x2,TOP+hNext), bottom: BOT
    // Shape: left side is a thin slice; right side is the full drop
    return (
      <path
        key={`drop-${x1}`}
        d={`M${x1},${TOP + hCur} C${m},${TOP + hCur} ${m},${TOP + hNext} ${x2},${TOP + hNext} L${x2},${BOT} L${x1},${BOT} Z`}
        fill={color}
        fillOpacity={alpha}
      />
    )
  }

  // ── Rejection by stage ────────────────────────────────────────────────────
  const rejStages = s.rejection_stages ?? {}
  const STAGE_ORDER = ['Résumé Screen', 'Phone Screen', 'OA', 'Technical Interview', 'Final Round', 'Unknown']
  const stageEntries = Object.entries(rejStages).sort((a, b) => b[1] - a[1])
  const maxStageCount = stageEntries[0]?.[1] || 1

  return (
    <div style={{ padding: '28px 32px', overflowY: 'auto', height: '100%' }}>
      <div style={{ fontSize: 20, fontWeight: 800, color: T.text, marginBottom: 4 }}>Pipeline Analytics</div>
      <div style={{ fontSize: 13, color: T.muted, marginBottom: 28 }}>Summer 2026 AI/ML Internship Search</div>

      {/* Top stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14, marginBottom: 28 }}>
        {[
          { label: 'Total Discovered', value: s.total     ?? 0, color: T.accent },
          { label: 'Applied',          value: totalApplied,      color: '#3B82F6' },
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

        {/* Conversion rates + rejected breakdown */}
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

          {/* Rejected card */}
          <div style={{ background: T.card, border: `1px solid ${T.border}`, borderRadius: 12, padding: '18px 20px' }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: T.text, marginBottom: 8 }}>Rejected</div>
            <div style={{ fontSize: 24, fontWeight: 800, color: '#EF4444', letterSpacing: '-0.03em', marginBottom: 8 }}>{s.rejected ?? 0}</div>
            {stageEntries.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {stageEntries.slice(0, 4).map(([stage, cnt]) => (
                  <div key={stage}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                      <span style={{ fontSize: 10, color: T.muted }}>{stage}</span>
                      <span style={{ fontSize: 10, fontWeight: 700, color: '#EF4444', fontFamily: 'JetBrains Mono, monospace' }}>{cnt}</span>
                    </div>
                    <div style={{ height: 3, background: dark ? '#252538' : '#E8E8F4', borderRadius: 2, overflow: 'hidden' }}>
                      <div style={{ width: `${(cnt / (s.rejected || 1)) * 100}%`, height: '100%', background: '#EF4444', borderRadius: 2, opacity: 0.7 }} />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ fontSize: 11, color: T.muted }}>Skipped: {s.skipped ?? 0}</div>
            )}
          </div>
        </div>
      </div>

      {/* ── Pipeline Flow Sankey — data-driven ─────────────────────────────── */}
      <div style={{ background: T.card, border: `1px solid ${T.border}`, borderRadius: 12, padding: '20px 24px', marginBottom: 20 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: T.text, marginBottom: 4 }}>Pipeline Flow</div>
        <div style={{ fontSize: 11, color: T.muted, marginBottom: 16 }}>Where jobs end up after discovery — band width is proportional to count</div>
        <svg viewBox={`0 0 ${SVG_W} ${SVG_H}`} style={{ width: '100%', height: SVG_H }}>
          {/* Segment 1: Discovered → Applied (blue) */}
          {flowPath(X[0], h0, X[1], h1, '#3B82F6')}
          {/* Drop 1: Not applied at all (early rejected/skipped) */}
          {h1 < h0 && dropPath(X[0], h0, h1, X[1], '#EF4444')}

          {/* Segment 2: Applied → OA (amber) */}
          {flowPath(X[1], h1, X[2], h2, '#F59E0B')}
          {/* Drop 2: Applied but no OA (most common rejection) */}
          {h2 < h1 && dropPath(X[1], h1, h2, X[2], '#6B7280')}

          {/* Segment 3: OA → Interview (pink) */}
          {flowPath(X[2], h2, X[3], h3, '#EC4899')}
          {/* Drop 3: Got OA but no interview */}
          {h3 < h2 && dropPath(X[2], h2, h3, X[3], '#EF4444')}

          {/* Offer sliver at far right */}
          {sc(s.offer ?? 0) > 0 && (
            <rect x={X[3] - 8} y={TOP} width={8} height={sc(s.offer ?? 0)} fill="#10B981" fillOpacity={0.7} rx={2} />
          )}

          {/* Stage labels */}
          {[
            { x: X[0] + 4,  y: TOP - 2,  val: s.total ?? 0,    sub: 'Discovered', color: '#6366F1' },
            { x: X[1] + 4,  y: TOP - 2,  val: totalApplied,     sub: 'Applied',    color: '#3B82F6' },
            { x: X[2] + 4,  y: TOP - 2,  val: oaPlus,           sub: 'OA+',        color: '#F59E0B' },
            { x: X[3] - 60, y: TOP - 2,  val: intPlus,          sub: 'Interview+', color: '#EC4899' },
          ].map(n => (
            <g key={n.sub}>
              <text x={n.x} y={n.y + 10} fontFamily="JetBrains Mono, monospace" fontSize="12" fontWeight="800" fill={n.color}>{n.val}</text>
              <text x={n.x} y={n.y + 21} fontFamily="DM Sans, sans-serif" fontSize="9" fill="#8888A0">{n.sub}</text>
            </g>
          ))}

          {/* Drop labels */}
          {(s.total ?? 0) - totalApplied > 0 && (
            <text x={mx(X[0], X[1])} y={SVG_H - 4} fontFamily="DM Sans, sans-serif" fontSize="9" fill="#EF4444" textAnchor="middle">
              {(s.total ?? 0) - totalApplied} not applied
            </text>
          )}
          {totalApplied - oaPlus > 0 && (
            <text x={mx(X[1], X[2])} y={SVG_H - 4} fontFamily="DM Sans, sans-serif" fontSize="9" fill="#6B7280" textAnchor="middle">
              {totalApplied - oaPlus} no OA
            </text>
          )}
          {oaPlus - intPlus > 0 && (
            <text x={mx(X[2], X[3])} y={SVG_H - 4} fontFamily="DM Sans, sans-serif" fontSize="9" fill="#EF4444" textAnchor="middle">
              {oaPlus - intPlus} no interview
            </text>
          )}
          {(s.offer ?? 0) > 0 && (
            <text x={X[3] - 4} y={TOP + sc(s.offer ?? 0) + 14} fontFamily="DM Sans, sans-serif" fontSize="9" fill="#10B981" textAnchor="end">
              {s.offer} offer{s.offer !== 1 ? 's' : ''}
            </text>
          )}
        </svg>
      </div>

      {/* ── Rejection by Stage breakdown ─────────────────────────────────── */}
      {stageEntries.length > 0 && (
        <div style={{ background: T.card, border: `1px solid ${T.border}`, borderRadius: 12, padding: '20px 24px' }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: T.text, marginBottom: 4 }}>Rejection by Stage</div>
          <div style={{ fontSize: 11, color: T.muted, marginBottom: 16 }}>
            Set <em>rejection_stage</em> on rejected jobs to populate this chart
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {stageEntries.map(([stage, cnt]) => (
              <div key={stage}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
                  <div style={{ fontSize: 11, color: T.muted, width: 140, flexShrink: 0 }}>{stage}</div>
                  <div style={{ flex: 1, height: 20, background: dark ? '#252538' : '#E8E8F4', borderRadius: 4, overflow: 'hidden' }}>
                    <div style={{
                      width: `${(cnt / maxStageCount) * 100}%`, height: '100%',
                      background: '#EF4444', borderRadius: 4, opacity: 0.75,
                      display: 'flex', alignItems: 'center', paddingLeft: 8,
                      transition: 'width 0.6s ease', minWidth: cnt > 0 ? 24 : 0,
                    }}>
                      <span style={{ fontSize: 10, fontWeight: 800, color: '#fff', fontFamily: 'JetBrains Mono, monospace' }}>{cnt}</span>
                    </div>
                  </div>
                  <div style={{ fontSize: 10, color: T.muted, width: 36, textAlign: 'right', flexShrink: 0 }}>
                    {((cnt / (s.rejected || 1)) * 100).toFixed(0)}%
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
