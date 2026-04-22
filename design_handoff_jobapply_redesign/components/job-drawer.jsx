// Job detail drawer + Confirm Apply modal
const { useContext, useState } = React;

// ── Mock resume renderer ──────────────────────────────────────────────────────
function MockResume({ job, dark }) {
  const T = dark ? DARK : LIGHT;
  return (
    <div style={{ background: "#fff", color: "#1A1A2E", borderRadius: 8, padding: "28px 32px", fontSize: 11, lineHeight: 1.6, fontFamily: "Georgia, serif", boxShadow: "0 4px 24px rgba(0,0,0,0.15)" }}>
      <div style={{ textAlign: "center", borderBottom: "2px solid #1A1A2E", paddingBottom: 12, marginBottom: 16 }}>
        <div style={{ fontSize: 18, fontWeight: 700, letterSpacing: "0.05em", fontFamily: "DM Sans, sans-serif" }}>ISHANI KATHURIA</div>
        <div style={{ fontSize: 10, color: "#555", marginTop: 4 }}>San Francisco, CA · ishani@email.com · linkedin.com/in/ikathuria · github.com/ikathuria</div>
      </div>
      <div style={{ fontWeight: 700, fontSize: 10, textTransform: "uppercase", letterSpacing: "0.1em", borderBottom: "1px solid #ccc", marginBottom: 8 }}>Education</div>
      <div style={{ marginBottom: 12 }}>
        <div style={{ display: "flex", justifyContent: "space-between" }}><strong>University of California, Berkeley</strong><span>Aug 2022 – May 2026</span></div>
        <div>B.S. in Electrical Engineering & Computer Science · GPA: 3.92</div>
        <div style={{ color: "#555" }}>Relevant: Deep Learning, NLP, Probabilistic ML, Systems for ML</div>
      </div>
      <div style={{ fontWeight: 700, fontSize: 10, textTransform: "uppercase", letterSpacing: "0.1em", borderBottom: "1px solid #ccc", marginBottom: 8 }}>Experience</div>
      <div style={{ marginBottom: 10 }}>
        <div style={{ display: "flex", justifyContent: "space-between" }}><strong>AI Research Intern · {job.company}</strong><span style={{ color: "#8B5CF6", fontWeight: 700 }}>★ Tailored</span></div>
        <div style={{ color: "#555" }}>Expected Summer 2026</div>
        <div>• Will contribute to {job.title.toLowerCase()} research and development</div>
        <div>• Focus on large-scale model training and evaluation frameworks</div>
      </div>
      <div style={{ marginBottom: 10 }}>
        <div style={{ display: "flex", justifyContent: "space-between" }}><strong>ML Research Intern · Hugging Face</strong><span>May 2025 – Aug 2025</span></div>
        <div>• Developed novel attention mechanism, 18% faster inference on LLaMA-3</div>
        <div>• Published at NeurIPS 2025; 240+ citations in 6 months</div>
      </div>
      <div style={{ fontWeight: 700, fontSize: 10, textTransform: "uppercase", letterSpacing: "0.1em", borderBottom: "1px solid #ccc", marginBottom: 8 }}>Skills</div>
      <div style={{ color: "#444" }}>Python · PyTorch · JAX · Transformers · RLHF · CUDA · Linux · Git · SQL · React</div>
    </div>
  );
}

// ── Confirm Apply Modal ───────────────────────────────────────────────────────
function ConfirmModal({ job, onConfirm, onCancel, dark }) {
  const T = dark ? DARK : LIGHT;
  const [step, setStep] = useState("review"); // review | submitting | done
  const [checked, setChecked] = useState(false);

  if (step === "done") {
    return (
      <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)", zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center", backdropFilter: "blur(6px)" }}>
        <div style={{ background: T.surface, borderRadius: 16, padding: 40, textAlign: "center", maxWidth: 400, border: `1px solid ${T.border}` }}>
          <div style={{ fontSize: 48, marginBottom: 12 }}>🎉</div>
          <div style={{ fontSize: 20, fontWeight: 800, color: T.text, marginBottom: 8 }}>Application Submitted!</div>
          <div style={{ fontSize: 13, color: T.muted, marginBottom: 24 }}>
            Your application to <strong style={{ color: T.text }}>{job.company}</strong> has been submitted successfully.
          </div>
          <Btn variant="primary" onClick={onConfirm} size="lg">Done</Btn>
        </div>
      </div>
    );
  }

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)", zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center", backdropFilter: "blur(6px)" }}>
      <div style={{ background: T.surface, borderRadius: 16, width: 560, maxHeight: "85vh", overflow: "hidden", display: "flex", flexDirection: "column", border: `1px solid ${T.border}`, boxShadow: "0 32px 80px rgba(0,0,0,0.4)" }}>
        {/* Header */}
        <div style={{ padding: "20px 24px", borderBottom: `1px solid ${T.border}`, display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ width: 36, height: 36, borderRadius: 8, background: "#8B5CF620", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18 }}>⚡</div>
          <div>
            <div style={{ fontSize: 16, fontWeight: 800, color: T.text }}>Confirm Application</div>
            <div style={{ fontSize: 12, color: T.muted }}>Human-in-the-loop review — your approval is required</div>
          </div>
          <button onClick={onCancel} style={{ marginLeft: "auto", background: "none", border: "none", cursor: "pointer", color: T.muted, fontSize: 18 }}>✕</button>
        </div>

        <div style={{ flex: 1, overflowY: "auto", padding: "20px 24px" }}>
          {/* Job summary */}
          <div style={{ background: dark ? "#1A1A28" : "#F8F8FF", border: `1px solid ${T.border}`, borderRadius: 10, padding: "14px 16px", marginBottom: 16 }}>
            <div style={{ fontSize: 15, fontWeight: 700, color: T.text, marginBottom: 4 }}>{job.title}</div>
            <div style={{ fontSize: 12, color: T.muted, display: "flex", gap: 12 }}>
              <span>🏢 {job.company}</span>
              <span>📍 {job.location}</span>
              <span style={{ color: "#22C55E", fontWeight: 700 }}>✦ {Math.round(job.score * 100)}% match</span>
            </div>
          </div>

          {/* Resume preview */}
          <div style={{ fontSize: 11, fontWeight: 700, color: T.muted, textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: 8 }}>Tailored Resume Preview</div>
          <div style={{ borderRadius: 8, overflow: "hidden", border: `1px solid ${T.border}`, marginBottom: 16, maxHeight: 240, overflowY: "auto" }}>
            <MockResume job={job} dark={dark} />
          </div>

          {/* Warning */}
          <div style={{ background: "#F59E0B15", border: "1px solid #F59E0B40", borderRadius: 8, padding: "10px 14px", marginBottom: 16, display: "flex", gap: 10 }}>
            <span style={{ fontSize: 16, flexShrink: 0 }}>⚠️</span>
            <div style={{ fontSize: 12, color: T.text, lineHeight: 1.5 }}>
              <strong>This action cannot be undone.</strong> The AI will auto-fill and submit the application form on your behalf. Ensure your resume and cover letter are accurate before proceeding.
            </div>
          </div>

          {/* Checklist */}
          <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 20 }}>
            {["Resume is tailored and accurate", "Cover letter looks good", "I'm ready to apply to " + job.company].map((item, i) => (
              <label key={i} style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer", fontSize: 13, color: T.text }}>
                <input type="checkbox" onChange={i === 2 ? e => setChecked(e.target.checked) : undefined}
                  style={{ width: 16, height: 16, accentColor: "#8B5CF6" }} />
                {item}
              </label>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div style={{ padding: "16px 24px", borderTop: `1px solid ${T.border}`, display: "flex", gap: 10 }}>
          <Btn variant="secondary" onClick={onCancel} style={{ flex: 1 }}>Go Back</Btn>
          <Btn variant="primary" disabled={!checked} onClick={() => setStep("done")}
            style={{ flex: 2, background: checked ? "#8B5CF6" : undefined }}>
            ⚡ Submit Application
          </Btn>
        </div>
      </div>
    </div>
  );
}

// ── Job Drawer ────────────────────────────────────────────────────────────────
function JobDrawer({ job, onClose, dark, onConfirmApply }) {
  const T = dark ? DARK : LIGHT;
  const [activeTab, setActiveTab] = useState("overview");
  const [notes, setNotes] = useState(job.notes || "");
  const [jdExpanded, setJdExpanded] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  if (!job) return null;

  const score = job.score;
  const pct = Math.round(score * 100);
  const scoreColor = score >= 0.75 ? T.success : score >= 0.55 ? T.warning : T.danger;

  const drawerTabs = ["overview", "resume", "cover letter"];
  if (job.status === "ready" || job.status === "approved") {
    // already included
  }

  const primaryAction = {
    new:       { label: "✦ Tailor with AI", color: T.accent,    action: () => {} },
    ready:     { label: "⚡ Approve & Apply", color: "#8B5CF6", action: () => setShowConfirm(true) },
    approved:  { label: "⚡ Submit Application", color: "#8B5CF6", action: () => setShowConfirm(true) },
    applied:   { label: "📝 Got OA?", color: "#F59E0B",         action: () => {} },
    oa:        { label: "🎤 Got Interview?", color: "#EC4899",  action: () => {} },
    interview: { label: "🎉 Got Offer?", color: "#10B981",      action: () => {} },
    offer:     { label: "🎊 Celebrate!",  color: "#10B981",     action: () => {} },
    rejected:  null,
    skipped:   null,
  }[job.status];

  return (
    <>
      {showConfirm && (
        <ConfirmModal job={job} dark={dark}
          onConfirm={() => { setShowConfirm(false); onClose(); }}
          onCancel={() => setShowConfirm(false)}
        />
      )}

      <div style={{
        width: 440, flexShrink: 0, height: "100vh", display: "flex", flexDirection: "column",
        background: T.surface, borderLeft: `1px solid ${T.border}`,
        position: "sticky", top: 0,
      }}>
        {/* Header */}
        <div style={{ padding: "16px 20px", borderBottom: `1px solid ${T.border}`, flexShrink: 0 }}>
          <div style={{ display: "flex", alignItems: "flex-start", gap: 10, marginBottom: 10 }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 15, fontWeight: 800, color: T.text, lineHeight: 1.3, marginBottom: 4 }}>{job.title}</div>
              <div style={{ fontSize: 12, color: T.muted, display: "flex", gap: 8, flexWrap: "wrap" }}>
                <span style={{ fontWeight: 600, color: T.text }}>{job.company}</span>
                <span>·</span><span>{job.location}</span>
                <span>·</span><Tag>{job.source}</Tag>
              </div>
            </div>
            <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: T.muted, fontSize: 18, flexShrink: 0, padding: 4 }}>✕</button>
          </div>

          {/* Score + status row */}
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
            <StatusBadge status={job.status} size="md" />
            <div style={{ flex: 1 }}>
              <ScoreBar score={score} height={5} showLabel />
            </div>
          </div>

          {/* Primary action */}
          {primaryAction && (
            <button onClick={primaryAction.action}
              style={{
                width: "100%", padding: "11px 0", borderRadius: 9, border: "none", cursor: "pointer",
                background: primaryAction.color, color: "#fff", fontSize: 13, fontWeight: 700,
                fontFamily: "DM Sans, sans-serif", transition: "opacity 0.15s", letterSpacing: "0.01em",
              }}
              onMouseEnter={e => e.target.style.opacity = 0.88}
              onMouseLeave={e => e.target.style.opacity = 1}
            >{primaryAction.label}</button>
          )}
        </div>

        {/* Tabs */}
        <div style={{ display: "flex", borderBottom: `1px solid ${T.border}`, flexShrink: 0 }}>
          {drawerTabs.map(t => (
            <button key={t} onClick={() => setActiveTab(t)}
              style={{
                flex: 1, padding: "9px 4px", border: "none", cursor: "pointer", background: "transparent",
                fontFamily: "DM Sans, sans-serif", fontSize: 11, fontWeight: activeTab === t ? 700 : 500,
                color: activeTab === t ? T.accent : T.muted,
                borderBottom: activeTab === t ? `2px solid ${T.accent}` : "2px solid transparent",
                textTransform: "capitalize", transition: "all 0.12s",
              }}>{t}</button>
          ))}
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflowY: "auto", padding: "16px 20px" }}>
          {activeTab === "overview" && (
            <div>
              {/* Job description */}
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: T.muted, textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: 8 }}>Job Description</div>
                <div style={{ fontSize: 12, color: T.text, lineHeight: 1.7, whiteSpace: "pre-wrap", maxHeight: jdExpanded ? "none" : 120, overflow: "hidden", position: "relative" }}>
                  {job.description}
                </div>
                <button onClick={() => setJdExpanded(!jdExpanded)}
                  style={{ background: "none", border: "none", cursor: "pointer", color: T.accent, fontSize: 11, fontWeight: 700, padding: "4px 0", marginTop: 4 }}>
                  {jdExpanded ? "↑ Show less" : "↓ Show more"}
                </button>
              </div>

              <Divider />

              {/* Notes */}
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: T.muted, textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: 8 }}>Notes</div>
                <Textarea value={notes} onChange={setNotes} placeholder="Add notes about this job…" rows={3} />
              </div>

              {/* Interview date */}
              {job.interviewDate && (
                <div style={{ background: "#EC489915", border: "1px solid #EC489940", borderRadius: 8, padding: "10px 14px", marginBottom: 16 }}>
                  <div style={{ fontSize: 12, color: "#EC4899", fontWeight: 700 }}>🎤 Interview: April 28, 2026</div>
                  <div style={{ fontSize: 11, color: T.muted, marginTop: 3 }}>Prepare your talking points!</div>
                </div>
              )}

              {job.dateApplied && (
                <div style={{ fontSize: 12, color: T.muted, marginBottom: 8 }}>📅 Applied: {job.dateApplied}</div>
              )}

              <Divider />

              {/* Secondary actions */}
              <div style={{ fontSize: 11, fontWeight: 700, color: T.muted, textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: 10 }}>Actions</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                {job.url && <Btn variant="secondary" size="sm" onClick={() => {}} style={{ width: "100%" }}>🔗 View Posting</Btn>}
                {job.status === "new" && <Btn variant="ghost" size="sm" style={{ width: "100%", color: T.muted }}>⏭ Skip</Btn>}
                {job.status === "new" && <Btn variant="ghost" size="sm" style={{ width: "100%", color: T.danger }}>✕ Reject</Btn>}
                {["ready","approved"].includes(job.status) && <Btn variant="ghost" size="sm" style={{ width: "100%", color: T.muted }}>↩ Undo Tailor</Btn>}
                {["applied","oa","interview"].includes(job.status) && <Btn variant="ghost" size="sm" style={{ width: "100%", color: T.danger }}>✕ Got Rejected</Btn>}
              </div>
            </div>
          )}

          {activeTab === "resume" && (
            <div>
              {job.status === "new" ? (
                <div style={{ textAlign: "center", padding: "40px 0", color: T.muted }}>
                  <div style={{ fontSize: 32, marginBottom: 12 }}>◌</div>
                  <div style={{ fontWeight: 600, marginBottom: 6 }}>No resume yet</div>
                  <div style={{ fontSize: 12, marginBottom: 20 }}>Tailor this job to generate a customized resume using AI</div>
                  <Btn variant="primary">✦ Tailor Now</Btn>
                </div>
              ) : (
                <MockResume job={job} dark={dark} />
              )}
            </div>
          )}

          {activeTab === "cover letter" && (
            <div>
              {job.coverLetter ? (
                <>
                  <Textarea value={job.coverLetter} onChange={() => {}} rows={18}
                    style={{ fontSize: 12, lineHeight: 1.7 }} />
                  <div style={{ marginTop: 10, display: "flex", gap: 8 }}>
                    <Btn variant="secondary" size="sm">💾 Save edits</Btn>
                    <Btn variant="ghost" size="sm">⬇ Download PDF</Btn>
                  </div>
                </>
              ) : (
                <div style={{ textAlign: "center", padding: "40px 0", color: T.muted }}>
                  <div style={{ fontSize: 32, marginBottom: 12 }}>✉</div>
                  <div style={{ fontWeight: 600, marginBottom: 6 }}>No cover letter yet</div>
                  <div style={{ fontSize: 12, marginBottom: 20 }}>Generated automatically when you tailor this job</div>
                  <Btn variant="primary">✦ Tailor Now</Btn>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </>
  );
}

Object.assign(window, { JobDrawer, ConfirmModal });
