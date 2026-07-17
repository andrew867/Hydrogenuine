import React, { useCallback, useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import { api } from '../lib/api.js'
import Breadcrumbs from '../components/Breadcrumbs.jsx'
import { formatDateTime } from '../lib/timezone.js'
import StatusChip from '../components/StatusChip.jsx'
import AuditToast from '../components/AuditToast.jsx'
import { Modal } from 'hg_ui_kit'

function approvalStatus(a) {
  return a.status || a.decision || 'pending'
}

function approvalRequestedBy(a) {
  return a.requestedBy || a.requested_by || '—'
}

function approvalTimestamp(a) {
  return a.createdAt || a.timestamp || a.resolvedAt || null
}

export default function ProductApprovals({ onLogout }) {
  const [data, setData] = useState({ items: [], total: 0 })
  const [err, setErr] = useState(null)
  const [toast, setToast] = useState(null)
  const [overrideTarget, setOverrideTarget] = useState(null)
  const [overrideDecision, setOverrideDecision] = useState('approve')
  const [confirmText, setConfirmText] = useState('')
  const [overriding, setOverriding] = useState(false)

  const load = useCallback(() => {
    api.product.listApprovals().then(setData).catch((e) => setErr(e.message))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const submitOverride = async () => {
    if (!overrideTarget) return
    const expected = `OVERRIDE ${overrideTarget.id}`
    if (confirmText.trim() !== expected) {
      setErr(`Type "${expected}" to confirm.`)
      return
    }
    setOverriding(true)
    setErr(null)
    try {
      await api.product.overrideApproval(overrideTarget.id, { decision: overrideDecision })
      setToast(`Override recorded: ${overrideDecision} for ${overrideTarget.id}`)
      setOverrideTarget(null)
      setConfirmText('')
      load()
    } catch (e) {
      setErr(e.message)
    } finally {
      setOverriding(false)
    }
  }

  return (
    <Layout title="Approvals (Product)" onLogout={onLogout}>
      <Breadcrumbs items={[{ label: 'Home', href: '#/' }, { label: 'Approvals' }]} />
      {err && <div style={{ color: 'var(--danger)' }}>{err}</div>}
      <table width="100%" cellPadding="8" style={{ borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
            <th>ID</th>
            <th>Status</th>
            <th>Kind</th>
            <th>Risk</th>
            <th>Requested by</th>
            <th>Origin</th>
            <th>When</th>
            <th>Summary</th>
            <th>Override</th>
          </tr>
        </thead>
        <tbody>
          {data.items.map((a, i) => (
            <tr key={a.id || i} style={{ borderBottom: '1px solid var(--border)' }}>
              <td>{a.id || '—'}</td>
              <td><StatusChip status={approvalStatus(a)} label={approvalStatus(a)} /></td>
              <td>{a.kind || '—'}</td>
              <td>{a.risk || '—'}</td>
              <td>{approvalRequestedBy(a)}</td>
              <td>{a.origin?.label || a.workflow || a.chat_id || a.run_id || '—'}</td>
              <td>{formatDateTime(approvalTimestamp(a))}</td>
              <td>{a.summary || a.rationale || a.title || '—'}</td>
              <td>
                <button type="button" onClick={() => { setOverrideTarget(a); setConfirmText(''); setErr(null) }}>
                  Override…
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p style={{ fontSize: 12, color: 'var(--muted)' }}>Total: {data.total}</p>
      <Modal open={!!overrideTarget} onClose={() => setOverrideTarget(null)}>
        <div style={{ padding: 20, maxWidth: 480 }}>
          <h2 style={{ marginTop: 0, fontSize: 18 }}>Override approval</h2>
          <p style={{ fontSize: 13, color: 'var(--muted)' }}>
            Admin override is audit-logged. Type <code>OVERRIDE {overrideTarget?.id}</code> to confirm.
          </p>
          <label style={{ display: 'block', marginBottom: 12 }}>
            Decision
            <select value={overrideDecision} onChange={(e) => setOverrideDecision(e.target.value)} style={{ display: 'block', width: '100%', marginTop: 4 }}>
              <option value="approve">approve</option>
              <option value="deny">deny</option>
            </select>
          </label>
          <label style={{ display: 'block', marginBottom: 12 }}>
            Confirmation
            <input value={confirmText} onChange={(e) => setConfirmText(e.target.value)} style={{ display: 'block', width: '100%', marginTop: 4 }} />
          </label>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <button type="button" onClick={() => setOverrideTarget(null)}>Cancel</button>
            <button type="button" onClick={submitOverride} disabled={overriding}>
              {overriding ? 'Submitting…' : 'Submit override'}
            </button>
          </div>
        </div>
      </Modal>
      <AuditToast message={toast} onDismiss={() => setToast(null)} />
    </Layout>
  )
}
