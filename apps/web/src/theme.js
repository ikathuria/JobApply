// Greenbar design tokens for inline styles. Values are CSS variables defined in
// tokens.css, so light/dark switching happens in CSS (body.dark) and LIGHT/DARK
// are the same object. See BRAND.md.

const TOKENS = {
  bg:       'var(--bg)',
  surface:  'var(--surface)',
  card:     'var(--surface)',
  fill:     'var(--surface-2)',
  band:     'var(--band)',
  rowHover: 'var(--row-hover)',
  rowSel:   'var(--row-sel)',
  border:   'var(--line)',
  rule:     'var(--line-strong)',
  text:     'var(--ink)',
  text2:    'var(--ink-2)',
  muted:    'var(--muted)',
  faint:    'var(--faint)',
  accent:   'var(--accent)',
  accentBg: 'var(--accent-soft)',
  onAccent: 'var(--on-accent)',
  success:  'var(--ok)',
  warning:  'var(--warn)',
  danger:   'var(--bad)',
  info:     'var(--info)',
  pink:     'var(--info)',
  mono:     'var(--font-mono)',
  display:  'var(--font-display)',
  radius:   'var(--r-1)',
  radiusFloat: 'var(--r-2)',
  shadowFloat: 'var(--shadow-float)',
  scrim:    'var(--scrim)',
}

export const LIGHT = TOKENS
export const DARK = TOKENS

// Translucent tint of any token: alpha(T.success, 10) → 10% success over transparent.
export const alpha = (color, pct) => `color-mix(in srgb, ${color} ${pct}%, transparent)`

// ATS tiers: ≥90 meets the target, 75–89 close, <75 far (BRAND.md signature move 3).
export const ATS_TARGET = 90
export const atsColor = score =>
  score >= ATS_TARGET ? 'var(--ok)' : score >= 75 ? 'var(--warn)' : 'var(--bad)'

// Status: mono uppercase labels. `fill` statuses render solid; others as text/outline.
export const STATUS_META = {
  new:       { label: 'New',       color: 'var(--muted)',  bg: 'transparent' },
  queued:    { label: 'Ready',     color: 'var(--accent)', bg: 'var(--accent-soft)', fill: true },
  approved:  { label: 'Approved',  color: 'var(--accent)', bg: 'transparent' },
  applied:   { label: 'Applied',   color: 'var(--ink)',    bg: 'var(--surface-2)' },
  oa:        { label: 'OA',        color: 'var(--warn)',   bg: 'var(--warn-soft)' },
  interview: { label: 'Interview', color: 'var(--info)',   bg: 'var(--info-soft)' },
  offer:     { label: 'Offer',     color: 'var(--ok)',     bg: 'var(--ok-soft)', fill: true },
  rejected:  { label: 'Rejected',  color: 'var(--bad)',    bg: 'var(--bad-soft)' },
  skipped:   { label: 'Skipped',   color: 'var(--muted)',  bg: 'transparent' },
}

export const NEXT_ACTION = {
  new:       { label: 'Tailor →',  color: 'var(--accent)' },
  queued:    { label: 'Approve →', color: 'var(--accent)' },
  approved:  { label: 'Apply →',   color: 'var(--accent)' },
  applied:   { label: 'Track →',   color: 'var(--ink-2)' },
  oa:        { label: 'Update →',  color: 'var(--warn)' },
  interview: { label: 'Prep →',    color: 'var(--info)' },
  offer:     { label: 'View →',    color: 'var(--ok)' },
  rejected:  { label: 'View →',    color: 'var(--muted)' },
  skipped:   { label: 'View →',    color: 'var(--muted)' },
}
