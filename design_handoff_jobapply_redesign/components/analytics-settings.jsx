// Analytics + Settings screens
const { useContext, useState } = React;

// ── Analytics ─────────────────────────────────────────────────────────────────
function AnalyticsView() {
  const { dark } = useContext(ThemeCtx);
  const T = dark ? DARK : LIGHT;
  const s = window.STATS;

  const funnel = [
    { label: "Discovered",  value: s.total,     color: "#6366F1" },
    { label: "New",         value: s.new,        color: "#6B7280" },
    { label: "Tailored",    value: s.ready,      color: "#22C55E" },
    { label: "Applied",     value: s.applied,    color: "#3B82F6" },
    { label: "OA",          value: s.oa,         color: "#F59E0B" },
    { label: "Interview",   value: s.interview,  color: "#EC4899" },
    { label: "Offer",       value: s.offer,      color: "#10B981" },
  ];

  const maxVal = funnel[0].value;

  const conversionRows = [
    { from: "Discovered → Applied", rate: ((s.applied / s.total) * 100).toFixed(1), color: "#3B82F6" },
    { from: "Applied → OA",         rate: ((s.oa / Math.max(s.applied,1)) * 100).toFixed(1), color: "#F59E0B" },
    { from: "OA → Interview",       rate: ((s.interview / Math.max(s.oa,1)) * 100).toFixed(1), color: "#EC4899" },
    { from: "Interview → Offer",    rate: ((s.offer / Math.max(s.interview,1)) * 100).toFixed(1), color: "#10B981" },
  ];

  const sourceData = [
    { label: "intern_list", count: 420, color: "#6366F1" },
    { label: "linkedin",    count: 340, color: "#0A66C2" },
    { label: "handshake",   count: 125, color: "#E8534A" },
  ];
  const totalSrc = sourceData.reduce((a, b) => a + b.count, 0);

  return (
    <div style={{ padding: "28px 32px", overflowY: "auto", height: "100%" }}>
      <div style={{ fontSize: 20, fontWeight: 800, color: T.text, marginBottom: 4 }}>Pipeline Analytics</div>
      <div style={{ fontSize: 13, color: T.muted, marginBottom: 28 }}>Summer 2026 AI/ML Internship Search</div>

      {/* Top stats */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14, marginBottom: 28 }}>
        {[
          { label: "Total Discovered", value: s.total, color: T.accent },
          { label: "Applied",          value: s.applied, color: "#3B82F6" },
          { label: "In Pipeline",      value: s.oa + s.interview, color: "#EC4899" },
          { label: "Offers",           value: s.offer, color: "#10B981" },
        ].map(st => (
          <div key={st.label} style={{ background: T.card, border: `1px solid ${T.border}`, borderRadius: 12, padding: "16px 20px" }}>
            <div style={{ fontSize: 28, fontWeight: 800, color: st.color, letterSpacing: "-0.03em" }}>{st.value}</div>
            <div style={{ fontSize: 11, fontWeight: 700, color: T.muted, textTransform: "uppercase", letterSpacing: "0.07em", marginTop: 4 }}>{st.label}</div>
          </div>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 20, marginBottom: 20 }}>
        {/* Funnel */}
        <div style={{ background: T.card, border: `1px solid ${T.border}`, borderRadius: 12, padding: "20px 24px" }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: T.text, marginBottom: 20 }}>Application Funnel</div>
          {funnel.map((stage, i) => {
            const width = (stage.value / maxVal) * 100;
            const prevVal = i > 0 ? funnel[i-1].value : stage.value;
            const dropPct = prevVal > 0 ? Math.round((1 - stage.value / prevVal) * 100) : 0;
            return (
              <div key={stage.label} style={{ marginBottom: 10 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
                  <div style={{ fontSize: 11, color: T.muted, width: 76, flexShrink: 0 }}>{stage.label}</div>
                  <div style={{ flex: 1, height: 22, background: dark ? "#252538" : "#E8E8F4", borderRadius: 4, overflow: "hidden", position: "relative" }}>
                    <div style={{ width: `${width}%`, height: "100%", background: stage.color, borderRadius: 4, display: "flex", alignItems: "center", paddingLeft: 8, transition: "width 0.6s ease", minWidth: stage.value > 0 ? 28 : 0 }}>
                      <span style={{ fontSize: 10, fontWeight: 800, color: "#fff", fontFamily: "JetBrains Mono, monospace" }}>{stage.value}</span>
                    </div>
                  </div>
                  {i > 0 && dropPct > 0 && (
                    <div style={{ fontSize: 10, color: T.muted, width: 44, textAlign: "right", flexShrink: 0 }}>-{dropPct}%</div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Conversion rates + source breakdown */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ background: T.card, border: `1px solid ${T.border}`, borderRadius: 12, padding: "18px 20px" }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: T.text, marginBottom: 14 }}>Conversion Rates</div>
            {conversionRows.map(row => (
              <div key={row.from} style={{ marginBottom: 10 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                  <span style={{ fontSize: 11, color: T.muted }}>{row.from}</span>
                  <span style={{ fontSize: 11, fontWeight: 800, color: row.color, fontFamily: "JetBrains Mono, monospace" }}>{row.rate}%</span>
                </div>
                <div style={{ height: 4, background: dark ? "#252538" : "#E8E8F4", borderRadius: 4, overflow: "hidden" }}>
                  <div style={{ width: `${Math.min(parseFloat(row.rate), 100)}%`, height: "100%", background: row.color, borderRadius: 4 }} />
                </div>
              </div>
            ))}
          </div>

          <div style={{ background: T.card, border: `1px solid ${T.border}`, borderRadius: 12, padding: "18px 20px" }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: T.text, marginBottom: 14 }}>Source Breakdown</div>
            {sourceData.map(src => (
              <div key={src.label} style={{ marginBottom: 10 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                  <span style={{ fontSize: 11, color: T.muted, fontFamily: "JetBrains Mono, monospace" }}>{src.label}</span>
                  <span style={{ fontSize: 11, fontWeight: 800, color: T.text }}>{src.count}</span>
                </div>
                <div style={{ height: 4, background: dark ? "#252538" : "#E8E8F4", borderRadius: 4, overflow: "hidden" }}>
                  <div style={{ width: `${(src.count / totalSrc) * 100}%`, height: "100%", background: src.color, borderRadius: 4 }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Sankey-style flow */}
      <div style={{ background: T.card, border: `1px solid ${T.border}`, borderRadius: 12, padding: "20px 24px" }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: T.text, marginBottom: 6 }}>Pipeline Flow</div>
        <div style={{ fontSize: 11, color: T.muted, marginBottom: 20 }}>Where jobs end up after discovery</div>
        <svg viewBox="0 0 700 160" style={{ width: "100%", height: 160 }}>
          {/* Flow bands — simplified Sankey */}
          {/* Discovered → Applied */}
          <path d="M 0,20 C 120,20 120,60 240,60 L 240,100 C 120,100 120,60 0,60 Z" fill="#3B82F630" />
          {/* Discovered → Skipped/Rejected */}
          <path d="M 0,65 C 120,65 120,130 240,130 L 240,155 C 120,155 120,140 0,100 Z" fill="#EF444420" />
          {/* Applied → OA */}
          <path d="M 240,62 C 360,62 360,70 480,70 L 480,82 C 360,82 360,74 240,74 Z" fill="#F59E0B40" />
          {/* Applied → Ghosted */}
          <path d="M 240,78 C 360,78 360,110 480,110 L 480,125 C 360,125 360,95 240,100 Z" fill="#6B728030" />
          {/* OA → Interview */}
          <path d="M 480,71 C 580,71 580,76 680,76 L 680,82 C 580,82 580,78 480,80 Z" fill="#EC489940" />
          {/* OA → Rejected */}
          <path d="M 480,83 C 580,83 580,105 680,105 L 680,118 C 580,118 580,98 480,98 Z" fill="#EF444430" />

          {/* Node labels */}
          {[
            { x: 0, y: 10, label: "885", sub: "Discovered", color: "#6366F1" },
            { x: 240, y: 52, label: "368", sub: "Applied", color: "#3B82F6" },
            { x: 480, y: 62, label: "4", sub: "OA", color: "#F59E0B" },
            { x: 680, y: 68, label: "2", sub: "Interview", color: "#EC4899" },
          ].map(n => (
            <g key={n.label + n.sub}>
              <text x={n.x + 4} y={n.y} fontFamily="JetBrains Mono" fontSize="13" fontWeight="800" fill={n.color}>{n.label}</text>
              <text x={n.x + 4} y={n.y + 13} fontFamily="DM Sans" fontSize="9" fill="#8888A0">{n.sub}</text>
            </g>
          ))}

          {/* Drop-off labels */}
          <text x={100} y={148} fontFamily="DM Sans" fontSize="9" fill="#EF4444">157 skipped/rejected</text>
          <text x={340} y={130} fontFamily="DM Sans" fontSize="9" fill="#6B7280">364 no response</text>
          <text x={580} y={125} fontFamily="DM Sans" fontSize="9" fill="#EF4444">2 rejected post-OA</text>
        </svg>
      </div>
    </div>
  );
}

// ── Settings ──────────────────────────────────────────────────────────────────
function SettingsView() {
  const { dark } = useContext(ThemeCtx);
  const T = dark ? DARK : LIGHT;
  const [geminiKey, setGeminiKey] = useState("●●●●●●●●●●●●●●●●●●●●");
  const [savedMsg, setSavedMsg] = useState(false);

  const section = (title) => (
    <div style={{ fontSize: 11, fontWeight: 700, color: T.muted, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 12, marginTop: 24 }}>{title}</div>
  );

  const field = (label, value, onChange, type = "text", hint) => (
    <div style={{ marginBottom: 14 }}>
      <div style={{ fontSize: 12, fontWeight: 600, color: T.text, marginBottom: 5 }}>{label}</div>
      <Input value={value} onChange={onChange} placeholder={label} style={{}} />
      {hint && <div style={{ fontSize: 11, color: T.muted, marginTop: 4 }}>{hint}</div>}
    </div>
  );

  return (
    <div style={{ padding: "28px 32px", maxWidth: 640, overflowY: "auto", height: "100%" }}>
      <div style={{ fontSize: 20, fontWeight: 800, color: T.text, marginBottom: 4 }}>Settings</div>
      <div style={{ fontSize: 13, color: T.muted, marginBottom: 4 }}>Configure your profile, API keys, and preferences</div>
      <Divider />

      {section("Your Profile")}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
        {field("Full Name", "Ishani Kathuria", () => {})}
        {field("Email", "ishani@berkeley.edu", () => {})}
        {field("LinkedIn URL", "linkedin.com/in/ikathuria", () => {})}
        {field("GitHub URL", "github.com/ikathuria", () => {})}
        {field("Location", "San Francisco, CA", () => {})}
        {field("Target Role", "AI/ML Intern – Summer 2026", () => {})}
      </div>

      {section("API Keys")}
      <div style={{ background: "#F59E0B15", border: "1px solid #F59E0B40", borderRadius: 8, padding: "10px 14px", marginBottom: 14, fontSize: 12, color: T.text }}>
        ⚠️ Keys are stored locally and used only by your local instance. Never commit them to git.
      </div>
      {field("Google Gemini API Key", geminiKey, setGeminiKey, "password", "Used for resume tailoring and cover letter generation")}
      {field("Anthropic API Key (optional)", "", () => {}, "password", "Fallback LLM provider")}

      {section("Discovery Preferences")}
      <div style={{ marginBottom: 14 }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: T.text, marginBottom: 8 }}>Job Sources</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {["intern_list.io", "LinkedIn", "Handshake"].map(src => (
            <label key={src} style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer", fontSize: 13, color: T.text }}>
              <input type="checkbox" defaultChecked style={{ width: 15, height: 15, accentColor: T.accent }} />
              {src}
            </label>
          ))}
        </div>
      </div>
      {field("Min Score Threshold", "0.65", () => {}, "number", "Jobs below this score are auto-skipped")}
      {field("Max Daily Applications", "10", () => {}, "number", "Safety limit for auto-apply runs")}

      {section("Application Behavior")}
      <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 20 }}>
        {[
          ["Require human approval before every submit", true],
          ["Auto-screenshot form before submitting", true],
          ["Send email notification on new offer", false],
          ["Auto-skip jobs below min score threshold", true],
        ].map(([label, def]) => (
          <label key={label} style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer", fontSize: 13, color: T.text }}>
            <input type="checkbox" defaultChecked={def} style={{ width: 15, height: 15, accentColor: T.accent }} />
            {label}
          </label>
        ))}
      </div>

      <div style={{ display: "flex", gap: 10 }}>
        <Btn variant="primary" onClick={() => { setSavedMsg(true); setTimeout(() => setSavedMsg(false), 2000); }}>
          {savedMsg ? "✓ Saved!" : "Save Settings"}
        </Btn>
        <Btn variant="secondary">Reset to Defaults</Btn>
      </div>
    </div>
  );
}

Object.assign(window, { AnalyticsView, SettingsView });
