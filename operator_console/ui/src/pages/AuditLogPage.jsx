import React, { useCallback, useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import { AsyncPageBody, TimeAgo } from 'hg_ui_kit'
import { api } from '../lib/api.js'

export default function AuditLogPage() {
  const [rows, setRows] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [eventType, setEventType] = useState('')
  const [tenantFilter, setTenantFilter] = useState('')
  const adminMode = api.proofs.hasProofAccess()

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    const params = { limit: 100 }
    if (eventType.trim()) params.event_type = eventType.trim()
    if (adminMode && tenantFilter.trim()) params.tenant_id = tenantFilter.trim()
    const request = adminMode ? api.gatewayV1.getAdminAudit(params) : api.gatewayV1.getTenantAudit(params)
    request
      .then((body) => {
        setRows(body.items || [])
        setTotal(body.total || 0)
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [adminMode, eventType, tenantFilter])

  useEffect(() => { load() }, [load])

  const exportCsv = () => {
    const header = ['event_id', 'tenant_id', 'event_type', 'created_at', 'payload']
    const lines = rows.map((row) =>
      [row.event_id ?? '', row.tenant_id ?? '', row.event_type ?? '', row.created_at ?? '', JSON.stringify(row.payload ?? {})]
        .map((cell) => `"${String(cell).replace(/"/g, '""')}"`)
        .join(','),
    )
    const blob = new Blob([[header.join(','), ...lines].join('\n')], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `audit_${adminMode ? 'admin' : 'tenant'}_${new Date().toISOString().slice(0, 10)}.csv`
    anchor.click()
    URL.revokeObjectURL(url)
  }

  return (
    <Layout title="Audit log">
      <div style={{ padding: 16 }}>
        <p className="muted">{adminMode ? 'Cross-tenant audit events (superadmin)' : 'Tenant-scoped audit events'}</p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, marginBottom: 16 }}>
          <label>
            Event type
            <input value={eventType} onChange={(e) => setEventType(e.target.value)} placeholder="tenant.export" />
          </label>
          {adminMode ? (
            <label>
              Tenant ID
              <input value={tenantFilter} onChange={(e) => setTenantFilter(e.target.value)} placeholder="default" />
            </label>
          ) : null}
          <button type="button" onClick={load}>Refresh</button>
          <button type="button" onClick={exportCsv} disabled={rows.length === 0}>Export CSV</button>
        </div>
        <AsyncPageBody
          loading={loading}
          error={error}
          onRetry={load}
          empty={!loading && !error && rows.length === 0}
          emptyTitle="No audit events"
          emptyDescription="Audit events will appear here as the gateway records them."
        >
          <table className="data-table">
            <thead>
              <tr>
                <th>When</th>
                <th>Tenant</th>
                <th>Event</th>
                <th>Payload</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={`${row.event_id}-${row.created_at}`}>
                  <td>{row.created_at ? <TimeAgo value={row.created_at} /> : '—'}</td>
                  <td><code>{row.tenant_id || '—'}</code></td>
                  <td>{row.event_type || '—'}</td>
                  <td><pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{JSON.stringify(row.payload || {}, null, 2)}</pre></td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="muted" style={{ marginTop: 12 }}>Total: {total}</p>
        </AsyncPageBody>
      </div>
    </Layout>
  )
}
