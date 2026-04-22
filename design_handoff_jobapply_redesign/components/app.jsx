// Root App component
const { useState, useContext, useEffect } = React;

function App() {
  const stored = (() => { try { return JSON.parse(localStorage.getItem("ja_state") || "{}"); } catch { return {}; } })();

  const [dark, setDarkRaw]       = useState(stored.dark !== false);
  const [screen, setScreen]      = useState(stored.screen || "jobs");
  const [tab, setTab]            = useState(stored.tab || "new");
  const [selectedJob, setSelectedJob] = useState(null);

  const setDark = (v) => { setDarkRaw(v); localStorage.setItem("ja_state", JSON.stringify({ dark: v, screen, tab })); };
  const goScreen = (s) => { setScreen(s); localStorage.setItem("ja_state", JSON.stringify({ dark, screen: s, tab })); };
  const goTab = (t) => { setTab(t); setScreen("jobs"); localStorage.setItem("ja_state", JSON.stringify({ dark, screen: "jobs", tab: t })); };

  const T = dark ? DARK : LIGHT;

  // Tweaks protocol
  useEffect(() => {
    const handler = (e) => {
      if (e.data?.type === "__activate_edit_mode")   document.getElementById("tweaks-panel").style.display = "flex";
      if (e.data?.type === "__deactivate_edit_mode") document.getElementById("tweaks-panel").style.display = "none";
    };
    window.addEventListener("message", handler);
    window.parent.postMessage({ type: "__edit_mode_available" }, "*");
    return () => window.removeEventListener("message", handler);
  }, []);

  return (
    <ThemeCtx.Provider value={{ dark }}>
      <div style={{
        display: "flex", height: "100vh", overflow: "hidden",
        background: T.bg, fontFamily: "DM Sans, sans-serif", color: T.text,
        transition: "background 0.2s, color 0.2s",
      }}>
        <Sidebar screen={screen} setScreen={goScreen} dark={dark} setDark={setDark} />

        {/* Main content */}
        <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
          {screen === "jobs" && (
            <>
              <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
                <JobsView
                  onSelectJob={setSelectedJob}
                  selectedJob={selectedJob}
                  tab={tab}
                  setTab={goTab}
                />
              </div>
              {selectedJob && (
                <JobDrawer
                  job={selectedJob}
                  dark={dark}
                  onClose={() => setSelectedJob(null)}
                  onConfirmApply={() => setSelectedJob(null)}
                />
              )}
            </>
          )}
          {screen === "analytics" && (
            <div style={{ flex: 1, overflowY: "auto" }}>
              <AnalyticsView />
            </div>
          )}
          {screen === "settings" && (
            <div style={{ flex: 1, overflowY: "auto" }}>
              <SettingsView />
            </div>
          )}
        </div>

        {/* Tweaks panel */}
        <div id="tweaks-panel" style={{
          display: "none", position: "fixed", bottom: 20, right: 20, zIndex: 999,
          background: T.surface, border: `1px solid ${T.border}`, borderRadius: 12,
          padding: "16px 18px", flexDirection: "column", gap: 12, minWidth: 200,
          boxShadow: "0 8px 32px rgba(0,0,0,0.3)",
        }}>
          <div style={{ fontSize: 12, fontWeight: 800, color: T.text, letterSpacing: "0.05em" }}>TWEAKS</div>
          <div>
            <div style={{ fontSize: 11, color: T.muted, marginBottom: 6, fontWeight: 600 }}>Theme</div>
            <div style={{ display: "flex", gap: 6 }}>
              {["Dark", "Light"].map(v => (
                <button key={v} onClick={() => setDark(v === "Dark")}
                  style={{ flex: 1, padding: "5px 0", borderRadius: 6, border: `1px solid ${T.border}`, cursor: "pointer", fontSize: 11, fontWeight: 700, fontFamily: "DM Sans, sans-serif", background: (dark ? v === "Dark" : v === "Light") ? T.accent : "transparent", color: (dark ? v === "Dark" : v === "Light") ? "#fff" : T.muted }}>{v}</button>
              ))}
            </div>
          </div>
          <div>
            <div style={{ fontSize: 11, color: T.muted, marginBottom: 6, fontWeight: 600 }}>Active Screen</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {["jobs", "analytics", "settings"].map(s => (
                <button key={s} onClick={() => goScreen(s)}
                  style={{ padding: "5px 10px", borderRadius: 6, border: `1px solid ${T.border}`, cursor: "pointer", fontSize: 11, fontWeight: 700, fontFamily: "DM Sans, sans-serif", textAlign: "left", background: screen === s ? T.accentBg : "transparent", color: screen === s ? T.accent : T.muted, textTransform: "capitalize" }}>{s}</button>
              ))}
            </div>
          </div>
          <div>
            <div style={{ fontSize: 11, color: T.muted, marginBottom: 6, fontWeight: 600 }}>Active Tab (Jobs)</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
              {["new","ready","applied","all"].map(t => (
                <button key={t} onClick={() => goTab(t)}
                  style={{ padding: "4px 8px", borderRadius: 5, border: `1px solid ${T.border}`, cursor: "pointer", fontSize: 10, fontWeight: 700, fontFamily: "DM Sans, sans-serif", background: tab === t ? T.accentBg : "transparent", color: tab === t ? T.accent : T.muted, textTransform: "capitalize" }}>{t}</button>
              ))}
            </div>
          </div>
          <div>
            <div style={{ fontSize: 11, color: T.muted, marginBottom: 6, fontWeight: 600 }}>Preview Job Detail</div>
            <button onClick={() => { setScreen("jobs"); setSelectedJob(window.JOBS[0]); }}
              style={{ width: "100%", padding: "6px 0", borderRadius: 6, border: `1px solid ${T.border}`, cursor: "pointer", fontSize: 11, fontWeight: 700, fontFamily: "DM Sans, sans-serif", background: T.accentBg, color: T.accent }}>Open Drawer</button>
          </div>
          <div>
            <div style={{ fontSize: 11, color: T.muted, marginBottom: 6, fontWeight: 600 }}>Confirm Modal</div>
            <button onClick={() => { setScreen("jobs"); setSelectedJob(window.JOBS[0]); }}
              style={{ width: "100%", padding: "6px 0", borderRadius: 6, border: `1px solid #8B5CF6`, cursor: "pointer", fontSize: 11, fontWeight: 700, fontFamily: "DM Sans, sans-serif", background: "#8B5CF615", color: "#8B5CF6" }}>Preview Apply Flow</button>
          </div>
        </div>
      </div>
    </ThemeCtx.Provider>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
