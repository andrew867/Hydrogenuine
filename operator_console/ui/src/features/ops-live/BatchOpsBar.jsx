import React, { useState } from 'react'
import { api } from '../../lib/api.js'
import StateNotice from '../../components/StateNotice.jsx'

export default function BatchOpsBar({ selectedWorkflows, onComplete }) {
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)
  const [err, setErr] = useState(null)

  const runBatch = async (action) => {
    if (!selectedWorkflows.length) return
    setBusy(true)
    setErr(null)
    setResult(null)
    const outcomes = []
    try {
      for (const workflowId of selectedWorkflows) {
        if (action === 'pause') {
          outcomes.push(await api.pauseWorkflow(workflowId))
        } else if (action === 'resume') {
          outcomes.push(await api.resumeWorkflow(workflowId))
        } else if (action === 'rollback') {
          outcomes.push(await api.rollbackWorkflow(workflowId))
        }
      }
      setResult({ action, count: outcomes.length })
      onComplete?.()
    } catch (e) {
      setErr(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section
      style={{
        marginBottom: 16,
        padding: 12,
        border: '1px solid var(--border)',
        borderRadius: 12,
        background: 'var(--panel-2)',
      }}
      data-testid="ops-batch-bar"
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
        <strong>Batch workflow controls</strong>
        <span style={{ color: 'var(--muted)', fontSize: 13 }}>{selectedWorkflows.length} workflow(s) selected</span>
      </div>
      <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
        <button type="button" disabled={busy || !selectedWorkflows.length} onClick={() => runBatch('pause')}>
          Pause selected
        </button>
        <button type="button" disabled={busy || !selectedWorkflows.length} onClick={() => runBatch('resume')}>
          Resume selected
        </button>
        <button type="button" disabled={busy || !selectedWorkflows.length} onClick={() => runBatch('rollback')}>
          Rollback selected
        </button>
      </div>
      {result ? (
        <StateNotice
          tone="success"
          title={`${result.action} completed`}
          detail={`Applied to ${result.count} workflow(s).`}
        />
      ) : null}
      {err ? <StateNotice tone="danger" title="Batch action failed" detail={err} /> : null}
    </section>
  )
}
