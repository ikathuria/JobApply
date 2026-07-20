// API client — all fetch calls to FastAPI backend

const BASE = '/api'

async function req(method, path, body) {
  const opts = {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  }
  const res = await fetch(BASE + path, opts)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || res.statusText)
  }
  // 204 No Content
  if (res.status === 204) return null
  return res.json()
}

async function textReq(method, path, body) {
  const opts = {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  }
  const res = await fetch(BASE + path, opts)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || res.statusText)
  }
  return res.text()
}

export const api = {
  stats:      ()          => req('GET',   '/stats'),
  focus:      ()          => req('GET',   '/focus'),
  jobs:       (params={}) => req('GET',   '/jobs?' + new URLSearchParams(params)),
  job:        (id)        => req('GET',   `/jobs/${id}`),
  patch:      (id, data)  => req('PATCH', `/jobs/${id}`, data),
  tailor:     (id)        => req('POST',  `/jobs/${id}/tailor`),
  coverLetter:(id)        => textReq('GET', `/jobs/${id}/cover_letter`),
  saveCL:     (id, text)  => req('PATCH', `/jobs/${id}/cover_letter`, { text }),
  import:     (job)       => req('POST',  '/jobs/import', job),
  bulk:       (ids, status) => req('POST', '/jobs/bulk', { ids, status }),
  resumeUrl:  (id)        => `${BASE}/jobs/${id}/resume`,
  coverLetterPdfUrl: (id) => `${BASE}/jobs/${id}/cover_letter.pdf`,

  // ── Outreach: recruiters ──
  recruiters:       ()          => req('GET',    '/recruiters'),
  addRecruiter:     (data)      => req('POST',   '/recruiters', data),
  patchRecruiter:   (id, data)  => req('PATCH',  `/recruiters/${id}`, data),
  deleteRecruiter:  (id)        => req('DELETE', `/recruiters/${id}`),
  recruiterOutreach:(id)        => req('GET',    `/recruiters/${id}/outreach`),

  // ── Outreach: emails ──
  draftOutreach:    (data)      => req('POST',   '/outreach/draft', data),
  patchOutreach:    (id, data)  => req('PATCH',  `/outreach/${id}`, data),
  sendOutreach:     (id)        => req('POST',   `/outreach/${id}/send`),
  followups:        ()          => req('GET',    '/outreach/followups'),
  emailFinder:      (first, last, domain, probe=false) =>
                       req('GET', '/email-finder?' + new URLSearchParams({ first, last, domain, probe })),

  // ── Recruiting timeline + reminders (M19) ──
  timeline:         ()          => req('GET',    '/timeline'),
  reminders:        ()          => req('GET',    '/reminders'),
  remindersDue:     ()          => req('GET',    '/reminders/due'),
  addReminder:      (data)      => req('POST',   '/reminders', data),
  patchReminder:    (id, data)  => req('PATCH',  `/reminders/${id}`, data),
  deleteReminder:   (id)        => req('DELETE', `/reminders/${id}`),
}
