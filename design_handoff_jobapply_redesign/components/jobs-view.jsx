// Jobs view — focus queue, tabs, job list
const { useContext, useState, useMemo } = React;

function FocusQueue({ onSelectJob, setTab }) {
  const { dark } = useContext(ThemeCtx);
  const T = dark ? DARK : LIGHT;
  const items = window.FOCUS_ITEMS;

  return (
    <div style={{ marginBottom: 24 }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: T.muted, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 10 }}>
        Today's Focus
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 10 }}>
        {items.map(item => (
          <div key={item.id}
            onClick={() => {
              if (item.jobId) onSelectJob(window.JOBS.find(j => j.id === item.jobId));
              else setTab(item.tab);
            }}
            style={{
              background: T.card, border: `1px solid ${T.border}`,
              borderLeft: `3px solid ${item.color}`,
              borderRadius: 10, padding: "12px 14px", cursor: "pointer",
              transition: "all 0.15s",
              display: "flex", flexDirection: "column", gap: 6,
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = item.color; e.currentTarget.style.boxShadow = `0 0 0 3px ${item.color}18`; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = T.border; e.currentTarget.style.borderLeftColor = item.color; e.currentTarget.style.boxShadow = "none"; }}
          >
            <div style={{ display: "flex", alignItems: "flex-start", gap: 8 }}>
              <span style={{ fontSize: 16, lineHeight: 1.2 }}>{item.icon}</span>
              <span style={{ fontSize: 12, color: T.text, fontWeight: 500, flex: 1, lineHeight: 1.4 }}>{item.label}</span>
            </div>
            <span style={{ fontSize: 11, fontWeight: 700, color: item.color, alignSelf: "flex-start" }}>{item.cta} →</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function JobRow({ job, onSelect, selected }) {
  const { dark } = useContext(ThemeCtx);
  const T = dark ? DARK : LIGHT;
  const [hov, setHov] = useState(false);
  const score = job.score;
  const pct = Math.round(score * 100);
  const scoreColor = score >= 0.75 ? T.success : score >= 0.55 ? T.warning : T.danger;
  const isActive = selected;

  const nextAction = {
    new:       { label: "Tailor", color: T.accent },
    ready:     { label: "Approve", color: "#8B5CF6" },
    approved:  { label: "Apply", color: T.accent },
    applied:   { label: "Track", color: "#3B82F6" },
    oa:        { label: "Update", color: "#F59E0B" },
    interview: { label: "Prep", color: "#EC4899" },
    offer:     { label: "View", color: T.success },
    rejected:  { label: "View", color: T.muted },
    skipped:   { label: "View", color: T.muted },
  }[job.status] || { label: "View", color: T.muted };

  return (
    <div onClick={() => onSelect(job)}
      onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      style={{
        display: "flex", alignItems: "center", gap: 12, padding: "10px 16px",
        borderRadius: 8, cursor: "pointer", transition: "all 0.12s",
        background: isActive ? T.accentBg : hov ? (dark ? "#1E1E2E" : "#F0F0FA") : "transparent",
        borderLeft: isActive ? `2px solid ${T.accent}` : "2px solid transparent",
        marginBottom: 1,
      }}>

      {/* Score circle */}
      <div style={{
        width: 36, height: 36, borderRadius: "50%", flexShrink: 0,
        background: `conic-gradient(${scoreColor} ${pct * 3.6}deg, ${dark ? "#252538" : "#E2E2EE"} 0deg)`,
        display: "flex", alignItems: "center", justifyContent: "center",
        position: "relative",
      }}>
        <div style={{
          width: 26, height: 26, borderRadius: "50%", background: isActive ? T.accentBg : (dark ? T.surface : "#fff"),
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 9, fontWeight: 800, color: scoreColor, fontFamily: "JetBrains Mono, monospace",
        }}>{pct}</div>
      </div>

      {/* Title + company */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: T.text, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", display: "flex", alignItems: "center", gap: 6 }}>
          {job.starred && <span style={{ color: "#F59E0B", fontSize: 10 }}>★</span>}
          {job.title}
        </div>
        <div style={{ fontSize: 11, color: T.muted, display: "flex", alignItems: "center", gap: 6, marginTop: 1 }}>
          <span style={{ fontWeight: 600 }}>{job.company}</span>
          <span>·</span>
          <span>{job.location}</span>
          {job.interviewDate && <span style={{ color: "#EC4899", fontWeight: 600 }}>· Apr 28</span>}
        </div>
      </div>

      {/* Source tag */}
      <Tag style={{ display: hov || isActive ? "inline" : "none" }}>{job.source}</Tag>

      {/* Status badge */}
      <StatusBadge status={job.status} />

      {/* Action hint */}
      {(hov || isActive) && (
        <div style={{ fontSize: 11, fontWeight: 700, color: nextAction.color, whiteSpace: "nowrap", minWidth: 50, textAlign: "right" }}>
          {nextAction.label} →
        </div>
      )}
    </div>
  );
}

const TABS = [
  { id: "new",      label: "New",      count: () => window.STATS.new },
  { id: "ready",    label: "Ready",    count: () => window.STATS.ready },
  { id: "approved", label: "Approved", count: () => window.STATS.approved },
  { id: "applied",  label: "Applied",  count: () => window.STATS.applied + window.STATS.oa + window.STATS.interview },
  { id: "all",      label: "All",      count: () => window.STATS.total },
];

function JobsView({ onSelectJob, selectedJob, tab, setTab }) {
  const { dark } = useContext(ThemeCtx);
  const T = dark ? DARK : LIGHT;
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState("score");
  const [minScore, setMinScore] = useState(0);

  const filteredJobs = useMemo(() => {
    let jobs = window.JOBS;
    // Tab filter
    if (tab === "new")      jobs = jobs.filter(j => j.status === "new");
    else if (tab === "ready")    jobs = jobs.filter(j => j.status === "ready");
    else if (tab === "approved") jobs = jobs.filter(j => j.status === "approved");
    else if (tab === "applied")  jobs = jobs.filter(j => ["applied","oa","interview","offer"].includes(j.status));
    // Search
    if (search) {
      const q = search.toLowerCase();
      jobs = jobs.filter(j => j.title.toLowerCase().includes(q) || j.company.toLowerCase().includes(q) || j.location.toLowerCase().includes(q));
    }
    // Score filter
    jobs = jobs.filter(j => j.score >= minScore);
    // Sort
    if (sort === "score")   jobs = [...jobs].sort((a, b) => b.score - a.score);
    if (sort === "company") jobs = [...jobs].sort((a, b) => a.company.localeCompare(b.company));
    if (sort === "starred") jobs = [...jobs].sort((a, b) => (b.starred ? 1 : 0) - (a.starred ? 1 : 0));
    // Starred always first within sort
    return [...jobs.filter(j => j.starred), ...jobs.filter(j => !j.starred)];
  }, [tab, search, sort, minScore]);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      {/* Focus queue */}
      <div style={{ padding: "20px 24px 0", flexShrink: 0 }}>
        <FocusQueue onSelectJob={onSelectJob} setTab={setTab} />
      </div>

      {/* Tab bar */}
      <div style={{ padding: "0 24px", flexShrink: 0, borderBottom: `1px solid ${T.border}`, display: "flex", alignItems: "center", gap: 4 }}>
        {TABS.map(t => {
          const active = tab === t.id;
          const count = t.count();
          return (
            <button key={t.id} onClick={() => setTab(t.id)}
              style={{
                padding: "10px 14px", border: "none", cursor: "pointer", borderRadius: "8px 8px 0 0",
                background: "transparent", fontFamily: "DM Sans, sans-serif",
                fontSize: 12, fontWeight: active ? 700 : 500,
                color: active ? T.accent : T.muted,
                borderBottom: active ? `2px solid ${T.accent}` : "2px solid transparent",
                display: "flex", alignItems: "center", gap: 6, transition: "all 0.12s",
              }}>
              {t.label}
              {count > 0 && (
                <span style={{
                  background: active ? T.accent : (dark ? "#252538" : "#E2E2EE"),
                  color: active ? "#fff" : T.muted,
                  fontSize: 10, fontWeight: 800, borderRadius: 10, padding: "1px 6px",
                }}>{count}</span>
              )}
            </button>
          );
        })}

        <div style={{ flex: 1 }} />

        {/* Import button */}
        <button style={{
          padding: "6px 12px", borderRadius: 6, border: `1px solid ${T.border}`,
          background: "transparent", color: T.muted, fontSize: 11, fontWeight: 600,
          cursor: "pointer", fontFamily: "DM Sans, sans-serif", marginBottom: 2,
        }}>+ Import</button>
      </div>

      {/* Filter bar */}
      <div style={{ padding: "12px 24px", flexShrink: 0, display: "flex", gap: 10, alignItems: "center" }}>
        <Input value={search} onChange={setSearch} placeholder="Search title, company, location…" icon="⌕" style={{ flex: 1, maxWidth: 360 }} />

        <select value={sort} onChange={e => setSort(e.target.value)} style={{
          padding: "8px 12px", borderRadius: 8, border: `1px solid ${T.border}`,
          background: dark ? "#1A1A28" : "#FAFAFA", color: T.text,
          fontSize: 12, fontFamily: "DM Sans, sans-serif", cursor: "pointer", outline: "none",
        }}>
          <option value="score">Score ↓</option>
          <option value="company">Company A–Z</option>
          <option value="starred">Starred first</option>
        </select>

        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 11, color: T.muted, whiteSpace: "nowrap" }}>Min score</span>
          <input type="range" min={0} max={1} step={0.05} value={minScore}
            onChange={e => setMinScore(parseFloat(e.target.value))}
            style={{ width: 80, accentColor: T.accent }}
          />
          <span style={{ fontSize: 11, color: T.text, fontFamily: "JetBrains Mono, monospace", width: 32 }}>{Math.round(minScore * 100)}%</span>
        </div>

        <div style={{ fontSize: 11, color: T.muted, whiteSpace: "nowrap" }}>
          {filteredJobs.length} jobs
        </div>
      </div>

      {/* Job list */}
      <div style={{ flex: 1, overflowY: "auto", padding: "0 12px 24px" }}>
        {filteredJobs.length === 0 ? (
          <div style={{ textAlign: "center", padding: "60px 0", color: T.muted }}>
            <div style={{ fontSize: 32, marginBottom: 12 }}>◌</div>
            <div style={{ fontSize: 14, fontWeight: 600 }}>No jobs match these filters</div>
            <div style={{ fontSize: 12, marginTop: 4 }}>Try adjusting the score or search</div>
          </div>
        ) : (
          filteredJobs.map(job => (
            <JobRow key={job.id} job={job} onSelect={onSelectJob} selected={selectedJob?.id === job.id} />
          ))
        )}

        {tab === "new" && (
          <div style={{ textAlign: "center", padding: "16px 0", color: T.muted, fontSize: 12 }}>
            Showing {filteredJobs.length} of {window.STATS.new} new jobs · sorted by AI score
          </div>
        )}
      </div>
    </div>
  );
}

Object.assign(window, { JobsView });
