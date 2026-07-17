import React from 'react'
import Layout from '../components/Layout.jsx'
import Breadcrumbs from '../components/Breadcrumbs.jsx'
import StateNotice from '../components/StateNotice.jsx'
import { useRunsData } from '../features/runs/useRunsData.js'
import RunsDataTable from '../features/runs/RunsDataTable.jsx'

export default function Runs() {
  const {
    runs,
    isLoading,
    isFetching,
    err,
    load,
    cancelStale,
    staleCancelling,
    staleResult,
    channelHealthy,
  } = useRunsData()

  return (
    <Layout title="Runs">
      <Breadcrumbs items={[{ label: 'Home', href: '#/' }, { label: 'Runs' }]} />
      {err && <StateNotice tone="danger" title="Could not load runs" detail={err} action={<button type="button" onClick={load}>Retry</button>} />}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, flexWrap: 'wrap', gap: 8 }}>
        <span style={{ color: 'var(--muted)' }}>
          {runs.length} runs in the current operator view
          {channelHealthy ? ' · live SSE' : ''}
          {isFetching && !isLoading ? ' · refreshing…' : ''}
        </span>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <button type="button" onClick={cancelStale} disabled={staleCancelling} title="Cancel all running, launching, and gate-queue runs">
            {staleCancelling ? 'Cancelling…' : 'Cancel all active jobs'}
          </button>
          <button type="button" onClick={load}>Refresh</button>
        </div>
      </div>
      {staleResult && (
        <StateNotice
          tone={staleResult.ok ? 'success' : 'danger'}
          title={staleResult.ok ? `Cancelled ${staleResult.count ?? 0} active run(s)` : 'Cancel active runs failed'}
          detail={staleResult.ok ? (staleResult.stale_found === 0 ? 'No active runs found.' : null) : (staleResult.error || 'Unknown error')}
        />
      )}
      {isLoading ? (
        <StateNotice title="Loading runs" detail="Reading DAG run history from the operator API." />
      ) : runs.length === 0 ? (
        <StateNotice title="No runs found" detail="This view will populate once workflows or proofs have been executed through the runtime." />
      ) : (
        <RunsDataTable runs={runs} />
      )}
    </Layout>
  )
}
