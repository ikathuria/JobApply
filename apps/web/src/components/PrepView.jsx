import { useState, useEffect, useCallback, useContext } from 'react'
import { ThemeCtx } from './ThemeContext.jsx'
import { DARK, LIGHT } from '../theme.js'
import { api } from '../api.js'
import { Card, Btn, EmptyState, Spinner, SectionLabel, Divider, StatusBadge, Tag } from './ui/index.jsx'

function fmtDate(s) {
  return s ? String(s).slice(0, 10) : ''
}

const BUCKETS = [
  { key: 'behavioral', label: 'Behavioral' },
  { key: 'technical', label: 'Technical' },
  { key: 'system_design', label: 'System Design' },
]

function QuestionBucket({ title, items, T }) {
  if (!items || !items.length) return null
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ fontSize: 13, fontWeight: 800, color: T.text, marginBottom: 8 }}>{title}</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {items.map((it, i) => (
          <Card key={i} style={{ padding: '12px 14px' }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: T.text }}>{it.q || it.question}</div>
            {(it.talking_points || []).length > 0 && (
              <ul style={{ margin: '7px 0 0', paddingLeft: 18, color: T.muted, fontSize: 12.5, lineHeight: 1.5 }}>
                {it.talking_points.map((tp, j) => <li key={j}>{tp}</li>)}
              </ul>
            )}
          </Card>
        ))}
      </div>
    </div>
  )
}

export default function PrepView() {
  const { dark } = useContext(ThemeCtx)
  const T = dark ? DARK : LIGHT

  const [jobs, setJobs] = useState(null)
  const [selectedId, setSelectedId] = useState(null)
  const [prep, setPrep] = useState(null)          // { content, model, updated_at }
  const [loadingPrep, setLoadingPrep] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [toast, setToast] = useState(null)

  const flash = (msg, kind = 'ok') => {
    setToast({ msg, kind })
    setTimeout(() => setToast(null), 3200)
  }

  const loadJobs = useCallback(() => {
    api.prepJobs().then(setJobs).catch(() => setJobs([]))
  }, [])

  useEffect(() => { loadJobs() }, [loadJobs])

  const selectJob = (job) => {
    setSelectedId(job.id)
    setPrep(null)
    if (job.has_prep) {
      setLoadingPrep(true)
      api.getPrep(job.id)
        .then(setPrep)
        .catch(() => setPrep(null))
        .finally(() => setLoadingPrep(false))
    }
  }

  const generate = async (jobId) => {
    setGenerating(true)
    try {
      const res = await api.generatePrep(jobId)
      setPrep(res)
      loadJobs()
      flash('Prep pack generated')
    } catch (e) {
      flash(e.message || 'Generation failed — check the LLM API key', 'err')
    } finally {
      setGenerating(false)
    }
  }

  const selected = jobs?.find(j => j.id === selectedId)
  const c = prep?.content

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
      {/* ── Left: interview-stage jobs ── */}
      <div style={{ width: 320, borderRight: `1px solid ${T.border}`, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{ padding: '18px 16px 10px' }}>
          <SectionLabel style={{ marginBottom: 4 }}>Interview stage</SectionLabel>
          <div style={{ fontSize: 12, color: T.muted }}>Jobs at OA or interview — generate a tailored prep pack for each.</div>
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: '0 16px 16px', display: 'flex', flexDirection: 'column', gap: 8 }}>
          {jobs === null && <div style={{ padding: 20, textAlign: 'center' }}><Spinner /></div>}
          {jobs?.length === 0 && (
            <EmptyState icon="🎤" title="No interviews yet" sub="Jobs move here when you set their status to OA or Interview." />
          )}
          {jobs?.map(j => (
            <Card key={j.id} onClick={() => selectJob(j)}
              style={selectedId === j.id ? { borderColor: T.accent, boxShadow: `0 0 0 3px ${T.accent}18` } : {}}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
                <div style={{ fontWeight: 700, fontSize: 13.5, color: T.text, minWidth: 0 }}>{j.title}</div>
                <StatusBadge status={j.status} />
              </div>
              <div style={{ fontSize: 12, color: T.muted, marginTop: 3 }}>{j.company || '—'}</div>
              <div style={{ fontSize: 11.5, color: T.muted, marginTop: 4, display: 'flex', justifyContent: 'space-between' }}>
                <span>{j.interview_date ? `Interview ${fmtDate(j.interview_date)}` : 'No date set'}</span>
                {j.has_prep ? <span style={{ color: T.success, fontWeight: 700 }}>✓ prep</span> : <span>no prep</span>}
              </div>
            </Card>
          ))}
        </div>
      </div>

      {/* ── Right: prep pack ── */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 24 }}>
        {!selected && (
          <EmptyState icon="◌" title="Select an interview" sub="Pick a job on the left to view or generate its prep pack." />
        )}

        {selected && (
          <div>
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
              <div>
                <div style={{ fontSize: 20, fontWeight: 800, color: T.text }}>{selected.title}</div>
                <div style={{ fontSize: 13, color: T.muted, marginTop: 2 }}>
                  {selected.company}{selected.interview_date ? ` · interview ${fmtDate(selected.interview_date)}` : ''}
                </div>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <Btn size="sm" variant={c ? 'secondary' : 'primary'} onClick={() => generate(selected.id)} disabled={generating}>
                  {generating ? <Spinner size={14} color="#fff" /> : c ? 'Regenerate' : 'Generate prep'}
                </Btn>
              </div>
            </div>

            {generating && !c && (
              <Card style={{ marginTop: 18, display: 'flex', alignItems: 'center', gap: 10 }}>
                <Spinner size={16} /> <span style={{ color: T.muted, fontSize: 13 }}>Generating your prep pack…</span>
              </Card>
            )}

            {loadingPrep && <div style={{ padding: 20 }}><Spinner /></div>}

            {!loadingPrep && !c && !generating && (
              <EmptyState icon="✦" title="No prep pack yet"
                sub="Generate a tailored pack — company snapshot, topics to review, and practice questions grounded in your real experience." />
            )}

            {c && (
              <div style={{ marginTop: 18 }}>
                {c.snapshot && (
                  <Card style={{ marginBottom: 16 }}>
                    <SectionLabel>Snapshot</SectionLabel>
                    <div style={{ fontSize: 13.5, color: T.text, lineHeight: 1.55 }}>{c.snapshot}</div>
                  </Card>
                )}

                {(c.topics_to_review || []).length > 0 && (
                  <div style={{ marginBottom: 16 }}>
                    <SectionLabel>Topics to review</SectionLabel>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                      {c.topics_to_review.map((t, i) => <Tag key={i}>{t}</Tag>)}
                    </div>
                  </div>
                )}

                <SectionLabel>Practice questions</SectionLabel>
                {BUCKETS.map(b => (
                  <QuestionBucket key={b.key} title={b.label} items={c.questions?.[b.key]} T={T} />
                ))}

                {(c.questions_to_ask || []).length > 0 && (
                  <>
                    <Divider style={{ margin: '16px 0 12px' }} />
                    <SectionLabel>Questions to ask them</SectionLabel>
                    <ul style={{ margin: 0, paddingLeft: 18, color: T.text, fontSize: 13, lineHeight: 1.6 }}>
                      {c.questions_to_ask.map((q, i) => <li key={i}>{q}</li>)}
                    </ul>
                  </>
                )}

                {(c.checklist || []).length > 0 && (
                  <>
                    <Divider style={{ margin: '16px 0 12px' }} />
                    <SectionLabel>Checklist</SectionLabel>
                    <ul style={{ margin: 0, paddingLeft: 18, color: T.muted, fontSize: 13, lineHeight: 1.6 }}>
                      {c.checklist.map((q, i) => <li key={i}>{q}</li>)}
                    </ul>
                  </>
                )}

                {prep?.model && (
                  <div style={{ marginTop: 18, fontSize: 11, color: T.muted }}>
                    Generated by {prep.model}{prep.updated_at ? ` · ${fmtDate(prep.updated_at)}` : ''}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
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
