import React, { useCallback, useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import { AsyncPageBody, Banner, KeyValueGrid } from 'hg_ui_kit'
import { GATEWAY_V1_BASE } from '../lib/gatewayAuth.js'

async function gatewayGet(path) {
  const res = await fetch(`${GATEWAY_V1_BASE}${path}`, { credentials: 'include' })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`HTTP ${res.status}: ${text.slice(0, 200)}`)
  }
  return res.json()
}

export default function ProductSystem({ session, onLogout }) {
  const [version, setVersion] = useState(null)
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    Promise.all([gatewayGet('/system/version'), gatewayGet('/system/status')])
      .then(([versionBody, statusBody]) => {
        setVersion(versionBody)
        setStatus(statusBody)
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load])

  const diagnostics = status?.diagnostics || []

  return (
    <Layout title="System" onLogout={onLogout}>
      <div style={{ padding: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, marginBottom: 16 }}>
          <p className="muted">Gateway reachability for {session?.tenant_id || 'tenant'}.</p>
          <button type="button" onClick={load}>Refresh</button>
        </div>
        <AsyncPageBody loading={loading} error={error} onRetry={load}>
          {status?.status && status.status !== 'green' ? (
            <Banner tone={status.status === 'red' ? 'danger' : 'warning'}>
              System status is {status.status}. Review diagnostics below.
            </Banner>
          ) : null}
          <section style={{ marginTop: 16 }}>
            <h3>Overall status: {status?.status || 'unknown'}</h3>
            <KeyValueGrid
              entries={[
                { key: 'Service', value: version?.service || 'hg_gateway' },
                { key: 'Version', value: version?.version || '—' },
                { key: 'Build hash', value: version?.build_hash || '—' },
                { key: 'Environment', value: version?.environment || '—' },
              ]}
            />
          </section>
          <section style={{ marginTop: 24 }}>
            <h3>Diagnostics</h3>
            {diagnostics.length === 0 ? (
              <p className="muted">No diagnostics returned.</p>
            ) : (
              diagnostics.map((row, index) => (
                <div key={`${row.component}-${index}`} className="card" style={{ marginBottom: 12, padding: 12 }}>
                  <strong>{row.component || 'component'}</strong>
                  {row.detail ? <div className="muted">{row.detail}</div> : null}
                  {row.actionable ? <div style={{ color: 'var(--warning)' }}>{row.actionable}</div> : null}
                  {row.error ? <div style={{ color: 'var(--danger)' }}>{row.error}</div> : null}
                </div>
              ))
            )}
          </section>
        </AsyncPageBody>
      </div>
    </Layout>
  )
}
