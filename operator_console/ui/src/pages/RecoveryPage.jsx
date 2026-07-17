import React, { useCallback, useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import Breadcrumbs from '../components/Breadcrumbs.jsx'
import SharedEventSummary from '../components/SharedEventSummary.jsx'
import StateNotice from '../components/StateNotice.jsx'
import { PageSkeleton } from '../components/PageStates.jsx'
import { api } from '../lib/api.js'
import { withReturnUrl } from '../lib/navigationContext.js'

export default function RecoveryPage() {
  const [summary, setSummary] = useState(null)
  const [err, setErr] = useState(null)
  const [loading, setLoading] = useState(true)
  const [actionMsg, setActionMsg] = useState(null)

  const load = useCallback(() => {
    setErr(null)
    setLoading(true)
    api.getRecoverySummary()
      .then((data) => setSummary(data))
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load])

  const runAction = (action, targetType, targetId, details = {}) => {
    setActionMsg(null)
    setErr(null)
    api.recordRecoveryAction({ action, target_type: targetType, target_id: targetId, details })
      .then((result) => {
        setActionMsg(`Recorded ${action} on ${targetId}. Evidence: ${result.evidence_path || 'ledger'}`)
        load()
        if (result.post_action_landing) {
          window.location.hash = withReturnUrl(result.post_action_landing)
        }
      })
      .catch((e) => setErr(e.message))
  }

  const counts = summary?.counts || {}

  return (
    <Layout title="Recovery">
      <Breadcrumbs items={[{ label: 'Home', href: '#/home' }, { label: 'Recovery' }]} />
      <SharedEventSummary
        eyebrow="Recovery hub"
        title="Recovery"
        intro="Stuck runs, failed work, tripped breakers, purge, and retention cleanup in one place. Actions are recorded to activity and proof evidence."
        status={counts.stuck || counts.failed || counts.breakers ? 'watch' : 'healthy'}
        statusTone={counts.stuck || counts.failed ? 'warn' : 'good'}
        happened={`${counts.stuck || 0} stuck · ${counts.failed || 0} failed · ${counts.breakers || 0} breakers · ${counts.incidents || 0} incidents`}
        when={summary?.generated_at || '—'}
        why="Operators need a single recovery surface with an audit trail."
        changed={actionMsg || 'No recovery action recorded this session.'}
        next="After an action, inspect timeline or proofs for the recorded evidence."
        context={[
          { label: 'Timeline', value: '#/timeline' },
          { label: 'Proofs', value: '#/proofs' },
          { label: 'Retention', value: '#/retention' },
        ]}
      />
      {err && <StateNotice tone="danger" title="Recovery error" detail={err} action={<button type="button" onClick={load}>Retry</button>} />}
      {loading ? <PageSkeleton label="Loading" /> : null}
      {!loading && summary && (
        <>
          <section style={{ marginBottom: 24 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h2 style={{ fontSize: 18, margin: 0 }}>Stuck runs</h2>
              <button type="button" onClick={() => runAction('cancel_stale_runs', 'runs', 'stale', { stale_minutes: 30 })}>
                Cancel stale (30m)
              </button>
            </div>
            {(summary.stuck_runs || []).length === 0 ? (
              <StateNotice title="No stuck runs" detail="No runs have been running longer than the stale threshold." />
            ) : (
              <table className="table-basic" style={{ marginTop: 8 }}>
                <thead>
                  <tr><th>Run</th><th>Status</th><th>Started</th><th>Actions</th></tr>
                </thead>
                <tbody>
                  {(summary.stuck_runs || []).map((row) => (
                    <tr key={row.run_id || row.id}>
                      <td><code>{row.run_id || row.id}</code></td>
                      <td>{row.status}</td>
                      <td>{row.started_at || row.created_at || '—'}</td>
                      <td>
                        <button type="button" onClick={() => runAction('cancel_run', 'run', row.run_id || row.id)}>Cancel</button>
                        {' '}
                        <a className="nav-link" href={`#/runs/${row.run_id || row.id}`}>Open</a>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>

          <section style={{ marginBottom: 24 }}>
            <h2 style={{ fontSize: 18 }}>Failed runs</h2>
            {(summary.failed_runs || []).length === 0 ? (
              <StateNotice title="No failed runs in recent index" detail="Failed and blocked runs will appear here for retry or replay." />
            ) : (
              <table className="table-basic" style={{ marginTop: 8 }}>
                <thead>
                  <tr><th>Run</th><th>Status</th><th>Actions</th></tr>
                </thead>
                <tbody>
                  {(summary.failed_runs || []).map((row) => (
                    <tr key={row.run_id || row.id}>
                      <td><code>{row.run_id || row.id}</code></td>
                      <td>{row.status}</td>
                      <td>
                        <button type="button" onClick={() => runAction('replay_run', 'run', row.run_id || row.id)}>Replay</button>
                        {' '}
                        <button type="button" onClick={() => runAction('resume_run', 'run', row.run_id || row.id)}>Resume</button>
                        {' '}
                        <button type="button" onClick={() => runAction('purge_run', 'run', row.run_id || row.id)}>Purge artifacts</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>

          <section style={{ marginBottom: 24 }}>
            <h2 style={{ fontSize: 18 }}>Circuit breakers</h2>
            {(summary.tripped_breakers || []).length === 0 ? (
              <StateNotice title="No tripped breakers" detail="Breakers in open state will appear here." />
            ) : (
              <ul style={{ listStyle: 'none', padding: 0 }}>
                {(summary.tripped_breakers || []).map((b) => (
                  <li key={`${b.workflow_id}:${b.destination || ''}`} style={{ marginBottom: 8 }}>
                    <code>{b.workflow_id}</code>
                    {b.destination ? ` / ${b.destination}` : ''}
                    {' '}
                    <button
                      type="button"
                      onClick={() => runAction('reset_breaker', 'breaker', b.workflow_id, { destination: b.destination })}
                    >
                      Reset
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section style={{ marginBottom: 24 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h2 style={{ fontSize: 18, margin: 0 }}>Retention cleanup</h2>
              <button type="button" onClick={() => runAction('retention_cleanup', 'workspace', 'default', { retention_days: 365, dry_run: false })}>
                Run retention job
              </button>
            </div>
            <p className="muted" style={{ fontSize: 13 }}>
              Purge audit entries: {(summary.recent_purge_audit || []).length}. See <a href="#/retention" className="nav-link">Retention</a> for redact preview.
            </p>
          </section>

          <section>
            <h2 style={{ fontSize: 18 }}>Incident queue</h2>
            {(summary.incident_queue || []).length === 0 ? (
              <StateNotice title="Incident queue empty" detail="Terminal failures from dead-letter queue appear here." />
            ) : (
              <ul style={{ listStyle: 'none', padding: 0 }}>
                {(summary.incident_queue || []).slice(0, 20).map((item, idx) => (
                  <li key={item.incident_id || item.id || idx} style={{ marginBottom: 6 }}>
                    <code>{item.incident_id || item.id || 'incident'}</code>
                    {' '}
                    <span className="muted">{item.workflow_id || item.workflow || ''}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </Layout>
  )
}
