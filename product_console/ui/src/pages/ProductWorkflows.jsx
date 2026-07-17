import React, { useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import StatusChip from '../components/StatusChip.jsx'
import { api } from '../lib/api.js'

export default function ProductWorkflows({ wfId, onLogout }) {
  const [data, setData] = useState({ items: [], total: 0 })
  const [detail, setDetail] = useState(null)
  const [err, setErr] = useState(null)
  const [running, setRunning] = useState(false)
  const [templates, setTemplates] = useState([])
  const [templateId, setTemplateId] = useState('')
  const [payloadText, setPayloadText] = useState('{\"mode\":\"live\"}')
  const [liveActionsEnabled, setLiveActionsEnabled] = useState(false)

  useEffect(() => {
    api.product.listWorkflows().then(setData).catch((e) => setErr(e.message))
    api.product.listTemplates().then((r) => setTemplates(r.items || [])).catch(() => {})
    api.product.getDemoConfig()
      .then((cfg) => {
        const live = Boolean(cfg?.live_actions_enabled)
        setLiveActionsEnabled(live)
        if (live) setPayloadText('{\"mode\":\"live\"}')
      })
      .catch(() => setLiveActionsEnabled(false))
  }, [])
  useEffect(() => {
    if (!wfId) return
    api.product.getWorkflow(wfId).then(setDetail).catch(() => setDetail(null))
  }, [wfId])

  const handleRun = () => {
    setRunning(true)
    let payload = { mode: 'shadow' }
    try {
      payload = payloadText.trim() ? JSON.parse(payloadText) : payload
    } catch (e) {
      setErr(`Invalid JSON payload: ${e.message}`)
      setRunning(false)
      return
    }
    if (templateId) payload.template_id = templateId
    api.product.triggerWorkflowRun(wfId, payload)
      .then(() => setErr(null))
      .catch((e) => setErr(e.message))
      .finally(() => setRunning(false))
  }

  if (wfId && detail) {
    return (
      <Layout title={`Workflow: ${wfId}`} onLogout={onLogout}>
        {err && <div style={{ color: 'var(--danger)' }}>{err}</div>}
        <p><StatusChip status={detail.status} /> <StatusChip status={detail.readiness} label={detail.readiness} /></p>
        <p><a href="#/workflows">← Workflows</a></p>
        <div className="section-card" style={{ marginBottom: 16 }}>
          <h3 style={{ marginTop: 0 }}>Trigger run</h3>
          <label style={{ display: 'block', marginBottom: 6 }}>Template (optional)</label>
          <select value={templateId} onChange={(e) => setTemplateId(e.target.value)} style={{ padding: 8, borderRadius: 8, marginBottom: 10 }}>
            <option value="">None</option>
            {templates.map((t) => (
              <option key={t.template_id} value={t.template_id}>{t.template_id}</option>
            ))}
          </select>
          <label style={{ display: 'block', marginBottom: 6 }}>Payload (JSON)</label>
          <textarea
            value={payloadText}
            onChange={(e) => setPayloadText(e.target.value)}
            rows={5}
            style={{ width: '100%', padding: 8, borderRadius: 8, border: '1px solid var(--border)', background: '#0b1118', color: 'var(--text)' }}
          />
          <div style={{ marginTop: 10 }}>
            <button type="button" onClick={handleRun} disabled={running}>
              {running ? 'Running…' : liveActionsEnabled ? 'Run (live)' : 'Run (shadow)'}
            </button>
          </div>
        </div>
      </Layout>
    )
  }

  return (
    <Layout title="Workflows (Product)" onLogout={onLogout}>
      {err && <div style={{ color: 'var(--danger)' }}>{err}</div>}
      <table width="100%" cellPadding="8" style={{ borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
            <th>ID</th>
            <th>Name</th>
            <th>Status</th>
            <th>Readiness</th>
          </tr>
        </thead>
        <tbody>
          {data.items.map((w) => (
            <tr key={w.id} style={{ borderBottom: '1px solid var(--border)' }}>
              <td><a href={`#/workflows/${w.id}`}>{w.id}</a></td>
              <td>{w.name || w.id}</td>
              <td><StatusChip status={w.status} /></td>
              <td><StatusChip status={w.readiness} label={w.readiness} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </Layout>
  )
}


