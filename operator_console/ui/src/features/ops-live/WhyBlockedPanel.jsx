import React, { useEffect, useState } from 'react'
import { Modal } from 'hg_ui_kit'
import { api } from '../../lib/api.js'
import StateNotice from '../../components/StateNotice.jsx'

export default function WhyBlockedPanel({ workItemId, open, onClose }) {
  const [explanation, setExplanation] = useState(null)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState(null)

  useEffect(() => {
    if (!open || !workItemId) {
      setExplanation(null)
      setErr(null)
      return undefined
    }
    let cancelled = false
    setLoading(true)
    setErr(null)
    api
      .explainBlock(workItemId)
      .then((r) => {
        if (!cancelled) setExplanation(r)
      })
      .catch((e) => {
        if (!cancelled) setErr(e.message)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [open, workItemId])

  return (
    <Modal open={open} onClose={onClose}>
      <div style={{ padding: 20, maxWidth: 520 }} data-testid="ops-why-blocked-panel">
        <h2 style={{ marginTop: 0, fontSize: 18 }}>Why blocked?</h2>
        <p style={{ color: 'var(--muted)', fontSize: 13 }}>Work item: {workItemId || '—'}</p>
        {loading ? <StateNotice title="Loading explanation" detail="Querying control-surface materialized index." /> : null}
        {err ? <StateNotice tone="danger" title="Could not explain block" detail={err} /> : null}
        {explanation ? (
          <div style={{ fontSize: 14 }}>
            <p><strong>Blocked:</strong> {explanation.blocked ? 'yes' : 'no'}</p>
            {explanation.gate ? <p><strong>Gate:</strong> {explanation.gate}</p> : null}
            {Array.isArray(explanation.missing_evidence) && explanation.missing_evidence.length > 0 ? (
              <p><strong>Missing evidence:</strong> {explanation.missing_evidence.join(', ')}</p>
            ) : null}
            {explanation.recommended_next_step ? (
              <p><strong>Recommended:</strong> {explanation.recommended_next_step}</p>
            ) : null}
          </div>
        ) : null}
        <div style={{ marginTop: 16, display: 'flex', justifyContent: 'flex-end' }}>
          <button type="button" onClick={onClose}>Close</button>
        </div>
      </div>
    </Modal>
  )
}
