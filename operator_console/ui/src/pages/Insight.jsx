import React, { useCallback, useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import { api } from '../lib/api.js'
import { AsyncPageBody } from '../components/PageStates.jsx'

const HOURS_OPTIONS = [6, 24, 48, 168]

function fmt(v) {
  if (v == null) return '—'
  if (typeof v === 'number') return Number.isInteger(v) ? String(v) : v.toFixed(3)
  return String(v)
}

export default function Insight() {
  const [hours, setHours] = useState(24)
  const [dagOnly, setDagOnly] = useState(false)
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)

  const load = useCallback(() => {
    setErr(null)
    api.getMonitoringInsight(hours, 400, dagOnly)
      .then((r) => setData(r))
      .catch((e) => setErr(e.message))
  }, [hours, dagOnly])

  useEffect(() => { load() }, [load])

  const totals = data?.totals || {}
  const workflows = data?.by_workflow || []
  const anomalies = data?.anomalies || []
  const recentRuns = data?.recent_runs || []

  return (
    <Layout title="Insight">
      <section className="section-card" style={{ marginBottom: 16 }}>
        <h2 style={{ marginTop: 0 }}>DAG runtime insight</h2>
        <p style={{ marginBottom: 8 }}>
          Window:{' '}
          {HOURS_OPTIONS.map((h) => (
            <button
              key={h}
              type="button"
              onClick={() => setHours(h)}
              style={{ marginRight: 8, fontWeight: h === hours ? 'bold' : 'normal' }}
            >
              {h}h
            </button>
          ))}
          <button type="button" onClick={load}>Refresh</button>
        </p>
        <label style={{ display: 'inline-flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
          <input type="checkbox" checked={dagOnly} onChange={(e) => setDagOnly(e.target.checked)} />
          DAG-runtime only
        </label>
      </section>

      <AsyncPageBody loading={!data && !err} error={err} onRetry={load} loadingLabel="Loading insight metrics">
      <section className="section-card" style={{ marginBottom: 16 }}>
        <h2 style={{ marginTop: 0 }}>Totals</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: 12 }}>
          <div><strong>Runs</strong><div>{fmt(totals.runs)}</div></div>
          <div><strong>Failed runs</strong><div>{fmt(totals.failed_runs)}</div></div>
          <div><strong>Fail rate</strong><div>{fmt(totals.fail_rate)}</div></div>
          <div><strong>Blocked nodes</strong><div>{fmt(totals.blocked_nodes)}</div></div>
          <div><strong>Policy violations</strong><div>{fmt(totals.policy_violations)}</div></div>
          <div><strong>Runtime command</strong><div>{data?.dag_runtime?.command || '—'}</div></div>
        </div>
        <p className="muted" style={{ marginTop: 10 }}>
          Configured DAG runtime jobs: {(data?.dag_runtime?.configured_jobs || []).join(', ') || 'none'}
        </p>
      </section>

      <section className="section-card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>Workflow health</h3>
        <table>
          <thead>
            <tr>
              <th>workflow</th>
              <th>runs</th>
              <th>failed</th>
              <th>fail_rate</th>
              <th>avg_duration_s</th>
              <th>p95_duration_s</th>
              <th>outliers</th>
              <th>blocked</th>
              <th>violations</th>
            </tr>
          </thead>
          <tbody>
            {workflows.map((w) => (
              <tr key={w.workflow_id}>
                <td>{w.workflow_id}</td>
                <td>{fmt(w.runs)}</td>
                <td>{fmt(w.failed_runs)}</td>
                <td>{fmt(w.fail_rate)}</td>
                <td>{fmt(w.avg_duration_s)}</td>
                <td>{fmt(w.p95_duration_s)}</td>
                <td>{fmt(w.outlier_runs)}</td>
                <td>{fmt(w.blocked_nodes)}</td>
                <td>{fmt(w.policy_violations)}</td>
              </tr>
            ))}
            {!workflows.length && (
              <tr><td colSpan={9} className="muted">No workflow data in selected window.</td></tr>
            )}
          </tbody>
        </table>
      </section>

      <section className="section-card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>Anomalies</h3>
        <table>
          <thead>
            <tr>
              <th>type</th>
              <th>workflow</th>
              <th>run_id</th>
              <th>value</th>
              <th>threshold</th>
            </tr>
          </thead>
          <tbody>
            {anomalies.map((a, i) => (
              <tr key={`${a.type}-${a.workflow_id || 'wf'}-${a.run_id || i}`}>
                <td>{a.type}</td>
                <td>{a.workflow_id || '—'}</td>
                <td>{a.run_id || '—'}</td>
                <td>{fmt(a.value)}</td>
                <td>{fmt(a.threshold)}</td>
              </tr>
            ))}
            {!anomalies.length && (
              <tr><td colSpan={5} className="muted">No anomalies detected.</td></tr>
            )}
          </tbody>
        </table>
      </section>

      <section className="section-card">
        <h3 style={{ marginTop: 0 }}>Recent runs</h3>
        <table>
          <thead>
            <tr>
              <th>run_id</th>
              <th>workflow</th>
              <th>status</th>
              <th>duration_s</th>
              <th>blocked</th>
              <th>violations</th>
            </tr>
          </thead>
          <tbody>
            {recentRuns.map((r) => (
              <tr key={r.run_id}>
                <td>{r.run_id}</td>
                <td>{r.workflow_id}</td>
                <td>{r.status}</td>
                <td>{fmt(r.duration_s)}</td>
                <td>{fmt(r.blocked_nodes)}</td>
                <td>{fmt(r.policy_violations)}</td>
              </tr>
            ))}
            {!recentRuns.length && (
              <tr><td colSpan={6} className="muted">No recent runs in selected window.</td></tr>
            )}
          </tbody>
        </table>
      </section>
      </AsyncPageBody>
    </Layout>
  )
}
