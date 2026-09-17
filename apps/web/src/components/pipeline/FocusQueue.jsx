import { DARK, LIGHT } from '../../theme.js'

export default function FocusQueue({ focus, onSelectJob, setTab, dark, open, onToggle }) {
  const T = dark ? DARK : LIGHT
  if (!focus?.length) return null

  const openItem = item => {
    if (item.jobId) onSelectJob({ id: item.jobId, _needsFetch: true })
    else setTab(item.tab)
  }

  return (
    <div style={{ marginBottom: open ? 24 : 14 }}>
      <button
        onClick={onToggle}
        aria-expanded={open}
        style={{
          display: 'flex', alignItems: 'center', gap: 8, width: '100%',
          background: 'none', border: 'none', cursor: 'pointer', padding: 0,
          fontFamily: 'Inter, system-ui, sans-serif',
        }}
      >
        <span style={{ fontSize: 11, fontWeight: 700, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
          Today's Focus
        </span>
        <span style={{
          fontSize: 10, fontWeight: 800, color: T.text, background: T.border,
          borderRadius: 10, padding: '1px 7px',
        }}>{focus.length}</span>
        <span style={{ flex: 1 }} />
        <span style={{ fontSize: 11, color: T.muted, transform: open ? 'rotate(90deg)' : 'none', transition: 'transform 0.15s' }}>▸</span>
      </button>

      {!open && (
        <div
          role="button" tabIndex={0}
          onClick={() => openItem(focus[0])}
          onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), openItem(focus[0]))}
          style={{
            marginTop: 8, display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer',
            fontSize: 12, color: T.text,
          }}
        >
          <span style={{ fontSize: 14 }}>{focus[0].icon}</span>
          <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{focus[0].label}</span>
          <span style={{ fontWeight: 700, color: focus[0].color, flexShrink: 0 }}>{focus[0].cta} →</span>
          {focus.length > 1 && <span style={{ color: T.muted, flexShrink: 0 }}>+{focus.length - 1} more</span>}
        </div>
      )}

      {open && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 10, marginTop: 10 }}>
          {focus.map(item => (
            <div key={item.id}
              role="button" tabIndex={0}
              onClick={() => openItem(item)}
              onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), openItem(item))}
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
      )}
    </div>
  )
}
