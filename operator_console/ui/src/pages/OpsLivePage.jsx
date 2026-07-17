import React, { useMemo, useState } from 'react'
import Layout from '../components/Layout.jsx'
import Breadcrumbs from '../components/Breadcrumbs.jsx'
import StateNotice from '../components/StateNotice.jsx'
import StatusChip from '../components/StatusChip.jsx'
import LiveGrid from '../features/ops-live/LiveGrid.jsx'
import WhyBlockedPanel from '../features/ops-live/WhyBlockedPanel.jsx'
import BatchOpsBar from '../features/ops-live/BatchOpsBar.jsx'
import { useOpsLiveData } from '../features/ops-live/useOpsLiveData.js'

export default function OpsLivePage() {
  const { entities, overview, incidents, err, loading, reload } = useOpsLiveData()
  const [selectedEntityIds, setSelectedEntityIds] = useState(() => new Set())
  const [selectedWorkflows, setSelectedWorkflows] = useState(() => new Set())
  const [blockedRef, setBlockedRef] = useState(null)

  const failingRuns = overview?.failing || []
  const pausedWorkflows = overview?.paused || []
  const recentRuns = overview?.recent || []

  const batchWorkflowList = useMemo(
    () => [...selectedWorkflows],
    [selectedWorkflows],
  )

  const toggleEntity = (entityId) => {
    setSelectedEntityIds((prev) => {
      const next = new Set(prev)
      if (next.has(entityId)) next.delete(entityId)
      else next.add(entityId)
      return next
    })
  }

  const toggleWorkflow = (workflowId) => {
    setSelectedWorkflows((prev) => {
      const next = new Set(prev)
      if (next.has(workflowId)) next.delete(workflowId)
      else next.add(workflowId)
      return next
    })
  }

  return (
    <Layout title="Live operations">
      <Breadcrumbs items={[{ label: 'Home', href: '#/' }, { label: 'Live ops' }]} />
      <p style={{ color: 'var(--muted)', marginTop: 0 }}>
        Real-time entity grid, failing runs, incident queue, and batch workflow controls wired to operator APIs.
      </p>
      {err ? (
        <StateNotice tone="danger" title="Partial load failure" detail={err} action={<button type="button" onClick={reload}>Retry</button>} />
      ) : null}
      <BatchOpsBar selectedWorkflows={batchWorkflowList} onComplete={reload} />
      <section style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <h2 style={{ fontSize: 16, margin: 0 }}>Paused workflows</h2>
          <button type="button" onClick={reload} disabled={loading}>{loading ? 'Refreshing…' : 'Refresh'}</button>
        </div>
        {pausedWorkflows.length === 0 ? (
          <p style={{ color: 'var(--muted)', fontSize: 13 }}>No paused workflows.</p>
        ) : (
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {pausedWorkflows.map((wf) => (
              <li key={wf} style={{ marginBottom: 6 }}>
                <label style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
                  <input
                    type="checkbox"
                    checked={selectedWorkflows.has(wf)}
                    onChange={() => toggleWorkflow(wf)}
                  />
                  <a href={`#/workflows`}>{wf}</a>
                </label>
              </li>
            ))}
          </ul>
        )}
      </section>
      <section style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: 16 }}>Failing runs</h2>
        {failingRuns.length === 0 ? (
          <p style={{ color: 'var(--muted)', fontSize: 13 }}>No failing runs in the recent window.</p>
        ) : (
          <div className="scroll-table-wrap">
            <table className="scroll-table" width="100%" cellPadding="6" style={{ borderCollapse: 'collapse', minWidth: 640 }}>
              <thead>
                <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
                  <th>Run</th>
                  <th>Workflow</th>
                  <th>Status</th>
                  <th>Started</th>
                </tr>
              </thead>
              <tbody>
                {failingRuns.map((run) => (
                  <tr key={run.run_id} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td><a href={`#/runs/${encodeURIComponent(run.run_id)}`}>{run.run_id?.slice(0, 8)}…</a></td>
                    <td>{run.graph_id || '—'}</td>
                    <td><StatusChip status={run.status} /></td>
                    <td>{run.started_at || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
      <section style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: 16 }}>Entity live grid</h2>
        {loading && !entities.length ? (
          <StateNotice title="Loading live grid" detail="Reading entities and status overview." />
        ) : (
          <LiveGrid
            entities={entities}
            selectedIds={selectedEntityIds}
            onToggleSelect={toggleEntity}
            onOpenBlocked={(entityId) => setBlockedRef(entityId)}
          />
        )}
      </section>
      <section>
        <h2 style={{ fontSize: 16 }}>Incident queue ({incidents.length})</h2>
        {incidents.length === 0 ? (
          <p style={{ color: 'var(--muted)', fontSize: 13 }}>No terminal failures parked.</p>
        ) : (
          <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13 }}>
            {incidents.slice(0, 8).map((item) => (
              <li key={item.incident_id || item.run_id}>
                <a href="#/incident-queue">{item.incident_id || item.run_id}</a>
                {item.failure_class ? ` · ${item.failure_class}` : ''}
              </li>
            ))}
          </ul>
        )}
      </section>
      {recentRuns.length > 0 ? (
        <p style={{ fontSize: 12, color: 'var(--muted)', marginTop: 16 }}>
          {recentRuns.length} recent runs tracked · <a href="#/">Open runs list</a>
        </p>
      ) : null}
      <WhyBlockedPanel
        workItemId={blockedRef}
        open={!!blockedRef}
        onClose={() => setBlockedRef(null)}
      />
    </Layout>
  )
}
