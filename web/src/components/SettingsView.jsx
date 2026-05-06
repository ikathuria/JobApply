import { useState, useContext } from 'react'
import { ThemeCtx } from './ThemeContext.jsx'
import { DARK, LIGHT } from '../theme.js'
import { Btn, Input, Divider } from './ui/index.jsx'

export default function SettingsView() {
  const { dark } = useContext(ThemeCtx)
  const T = dark ? DARK : LIGHT
  const [savedMsg, setSavedMsg] = useState(false)

  const Section = ({ title }) => (
    <div style={{ fontSize: 11, fontWeight: 700, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 12, marginTop: 24 }}>
      {title}
    </div>
  )

  const Field = ({ label, defaultValue = '', type = 'text', hint }) => {
    const [val, setVal] = useState(defaultValue)
    return (
      <div style={{ marginBottom: 14 }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: T.text, marginBottom: 5 }}>{label}</div>
        <Input value={val} onChange={setVal} placeholder={label} type={type} />
        {hint && <div style={{ fontSize: 11, color: T.muted, marginTop: 4 }}>{hint}</div>}
      </div>
    )
  }

  return (
    <div style={{ padding: '28px 32px', maxWidth: 640, overflowY: 'auto', height: '100%' }}>
      <div className="page-title" style={{ marginBottom: 4 }}>Settings</div>
      <div style={{ fontSize: 13, color: T.muted, marginBottom: 4 }}>Configure your profile, API keys, and preferences</div>
      <Divider />

      <Section title="Your Profile" />
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
        <Field label="Full Name"     defaultValue="Ishani Kathuria" />
        <Field label="Email"         defaultValue="ishani@purdue.edu" />
        <Field label="LinkedIn URL"  defaultValue="linkedin.com/in/ikathuria" />
        <Field label="GitHub URL"    defaultValue="github.com/ikathuria" />
        <Field label="Location"      defaultValue="West Lafayette, IN" />
        <Field label="Target Role"   defaultValue="AI/ML Intern – Summer 2026" />
      </div>

      <Section title="API Keys" />
      <div style={{ background: '#F59E0B15', border: '1px solid #F59E0B40', borderRadius: 8, padding: '10px 14px', marginBottom: 14, fontSize: 12, color: T.text }}>
        ⚠️ Set API keys in Streamlit secrets (<code>.streamlit/secrets.toml</code>) or as environment variables.
        Never commit them to git.
      </div>
      <Field label="Google Gemini API Key" defaultValue="●●●●●●●●●●●●●●●" type="password"
             hint="Used for resume tailoring and cover letter generation (GOOGLE_API_KEY)" />
      <Field label="Anthropic API Key (optional)" type="password"
             hint="Fallback LLM provider (ANTHROPIC_API_KEY)" />

      <Section title="Discovery Preferences" />
      <div style={{ marginBottom: 14 }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: T.text, marginBottom: 8 }}>Job Sources</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {['intern_list.io', 'LinkedIn', 'Handshake'].map(src => (
            <label key={src} style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', fontSize: 13, color: T.text }}>
              <input type="checkbox" defaultChecked style={{ width: 15, height: 15, accentColor: T.accent }} />
              {src}
            </label>
          ))}
        </div>
      </div>
      <Field label="Min Score Threshold" defaultValue="0.65" hint="Jobs below this score are auto-skipped" />
      <Field label="Max Daily Applications" defaultValue="10" hint="Safety limit for auto-apply runs" />

      <Section title="Application Behavior" />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 24 }}>
        {[
          ['Require human approval before every submit', true],
          ['Auto-screenshot form before submitting', true],
          ['Send email notification on new offer', false],
          ['Auto-skip jobs below min score threshold', true],
        ].map(([label, def]) => (
          <label key={label} style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', fontSize: 13, color: T.text }}>
            <input type="checkbox" defaultChecked={def} style={{ width: 15, height: 15, accentColor: T.accent }} />
            {label}
          </label>
        ))}
      </div>

      <div style={{ display: 'flex', gap: 10 }}>
        <Btn variant="primary" onClick={() => { setSavedMsg(true); setTimeout(() => setSavedMsg(false), 2000) }}>
          {savedMsg ? '✓ Saved!' : 'Save Settings'}
        </Btn>
        <Btn variant="secondary">Reset to Defaults</Btn>
      </div>
    </div>
  )
}
