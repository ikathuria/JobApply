import { useState, useEffect, useCallback } from 'react'
import { ThemeCtx } from './components/ThemeContext.jsx'
import { DARK, LIGHT } from './theme.js'
import { api } from './api.js'
import Sidebar from './components/Sidebar.jsx'
import Topbar from './components/Topbar.jsx'
import JobsView from './components/JobsView.jsx'
import JobDrawer from './components/JobDrawer.jsx'
import DashboardView from './components/DashboardView.jsx'
import AnalyticsView from './components/AnalyticsView.jsx'
import SettingsView from './components/SettingsView.jsx'

function loadState() {
  try { return JSON.parse(localStorage.getItem('ja_state') || '{}') } catch { return {} }
}
function saveState(s) {
  try { localStorage.setItem('ja_state', JSON.stringify(s)) } catch {}
}

export default function App() {
  const stored = loadState()

  const [dark, setDarkRaw]     = useState(stored.dark !== false)
  const [screen, setScreenRaw] = useState(stored.screen || 'dashboard')
  const [tab, setTabRaw]       = useState(stored.tab || 'new')
  const [selectedJob, setSelectedJob] = useState(null)
  const [stats, setStats]      = useState(null)
  const [refreshKey, setRefreshKey]  = useState(0)

  // Sync dark mode to body class (used by CSS custom properties)
  useEffect(() => {
    document.body.classList.toggle('dark', dark)
  }, [dark])

  const setDark   = v => { setDarkRaw(v);   saveState({ dark: v, screen, tab }) }
  const setScreen = s => { setScreenRaw(s); saveState({ dark, screen: s, tab }) }
  const setTab    = t => {
    setTabRaw(t)
    setScreenRaw('jobs')
    saveState({ dark, screen: 'jobs', tab: t })
    setSelectedJob(null)
  }

  const onRefresh = useCallback(() => setRefreshKey(k => k + 1), [])

  useEffect(() => {
    api.stats().then(setStats).catch(() => {})
  }, [refreshKey])

  useEffect(() => {
    const handler = e => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return
      if (e.key === 'Escape') setSelectedJob(null)
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  const T = dark ? DARK : LIGHT

  return (
    <ThemeCtx.Provider value={{ dark }}>
      <div className="app-root" style={{ color: T.text }}>
        <Sidebar
          screen={screen}
          setScreen={setScreen}
          dark={dark}
          setDark={setDark}
          stats={stats}
        />

        <div className="app-main">
          <Topbar screen={screen} />

          <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            {screen === 'dashboard' && (
              <DashboardView
                stats={stats}
                setTab={setTab}
                onSelectJob={job => { setSelectedJob(job); setScreen('jobs') }}
                onRefresh={refreshKey}
              />
            )}

            {screen === 'jobs' && (
              <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                  <JobsView
                    onSelectJob={setSelectedJob}
                    selectedJob={selectedJob}
                    tab={tab}
                    setTab={setTab}
                    stats={stats}
                    onRefresh={refreshKey}
                    triggerRefresh={onRefresh}
                  />
                </div>
                {selectedJob && (
                  <JobDrawer
                    job={selectedJob}
                    dark={dark}
                    onClose={() => setSelectedJob(null)}
                    onRefresh={onRefresh}
                  />
                )}
              </div>
            )}

            {screen === 'analytics' && (
              <div style={{ flex: 1, overflowY: 'auto' }}>
                <AnalyticsView stats={stats} />
              </div>
            )}

            {screen === 'settings' && (
              <div style={{ flex: 1, overflowY: 'auto' }}>
                <SettingsView />
              </div>
            )}
          </div>
        </div>
      </div>
    </ThemeCtx.Provider>
  )
}
