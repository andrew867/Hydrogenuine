import React, { useCallback, useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import { api } from '../lib/api.js'
import StateNotice from '../components/StateNotice.jsx'

export default function ReliabilityPage() {
  const [failureClasses, setFailureClasses] = useState([])
  const [policies, setPolicies] = useState({})
  const [breakers, setBreakers] = useState([])
  const [deadletter, setDeadletter] = useState([])
  const [budgetSummary, setBudgetSummary] = useState({ by_workflow: {}, recent_runs: 0 })
  const [err, setErr] = useState(null)

  const load = useCallback(() => {
    setErr(null)
    api.getFailureClasses()
      .then((r) => r.ok !== false && r.classes && setFailureClasses(r.classes))
      .catch((e) => setErr(e.message))
    api.getRetryPolicy()
      .then((r) => r.ok !== false && r.policies && setPolicies(r.policies))
      .catch(() => {})
    api.getBreakers()
      .then((r) => r.ok !== false && r.breakers && setBreakers(r.breakers))
      .catch(() => {})
    api.getReliabilityIncidentQueue()
      .then((r) => r.ok !== false && r.items && setDeadletter(r.items))
      .catch(() => {})
    api.getBudgetSummary()
      .then((r) => r.ok !== false && setBudgetSummary({ by_workflow: r.by_workflow || {}, recent_runs: r.recent_runs || 0 }))
      .catch(() => {})
  }, [])

  useEffect(() => { load() }, [load])

  const resetBreaker = (workflowId, destination) => {
    setErr(null)
    api.resetBreaker(workflowId, destination)
      .then(() => load())
      .catch((e) => setErr(e.message))
  }

  return (
    <Layout title="Reliability — Failure, Retry, Circuit Breakers, Incident Queue, Budget">
      {err && <StateNotice tone="danger" title="Could not fully load reliability data" detail={err} action={<button type="button" onClick={load}>Retry</button>} />}
      <section style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <div style={{ color: 'var(--muted)' }}>
            {failureClasses.length} failure classes, {breakers.length} breakers, {deadletter.length} incident items.
          </div>
          <button type="button" onClick={load}>Refresh</button>
        </div>
        <h2 style={{ fontSize: 18 }}>Failure Classes</h2>
        {failureClasses.length === 0 ? (
          <StateNotice title="No failure classes reported" detail="The reliability classifier has not produced any active failure-class catalog entries yet." />
        ) : (
        <ul style={{ listStyle: 'none', padding: 0 }}>
          {failureClasses.map((c) => (
            <li key={c} style={{ padding: 4 }}>{c}</li>
          ))}
        </ul>
        )}
      </section>
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 18 }}>Retry Policy</h2>
        {Object.keys(policies).length === 0 ? (
          <StateNotice title="No retry policy data" detail="Retry policy metadata is not available from the operator API yet." />
        ) : (
        <table style={{ borderCollapse: 'collapse', width: '100%' }}>
          <thead>
            <tr>
              <th style={{ border: '1px solid var(--border)', padding: 8 }}>class</th>
              <th style={{ border: '1px solid var(--border)', padding: 8 }}>max_attempts</th>
              <th style={{ border: '1px solid var(--border)', padding: 8 }}>retryable</th>
              <th style={{ border: '1px solid var(--border)', padding: 8 }}>retry_backoff_ms</th>
              <th style={{ border: '1px solid var(--border)', padding: 8 }}>escalation</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(policies).map(([cls, p]) => (
              <tr key={cls}>
                <td style={{ border: '1px solid var(--border)', padding: 8 }}>{cls}</td>
                <td style={{ border: '1px solid var(--border)', padding: 8 }}>{p.max_attempts}</td>
                <td style={{ border: '1px solid var(--border)', padding: 8 }}>{String(p.retryable)}</td>
                <td style={{ border: '1px solid var(--border)', padding: 8 }}>{p.retry_backoff_ms}</td>
                <td style={{ border: '1px solid var(--border)', padding: 8 }}>{p.escalation}</td>
              </tr>
            ))}
          </tbody>
        </table>
        )}
      </section>
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 18 }}>Circuit Breakers</h2>
        {breakers.length === 0 ? (
          <p>No breakers.</p>
        ) : (
          <table style={{ borderCollapse: 'collapse', width: '100%' }}>
            <thead>
              <tr>
                <th style={{ border: '1px solid var(--border)', padding: 8 }}>workflow_id</th>
                <th style={{ border: '1px solid var(--border)', padding: 8 }}>destination</th>
                <th style={{ border: '1px solid var(--border)', padding: 8 }}>failures</th>
                <th style={{ border: '1px solid var(--border)', padding: 8 }}>tripped</th>
                <th style={{ border: '1px solid var(--border)', padding: 8 }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {breakers.map((b, i) => (
                <tr key={i}>
                  <td style={{ border: '1px solid var(--border)', padding: 8 }}>{b.workflow_id}</td>
                  <td style={{ border: '1px solid var(--border)', padding: 8 }}>{b.destination ?? '—'}</td>
                  <td style={{ border: '1px solid var(--border)', padding: 8 }}>{b.failures}</td>
                  <td style={{ border: '1px solid var(--border)', padding: 8 }}>{String(!!b.tripped)}</td>
                  <td style={{ border: '1px solid var(--border)', padding: 8 }}>
                    <button type="button" onClick={() => resetBreaker(b.workflow_id, b.destination)}>Reset</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 18 }}>Incident Queue</h2>
        {deadletter.length === 0 ? (
          <p>No incident items.</p>
        ) : (
          <ul>
            {deadletter.map((item, i) => (
              <li key={i}>{item.task_id} / {item.run_id} — {item.written_at}</li>
            ))}
          </ul>
        )}
      </section>
      <section>
        <h2 style={{ fontSize: 18 }}>Budget summary (recent runs: {budgetSummary.recent_runs})</h2>
        {Object.keys(budgetSummary.by_workflow).length === 0 ? (
          <p>No workflow data.</p>
        ) : (
          <table style={{ borderCollapse: 'collapse', width: '100%' }}>
            <thead>
              <tr>
                <th style={{ border: '1px solid var(--border)', padding: 8 }}>workflow_id</th>
                <th style={{ border: '1px solid var(--border)', padding: 8 }}>runs</th>
                <th style={{ border: '1px solid var(--border)', padding: 8 }}>total_budget_used</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(budgetSummary.by_workflow).map(([wid, v]) => (
                <tr key={wid}>
                  <td style={{ border: '1px solid var(--border)', padding: 8 }}>{wid}</td>
                  <td style={{ border: '1px solid var(--border)', padding: 8 }}>{v.runs}</td>
                  <td style={{ border: '1px solid var(--border)', padding: 8 }}>{v.total_budget_used}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </Layout>
  )
}


