// Design tokens — warm paper/ink palette
// Light = warm cream paper; Dark = warm dark brown

export const LIGHT = {
  bg:       '#F4F3EE',
  surface:  '#FFFFFF',
  card:     '#FAFAF8',
  border:   '#E4E1D7',
  text:     '#1F1A14',
  muted:    '#8A847A',
  accent:   '#C96442',
  accentBg: 'rgba(201,100,66,0.10)',
  success:  '#5B8C44',
  warning:  '#B57828',
  danger:   '#B4452C',
  pink:     '#C28098',
}

export const DARK = {
  bg:       '#1A1714',
  surface:  '#211E1A',
  card:     '#2A2520',
  border:   '#3A342D',
  text:     '#EDE8DF',
  muted:    '#8A847A',
  accent:   '#C96442',
  accentBg: 'rgba(201,100,66,0.14)',
  success:  '#6A9068',
  warning:  '#C49840',
  danger:   '#B4452C',
  pink:     '#C28098',
}

export const STATUS_META = {
  new:       { label: 'New',       color: '#5B88B5', bg: 'rgba(91,136,181,0.14)'  },
  queued:    { label: 'Ready',     color: '#6A9068', bg: 'rgba(106,144,104,0.14)' },
  approved:  { label: 'Approved',  color: '#8B7BB8', bg: 'rgba(139,123,184,0.14)' },
  applied:   { label: 'Applied',   color: '#D17847', bg: 'rgba(209,120,71,0.14)'  },
  oa:        { label: 'OA',        color: '#C49840', bg: 'rgba(196,152,64,0.14)'  },
  interview: { label: 'Interview', color: '#C28098', bg: 'rgba(194,128,152,0.14)' },
  offer:     { label: 'Offer',     color: '#5A9DA8', bg: 'rgba(90,157,168,0.14)'  },
  rejected:  { label: 'Rejected',  color: '#B4452C', bg: 'rgba(180,69,44,0.14)'   },
  skipped:   { label: 'Skipped',   color: '#B5AFA3', bg: 'rgba(181,175,163,0.14)' },
}

export const NEXT_ACTION = {
  new:       { label: 'Tailor →',  color: '#C96442' },
  queued:    { label: 'Approve →', color: '#8B7BB8' },
  approved:  { label: 'Apply →',   color: '#C96442' },
  applied:   { label: 'Track →',   color: '#D17847' },
  oa:        { label: 'Update →',  color: '#C49840' },
  interview: { label: 'Prep →',    color: '#C28098' },
  offer:     { label: 'View →',    color: '#5A9DA8' },
  rejected:  { label: 'View →',    color: '#B5AFA3' },
  skipped:   { label: 'View →',    color: '#B5AFA3' },
}
