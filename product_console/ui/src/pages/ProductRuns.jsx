import React, { useCallback, useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import StatusChip from '../components/StatusChip.jsx'
import Breadcrumbs from '../components/Breadcrumbs.jsx'
import { api } from '../lib/api.js'
import { formatDateTime } from '../lib/timezone.js'
import { AsyncPageBody } from '../components/PageStates.jsx'

export default function ProductRuns({ onLogout }) {
  const [data, setData] = useState({ items: [], total: 0 })
  const [workflowId, setWorkflowId] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState(null)

  const load = useCallback(() => {
    const params = { limit: 50 }
    if (workflowId) params.workflow_id = workflowId
    if (statusFilter) params.status = statusFilter
    setLoading(true)
    setErr(null)
    api.product.listRuns(params)
      .then(setData)
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false))
  }, [workflowId, statusFilter])

  useEffect(() => { load() }, [load])

  return (
    <Layout title="Runs (Product)" onLogout={onLogout}>
      <Breadcrumbs items={[{ label: 'Home', href: '#/' }, { label: 'Runs' }]} />
      <div style={{ marginBottom: 16, display: 'flex', gap: 12, flexWrap: 'wrap' }}>
        <input
          placeholder="Workflow ID"
          value={workflowId}
          onChange={(e) => setWorkflowId(e.target.value)}
          style={{ padding: 6 }}
        />
        <input
          placeholder="Status"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          style={{ padding: 6 }}
        />
      </div>
      <AsyncPageBody
        loading={loading}
        error={err}
        onRetry={load}
        empty={!loading && !err && data.items.length === 0}
        emptyTitle="No runs yet"
        emptyDescription="Start a workflow from Templates or Workflows to see product runs here."
        loadingLabel="Loading product runs"
      >
        <table width="100%" cellPadding="8" style={{ borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
              <th>Run ID</th>
              <th>Workflow</th>
              <th>Status</th>
              <th>Started</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((r) => (
              <tr key={r.run_id} style={{ borderBottom: '1px solid var(--border)' }}>
                <td><a href={`#/runs/${r.run_id}`}>{r.run_id}</a></td>
                <td>{r.graph_id || '—'}</td>
                <td><StatusChip status={r.status} /></td>
                <td>{formatDateTime(r.started_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p style={{ fontSize: 12, color: 'var(--muted)' }}>Total: {data.total}</p>
      </AsyncPageBody>
    </Layout>
  )
}
