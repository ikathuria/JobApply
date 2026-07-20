import { useState, useEffect, useCallback, useContext } from 'react'
import { ThemeCtx } from './ThemeContext.jsx'
import { DARK, LIGHT } from '../theme.js'
import { api } from '../api.js'
import { Card, Btn, EmptyState, Spinner, SectionLabel, Tag } from './ui/index.jsx'

// Group order for the three buckets shown top-to-bottom.
const GROUPS = [
  { id: 'open',     label: 'Open now' },
  { id: 'upcoming', label: 'Upcoming' },
  { id: 'closed',   label: 'Closed' },
]

// Map a per-company window status to a bucket + a pill color token.
function bucketOf(status) {
  if (status === 'open' || status === 'rolling' || status === 'closing_soon') return 'open'
  if (status === 'upcoming') return 'upcoming'
  return 'closed'
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
function fmtDate(iso) {
  if (!iso) return ''
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(iso))
  if (!m) return String(iso).slice(0, 10)
  return `${MONTHS[+m[2] - 1]} ${+m[3]}`
}
function addDays(iso, n) {
  if (!iso) return null
  const d = new Date(iso + 'T00:00:00')
  d.setDate(d.getDate() + n)
  return d.toISOString().slice(0, 10)
}
function todayISO() {
  return new Date().toISOString().slice(0, 10)
}
function maxDate(a, b) {
  return (a || '') > (b || '') ? a : b
}

// Human window text + pill color token per status.
function windowMeta(c, T) {
  switch (c.status) {
    case 'rolling':
      return { text: `Rolling${c.opens ? ` · open since ${fmtDate(c.opens)}` : ' · open now'}`, color: T.success }
    case 'open':
      return {
        text: c.closes ? `Open · closes ${fmtDate(c.closes)} (${c.days_until_close}d)` : 'Open now',
        color: T.success,
      }
    case 'closing_soon':
      return { text: `Closing in ${c.days_until_close}d · ${fmtDate(c.closes)}`, color: T.warning }
    case 'upcoming':
      return { text: `Opens ${fmtDate(c.opens)} · in ${c.days_until_open}d`, color: '#5B88B5' }
    default:
      return { text: 'Closed for this cycle', color: T.muted }
  }
}

// Default due date for a reminder given the company window + reminder kind.
function defaultDue(c, kind) {
  const t = todayISO()
  if (kind === 'reach_out') {
    // Line up a referral ~a week before the window opens (never in the past).
    if (c.status === 'upcoming') return maxDate(t, addDays(c.opens, -7))
    return t  // already open/rolling — reach out now
  }
  // apply
  if (c.status === 'upcoming') return c.opens || t
  if (c.status === 'closing_soon') return c.closes || t
  return t  // open / rolling / closed — apply now
}

export default function TimelineView({ onReachOut, onOpenRoles }) {
  const { dark } = useContext(ThemeCtx)
  const T = dark ? DARK : LIGHT

  const [data, setData] = useState(null)          // { cycle, note, companies: [...] }
  const [reminders, setReminders] = useState([])  // all reminders (open + done)
  const [due, setDue] = useState([])              // reminders due today
  const [toast, setToast] = useState(null)

  const flash = (msg, kind = 'ok') => {
    setToast({ msg, kind })
    setTimeout(() => setToast(null), 3000)
  }

  const loadReminders = useCallback(() => {
    api.reminders().then(setReminders).catch(() => setReminders([]))
    api.remindersDue().then(setDue).catch(() => setDue([]))
  }, [])

  useEffect(() => {
    api.timeline().then(setData).catch(() => setData({ companies: [] }))
    loadReminders()
  }, [loadReminders])

  // Open (not-done) reminder for a company+kind, if any.
  const openReminder = (company, kind) =>
    reminders.find(r => r.company === company && r.kind === kind && !r.done)

  const toggleReminder = async (c, kind) => {
    const existing = openReminder(c.name, kind)
    try {
      if (existing) {
        await api.deleteReminder(existing.id)
        flash(`Reminder cleared for ${c.name}`)
      } else {
        const dueDate = defaultDue(c, kind)
        await api.addReminder({
          company: c.name, kind, due_date: dueDate,
          note: kind === 'reach_out'
            ? `Line up a referral / reach out for ${c.name}`
            : `Apply to ${c.name}${c.program ? ` (${c.program})` : ''}`,
        })
        flash(`${kind === 'reach_out' ? 'Reach-out' : 'Apply'} reminder set · ${c.name} · ${fmtDate(dueDate)}`)
      }
      loadReminders()
    } catch (e) {
      flash(e.message || 'Could not update reminder', 'err')
    }
  }

  const dismissDue = async (r) => {
    try {
      await api.patchReminder(r.id, { done: 1 })
      loadReminders()
    } catch (e) {
      flash(e.message || 'Could not dismiss', 'err')
    }
  }

  if (!data) {
    return <div style={{ padding: 40, textAlign: 'center' }}><Spinner /></div>
  }

  const companies = data.companies || []
  const grouped = { open: [], upcoming: [], closed: [] }
  for (const c of companies) grouped[bucketOf(c.status)].push(c)
  // Within a bucket: high priority first, then most open roles, then name.
  const rank = p => (p === 'high' ? 0 : p === 'medium' ? 1 : 2)
  for (const g of Object.values(grouped)) {
    g.sort((a, b) =>
      rank(a.priority) - rank(b.priority) ||
      (b.open_roles || 0) - (a.open_roles || 0) ||
      (a.name || '').localeCompare(b.name || ''))
  }

  const totalOpenRoles = companies.reduce((n, c) => n + (c.open_roles || 0), 0)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Due-reminder banner */}
      {due.length > 0 && (
        <div style={{
          margin: '14px 20px 0', padding: '10px 16px', borderRadius: 10,
          background: 'rgba(196,152,64,0.14)', border: `1px solid ${T.warning}50`,
          color: T.text, fontSize: 13, display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap',
        }}>
          <span style={{ fontSize: 16 }}>⏰</span>
          <span style={{ fontWeight: 700 }}>{due.length} reminder{due.length !== 1 ? 's' : ''} due:</span>
          {due.map(r => (
            <button key={r.id} onClick={() => dismissDue(r)} title="Click to mark done"
              style={{
                background: 'transparent', border: `1px solid ${T.warning}55`, borderRadius: 14,
                padding: '2px 10px', fontSize: 12, color: T.text, cursor: 'pointer',
              }}>
              {r.kind === 'reach_out' ? '🤝' : '✉️'} {r.company} ({fmtDate(r.due_date)}) ✓
            </button>
          ))}
        </div>
      )}

      {/* Header */}
      <div style={{ padding: '18px 20px 4px' }}>
        <div style={{ fontSize: 13, color: T.muted }}>
          {data.cycle} · <b style={{ color: T.text }}>{totalOpenRoles}</b> open role{totalOpenRoles !== 1 ? 's' : ''} across {companies.length} target companies.
          Dates are typical windows — live role counts are ground truth.
        </div>
      </div>

      {/* Scrollable groups */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '10px 20px 24px' }}>
        {GROUPS.map(g => {
          const list = grouped[g.id]
          if (!list.length) return null
          return (
            <div key={g.id} style={{ marginBottom: 22 }}>
              <SectionLabel style={{ marginBottom: 12 }}>
                {g.label} <span style={{ color: T.muted, fontWeight: 600 }}>· {list.length}</span>
              </SectionLabel>
              <div style={{
                display: 'grid', gap: 12,
                gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
              }}>
                {list.map(c => {
                  const wm = windowMeta(c, T)
                  const applySet = !!openReminder(c.name, 'apply')
                  const reachSet = !!openReminder(c.name, 'reach_out')
                  return (
                    <Card key={c.name} style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                      {/* title row */}
                      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8 }}>
                        <div style={{ minWidth: 0 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 7, flexWrap: 'wrap' }}>
                            <span style={{ fontSize: 15, fontWeight: 800, color: T.text }}>{c.name}</span>
                            {c.priority === 'high' && <span title="High priority" style={{ color: T.accent }}>★</span>}
                          </div>
                          <div style={{ fontSize: 11.5, color: T.muted, marginTop: 2 }}>{c.tier}{c.program ? ` · ${c.program}` : ''}</div>
                        </div>
                        <span style={{
                          flexShrink: 0, fontSize: 11, fontWeight: 700, color: wm.color,
                          background: wm.color + '1F', border: `1px solid ${wm.color}40`,
                          borderRadius: 20, padding: '3px 9px', whiteSpace: 'nowrap',
                        }}>
                          {wm.text}
                        </span>
                      </div>

                      {/* badges */}
                      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                        {c.sponsor && (
                          <Tag style={{ background: T.success + '1F', color: T.success }}>H-1B sponsor</Tag>
                        )}
                        {c.has_contact
                          ? <Tag style={{ background: T.accent + '1F', color: T.accent }}>✓ contact</Tag>
                          : null}
                        <button onClick={() => c.open_roles > 0 && onOpenRoles?.(c.name)}
                          disabled={!c.open_roles}
                          style={{
                            border: 'none', borderRadius: 5, padding: '2px 8px',
                            fontSize: 11, fontWeight: 700, fontFamily: 'JetBrains Mono, monospace',
                            cursor: c.open_roles ? 'pointer' : 'default',
                            background: c.open_roles ? '#5B88B51F' : T.border,
                            color: c.open_roles ? '#5B88B5' : T.muted,
                          }}>
                          {c.open_roles} open role{c.open_roles !== 1 ? 's' : ''}{c.open_roles ? ' →' : ''}
                        </button>
                      </div>

                      {c.notes && (
                        <div style={{ fontSize: 12, color: T.muted, lineHeight: 1.45 }}>{c.notes}</div>
                      )}

                      {/* actions */}
                      <div style={{ display: 'flex', gap: 7, flexWrap: 'wrap', marginTop: 2 }}>
                        <Btn size="sm" variant={applySet ? 'success' : 'secondary'} onClick={() => toggleReminder(c, 'apply')}>
                          {applySet ? '✓ Apply reminder' : '⏰ Remind: apply'}
                        </Btn>
                        <Btn size="sm" variant={reachSet ? 'success' : 'secondary'} onClick={() => toggleReminder(c, 'reach_out')}>
                          {reachSet ? '✓ Reach-out reminder' : '🤝 Remind: referral'}
                        </Btn>
                        <Btn size="sm" variant="ghost" onClick={() => onReachOut?.(c.name)}>Reach out</Btn>
                        {c.careers_url && (
                          <a href={c.careers_url} target="_blank" rel="noreferrer"
                            style={{ fontSize: 12, color: T.accent, alignSelf: 'center', textDecoration: 'none' }}>
                            Careers ↗
                          </a>
                        )}
                      </div>
                    </Card>
                  )
                })}
              </div>
            </div>
          )
        })}

        {companies.length === 0 && (
          <EmptyState icon="🗓" title="No calendar loaded" sub="config/recruiting_calendar.json is missing or empty." />
        )}
      </div>

      {/* Toast */}
      {toast && (
        <div style={{
          position: 'fixed', bottom: 24, right: 24, zIndex: 1000,
          padding: '12px 18px', borderRadius: 10, fontSize: 13, fontWeight: 600, color: '#fff',
          background: toast.kind === 'err' ? T.danger : T.success,
          boxShadow: '0 6px 24px rgba(0,0,0,0.25)',
        }}>
          {toast.msg}
        </div>
      )}
    </div>
  )
}
