import { useState, useContext } from 'react'
import { ThemeCtx } from '../ThemeContext.jsx'
import { DARK, LIGHT, STATUS_META } from '../../theme.js'

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
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color, fontWeight: 700, minWidth: 32 }}>
          {pct}%
        </span>
      )}
    </div>
  )
}

// ── Status badge ──────────────────────────────────────────────────────────────
export function StatusBadge({ status, size = 'sm' }) {
  const meta = STATUS_META[status] || { label: status, color: '#888', bg: '#88888820' }
  const pad = size === 'sm' ? '2px 8px' : '3px 12px'
  const fs  = size === 'sm' ? 11 : 12
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 5,
      padding: pad, borderRadius: 20, fontSize: fs, fontWeight: 700,
      color: meta.color, background: meta.bg, letterSpacing: '0.03em',
      border: `1px solid ${meta.color}30`, whiteSpace: 'nowrap',
    }}>
      <span style={{ width: 6, height: 6, borderRadius: '50%', background: meta.color, flexShrink: 0 }} />
      {meta.label}
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
    fontFamily: 'Inter, system-ui, sans-serif', fontWeight: 600, borderRadius: 8,
    transition: 'all 0.15s ease', opacity: disabled ? 0.5 : 1,
    fontSize:  size === 'sm' ? 12 : size === 'lg' ? 15 : 13,
    padding:   size === 'sm' ? '5px 12px' : size === 'lg' ? '13px 24px' : '8px 16px',
  }
  const variants = {
    primary:   { background: hov ? T.accent + 'CC' : T.accent, color: '#fff' },
    secondary: { background: hov ? T.border : T.card, color: T.text, border: `1px solid ${T.border}` },
    ghost:     { background: hov ? T.accentBg : 'transparent', color: T.muted },
    danger:    { background: hov ? T.danger + 'CC' : T.danger, color: '#fff' },
    success:   { background: hov ? T.success + 'CC' : T.success, color: '#fff' },
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
      display: 'inline-block', padding: '2px 8px', borderRadius: 5,
      fontSize: 11, fontWeight: 600, fontFamily: 'JetBrains Mono, monospace',
      background: T.border, color: T.muted, ...style,
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
      onMouseEnter={() => onClick && setHov(true)} onMouseLeave={() => setHov(false)}
      style={{
        background: T.card, border: `1px solid ${hov && onClick ? T.accent + '60' : T.border}`,
        borderRadius: 12, padding: noPad ? 0 : '16px 20px',
        cursor: onClick ? 'pointer' : 'default',
        transition: 'border-color 0.15s, box-shadow 0.15s',
        boxShadow: hov && onClick ? `0 0 0 3px ${T.accent}18` : dark ? 'none' : '0 1px 4px rgba(0,0,0,0.06)',
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
          borderRadius: 8, color: T.text, fontSize: 13,
          fontFamily: 'Inter, system-ui, sans-serif', outline: 'none',
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
        borderRadius: 8, color: T.text, fontSize: 13,
        fontFamily: 'Inter, system-ui, sans-serif', outline: 'none', resize: 'vertical',
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
      fontSize: 11, fontWeight: 700, color: T.muted,
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

// ── Empty state ───────────────────────────────────────────────────────────────
export function EmptyState({ icon = '◌', title, sub, action }) {
  const { dark } = useContext(ThemeCtx)
  const T = dark ? DARK : LIGHT
  return (
    <div style={{ textAlign: 'center', padding: '60px 24px', color: T.muted }}>
      <div style={{ fontSize: 36, marginBottom: 14 }}>{icon}</div>
      <div style={{ fontSize: 14, fontWeight: 700, color: T.text, marginBottom: 6 }}>{title}</div>
      {sub && <div style={{ fontSize: 12, marginBottom: action ? 20 : 0 }}>{sub}</div>}
      {action}
    </div>
  )
}
