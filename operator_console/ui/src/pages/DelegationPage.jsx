import React, { useCallback, useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import JsonBlock from '../components/JsonBlock.jsx'
import { api } from '../lib/api.js'

export default function DelegationPage({ runId: propRunId }) {
  const [runId, setRunId] = useState(propRunId || '')
  const [summary, setSummary] = useState(null)
  const [graph, setGraph] = useState(null)
  const [anomalies, setAnomalies] = useState([])
  const [incidentReport, setIncidentReport] = useState(null)
  const [err, setErr] = useState(null)

  const load = useCallback((rid) => {
    if (!rid) {
      setSummary(null)
      setGraph(null)
      setAnomalies([])
      setIncidentReport(null)
      setErr(null)
      return
    }
    setErr(null)
    api.getDelegationSummary(rid)
      .then((r) => r.ok && r.summary && setSummary(r.summary))
      .catch(() => setSummary(null))
    api.getDelegationGraph(rid)
      .then((r) => r.ok && r.graph && setGraph(r.graph))
      .catch(() => setGraph(null))
    api.getDelegationAnomalies(rid)
      .then((r) => setAnomalies(r.ok ? (r.anomalies || []) : []))
      .catch(() => setAnomalies([]))
    api.getIncidentReport(rid)
      .then((r) => r.ok && r.report && setIncidentReport(r.report))
      .catch(() => setIncidentReport(null))
  }, [])

  useEffect(() => {
    if (propRunId) setRunId(propRunId)
  }, [propRunId])

  useEffect(() => {
    load(runId)
  }, [runId, load])

  return (
    <Layout title="Delegation and Emergent Behavior">
      {err && <p style={{ color: 'var(--danger)' }}>{err}</p>}
      <section style={{ marginBottom: 24 }}>
        <label style={{ marginRight: 8 }}>Run ID:</label>
        <input
          type="text"
          value={runId}
          onChange={(e) => setRunId(e.target.value.trim())}
          placeholder="paste run_id from Runs or Run detail"
          style={{ width: 360, padding: 6 }}
        />
        <a href="#/runs" style={{ marginLeft: 12 }}>Browse runs</a>
      </section>
      {!runId && (
        <p>Enter a run ID (from Runs list or Run detail) to view delegation summary, graph, anomalies, and incident report.</p>
      )}
      {runId && !summary && !graph && anomalies.length === 0 && !incidentReport && (
        <p>No delegation data for this run. Delegation artifacts are written when the run used run_dir (e.g. DAG runs).</p>
      )}
      {runId && (summary || graph || anomalies.length > 0 || incidentReport) && (
        <>
          <section style={{ marginBottom: 24 }}>
            <h2 style={{ fontSize: 18 }}>Delegation summary</h2>
            {summary ? (
              <>
                <p><strong>Workflow:</strong> {summary.workflow_id} · <strong>Status:</strong> {summary.final_state?.status} · <strong>External writes blocked:</strong> {summary.final_state?.external_writes_blocked}</p>
                {summary.metrics && (
                  <table style={{ borderCollapse: 'collapse', width: '100%', maxWidth: 600 }}>
                    <tbody>
                      {Object.entries(summary.metrics).map(([k, v]) => (
                        <tr key={k}>
                          <td style={{ border: '1px solid var(--border)', padding: 6 }}>{k}</td>
                          <td style={{ border: '1px solid var(--border)', padding: 6 }}>{String(v)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
                {summary.quality && (
                  <p><strong>Quality score:</strong> {summary.quality.score} · <strong>Degraded:</strong> {String(summary.quality.degraded)}</p>
                )}
                {summary.intervention && (
                  <p><strong>Intervention:</strong> {summary.intervention.step} {summary.intervention.exceeded_budget ? `(${summary.intervention.exceeded_budget})` : ''}</p>
                )}
              </>
            ) : (
              <p>No summary.</p>
            )}
          </section>
          <section style={{ marginBottom: 24 }}>
            <h2 style={{ fontSize: 18 }}>Anomaly timeline</h2>
            {anomalies.length === 0 ? (
              <p>No anomalies.</p>
            ) : (
              <table style={{ borderCollapse: 'collapse', width: '100%' }}>
                <thead>
                  <tr>
                    <th style={{ border: '1px solid var(--border)', padding: 8 }}>Detector</th>
                    <th style={{ border: '1px solid var(--border)', padding: 8 }}>Severity</th>
                    <th style={{ border: '1px solid var(--border)', padding: 8 }}>Action</th>
                    <th style={{ border: '1px solid var(--border)', padding: 8 }}>Evidence</th>
                  </tr>
                </thead>
                <tbody>
                  {anomalies.map((a, i) => (
                    <tr key={i}>
                      <td style={{ border: '1px solid var(--border)', padding: 8 }}>{a.detector_id}</td>
                      <td style={{ border: '1px solid var(--border)', padding: 8 }}>{a.severity}</td>
                      <td style={{ border: '1px solid var(--border)', padding: 8 }}>{a.recommended_action}</td>
                      <td style={{ border: '1px solid var(--border)', padding: 8 }}>
                        {Array.isArray(a.evidence) ? a.evidence.map((e, j) => `${e.pointer}=${e.value}`).join(', ') : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
          <section style={{ marginBottom: 24 }}>
            <h2 style={{ fontSize: 18 }}>Delegation graph</h2>
            {graph ? (
              <>
                <p><strong>Nodes:</strong> {graph.nodes?.length ?? 0} · <strong>Edges:</strong> {graph.edges?.length ?? 0}</p>
                {graph.nodes?.length > 0 && (
                  <table style={{ borderCollapse: 'collapse', width: '100%' }}>
                    <thead>
                      <tr>
                        <th style={{ border: '1px solid var(--border)', padding: 8 }}>ID</th>
                        <th style={{ border: '1px solid var(--border)', padding: 8 }}>Owner</th>
                        <th style={{ border: '1px solid var(--border)', padding: 8 }}>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {graph.nodes.slice(0, 50).map((n, i) => (
                        <tr key={i}>
                          <td style={{ border: '1px solid var(--border)', padding: 8 }}>{n.id}</td>
                          <td style={{ border: '1px solid var(--border)', padding: 8 }}>{n.owner}</td>
                          <td style={{ border: '1px solid var(--border)', padding: 8 }}>{n.status}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
                {graph.nodes?.length > 50 && <p>… and {graph.nodes.length - 50} more nodes.</p>}
              </>
            ) : (
              <p>No graph.</p>
            )}
          </section>
          <section>
            <h2 style={{ fontSize: 18 }}>Incident report</h2>
            <p>
              <a href={api.getIncidentReportMdUrl(runId)}>Download incident report (.md)</a>
            </p>
            {incidentReport && (
              <JsonBlock value={incidentReport} />
            )}
          </section>
        </>
      )}
    </Layout>
  )
}


