import React, { useCallback, useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import { api } from '../lib/api.js'
import StateNotice from '../components/StateNotice.jsx'

function WorkflowTable({ rows }) {
  if (!rows.length) return null
  return (
    <div style={{ overflowX: 'auto', maxWidth: '100%' }}>
      <table cellPadding="8" style={{ borderCollapse: 'collapse', width: '100%', minWidth: 720 }}>
        <thead>
          <tr style={{ borderBottom: '1px solid var(--border)' }}>
            <th style={{ textAlign: 'left' }}>Workflow</th>
            <th style={{ textAlign: 'left' }}>Success</th>
            <th style={{ textAlign: 'left' }}>Degraded</th>
            <th style={{ textAlign: 'left' }}>Failed</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([workflowId, counts]) => (
            <tr key={workflowId} style={{ borderBottom: '1px solid var(--border)' }}>
              <td style={{ wordBreak: 'break-word' }}>{workflowId}</td>
              <td>{counts?.success ?? 0}</td>
              <td>{counts?.degraded ?? 0}</td>
              <td>{counts?.failed ?? 0}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function ServiceLevelsPage() {
  const [daily, setDaily] = useState(null)
  const [weekly, setWeekly] = useState(null)
  const [err, setErr] = useState(null)
  const [tab, setTab] = useState('daily')
  const [loading, setLoading] = useState(false)
  const current = tab === 'daily' ? daily : weekly
  const workflowRows = Object.entries(current?.runs_by_workflow || {})
    .sort(([, left], [, right]) => ((right?.failed ?? 0) + (right?.degraded ?? 0)) - ((left?.failed ?? 0) + (left?.degraded ?? 0)))
    .slice(0, 20)
  const failureRows = current?.top_failures || []

  const loadDaily = useCallback(() => {
    setErr(null)
    setLoading(true)
    api.getSlaDaily()
      .then((r) => r.ok !== false && r.report && setDaily(r.report))
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false))
  }, [])

  const loadWeekly = useCallback(() => {
    setErr(null)
    setLoading(true)
    api.getSlaWeekly()
      .then((r) => r.ok !== false && r.report && setWeekly(r.report))
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (tab === 'daily') loadDaily()
    else loadWeekly()
  }, [tab, loadDaily, loadWeekly])

  return (
    <Layout title="Service Levels">
      {err && <StateNotice tone="danger" title="Could not load service-level report" detail={err} action={<button type="button" onClick={() => (tab === 'daily' ? loadDaily() : loadWeekly())}>Retry</button>} />}
      <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
        <button type="button" onClick={() => setTab('daily')}>Daily</button>
        <button type="button" onClick={() => setTab('weekly')}>Weekly</button>
        <button type="button" onClick={() => (tab === 'daily' ? loadDaily() : loadWeekly())}>Refresh</button>
      </div>
      {loading && <StateNotice title="Loading service-level report" detail={`Fetching the ${tab} SLA report.`} />}
      {tab === 'daily' && daily != null && (
        <>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 16 }}>
          <div className="card"><strong>{Object.keys(daily.runs_by_workflow || {}).length}</strong><div className="muted">Workflows with runs</div></div>
          <div className="card"><strong>{(daily.top_failures || []).length}</strong><div className="muted">Top failures</div></div>
        </div>
        <WorkflowTable rows={workflowRows} />
        </>
      )}
      {tab === 'weekly' && weekly != null && (
        <>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 16 }}>
          <div className="card"><strong>{Object.keys(weekly.runs_by_workflow || {}).length}</strong><div className="muted">Workflows with runs</div></div>
          <div className="card"><strong>{(weekly.top_failures || []).length}</strong><div className="muted">Top failures</div></div>
        </div>
        <WorkflowTable rows={workflowRows} />
        </>
      )}
      {!loading && current != null && failureRows.length > 0 && (
        <section style={{ marginTop: 16 }}>
          <h2 style={{ fontSize: 18, marginBottom: 8 }}>Top failures</h2>
          <div style={{ overflowX: 'auto', maxWidth: '100%' }}>
            <table cellPadding="8" style={{ borderCollapse: 'collapse', width: '100%', minWidth: 720 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)' }}>
                  <th style={{ textAlign: 'left' }}>Workflow</th>
                  <th style={{ textAlign: 'left' }}>Failure class</th>
                  <th style={{ textAlign: 'left' }}>Count</th>
                </tr>
              </thead>
              <tbody>
                {failureRows.map((row, index) => (
                  <tr key={`${row.workflow_id || row.failure_class || 'failure'}-${index}`} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td style={{ wordBreak: 'break-word' }}>{row.workflow_id || '—'}</td>
                    <td>{row.failure_class || '—'}</td>
                    <td>{row.count ?? 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
      {!loading && tab === 'daily' && daily && Object.keys(daily.runs_by_workflow || {}).length === 0 && (
        <StateNotice title="No daily SLA data" detail="No workflow traces were summarized for the current daily report window." />
      )}
      {!loading && tab === 'daily' && daily == null && !err && (
        <StateNotice title="No daily report yet" detail="The daily SLA report did not return any structured data." />
      )}
      {!loading && tab === 'weekly' && weekly && Object.keys(weekly.runs_by_workflow || {}).length === 0 && (
        <StateNotice title="No weekly SLA data" detail="No workflow traces were summarized for the current weekly report window." />
      )}
      {!loading && tab === 'weekly' && weekly == null && !err && (
        <StateNotice title="No weekly report yet" detail="The weekly SLA report did not return any structured data." />
      )}
    </Layout>
  )
}


