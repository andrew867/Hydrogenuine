import React, { useCallback, useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import { api } from '../lib/api.js'
import StateNotice from '../components/StateNotice.jsx'

const formatTimestamp = (value) => {
  if (!value) return 'n/a'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toISOString().replace('T', ' ').replace('Z', ' UTC')
}

export default function IncidentQueuePage() {
  const [items, setItems] = useState([])
  const [err, setErr] = useState(null)
  const [replayResult, setReplayResult] = useState(null)
  const [dedupResult, setDedupResult] = useState(null)
  const [loading, setLoading] = useState(false)

  const load = useCallback(() => {
    setErr(null)
    setLoading(true)
    api
      .getIncidentQueue()
      .then((r) => setItems(Array.isArray(r.items) ? r.items : []))
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const replay = (incidentId) => {
    if (!incidentId) return
    setErr(null)
    setReplayResult(null)
    api
      .replayIncidentQueue(incidentId, true)
      .then((r) => setReplayResult(r))
      .catch((e) => setErr(e.message))
  }

  const showDedup = (workflowId) => {
    if (!workflowId) return
    setErr(null)
    setDedupResult(null)
    api
      .getWorkflowDedup(workflowId, 25)
      .then((r) => setDedupResult(r))
      .catch((e) => setErr(e.message))
  }

  return (
    <Layout title="Incident Queue">
      {err && <StateNotice tone="danger" title="Could not load incident queue" detail={err} action={<button type="button" onClick={load}>Retry</button>} />}
      <p>Terminal failures; replay in shadow (no side effects).</p>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <span style={{ color: 'var(--muted)' }}>{items.length} incident items</span>
        <button type="button" onClick={load}>Refresh</button>
      </div>
      {loading ? (
        <StateNotice title="Loading incidents" detail="Reading terminal failures and replay candidates." />
      ) : items.length === 0 ? (
        <StateNotice title="No incident items" detail="No terminal failures are currently parked in the operator queue." />
      ) : (
        <table className="table full-width">
          <thead>
            <tr>
              <th>ID</th>
              <th>Run</th>
              <th>Status</th>
              <th>Failure</th>
              <th>Started</th>
              <th>Dedupe</th>
              <th>Replay</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id || item.run_id || item.incident_id}>
                <td>{item.id || item.incident_id || 'unknown'}</td>
                <td>{item.run_id || item.graph_id || 'n/a'}</td>
                <td>{item.status || 'unknown'}</td>
                <td>{item.failure_class || JSON.stringify(item.error || item.replay_payload) || 'error'}</td>
                <td>{formatTimestamp(item.started_at || item.written_at)}</td>
                <td>
                  <button
                    type="button"
                    onClick={() => showDedup(item.task_id || item.workflow_id || item.graph_id)}
                  >
                    View dedupe
                  </button>
                </td>
                <td>
                  <button type="button" onClick={() => replay(item.id || item.incident_id)}>
                    Replay (shadow)
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {replayResult && (
        <section style={{ marginTop: 16 }}>
          <h3>Replay result</h3>
          <pre style={{ background: 'var(--panel-2)', padding: 12 }}>{JSON.stringify(replayResult, null, 2)}</pre>
        </section>
      )}
      {dedupResult && (
        <section style={{ marginTop: 16 }}>
          <h3>Dedupe context</h3>
          <pre style={{ background: 'var(--panel-2)', padding: 12 }}>{JSON.stringify(dedupResult, null, 2)}</pre>
        </section>
      )}
    </Layout>
  )
}


