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

export const api = {
  stats:      ()          => req('GET',   '/stats'),
  focus:      ()          => req('GET',   '/focus'),
  jobs:       (params={}) => req('GET',   '/jobs?' + new URLSearchParams(params)),
  job:        (id)        => req('GET',   `/jobs/${id}`),
  patch:      (id, data)  => req('PATCH', `/jobs/${id}`, data),
  tailor:     (id)        => req('POST',  `/jobs/${id}/tailor`),
  coverLetter:(id)        => req('GET',   `/jobs/${id}/cover_letter`).then(r => r),
  saveCL:     (id, text)  => req('PATCH', `/jobs/${id}/cover_letter`, { text }),
  import:     (job)       => req('POST',  '/jobs/import', job),
  bulk:       (ids, status) => req('POST', '/jobs/bulk', { ids, status }),
  resumeUrl:  (id)        => `${BASE}/jobs/${id}/resume`,
}
