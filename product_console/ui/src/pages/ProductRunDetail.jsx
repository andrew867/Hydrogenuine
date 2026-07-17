import React, { useCallback, useEffect, useState } from 'react'

import Layout from '../components/Layout.jsx'

import StatusChip from '../components/StatusChip.jsx'

import JsonBlock from '../components/JsonBlock.jsx'

import Breadcrumbs from '../components/Breadcrumbs.jsx'

import { api } from '../lib/api.js'

import { formatDateTime } from '../lib/timezone.js'

import { AsyncPageBody } from '../components/PageStates.jsx'

import AuditToast from '../components/AuditToast.jsx'



function ModeBadge({ mode }) {

  const label = mode === 'live' ? 'Live' : 'Shadow'

  const tone = mode === 'live' ? 'var(--danger)' : 'var(--muted)'

  return (

    <span

      title={mode === 'live' ? 'Live actions may affect production state.' : 'Shadow mode replays without side effects.'}

      style={{

        marginLeft: 8,

        fontSize: 12,

        padding: '2px 8px',

        borderRadius: 999,

        border: `1px solid ${tone}`,

        color: tone,

      }}

    >

      {label}

    </span>

  )

}



export default function ProductRunDetail({ runId, onLogout }) {

  const [run, setRun] = useState(null)

  const [artifacts, setArtifacts] = useState(null)

  const [err, setErr] = useState(null)

  const [toast, setToast] = useState(null)

  const [actionMode, setActionMode] = useState('live')

  const [liveActionsEnabled, setLiveActionsEnabled] = useState(false)

  const [replaying, setReplaying] = useState(false)

  const [rollingBack, setRollingBack] = useState(false)

  const [exporting, setExporting] = useState(false)



  const load = useCallback(() => {

    if (!runId) return

    api.product.getRun(runId).then(setRun).catch((e) => setErr(e.message))

    api.product.listRunArtifacts(runId).then(setArtifacts).catch(() => setArtifacts({ items: [] }))

  }, [runId])



  useEffect(() => {

    load()

  }, [load])



  useEffect(() => {

    api.product.getDemoConfig()

      .then((cfg) => {

        const live = Boolean(cfg?.live_actions_enabled)

        setLiveActionsEnabled(live)

        setActionMode(live ? 'live' : 'shadow')

      })

      .catch(() => {

        setLiveActionsEnabled(false)

        setActionMode('shadow')

      })

  }, [])



  const handleReplay = () => {

    setReplaying(true)

    api.product.replayRun(runId, { mode: actionMode })

      .then(() => {

        setErr(null)

        setToast(`Replay (${actionMode}) accepted`)

        load()

      })

      .catch((e) => setErr(e.message))

      .finally(() => setReplaying(false))

  }



  const handleRollback = () => {

    setRollingBack(true)

    api.product.rollbackRun(runId, { mode: actionMode })

      .then(() => {

        setErr(null)

        setToast(`Rollback (${actionMode}) accepted`)

        load()

      })

      .catch((e) => setErr(e.message))

      .finally(() => setRollingBack(false))

  }



  const handleExport = async () => {

    setExporting(true)

    try {

      const report = await api.product.getAuditReport(runId)

      const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })

      const url = URL.createObjectURL(blob)

      const a = document.createElement('a')

      a.href = url

      a.download = `audit_report_${runId.slice(0, 8)}.json`

      a.click()

      URL.revokeObjectURL(url)

      setToast('Audit report downloaded')

    } catch (e) {

      setErr(e.message)

    } finally {

      setExporting(false)

    }

  }



  const downloadArtifact = async (name) => {

    try {

      const blob = await api.product.downloadRunArtifact(runId, name)

      const url = URL.createObjectURL(blob)

      const a = document.createElement('a')

      a.href = url

      a.download = name.split('/').pop() || 'artifact'

      a.click()

      URL.revokeObjectURL(url)

      setToast(`Downloaded ${name}`)

    } catch (e) {

      setErr(e.message)

    }

  }



  if (!runId) return <Layout title="Run" onLogout={onLogout}>Missing run ID</Layout>



  return (

    <Layout title={`Run ${runId.slice(0, 8)}…`} onLogout={onLogout}>

      <Breadcrumbs items={[{ label: 'Home', href: '#/' }, { label: 'Runs', href: '#/runs' }, { label: runId.slice(0, 8) }]} />

      <p><a href="#/runs">← Runs</a></p>

      <AsyncPageBody loading={!run && !err} error={err && !run ? err : null} loadingLabel="Loading run detail">

      {run ? (

      <>

      {err ? <div style={{ color: 'var(--danger)', marginBottom: 12 }}>{err}</div> : null}

      <div style={{ marginBottom: 16 }}>

        <StatusChip status={run.status} />

        <ModeBadge mode={actionMode} />

        {run.graph_id && <span style={{ marginLeft: 8 }}>Workflow: {run.graph_id}</span>}

        <div style={{ marginTop: 8, display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>

          <label style={{ fontSize: 13 }}>

            Action mode

            <select value={actionMode} onChange={(e) => setActionMode(e.target.value)} style={{ marginLeft: 8 }}>

              <option value="shadow">shadow</option>

              <option
                value="live"
                disabled={!liveActionsEnabled}
                title={liveActionsEnabled ? 'Live actions may affect production state.' : 'Live mode requires demo live_actions_enabled'}
              >
                live
              </option>

            </select>

          </label>

          <button type="button" onClick={handleReplay} disabled={replaying}>

            {replaying ? 'Replaying…' : 'Replay'}

          </button>

          <button type="button" onClick={handleRollback} disabled={rollingBack}>

            {rollingBack ? 'Rolling back…' : 'Rollback'}

          </button>

          <button type="button" onClick={handleExport} disabled={exporting}>

            {exporting ? 'Exporting…' : 'Download audit report'}

          </button>

          <button type="button" onClick={load}>Refresh</button>

        </div>

      </div>

      <section style={{ marginBottom: 24 }}>

        <h2 style={{ fontSize: 16 }}>Audit summary</h2>

        <JsonBlock value={run.audit_summary || {}} />

      </section>

      <section style={{ marginBottom: 24 }}>

        <h2 style={{ fontSize: 16 }}>Run metadata</h2>

        <JsonBlock value={{ run_id: run.run_id, graph_id: run.graph_id, status: run.status, started_at: formatDateTime(run.started_at), ended_at: formatDateTime(run.ended_at) }} />

      </section>

      {Array.isArray(run.trace_timeline) && run.trace_timeline.length > 0 && (

        <section style={{ marginBottom: 24 }}>

          <h2 style={{ fontSize: 16 }}>Execution timeline</h2>

          <table width="100%" cellPadding="8" style={{ borderCollapse: 'collapse' }}>

            <thead>

              <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>

                <th>Node</th>

                <th>Entity</th>

                <th>Status</th>

                <th>Started</th>

                <th>Ended</th>

                <th>Duration (ms)</th>

                <th>Error</th>

              </tr>

            </thead>

            <tbody>

              {run.trace_timeline.map((row, idx) => (

                <tr key={`${row.node_id || idx}-${idx}`} style={{ borderBottom: '1px solid var(--border)' }}>

                  <td>{row.node_id || '—'}</td>

                  <td>{row.assigned_entity || row.node_type || '—'}</td>

                  <td><StatusChip status={row.status} /></td>

                  <td>{formatDateTime(row.started_at)}</td>

                  <td>{formatDateTime(row.ended_at)}</td>

                  <td>{row.duration_ms ?? '—'}</td>

                  <td style={{ fontFamily: 'monospace', fontSize: 12 }}>

                    {row.error ? JSON.stringify(row.error) : '—'}

                  </td>

                </tr>

              ))}

            </tbody>

          </table>

        </section>

      )}

      {artifacts?.items?.length > 0 && (

        <section>

          <h2 style={{ fontSize: 16 }}>Artifacts</h2>

          <ul>

            {artifacts.items.map((a, i) => (

              <li key={i}>

                <button type="button" onClick={() => downloadArtifact(a.name)}>

                  {a.name}

                </button>

                {' '}({a.kind}, {a.size} bytes)

              </li>

            ))}

          </ul>

        </section>

      )}

      </>

      ) : null}

      </AsyncPageBody>

      <AuditToast message={toast} onDismiss={() => setToast(null)} />

    </Layout>

  )

}


