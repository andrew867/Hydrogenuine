import React, { useEffect, useState, useRef } from 'react'
import Layout from '../components/Layout.jsx'
import JsonBlock from '../components/JsonBlock.jsx'
import MermaidBlock from '../components/MermaidBlock.jsx'
import Breadcrumbs from '../components/Breadcrumbs.jsx'
import SharedEventSummary from '../components/SharedEventSummary.jsx'
import { api } from '../lib/api.js'
import { formatDateTime } from '../lib/timezone.js'
import { buildHashHref, getCurrentHashWithoutReturnUrl, getHashQueryParam, normalizeHashHref } from '../lib/navigationContext.js'
import { AsyncPageBody } from '../components/PageStates.jsx'

export default function RunDetail({ runId }) {
  const [run, setRun] = useState(null)
  const [arts, setArts] = useState([])
  const [snaps, setSnaps] = useState([])
  const [checkpoints, setCheckpoints] = useState([])
  const [events, setEvents] = useState([])
  const [runState, setRunState] = useState(null)
  const [memoryData, setMemoryData] = useState(null)
  const [contextData, setContextData] = useState(null)
  const [activeTab, setActiveTab] = useState('memory')
  const [err, setErr] = useState(null)
  const eventSourceRef = useRef(null)
  const [ownershipChain, setOwnershipChain] = useState([])
  const [ownershipEdges, setOwnershipEdges] = useState([])
  const [ownershipEvents, setOwnershipEvents] = useState([])
  const [ownershipAvailability, setOwnershipAvailability] = useState(null)
  const [ownershipSearchQ, setOwnershipSearchQ] = useState('')
  const [ownershipSearchHits, setOwnershipSearchHits] = useState([])
  const [ownershipError, setOwnershipError] = useState(null)
  const [analytics, setAnalytics] = useState(null)
  const [toolTrace, setToolTrace] = useState([])
  const [toolTraceNote, setToolTraceNote] = useState('')
  const [delegationSummary, setDelegationSummary] = useState(null)
  const [delegationAnomalies, setDelegationAnomalies] = useState([])
  const [lineageSummary, setLineageSummary] = useState(null)
  const returnUrl = normalizeHashHref(getHashQueryParam('returnUrl', '#/'))
  const currentReturnUrl = getCurrentHashWithoutReturnUrl()
  const runDagHref = buildHashHref('#/run', { run_id: runId, returnUrl: currentReturnUrl })
  const compareHref = buildHashHref('#/compare', { left: runId, returnUrl: currentReturnUrl })

  const refresh = async () => {
    try {
      setErr(null)
      const r = await api.getRun(runId)
      if (!r || r.ok === false) {
        setRun(null)
        setErr(r?.error?.message || r?.error?.code || 'Run not found')
        return
      }
      setRun(r)
      try {
        const lRes = await api.getRunLineage(runId)
        setLineageSummary(lRes.ok === false ? null : lRes)
      } catch { setLineageSummary(null) }
      const noRunDir = r.run_dir_missing || (r.status === 'blocked' && !r.run_dir) || (r.status === 'pending_approval' && !r.run_dir)
      if (noRunDir) {
        setArts([])
        setSnaps([])
        setCheckpoints([])
        setRunState(null)
        setMemoryData(null)
        setContextData(null)
        setOwnershipChain([])
        setOwnershipEdges([])
        setOwnershipEvents([])
        setOwnershipAvailability(null)
        setAnalytics(null)
        setToolTrace([])
        setToolTraceNote('')
        setDelegationSummary(null)
        setDelegationAnomalies([])
        return
      }
      const a = await api.listArtifacts(runId)
      setArts(a.artifacts || [])
      const s = await api.listSnapshots(runId)
      setSnaps(s.snapshots || [])
      const c = await api.listCheckpoints(runId)
      setCheckpoints(c.checkpoints || [])
      const st = await api.getRunState(runId)
      setRunState(st.ok ? st.state : null)
      try {
        const mem = await api.getJsonArtifact(runId, 'memory')
        setMemoryData(mem.ok ? mem.data : null)
      } catch { setMemoryData(null) }
      try {
        const ctx = await api.getJsonArtifact(runId, 'context')
        setContextData(ctx.ok ? ctx.data : null)
      } catch { setContextData(null) }
      try {
        const chainRes = await api.getOwnershipChain(runId)
        setOwnershipChain(chainRes.ok ? (chainRes.chain || []) : [])
        setOwnershipError(chainRes.error || null)
      } catch { setOwnershipChain([]); setOwnershipError(null) }
      try {
        const edgesRes = await api.getOwnershipEdges(runId)
        setOwnershipEdges(edgesRes.ok ? (edgesRes.edges || []) : [])
      } catch { setOwnershipEdges([]) }
      try {
        const evRes = await api.getOwnershipEvents(runId, null, 100)
        setOwnershipEvents(evRes.ok ? (evRes.events || []) : [])
      } catch { setOwnershipEvents([]) }
      try {
        const avRes = await api.getOwnershipAvailability(runId)
        setOwnershipAvailability(avRes)
      } catch { setOwnershipAvailability(null) }
      try {
        const aRes = await api.getAnalytics(runId)
        setAnalytics(aRes.ok ? aRes : null)
      } catch { setAnalytics(null) }
      try {
        const tRes = await api.getToolTrace(runId)
        setToolTrace(tRes.ok ? (tRes.items || []) : [])
        setToolTraceNote(tRes.note || '')
      } catch { setToolTrace([]); setToolTraceNote('') }
      try {
        const dRes = await api.getDelegationSummary(runId)
        setDelegationSummary(dRes.ok ? dRes.summary : null)
      } catch { setDelegationSummary(null) }
      try {
        const aRes = await api.getDelegationAnomalies(runId)
        setDelegationAnomalies(aRes.ok ? (aRes.anomalies || []) : [])
      } catch { setDelegationAnomalies([]) }
    } catch (e) {
      setErr(e.message)
    }
  }

  useEffect(() => { refresh() }, [runId])

  // SSE event stream (only when run has a run_dir so the stream exists)
  useEffect(() => {
    if (!runId || (run && (run.run_dir_missing || !run.run_dir))) return
    setEvents([])
    let es = null
    let cancelled = false
    ;(async () => {
      try {
        const tokenPayload = await api.getRunEventsStreamToken(runId)
        if (cancelled) return
        const url = api.eventsStreamUrl(runId, tokenPayload?.token)
        es = new EventSource(url)
        eventSourceRef.current = es
        es.addEventListener('ready', () => {})
        es.addEventListener('line', (e) => {
          try {
            const data = e.data ? JSON.parse(e.data) : {}
            setEvents(prev => [...prev.slice(-199), { ...data, _ts: Date.now() }])
          } catch {
            setEvents(prev => [...prev.slice(-199), { raw: e.data, _ts: Date.now() }])
          }
        })
        es.onerror = () => { es.close() }
      } catch {
        // stream unavailable
      }
    })()
    return () => {
      cancelled = true
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
        eventSourceRef.current = null
      }
      if (es) es.close()
    }
  }, [runId, run?.run_dir_missing, run?.run_dir])

  const onResume = async () => {
    try {
      await api.resumeRun(runId)
      await refresh()
    } catch (e) { setErr(e.message) }
  }

  const onReplay = async () => {
    try {
      const res = await api.replayRun(runId)
      if (res.ok && res.run_id) {
        window.location.hash = `#/runs/${res.run_id}`
      } else {
        setErr(res.error?.message || res.error?.code || 'Replay failed')
      }
    } catch (e) { setErr(e.message) }
  }

  const onCancel = async () => {
    try {
      await api.cancelRun(runId)
      await refresh()
    } catch (e) { setErr(e.message) }
  }

  const runStatusTone = (status) => {
    if (status === 'completed') return 'good'
    if (status === 'blocked' || status === 'failed') return 'danger'
    if (status === 'pending_approval' || status === 'cancelled') return 'warn'
    if (status === 'running' || status === 'launching') return 'info'
    return 'neutral'
  }

  const doOwnershipSearch = async () => {
    try {
      const r = await api.searchOwnership(runId, ownershipSearchQ)
      setOwnershipSearchHits(r.ok ? (r.hits || []) : [])
    } catch { setOwnershipSearchHits([]) }
  }

  return (
    <Layout title="Run detail">
      <Breadcrumbs items={[{ label: 'Home', href: '#/' }, { label: 'Runs', href: '#/' }, { label: 'Run detail' }, { label: runId.slice(0, 8) }]} />
      <AsyncPageBody loading={!run && !err} error={err} loadingLabel="Loading run detail">
      {run && (
        <>
          <SharedEventSummary
            eyebrow="Run detail"
            title={`Run ${run.run_id}`}
            intro="This page explains what the run did, why it was allowed or blocked, and what to inspect next."
            status={run.status || 'unknown'}
            statusTone={runStatusTone(run.status)}
            happened={run.summary?.status || run.status || 'unknown'}
            when={`${formatDateTime(run.started_at)}${run.ended_at ? ` · ended ${formatDateTime(run.ended_at)}` : ''}`}
            why={run.blocked_reason || lineageSummary?.workflow_id || run.graph_id || 'No explicit run reason recorded.'}
            changed={`Artifacts ${arts.length} · checkpoints ${checkpoints.length} · live events ${events.length} · snapshots ${snaps.length}`}
            next="Review checkpoints, open the run DAG, inspect lineage, or return to the origin page."
            context={[
              { label: 'Run', value: run.run_id },
              { label: 'Workflow', value: run.graph_id || run.workflow_id || '—' },
              { label: 'Correlation', value: run.correlation_id || '—' },
              { label: 'Origin', value: returnUrl !== '#/' ? returnUrl : 'current' },
            ]}
            actions={(
              <>
                <button onClick={onResume} style={{ padding:'8px 12px', borderRadius:8 }}>Resume</button>
                <button onClick={onReplay} style={{ padding:'8px 12px', borderRadius:8 }}>Replay</button>
                <button onClick={onCancel} style={{ padding:'8px 12px', borderRadius:8 }}>Cancel</button>
                <a href={runDagHref} style={{ padding:'8px 12px', borderRadius:8, border:'1px solid var(--border)', textDecoration: 'none' }}>Open Run DAG</a>
                <a href={compareHref} style={{ padding:'8px 12px', borderRadius:8, border:'1px solid var(--border)', textDecoration: 'none' }}>Open compare</a>
                {returnUrl !== '#/' ? <a href={returnUrl} style={{ textDecoration: 'none', alignSelf: 'center' }}>Back to origin</a> : null}
              </>
            )}
          />
          {run.status === 'cancelled' && (
            <div style={{ marginBottom: 16, padding: 16, borderRadius: 12, border: '1px solid rgba(255, 180, 80, 0.5)', background: 'rgba(255, 180, 80, 0.1)' }}>
              <div style={{ fontWeight: 600, marginBottom: 6 }}>Run cancelled</div>
              <div style={{ color: 'var(--muted)', fontSize: 14 }}>
                This run was stopped by an operator or automation policy before or during execution.
              </div>
            </div>
          )}
          {run.status === 'failed' && (
            <div style={{ marginBottom: 16, padding: 16, borderRadius: 12, border: '1px solid rgba(255, 100, 100, 0.5)', background: 'rgba(255, 100, 100, 0.08)' }}>
              <div style={{ fontWeight: 600, marginBottom: 6 }}>Run failed</div>
              <div style={{ color: 'var(--muted)', fontSize: 14 }}>
                {run.summary?.error_summary?.[0]?.message || run.blocked_reason || 'One or more nodes failed during execution. Inspect the summary and node events below.'}
              </div>
            </div>
          )}
          {run.status === 'pending_approval' && (
            <div style={{ marginBottom: 16, padding: 16, borderRadius: 12, border: '1px solid rgba(100, 180, 255, 0.5)', background: 'rgba(100, 180, 255, 0.08)' }}>
              <div style={{ fontWeight: 600, marginBottom: 6 }}>
                {run.blocked_reason ? 'Blocked by governance gate' : 'Awaiting human approval'}
              </div>
              <div style={{ color: 'var(--muted)', fontSize: 14 }}>
                {run.blocked_reason || 'This run is waiting for an explicit operator approval before launch.'}
              </div>
              <div style={{ marginTop: 8, fontSize: 13 }}>
                Run ID: <code>{run.run_id}</code> · Workflow: <strong>{run.graph_id || '—'}</strong>
                {run.correlation_id && <> · Correlation: <code>{run.correlation_id}</code></>}
              </div>
              <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
                <button onClick={async () => { try { await api.approveRun(runId); await refresh() } catch (e) { setErr(e.message) } }} style={{ padding: '8px 16px', borderRadius: 8, background: 'var(--success)', color: '#fff', border: 'none' }}>Approve</button>
                <button onClick={async () => { try { await api.denyRun(runId); await refresh() } catch (e) { setErr(e.message) } }} style={{ padding: '8px 16px', borderRadius: 8 }}>Deny</button>
              </div>
            </div>
          )}
          {(run.run_dir_missing || run.status === 'blocked') && run.status !== 'pending_approval' && (
            <div style={{ marginBottom: 16, padding: 16, borderRadius: 12, border: '1px solid rgba(255, 180, 80, 0.5)', background: 'rgba(255, 180, 80, 0.1)' }}>
              <div style={{ fontWeight: 600, marginBottom: 6 }}>Run blocked by governance</div>
              <div style={{ color: 'var(--muted)', fontSize: 14 }}>
                {run.blocked_reason || 'This run was attempted but stopped by the release gate or governance policy. No run directory was created.'}
              </div>
              <div style={{ marginTop: 8, fontSize: 13 }}>
                Run ID: <code>{run.run_id}</code> · Workflow: <strong>{run.graph_id || '—'}</strong>
                {run.correlation_id && <> · Correlation: <code>{run.correlation_id}</code></>}
              </div>
            </div>
          )}
          <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap: 16 }}>
            <div>
              <div style={{ fontWeight:600 }}>Summary</div>
              <JsonBlock value={run.summary || {}} />
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
                <span style={{ color: 'var(--muted)' }}>See the summary card above for the main action path.</span>
              </div>
              <span style={{ display:'block', marginTop: 6, color:'var(--muted)' }}>Resume: continue paused run. Replay: run again from recordings (new run). Cancel: mark run cancelled.</span>
            </div>
            <div>
              <MermaidBlock dag={run.graph} />
            </div>
          </div>

          {analytics && (
            <div style={{ marginTop: 18 }}>
              <div style={{ fontWeight:600, marginBottom: 6 }}>Analytics</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginBottom: 8 }}>
                {analytics.budget_used && Object.keys(analytics.budget_used).length > 0 && (
                  <div style={{ background: 'rgba(108, 197, 255, 0.12)', padding: 12, borderRadius: 8 }}>
                    <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 4 }}>Budget used</div>
                    <div style={{ fontFamily: 'monospace', fontSize: 12 }}>
                      {Object.entries(analytics.budget_used).map(([k, v]) => (
                        <div key={k}>{k}: {String(v)}</div>
                      ))}
                    </div>
                  </div>
                )}
                {analytics.counts && Object.keys(analytics.counts).length > 0 && (
                  <div style={{ background: 'rgba(141, 240, 164, 0.1)', padding: 12, borderRadius: 8 }}>
                    <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 4 }}>Counts</div>
                    <div style={{ fontFamily: 'monospace', fontSize: 12 }}>
                      {Object.entries(analytics.counts).map(([k, v]) => (
                        <div key={k}>{k}: {String(v)}</div>
                      ))}
                    </div>
                  </div>
                )}
                {analytics.final_status && (
                  <div style={{ background: 'var(--panel-success)', padding: 12, borderRadius: 8 }}>
                    <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 4 }}>Final status</div>
                    <div style={{ fontWeight: 600 }}>{analytics.final_status}</div>
                  </div>
                )}
              </div>
              {analytics.event_counts && Object.keys(analytics.event_counts).length > 0 && (
                <div style={{ marginTop: 8 }}>
                  <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 4 }}>Event counts</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, fontFamily: 'monospace', fontSize: 12 }}>
                    {Object.entries(analytics.event_counts).map(([ev, count]) => (
                      <span key={ev} style={{ background: 'rgba(255, 255, 255, 0.08)', padding: '4px 8px', borderRadius: 4 }}>{ev}: {count}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {analytics && (analytics.counts?.blocked > 0 || (analytics.node_summary && analytics.node_summary.some(n => n.error_code === 'STEERING_BLOCKED'))) && (
            <div style={{ marginTop: 18 }}>
              <div style={{ fontWeight:600, marginBottom: 6 }}>Steering</div>
              <div style={{ background: 'var(--panel-warn)', padding: 12, borderRadius: 8, fontSize: 13 }}>
                {analytics.counts?.blocked > 0 && (
                  <div style={{ marginBottom: 6 }}>Blocked by steering: <strong>{analytics.counts.blocked}</strong> node(s)</div>
                )}
                {analytics.node_summary && analytics.node_summary.filter(n => n.error_code === 'STEERING_BLOCKED').length > 0 && (
                  <div>
                    <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 4 }}>Nodes blocked (STEERING_BLOCKED)</div>
                    <div style={{ fontFamily: 'monospace', fontSize: 12 }}>
                      {analytics.node_summary.filter(n => n.error_code === 'STEERING_BLOCKED').map(n => (
                        <div key={n.id}>{n.id} — {n.status ?? 'blocked'}</div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          <div style={{ marginTop: 18 }}>
              <div style={{ fontWeight:600, marginBottom: 6 }}>Artifacts</div>
              <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap: 8 }}>
                {arts.slice(0, 50).map(p => (
                <a key={p} href={api.getArtifactUrl(runId, p)} target="_blank" rel="noreferrer">{p}</a>
                ))}
              </div>
            {arts.length > 50 && <div style={{ color:'var(--muted)', marginTop: 6 }}>Showing first 50.</div>}
          </div>

          <div style={{ marginTop: 18 }}>
            <div style={{ fontWeight:600, marginBottom: 6 }}>Events (live)</div>
            <div style={{ maxHeight: 200, overflow: 'auto', fontFamily: 'monospace', fontSize: 12, background: 'var(--panel-2)', padding: 8, borderRadius: 8 }}>
              {events.length === 0 && <div style={{ color:'var(--muted)' }}>Connecting to stream…</div>}
              {events.map((ev, i) => (
                <div key={i} style={{ marginBottom: 4 }}>{typeof ev === 'object' && ev !== null && !ev.raw ? JSON.stringify(ev) : String(ev.raw ?? ev)}</div>
              ))}
            </div>
          </div>

          <div style={{ marginTop: 18 }}>
            <div style={{ fontWeight:600, marginBottom: 6 }}>Tool invocation trace</div>
            {toolTraceNote && <div style={{ color: 'var(--muted)', marginBottom: 6 }}>{toolTraceNote}</div>}
            {toolTrace.length === 0 && <div style={{ color:'var(--muted)' }}>No tool invocations recorded.</div>}
            {toolTrace.length > 0 && (
              <table style={{ borderCollapse: 'collapse', width: '100%' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border)' }}>
                    <th style={{ textAlign: 'left', padding: 6 }}>node_id</th>
                    <th style={{ textAlign: 'left', padding: 6 }}>tool</th>
                    <th style={{ textAlign: 'left', padding: 6 }}>attempt</th>
                    <th style={{ textAlign: 'left', padding: 6 }}>inputs</th>
                    <th style={{ textAlign: 'left', padding: 6 }}>response</th>
                    <th style={{ textAlign: 'left', padding: 6 }}>error</th>
                  </tr>
                </thead>
                <tbody>
                  {toolTrace.map((t, i) => (
                    <tr key={`${t.node_id}-${i}`} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td style={{ padding: 6 }}>{t.node_id}</td>
                      <td style={{ padding: 6 }}>{t.assigned_entity || '—'}</td>
                      <td style={{ padding: 6 }}>{t.attempt_no ?? '—'}</td>
                      <td style={{ padding: 6, fontFamily: 'monospace', fontSize: 11 }}>{t.inputs ? JSON.stringify(t.inputs) : '—'}</td>
                      <td style={{ padding: 6, fontFamily: 'monospace', fontSize: 11 }}>{t.response ? JSON.stringify(t.response) : '—'}</td>
                      <td style={{ padding: 6, fontFamily: 'monospace', fontSize: 11 }}>{t.error ? JSON.stringify(t.error) : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {runState && runState.nodes && (
            <div style={{ marginTop: 18 }}>
              <div style={{ fontWeight:600, marginBottom: 6 }}>Node table</div>
              <table style={{ borderCollapse: 'collapse', width: '100%' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border)' }}>
                    <th style={{ textAlign: 'left', padding: 6 }}>node_id</th>
                    <th style={{ textAlign: 'left', padding: 6 }}>status</th>
                    <th style={{ textAlign: 'left', padding: 6 }}>started_at</th>
                    <th style={{ textAlign: 'left', padding: 6 }}>finished_at</th>
                    <th style={{ textAlign: 'left', padding: 6 }}>attempt_count</th>
                    <th style={{ textAlign: 'left', padding: 6 }}>error</th>
                  </tr>
                </thead>
                <tbody>
                  {runState.nodes.map((n, i) => (
                    <tr key={n.id || i} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td style={{ padding: 6 }}>{n.id}</td>
                      <td style={{ padding: 6 }}>{n.status ?? '—'}</td>
                      <td style={{ padding: 6 }}>{formatDateTime(n.started_at)}</td>
                      <td style={{ padding: 6 }}>{formatDateTime(n.finished_at ?? n.ended_at)}</td>
                      <td style={{ padding: 6 }}>{n.attempt_count ?? '—'}</td>
                      <td style={{ padding: 6 }}>{n.error ? (typeof n.error === 'string' ? n.error : (n.error.message || JSON.stringify(n.error))) : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {(memoryData || contextData) && (
            <div style={{ marginTop: 18 }}>
              <div style={{ fontWeight:600, marginBottom: 6 }}>Memory / Context</div>
              <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                {memoryData != null && <button onClick={() => setActiveTab('memory')} style={{ padding: '6px 12px', borderRadius: 6, fontWeight: activeTab === 'memory' ? 600 : 400 }}>Memory</button>}
                {contextData != null && <button onClick={() => setActiveTab('context')} style={{ padding: '6px 12px', borderRadius: 6, fontWeight: activeTab === 'context' ? 600 : 400 }}>Context</button>}
              </div>
              <div style={{ background: 'var(--panel-2)', padding: 12, borderRadius: 8 }}>
                {activeTab === 'memory' && memoryData != null && <JsonBlock value={memoryData} />}
                {activeTab === 'context' && contextData != null && <JsonBlock value={contextData} />}
              </div>
            </div>
          )}

          <div style={{ marginTop: 18 }}>
            <div style={{ fontWeight:600, marginBottom: 6 }}>Checkpoints (approvals queue)</div>
            {checkpoints.length === 0 && <div style={{ color:'var(--muted)' }}>No pending checkpoints.</div>}
            {checkpoints.length > 0 && (
              <ul>
                {checkpoints.map(cp => (
                  <li key={cp.checkpoint_id || cp.node_id}>
                    {cp.checkpoint_id || cp.node_id} {cp.node_id ? `(${cp.node_id})` : ''} {cp.status ? `[${cp.status}]` : ''}
                    {(cp.status === 'pending' || !cp.status) && (
                      <>
                        <button onClick={async () => { try { await api.approveCheckpoint(runId, cp.checkpoint_id || cp.node_id, { comment: '' }); await refresh() } catch (e) { setErr(e.message) } }} style={{ marginLeft: 8 }}>Approve</button>
                        <button onClick={async () => { try { await api.denyCheckpoint(runId, cp.checkpoint_id || cp.node_id, { comment: '' }); await refresh() } catch (e) { setErr(e.message) } }} style={{ marginLeft: 4 }}>Deny</button>
                      </>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>

          {(delegationSummary || delegationAnomalies.length > 0) && (
            <div style={{ marginTop: 18 }}>
              <div style={{ fontWeight:600, marginBottom: 6 }}>Delegation</div>
              <p>
                <a href={`#/runs/${runId}/delegation`} style={{ textDecoration: 'none' }}>Open full Delegation & emergent behavior</a>
              </p>
              {delegationSummary && (
                <p style={{ fontSize: 13 }}>
                  Status: {delegationSummary.final_state?.status} · External writes blocked: {delegationSummary.final_state?.external_writes_blocked} · Quality: {delegationSummary.quality?.score ?? '—'} (degraded: {String(delegationSummary.quality?.degraded ?? false)}) · Intervention: {delegationSummary.intervention?.step ?? '—'}
                </p>
              )}
              {delegationAnomalies.length > 0 && (
                <div style={{ marginTop: 6 }}>
                  <strong>Anomalies:</strong> {delegationAnomalies.length}
                  <ul style={{ marginTop: 4, paddingLeft: 20 }}>
                    {delegationAnomalies.slice(0, 5).map((a, i) => (
                      <li key={i}>{a.detector_id} ({a.severity}): {a.recommended_action}</li>
                    ))}
                    {delegationAnomalies.length > 5 && <li>… and {delegationAnomalies.length - 5} more</li>}
                  </ul>
                </div>
              )}
            </div>
          )}

          {lineageSummary && (
            <div style={{ marginTop: 18 }}>
              <div style={{ fontWeight:600, marginBottom: 6 }}>Lineage</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 10 }}>
                <div style={{ background: 'var(--panel-2)', padding: 12, borderRadius: 8 }}>
                  <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 4 }}>Run</div>
                  <div><code>{lineageSummary.run_id}</code></div>
                  <div style={{ marginTop: 4 }}>Status: <strong>{lineageSummary.status || '—'}</strong></div>
                  <div style={{ marginTop: 4 }}>Workflow: {lineageSummary.workflow_href ? <a href={lineageSummary.workflow_href}>{lineageSummary.workflow_id || lineageSummary.graph_id || '—'}</a> : <code>{lineageSummary.workflow_id || lineageSummary.graph_id || '—'}</code>}</div>
                  <div style={{ marginTop: 4 }}>Activity: {lineageSummary.activity_href ? <a href={lineageSummary.activity_href}>open activity</a> : '—'}</div>
                  <div style={{ marginTop: 4 }}>Chat activity: {lineageSummary.chat_activity_href ? <a href={lineageSummary.chat_activity_href}>open chat activity</a> : '—'}</div>
                </div>
                <div style={{ background: 'var(--panel-2)', padding: 12, borderRadius: 8 }}>
                  <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 4 }}>Swarm links</div>
                  <div>Parent: {lineageSummary.parent_run_id ? <a href={`#/runs/${lineageSummary.parent_run_id}`}>{lineageSummary.parent_run_id}</a> : '—'}</div>
                  <div>Children: {(lineageSummary.child_run_ids || []).length > 0 ? (lineageSummary.child_run_ids || []).map((childId, i) => (
                    <span key={childId}>
                      {i > 0 ? ', ' : ''}
                      <a href={`#/runs/${childId}`}>{childId}</a>
                    </span>
                  )) : '—'}</div>
                  <div style={{ marginTop: 4 }}>Correlated runs: {(lineageSummary.correlated_runs || []).length > 0 ? (lineageSummary.correlated_runs || []).map((row, i) => (
                    <span key={row.run_id}>
                      {i > 0 ? ', ' : ''}
                      <a href={`#/runs/${row.run_id}`}>{row.run_id}</a>
                    </span>
                  )) : '—'}</div>
                  <div style={{ marginTop: 4 }}>Related chats: {(lineageSummary.related_chat_ids || []).length > 0 ? (lineageSummary.related_chat_ids || []).map((chatId, i) => (
                    <span key={chatId}>
                      {i > 0 ? ', ' : ''}
                      <a href={`#/activity?chat_id=${encodeURIComponent(chatId)}`}>{chatId}</a>
                    </span>
                  )) : '—'}</div>
                  <div style={{ marginTop: 4 }}>Related swarms: {(lineageSummary.related_swarm_run_ids || []).length > 0 ? lineageSummary.related_swarm_run_ids.join(', ') : '—'}</div>
                </div>
              </div>
              <MermaidBlock dag={lineageSummary.lineage_graph} />
            </div>
          )}

          <div style={{ marginTop: 18 }}>
            <div style={{ fontWeight:600, marginBottom: 6 }}>Ownership (chain, events, search)</div>
            {ownershipError && <div style={{ color:'var(--danger)', marginBottom: 6 }}>{ownershipError}</div>}
            {ownershipChain.length > 0 && (
              <>
                <div style={{ marginBottom: 8 }}>Chain</div>
                <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: 12 }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border)' }}>
                      <th style={{ textAlign: 'left', padding: 6 }}>task_id</th>
                      <th style={{ textAlign: 'left', padding: 6 }}>sponsor</th>
                      <th style={{ textAlign: 'left', padding: 6 }}>accountable</th>
                      <th style={{ textAlign: 'left', padding: 6 }}>executor</th>
                      <th style={{ textAlign: 'left', padding: 6 }}>approver</th>
                      <th style={{ textAlign: 'left', padding: 6 }}>state</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ownershipChain.map((row, i) => (
                      <tr key={row.task_id || i} style={{ borderBottom: '1px solid var(--border)' }}>
                        <td style={{ padding: 6 }}>{row.task_id ?? '—'}</td>
                        <td style={{ padding: 6 }}>{row.sponsor_id || '—'}</td>
                        <td style={{ padding: 6 }}>{row.accountable_id || '—'}</td>
                        <td style={{ padding: 6 }}>{row.executor_id || '—'}</td>
                        <td style={{ padding: 6 }}>{row.approver_id || '—'}</td>
                        <td style={{ padding: 6 }}>{row.state ?? '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            )}
            {ownershipEdges.length > 0 && (
              <div style={{ marginTop: 8 }}>
                <div style={{ marginBottom: 4 }}>Edges</div>
                <div style={{ fontFamily: 'monospace', fontSize: 12 }}>
                  {ownershipEdges.map((e, i) => (
                    <div key={i}>{e.from_principal} → {e.to_principal} ({e.edge_type})</div>
                  ))}
                </div>
              </div>
            )}
            {ownershipEvents.length > 0 && (
              <div style={{ marginTop: 8 }}>
                <div style={{ marginBottom: 4 }}>Events (last 100)</div>
                <div style={{ maxHeight: 180, overflow: 'auto', fontFamily: 'monospace', fontSize: 11, background: 'var(--panel-2)', padding: 8, borderRadius: 8 }}>
                  {ownershipEvents.map((ev, i) => (
                    <div key={i} style={{ marginBottom: 2 }}>
                      {ev.type} by {ev.actor} @ {ev.task_id} {ev.ts != null ? formatDateTime(ev.ts) : ''}
                    </div>
                  ))}
                </div>
              </div>
            )}
            <div style={{ marginTop: 8, display: 'flex', gap: 8, alignItems: 'center' }}>
              <input
                type="text"
                placeholder="Search ownership events (FTS)"
                value={ownershipSearchQ}
                onChange={e => setOwnershipSearchQ(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') doOwnershipSearch() }}
                style={{ padding: '6px 10px', width: 280, borderRadius: 6 }}
              />
              <button onClick={doOwnershipSearch} style={{ padding: '6px 12px', borderRadius: 6 }}>Search</button>
            </div>
            {ownershipSearchHits.length > 0 && (
              <div style={{ marginTop: 6, fontFamily: 'monospace', fontSize: 11 }}>
                {ownershipSearchHits.length} hit(s): {ownershipSearchHits.map((h, i) => (
                  <div key={i}>{h.type} {h.actor} {h.task_id}</div>
                ))}
              </div>
            )}
            {ownershipAvailability != null && (
              <div style={{ marginTop: 8, color: 'var(--muted)', fontSize: 12 }}>
                Availability: {ownershipAvailability.note || (ownershipAvailability.principals?.length ? `${ownershipAvailability.principals.length} principal(s)` : 'No data (executor-side).')}
              </div>
            )}
            {ownershipChain.length === 0 && !ownershipError && <div style={{ color: 'var(--muted)' }}>No ownership data for this run (DB created when executor uses ownership protocol).</div>}
          </div>

          <div style={{ marginTop: 18 }}>
            <div style={{ fontWeight:600, marginBottom: 6 }}>Snapshots</div>
            {snaps.length === 0 && <div style={{ color:'var(--muted)' }}>No snapshots found. Enable state history in the executor pack.</div>}
            {snaps.length > 0 && (
              <ul>
                {snaps.slice(0, 30).map(s => (
                  <li key={s.seq}>
                    <a href={`#/runs/${runId}/snapshots/${s.seq}`}>seq {s.seq}</a>
                    <span style={{ color:'var(--muted)' }}> {s.reason || ''} {s.node_id ? `(${s.node_id})` : ''}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </>
      )}
      </AsyncPageBody>
    </Layout>
  )
}
