import React, { useCallback, useEffect, useRef, useState } from 'react'
import { useVisibilityAwareInterval } from 'hg_ui_kit'
import Layout from '../components/Layout.jsx'
import Breadcrumbs from '../components/Breadcrumbs.jsx'
import SharedEventSummary from '../components/SharedEventSummary.jsx'
import { api, getAdminKey } from '../lib/api.js'
import { getHashQueryParam, normalizeHashHref } from '../lib/navigationContext.js'

const SCENARIOS = [
  { value: 'weather_sweep_10', label: 'Weather (10 provinces)' },
  { value: 'swarm_weather_10_real', label: 'Swarm weather (10 provinces, proof bundle)' },
  { value: 'ticket_triage_5', label: 'Ticket triage (5)' },
  { value: 'persona_hopper_factcheck', label: 'Persona Grace Hopper factcheck' },
  { value: 'health', label: 'Health' },
  { value: '4claw_posts_3', label: '4claw (3 posts)' },
  { value: 'investor_demo', label: 'Investor demo' },
  { value: 'drift_quarantine_demo', label: 'Drift quarantine demo' },
  { value: 'prompt_injection_hardening_demo', label: 'Prompt-injection hardening demo' },
  { value: 'soak_trust_demo', label: 'Soak trust demo' },
]

export default function ProofRunnerPage() {
  const [scenario, setScenario] = useState('weather_sweep_10')
  const [useFixtures, setUseFixtures] = useState(true)
  const [running, setRunning] = useState(false)
  const [runId, setRunId] = useState(null)
  const [folder, setFolder] = useState(null)
  const [status, setStatus] = useState(null)
  const [logs, setLogs] = useState([])
  const [artifacts, setArtifacts] = useState([])
  const [err, setErr] = useState(null)
  const [confirm4claw, setConfirm4claw] = useState(false)
  const [returnUrl, setReturnUrl] = useState('#/')
  const abortRef = useRef(null)

  const pollStatus = useCallback((id) => {
    return api.proofs.getRunStatus(id).then((s) => {
      setStatus(s.status)
      setFolder(s.folder || null)
      return s
    })
  }, [])

  const streamLogs = useCallback((id) => {
    const url = api.proofs.getRunLogsUrl(id)
    abortRef.current = new AbortController()
    fetch(url, { headers: { 'Authorization': `Bearer ${getAdminKey()}` }, signal: abortRef.current.signal })
      .then((res) => {
        if (!res.ok) return
        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let buf = ''
        const read = () => {
          reader.read().then(({ done, value }) => {
            if (done) return
            buf += decoder.decode(value, { stream: true })
            const lines = buf.split('\n')
            buf = lines.pop() || ''
            for (const line of lines) {
              if (line.startsWith('data: ')) {
                try {
                  const data = JSON.parse(line.slice(6))
                  if (data?.line) setLogs((prev) => [...prev, data.line])
                } catch (_) {}
              }
            }
            read()
          }).catch(() => {})
        }
        read()
      })
      .catch(() => {})
  }, [])

  const run = useCallback((skip4clawConfirm = false) => {
    if (scenario === '4claw_posts_3' && !confirm4claw && !skip4clawConfirm) {
      setConfirm4claw(true)
      return
    }
    if (skip4clawConfirm) setConfirm4claw(true)
    setErr(null)
    setLogs([])
    setArtifacts([])
    setRunning(true)
    setRunId(null)
    setFolder(null)
    setStatus(null)
    const body = { label: scenario }
    if (useFixtures) body.params = { use_fixtures: true }
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current)
      pollIntervalRef.current = null
    }
    api.proofs.run(body)
      .then((data) => {
        setRunId(data.run_id)
        setFolder(data.folder)
        setStatus(data.status || 'running')
        streamLogs(data.run_id)
        pollIntervalRef.current = setInterval(() => {
          pollStatus(data.run_id).then((s) => {
            if (s.status === 'completed') {
              if (pollIntervalRef.current) clearInterval(pollIntervalRef.current)
              pollIntervalRef.current = null
              setRunning(false)
              api.proofs.getRunArtifacts(data.run_id).then((a) => setArtifacts(a.files || [])).catch(() => {})
            }
          }).catch(() => {
            if (pollIntervalRef.current) clearInterval(pollIntervalRef.current)
            pollIntervalRef.current = null
            setRunning(false)
          })
        }, 1500)
      })
      .catch((e) => {
        setErr(e.message)
        setRunning(false)
      })
  }, [scenario, useFixtures, confirm4claw, streamLogs])

  useVisibilityAwareInterval({
    enabled: running && !!runId,
    intervalMs: 5000,
    onTick: () => {
      pollStatus(runId)
        .then((s) => {
          if (s.status === 'completed') {
            setRunning(false)
            api.proofs.getRunArtifacts(runId).then((a) => setArtifacts(a.files || [])).catch(() => {})
          }
        })
        .catch(() => setRunning(false))
    },
  })

  useEffect(() => {
    const sync = () => setReturnUrl(normalizeHashHref(getHashQueryParam('returnUrl', '#/')))
    sync()
    window.addEventListener('hashchange', sync)
    return () => {
      window.removeEventListener('hashchange', sync)
      if (abortRef.current) abortRef.current.abort()
    }
  }, [])

  const needsConfirm = scenario === '4claw_posts_3' && !confirm4claw

  return (
    <Layout title="Proof runner">
      <Breadcrumbs items={[{ label: 'Home', href: '#/' }, { label: 'Proofs', href: '#/proofs' }, { label: 'Run proof' }]} />
      <p style={{ marginBottom: 16 }}>
        <a href="#/proofs" className="nav-link">View proofs</a>
        {' · '}
        Run a proof scenario. Results land in <code>docs/proofs/out/</code> and show up in the proof viewer.
      </p>
      {returnUrl !== '#/' && (
        <p style={{ marginBottom: 12 }}>
          <a href={returnUrl} className="nav-link">Back to origin</a>
        </p>
      )}
      <SharedEventSummary
        eyebrow="Proof runner"
        title="Run proof"
        intro="Run a scenario from an operator session. Results land in docs/proofs/out/ and show up in the proof viewer."
        status={api.proofs.hasProofAccess() ? (status || 'ready') : 'locked'}
        statusTone={api.proofs.hasProofAccess() ? (status === 'completed' ? 'good' : status === 'running' ? 'warn' : 'neutral') : 'danger'}
        happened={scenario}
        when={status || 'idle'}
        why="This is the canonical browser entry for generating trust artifacts and proof output."
        changed={`Logs ${logs.length} · artifacts ${artifacts.length}`}
        next="Run the selected scenario, then open proofs, timeline, or recovery from the same story."
        context={[
          { label: 'Scenario', value: scenario },
          { label: 'Access', value: api.proofs.hasProofAccess() ? 'operator session' : 'required' },
          { label: 'Run ID', value: runId || '—' },
        ]}
      />
      {!api.proofs.hasProofAccess() && (
        <div style={{ marginBottom: 16, padding: 12, border: '1px solid var(--border)', borderRadius: 8 }}>
          <p style={{ margin: 0, color: 'var(--danger)' }}>Sign in with an operator session to run proofs.</p>
          <p style={{ margin: '8px 0 0', color: 'var(--muted)', fontSize: 13 }}>
            The proof runner is available to operator and superadmin browser sessions. If you landed here cold, go through login once and come back.
          </p>
        </div>
      )}
      {api.proofs.hasProofAccess() && (
        <>
          {err && <p style={{ color: 'var(--danger)' }}>{err}</p>}
          {needsConfirm && (
            <div style={{ marginBottom: 16, padding: 12, border: '1px solid var(--border)', borderRadius: 8 }}>
              <p><strong>4claw (3 posts)</strong> will post to 4claw. Confirm to proceed.</p>
              <button type="button" className="btn-primary" onClick={() => run(true)}>Confirm and run</button>
              <button type="button" className="btn-secondary" style={{ marginLeft: 8 }} onClick={() => setScenario('weather_sweep_10')}>Choose another scenario</button>
            </div>
          )}
          {!needsConfirm && (
            <>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16, alignItems: 'center', marginBottom: 16 }}>
                <label>
                  Scenario{' '}
                  <select value={scenario} onChange={(e) => setScenario(e.target.value)}>
                    {SCENARIOS.map((s) => (
                      <option key={s.value} value={s.value}>{s.label}</option>
                    ))}
                  </select>
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <input type="checkbox" checked={useFixtures} onChange={(e) => setUseFixtures(e.target.checked)} />
                  Use fixtures (CI)
                </label>
                <button type="button" className="btn-primary" onClick={run} disabled={running}>
                  {running ? 'Running…' : 'Run'}
                </button>
              </div>
              {runId && (
                <div style={{ marginBottom: 16 }}>
                  <p><strong>Run ID:</strong> <code>{runId}</code></p>
                  {folder && <p><strong>Folder:</strong> <code title={folder}>{folder}</code></p>}
                  {status && <p><strong>Status:</strong> {status}</p>}
                  {status === 'running' && (
                    <p style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
                      <button
                        type="button"
                        className="btn-secondary"
                        onClick={async () => {
                          try {
                            await api.proofs.cancelRun(runId)
                            setStatus('cancel_requested')
                          } catch (e) {
                            setErr(e.message)
                          }
                        }}
                      >
                        Cancel run
                      </button>
                      <span style={{ color: 'var(--muted)', fontSize: 13 }}>
                        If this proof is stuck, cancel it here and verify the status change in the proof viewer.
                      </span>
                    </p>
                  )}
                  {status === 'completed' && (
                    <p>
                      <a href="#/proofs" className="nav-link">View proofs</a> to see latest runs.
                      {' · '}
                      <a href="#/timeline" className="nav-link">Open timeline</a>
                      {' · '}
                      <a href="#/governance" className="nav-link">Open recovery</a>
                    </p>
                  )}
                </div>
              )}
              {logs.length > 0 && (
                <div style={{ marginTop: 16 }}>
                  <h3 style={{ fontSize: 16 }}>Log output</h3>
                  <pre style={{ maxHeight: 320, overflow: 'auto', padding: 12, background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12 }}>
                    {logs.join('\n')}
                  </pre>
                </div>
              )}
              {status === 'completed' && artifacts.length > 0 && (
                <div style={{ marginTop: 16 }}>
                  <h3 style={{ fontSize: 16 }}>Output &amp; artifacts</h3>
                  <p style={{ fontSize: 14, color: 'var(--muted)', marginBottom: 8 }}>
                    Summary, weather report, checks, and screenshots from this run.
                  </p>
                  <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                    {artifacts.map((f) => (
                      <li key={f.path} style={{ marginBottom: 6, display: 'flex', alignItems: 'center', gap: 8 }}>
                        <code style={{ fontSize: 12 }}>{f.path}</code>
                        <span style={{ color: 'var(--muted)', fontSize: 12 }}>({f.size} B)</span>
                        <button
                          type="button"
                          className="btn-secondary"
                          style={{ fontSize: 12, padding: '2px 8px' }}
                          onClick={async () => {
                            try {
                              const url = api.proofs.getRunFileUrl(runId, f.path)
                              const res = await fetch(url, { headers: { 'Authorization': `Bearer ${getAdminKey()}` } })
                              if (!res.ok) throw new Error(res.statusText)
                              const blob = await res.blob()
                              const blobUrl = URL.createObjectURL(blob)
                              window.location.assign(blobUrl)
                              setTimeout(() => URL.revokeObjectURL(blobUrl), 60000)
                            } catch (e) {
                              setErr(e.message)
                            }
                          }}
                        >
                          Open
                        </button>
                        <button
                          type="button"
                          className="btn-secondary"
                          style={{ fontSize: 12, padding: '2px 8px' }}
                          onClick={async () => {
                            try {
                              const url = api.proofs.getRunFileUrl(runId, f.path)
                              const res = await fetch(url, { headers: { 'Authorization': `Bearer ${getAdminKey()}` } })
                              if (!res.ok) throw new Error(res.statusText)
                              const blob = await res.blob()
                              const a = document.createElement('a')
                              a.href = URL.createObjectURL(blob)
                              a.download = f.path.split('/').pop()
                              a.click()
                              URL.revokeObjectURL(a.href)
                            } catch (e) {
                              setErr(e.message)
                            }
                          }}
                        >
                          Download
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}
        </>
      )}
    </Layout>
  )
}
