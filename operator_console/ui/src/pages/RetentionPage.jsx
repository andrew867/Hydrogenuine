import React, { useCallback, useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import { api } from '../lib/api.js'

export default function RetentionPage() {
  const [previewJson, setPreviewJson] = useState('{"api_key": "secret", "data": "ok"}')
  const [redacted, setRedacted] = useState(null)
  const [purgeRunId, setPurgeRunId] = useState('')
  const [purgeResult, setPurgeResult] = useState(null)
  const [auditEntries, setAuditEntries] = useState([])
  const [err, setErr] = useState(null)
  const [retention, setRetention] = useState(null)
  const [retentionSaving, setRetentionSaving] = useState(false)
  const [exportLoading, setExportLoading] = useState(false)

  const loadRetention = useCallback(() => {
    api.gatewayV1.getTenantRetention()
      .then((r) => setRetention(r))
      .catch(() => setRetention(null))
  }, [])

  useEffect(() => { loadRetention() }, [loadRetention])

  const loadAudit = useCallback(() => {
    api.getRetentionAudit(50)
      .then((r) => r.ok !== false && r.entries && setAuditEntries(r.entries))
      .catch(() => setAuditEntries([]))
  }, [])

  useEffect(() => { loadAudit() }, [loadAudit])

  const doRedactPreview = () => {
    setErr(null)
    setRedacted(null)
    try {
      const payload = JSON.parse(previewJson)
      api.redactPreview(payload)
        .then((r) => r.ok !== false && r.redacted && setRedacted(r.redacted))
        .catch((e) => setErr(e.message))
    } catch (e) {
      setErr('Invalid JSON: ' + e.message)
    }
  }

  const doPurge = () => {
    if (!purgeRunId.trim()) return
    setErr(null)
    setPurgeResult(null)
    api.purgeByRunId(purgeRunId.trim())
      .then((r) => {
        if (r.ok !== false) setPurgeResult(r)
        else setErr(r.detail || 'Purge failed')
      })
      .catch((e) => setErr(e.message))
      .finally(loadAudit)
  }

  const saveRetention = () => {
    if (!retention) return
    setErr(null)
    setRetentionSaving(true)
    api.gatewayV1.patchTenantRetention({
      chats_days: retention.chats_days,
      docs_days: retention.docs_days,
      proofs_days: retention.proofs_days,
      logs_days: retention.logs_days,
      legal_hold_enabled: retention.legal_hold_enabled,
    })
      .then((r) => { setRetention(r); setRetentionSaving(false) })
      .catch((e) => { setErr(e.message); setRetentionSaving(false) })
  }

  const doExport = () => {
    setErr(null)
    setExportLoading(true)
    api.gatewayV1.downloadTenantExport()
      .then(() => setExportLoading(false))
      .catch((e) => { setErr(e.message); setExportLoading(false) })
  }

  return (
    <Layout title="Retention and Purge">
      {err && <p style={{ color: 'var(--danger)' }}>{err}</p>}
      {retention != null && (
        <section>
          <h3>Tenant retention</h3>
          {retention.legal_hold_enabled && (
            <p style={{ color: 'var(--warning)', fontWeight: 'bold' }}>Legal hold is ON — purge is blocked for this tenant.</p>
          )}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'center', marginTop: 8 }}>
            <label>Chats (days): <input type="number" min={1} value={retention.chats_days} onChange={(e) => setRetention((r) => ({ ...r, chats_days: parseInt(e.target.value, 10) || 90 }))} style={{ width: 64 }} /></label>
            <label>Docs (days): <input type="number" min={1} value={retention.docs_days} onChange={(e) => setRetention((r) => ({ ...r, docs_days: parseInt(e.target.value, 10) || 90 }))} style={{ width: 64 }} /></label>
            <label>Proofs (days): <input type="number" min={1} value={retention.proofs_days} onChange={(e) => setRetention((r) => ({ ...r, proofs_days: parseInt(e.target.value, 10) || 30 }))} style={{ width: 64 }} /></label>
            <label>Logs (days): <input type="number" min={1} value={retention.logs_days} onChange={(e) => setRetention((r) => ({ ...r, logs_days: parseInt(e.target.value, 10) || 30 }))} style={{ width: 64 }} /></label>
            <label><input type="checkbox" checked={retention.legal_hold_enabled} onChange={(e) => setRetention((r) => ({ ...r, legal_hold_enabled: e.target.checked }))} /> Legal hold</label>
            <button type="button" onClick={saveRetention} disabled={retentionSaving}>Save</button>
          </div>
          <p style={{ marginTop: 8 }}>
            <button type="button" onClick={doExport} disabled={exportLoading}>{exportLoading ? 'Preparing…' : 'Download full export (zip + manifest)'}</button>
          </p>
        </section>
      )}
      <section style={{ marginTop: 24 }}>
        <h3>Redact preview</h3>
        <textarea value={previewJson} onChange={(e) => setPreviewJson(e.target.value)} rows={4} style={{ width: '100%', fontFamily: 'monospace' }} />
        <button type="button" onClick={doRedactPreview}>Preview redacted</button>
        {redacted != null && (
          <pre style={{ background: 'var(--panel-2)', padding: 12, marginTop: 8, overflow: 'auto' }}>
            {JSON.stringify(redacted, null, 2)}
          </pre>
        )}
      </section>
      <section style={{ marginTop: 24 }}>
        <h3>Purge by run_id</h3>
        <input value={purgeRunId} onChange={(e) => setPurgeRunId(e.target.value)} placeholder="run_id" style={{ marginRight: 8 }} />
        <button type="button" onClick={doPurge}>Purge</button>
        {purgeResult && <p>Removed: {purgeResult.removed_count}; audit entry recorded.</p>}
      </section>
      <section style={{ marginTop: 24 }}>
        <h3>Recent purge audit</h3>
        <ul>
          {auditEntries.map((e, i) => (
            <li key={i}>{e.action} run_id={e.run_id} removed_count={e.removed_count} ts={e.ts}</li>
          ))}
        </ul>
      </section>
    </Layout>
  )
}


