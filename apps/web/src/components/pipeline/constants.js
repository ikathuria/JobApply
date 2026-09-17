export const TABS = [
  { id: 'new',      label: 'New',      statusFilter: 'new' },
  { id: 'ready',    label: 'Ready',    statusFilter: 'queued' },
  { id: 'approved', label: 'Approved', statusFilter: 'approved' },
  { id: 'applied',  label: 'Applied',  statusFilter: null },   // applied+oa+interview
  { id: 'all',      label: 'All',      statusFilter: null },
]

export function normalizeLocation(loc) {
  if (!loc) return ''
  const s = loc.trim()
  if (/^remote/i.test(s)) return 'Remote'
  return s
}

