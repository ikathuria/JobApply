// Design tokens — matches design_handoff_jobapply_redesign/README.md exactly

export const DARK = {
  bg:       '#0C0C14',
  surface:  '#13131E',
  card:     '#1A1A28',
  border:   '#252538',
  text:     '#EEEEF8',
  muted:    '#7878A0',
  accent:   '#6366F1',
  accentBg: 'rgba(99,102,241,0.12)',
  success:  '#22C55E',
  warning:  '#F59E0B',
  danger:   '#EF4444',
  pink:     '#EC4899',
}

export const LIGHT = {
  bg:       '#F4F4FA',
  surface:  '#FFFFFF',
  card:     '#FAFAFA',
  border:   '#E2E2EE',
  text:     '#1A1A2E',
  muted:    '#7878A0',
  accent:   '#4F52D9',
  accentBg: 'rgba(79,82,217,0.09)',
  success:  '#16A34A',
  warning:  '#D97706',
  danger:   '#DC2626',
  pink:     '#DB2777',
}

export const STATUS_META = {
  new:       { label: 'New',       color: '#6B7280', bg: 'rgba(107,114,128,0.15)' },
  queued:    { label: 'Ready',     color: '#22C55E', bg: 'rgba(34,197,94,0.15)'  },
  approved:  { label: 'Approved',  color: '#8B5CF6', bg: 'rgba(139,92,246,0.15)' },
  applied:   { label: 'Applied',   color: '#3B82F6', bg: 'rgba(59,130,246,0.15)' },
  oa:        { label: 'OA',        color: '#F59E0B', bg: 'rgba(245,158,11,0.15)' },
  interview: { label: 'Interview', color: '#EC4899', bg: 'rgba(236,72,153,0.15)' },
  offer:     { label: 'Offer',     color: '#10B981', bg: 'rgba(16,185,129,0.15)' },
  rejected:  { label: 'Rejected',  color: '#EF4444', bg: 'rgba(239,68,68,0.15)'  },
  skipped:   { label: 'Skipped',   color: '#9CA3AF', bg: 'rgba(156,163,175,0.15)'},
}

export const NEXT_ACTION = {
  new:       { label: 'Tailor →',    color: '#6366F1' },
  queued:    { label: 'Approve →',   color: '#8B5CF6' },
  approved:  { label: 'Apply →',     color: '#6366F1' },
  applied:   { label: 'Track →',     color: '#3B82F6' },
  oa:        { label: 'Update →',    color: '#F59E0B' },
  interview: { label: 'Prep →',      color: '#EC4899' },
  offer:     { label: 'View →',      color: '#10B981' },
  rejected:  { label: 'View →',      color: '#9CA3AF' },
  skipped:   { label: 'View →',      color: '#9CA3AF' },
}
