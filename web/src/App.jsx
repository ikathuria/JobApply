import { useState, useEffect, useCallback } from 'react'
import { ThemeCtx } from './components/ThemeContext.jsx'
import { DARK, LIGHT } from './theme.js'
import { api } from './api.js'
import Sidebar from './components/Sidebar.jsx'
import JobsView from './components/JobsView.jsx'
import JobDrawer from './components/JobDrawer.jsx'
import AnalyticsView from './components/AnalyticsView.jsx'
import SettingsView from './components/SettingsView.jsx'

// Persist nav state in localStorage
function loadState() {
  try { return JSON.parse(localStorage.getItem('ja_state') || '{}') } catch { return {} }
}
function saveState(s) {
  try { localStorage.setItem('ja_state', JSON.stringify(s)) } catch {}
}

export default function App() {
  const stored = loadState()

  const [dark, setDarkRaw]       = useState(stored.dark !== false)
  const [screen, setScreenRaw]   = useState(stored.screen || 'jobs')
  const [tab, setTabRaw]         = useState(stored.tab || 'new')
  const [selectedJob, setSelectedJob] = useState(null)
  const [stats, setStats]        = useState(null)
  const [refreshKey, setRefreshKey]  = useState(0)

  const setDark   = v => { setDarkRaw(v);   saveState({ dark: v, screen, tab }) }
  const setScreen = s => { setScreenRaw(s); saveState({ dark, screen: s, tab }) }
  const setTab    = t => { setTabRaw(t);    setScreenRaw('jobs'); saveState({ dark, screen: 'jobs', tab: t }); setSelectedJob(null) }

  // Refresh trigger — increments refreshKey so child components re-fetch
  const onRefresh = useCallback(() => setRefreshKey(k => k + 1), [])

  // Fetch stats on mount and after refreshes
  useEffect(() => {
    api.stats().then(setStats).catch(() => {})
  }, [refreshKey])

  const T = dark ? DARK : LIGHT

  // Keyboard shortcuts: j/k navigate, Esc closes drawer
  useEffect(() => {
    const handler = e => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return
      if (e.key === 'Escape') setSelectedJob(null)
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  return (
    <ThemeCtx.Provider value={{ dark }}>
      <div style={{
        display: 'flex', height: '100vh', overflow: 'hidden',
        background: T.bg, fontFamily: 'DM Sans, sans-serif', color: T.text,
        transition: 'background 0.18s ease, color 0.18s ease',
      }}>
        <Sidebar screen={screen} setScreen={setScreen} dark={dark} setDark={setDark} stats={stats} />

        {/* Main content */}
        <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
          {screen === 'jobs' && (
            <>
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
            </>
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
    </ThemeCtx.Provider>
  )
}
