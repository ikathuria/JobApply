import { useState, useEffect, useContext } from 'react'
import { ThemeCtx } from './ThemeContext.jsx'
import { DARK, LIGHT } from '../theme.js'
import { api } from '../api.js'
import { Btn, Input, Divider, Spinner, SectionLabel } from './ui/index.jsx'

const PROVIDERS = ['groq', 'gemini', 'anthropic']
const SOURCES = [
  { key: 'newgrad_jobs', label: 'newgrad-jobs.com (full-time new-grad)' },
  { key: 'intern_list', label: 'intern-list.com (internships / co-ops)' },
]

export default function SettingsView() {
  const { dark } = useContext(ThemeCtx)
  const T = dark ? DARK : LIGHT

  const [s, setS] = useState(null)       // settings object from the API
  const [saving, setSaving] = useState(false)
  const [toast, setToast] = useState(null)

  const flash = (msg, kind = 'ok') => {
    setToast({ msg, kind })
    setTimeout(() => setToast(null), 3000)
  }

  useEffect(() => {
    api.getSettings().then(setS).catch(() => flash('Could not load settings', 'err'))
  }, [])

  const save = async () => {
    setSaving(true)
    try {
      const fresh = await api.saveSettings(s)
      setS(fresh)
      flash('Settings saved')
    } catch (e) {
      flash(e.message || 'Save failed', 'err')
    } finally {
      setSaving(false)
    }
  }

  if (!s) {
    return <div style={{ padding: 40 }}><Spinner /></div>
  }

  const setLLM = (k, v) => setS({ ...s, llm: { ...s.llm, [k]: v } })
  const modelField = { groq: 'groq_model', gemini: 'gemini_model', anthropic: 'anthropic_model' }[s.llm.provider]

  const selectStyle = {
    background: T.card, color: T.text, border: `1px solid ${T.border}`,
    borderRadius: 8, padding: '9px 12px', fontSize: 13, width: '100%', outline: 'none',
  }
  const rowLabel = { fontSize: 12, fontWeight: 600, color: T.text, marginBottom: 5 }

  return (
    <div style={{ padding: '28px 32px', maxWidth: 640, overflowY: 'auto', height: '100%' }}>
      <div className="page-title" style={{ marginBottom: 4 }}>Settings</div>
      <div style={{ fontSize: 13, color: T.muted, marginBottom: 4 }}>Pipeline configuration — saved to config/settings.yaml and applied to the next run.</div>
      <Divider />

      {/* LLM */}
      <SectionLabel style={{ marginTop: 20 }}>LLM provider</SectionLabel>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
        <div>
          <div style={rowLabel}>Provider</div>
          <select value={s.llm.provider} onChange={e => setLLM('provider', e.target.value)} style={selectStyle}>
            {PROVIDERS.map(p => <option key={p} value={p}>{p}</option>)}
          </select>
        </div>
        <div>
          <div style={rowLabel}>Model ({s.llm.provider})</div>
          <Input value={s.llm[modelField] || ''} onChange={v => setLLM(modelField, v)} placeholder="model name" />
        </div>
      </div>
      <div style={{ fontSize: 11, color: T.muted, marginTop: 6 }}>
        API keys are set as environment variables (GROQ_API_KEY / GOOGLE_API_KEY / ANTHROPIC_API_KEY), never here.
      </div>

      {/* Scoring + filters */}
      <SectionLabel style={{ marginTop: 24 }}>Scoring &amp; filters</SectionLabel>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, alignItems: 'end' }}>
        <div>
          <div style={rowLabel}>Minimum score</div>
          <Input type="number" value={String(s.scoring.min_score)}
            onChange={v => setS({ ...s, scoring: { ...s.scoring, min_score: v } })} placeholder="0.0" />
          <div style={{ fontSize: 11, color: T.muted, marginTop: 4 }}>Jobs below this are dropped (0 = keep all, rank by score).</div>
        </div>
        <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', fontSize: 13, color: T.text, paddingBottom: 8 }}>
          <input type="checkbox" checked={s.filters.require_known_sponsor}
            onChange={e => setS({ ...s, filters: { ...s.filters, require_known_sponsor: e.target.checked } })}
            style={{ width: 15, height: 15, accentColor: T.accent }} />
          Only keep known H-1B sponsors
        </label>
      </div>

      {/* Sources */}
      <SectionLabel style={{ marginTop: 24 }}>Job sources</SectionLabel>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 24 }}>
        {SOURCES.map(({ key, label }) => (
          <label key={key} style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', fontSize: 13, color: T.text }}>
            <input type="checkbox" checked={!!s.sources[key]}
              onChange={e => setS({ ...s, sources: { ...s.sources, [key]: e.target.checked } })}
              style={{ width: 15, height: 15, accentColor: T.accent }} />
            {label}
          </label>
        ))}
        <div style={{ fontSize: 11, color: T.muted }}>LinkedIn / Handshake are paused in code; profile data lives in config/profile.json.</div>
      </div>

      {/* Notifications */}
      <SectionLabel style={{ marginTop: 24 }}>Email notifications</SectionLabel>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 12 }}>
        {[
          ['on_offer', 'Email me when a job reaches Offer'],
          ['on_interview', 'Email me when a job reaches Interview'],
        ].map(([key, label]) => (
          <label key={key} style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', fontSize: 13, color: T.text }}>
            <input type="checkbox" checked={!!s.notifications[key]}
              onChange={e => setS({ ...s, notifications: { ...s.notifications, [key]: e.target.checked } })}
              style={{ width: 15, height: 15, accentColor: T.accent }} />
            {label}
          </label>
        ))}
      </div>
      <div style={{ marginBottom: 6 }}>
        <div style={rowLabel}>Notify email (optional)</div>
        <Input value={s.notifications.email_to}
          onChange={v => setS({ ...s, notifications: { ...s.notifications, email_to: v } })}
          placeholder="defaults to GMAIL_ADDRESS" />
      </div>
      <div style={{ fontSize: 11, color: T.muted, marginBottom: 24 }}>
        Sent via your Gmail (GMAIL_ADDRESS / GMAIL_APP_PASSWORD). No-op if those aren't set.
      </div>

      <div style={{ display: 'flex', gap: 10 }}>
        <Btn variant="primary" onClick={save} disabled={saving}>
          {saving ? <Spinner size={14} color="#fff" /> : 'Save Settings'}
        </Btn>
        <Btn variant="secondary" onClick={() => api.getSettings().then(setS)} disabled={saving}>Reload</Btn>
      </div>

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
