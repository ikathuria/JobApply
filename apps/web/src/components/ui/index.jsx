import { useState, useContext } from 'react'
import { ThemeCtx } from '../ThemeContext.jsx'
import { DARK, LIGHT, STATUS_META, ATS_TARGET, alpha, atsColor } from '../../theme.js'

// ── Score bar ─────────────────────────────────────────────────────────────────
export function ScoreBar({ score, height = 4, showLabel = false }) {
  const { dark } = useContext(ThemeCtx)
  const T = dark ? DARK : LIGHT
  const pct = Math.round(score * 100)
  const color = score >= 0.75 ? T.success : score >= 0.55 ? T.warning : T.danger
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{ flex: 1, height, borderRadius: height, background: T.border, overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: height, transition: 'width 0.4s ease' }} />
      </div>
      {showLabel && (
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color, fontWeight: 700, minWidth: 32 }}>
          {pct}%
        </span>
      )}
    </div>
  )
}

// ── Status badge ──────────────────────────────────────────────────────────────
// Mono uppercase label; Ready and Offer are solid fills (BRAND.md › Components).
export function StatusBadge({ status, size = 'sm' }) {
  const meta = STATUS_META[status] || { label: status, color: 'var(--muted)', bg: 'transparent' }
  const pad = size === 'sm' ? '3px 8px' : '4px 12px'
  const fs  = size === 'sm' ? 11 : 12
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      padding: pad, borderRadius: 2, fontSize: fs, fontWeight: 600,
      fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.06em',
      color: meta.fill ? 'var(--on-accent)' : meta.color,
      background: meta.fill ? meta.color : meta.bg,
      border: `1px solid ${meta.fill ? meta.color : alpha(meta.color, 35)}`,
      whiteSpace: 'nowrap', minWidth: 76,
    }}>
      {meta.label}
    </span>
  )
}

// ── ATS score ─────────────────────────────────────────────────────────────────
// Mono number + thin bar with a tick at the 90 target. null → a "run" prompt.
export function AtsScore({ score, onRun, width = 92 }) {
  if (score == null) {
    return (
      <span title="No ATS score yet. Open the job and run it."
        onClick={onRun}
        style={{
          width, fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--muted)',
          textDecoration: 'underline dotted', textUnderlineOffset: 3, cursor: onRun ? 'pointer' : 'default',
        }}>run</span>
    )
  }
  const color = atsColor(score)
  return (
    <span title={`ATS ${score}/100 · target ${ATS_TARGET}`}
      style={{ width, display: 'inline-flex', alignItems: 'center', gap: 8 }}>
      <b style={{ fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 700, color, minWidth: 22, fontVariantNumeric: 'tabular-nums' }}>{score}</b>
      <span style={{ position: 'relative', flex: 1, height: 4, background: 'var(--line)' }}>
        <span className="gb-fill" style={{ position: 'absolute', inset: 0, width: `${score}%`, background: color }} />
        <span style={{ position: 'absolute', left: `${ATS_TARGET}%`, top: -3, bottom: -3, width: 1.5, background: 'var(--ink)' }} />
      </span>
    </span>
  )
}

// ── Button ─────────────────────────────────────────────────────────────────────
export function Btn({ children, variant = 'primary', onClick, style = {}, disabled = false, size = 'md' }) {
  const { dark } = useContext(ThemeCtx)
  const T = dark ? DARK : LIGHT
  const [hov, setHov] = useState(false)
  const base = {
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
    gap: 6, border: 'none', cursor: disabled ? 'not-allowed' : 'pointer',
    fontFamily: 'var(--font-text)', fontWeight: 600, borderRadius: 2,
    transition: 'all 0.15s ease', opacity: disabled ? 0.5 : 1,
    fontSize:  size === 'sm' ? 12 : size === 'lg' ? 15 : 13,
    padding:   size === 'sm' ? '5px 12px' : size === 'lg' ? '13px 24px' : '8px 16px',
    minHeight: size === 'sm' ? 32 : size === 'lg' ? 48 : 40,
  }
  const variants = {
    primary:   { background: hov ? 'var(--accent-hover)' : T.accent, color: T.onAccent },
    secondary: { background: hov ? T.fill : T.surface, color: T.text, border: `1px solid ${T.border}` },
    ghost:     { background: hov ? T.fill : 'transparent', color: T.text2 },
    danger:    { background: hov ? alpha(T.danger, 80) : T.danger, color: 'var(--on-accent)' },
    success:   { background: hov ? alpha(T.success, 80) : T.success, color: 'var(--on-accent)' },
  }
  return (
    <button style={{ ...base, ...variants[variant], ...style }}
      onClick={onClick} disabled={disabled}
      onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}>
      {children}
    </button>
  )
}

// ── Tag ───────────────────────────────────────────────────────────────────────
export function Tag({ children, style = {} }) {
  const { dark } = useContext(ThemeCtx)
  const T = dark ? DARK : LIGHT
  return (
    <span style={{
      display: 'inline-block', padding: '2px 8px', borderRadius: 2,
      fontSize: 11, fontWeight: 500, fontFamily: 'var(--font-mono)',
      background: T.fill, color: T.muted, ...style,
    }}>
      {children}
    </span>
  )
}

// ── Card ──────────────────────────────────────────────────────────────────────
export function Card({ children, style = {}, onClick, noPad = false }) {
  const { dark } = useContext(ThemeCtx)
  const T = dark ? DARK : LIGHT
  const [hov, setHov] = useState(false)
  return (
    <div onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (e => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), onClick())) : undefined}
      onMouseEnter={() => onClick && setHov(true)} onMouseLeave={() => setHov(false)}
      style={{
        background: T.card, border: `1px solid ${hov && onClick ? T.accent : T.border}`,
        borderRadius: 2, padding: noPad ? 0 : '16px 20px',
        cursor: onClick ? 'pointer' : 'default',
        transition: 'border-color var(--dur-1) var(--ease)',
        ...style,
      }}>
      {children}
    </div>
  )
}

// ── Input ─────────────────────────────────────────────────────────────────────
export function Input({ value, onChange, placeholder, style = {}, icon, type = 'text' }) {
  const { dark } = useContext(ThemeCtx)
  const T = dark ? DARK : LIGHT
  return (
    <div style={{ position: 'relative', ...style }}>
      {icon && (
        <span style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: T.muted, fontSize: 14, pointerEvents: 'none' }}>
          {icon}
        </span>
      )}
      <input value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} type={type}
        style={{
          width: '100%', boxSizing: 'border-box',
          padding: icon ? '9px 12px 9px 36px' : '9px 12px',
          background: T.card,
          border: `1px solid ${T.border}`,
          borderRadius: 2, color: T.text, fontSize: 13,
          fontFamily: 'var(--font-text)', outline: 'none',
        }}
      />
    </div>
  )
}

// ── Textarea ──────────────────────────────────────────────────────────────────
export function Textarea({ value, onChange, placeholder, rows = 4, style = {} }) {
  const { dark } = useContext(ThemeCtx)
  const T = dark ? DARK : LIGHT
  return (
    <textarea value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} rows={rows}
      style={{
        width: '100%', boxSizing: 'border-box', padding: '9px 12px',
        background: T.card,
        border: `1px solid ${T.border}`,
        borderRadius: 2, color: T.text, fontSize: 13,
        fontFamily: 'var(--font-text)', outline: 'none', resize: 'vertical',
        ...style,
      }}
    />
  )
}

// ── Divider ───────────────────────────────────────────────────────────────────
export function Divider({ style = {} }) {
  const { dark } = useContext(ThemeCtx)
  const T = dark ? DARK : LIGHT
  return <div style={{ height: 1, background: T.border, margin: '12px 0', ...style }} />
}

// ── Section label ─────────────────────────────────────────────────────────────
export function SectionLabel({ children, style = {} }) {
  const { dark } = useContext(ThemeCtx)
  const T = dark ? DARK : LIGHT
  return (
    <div style={{
      fontSize: 11, fontWeight: 600, color: T.muted, fontFamily: 'var(--font-mono)',
      textTransform: 'uppercase', letterSpacing: '0.08em',
      marginBottom: 10, ...style,
    }}>
      {children}
    </div>
  )
}

// ── Spinner ───────────────────────────────────────────────────────────────────
export function Spinner({ size = 20, color }) {
  const { dark } = useContext(ThemeCtx)
  const T = dark ? DARK : LIGHT
  return (
    <div style={{
      width: size, height: size, borderRadius: '50%',
      border: `2px solid ${T.border}`,
      borderTopColor: color || T.accent,
      animation: 'spin 0.7s linear infinite',
    }} />
  )
}

// inject keyframe
if (typeof document !== 'undefined') {
  const s = document.createElement('style')
  s.textContent = '@keyframes spin { to { transform: rotate(360deg); } }'
  document.head.appendChild(s)
}

// ── Toast ─────────────────────────────────────────────────────────────────────
// Shared by any view with a `flash(msg, kind)` helper + `{ msg, kind }` state.
export function Toast({ toast }) {
  const { dark } = useContext(ThemeCtx)
  const T = dark ? DARK : LIGHT
  if (!toast) return null
  return (
    <div role="status" aria-live="polite" style={{
      position: 'fixed', bottom: 24, right: 24, zIndex: 1000,
      padding: '12px 18px', borderRadius: 2, fontSize: 13, fontWeight: 600, color: 'var(--on-accent)',
      background: toast.kind === 'err' ? T.danger : T.success,
      boxShadow: 'var(--shadow-float)',
    }}>
      {toast.msg}
    </div>
  )
}

// ── Empty state ───────────────────────────────────────────────────────────────
export function EmptyState({ icon = '◌', title, sub, action }) {
  const { dark } = useContext(ThemeCtx)
  const T = dark ? DARK : LIGHT
  return (
    <div style={{ padding: '48px 28px', color: T.muted, borderTop: `1px solid ${T.rule}` }}>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 600, color: T.text, marginBottom: 6 }}>{title}</div>
      {sub && <div style={{ fontSize: 13, marginBottom: action ? 20 : 0 }}>{sub}</div>}
      {action}
    </div>
  )
}
