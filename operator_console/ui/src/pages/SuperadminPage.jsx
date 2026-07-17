import React, { useCallback, useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import { api } from '../lib/api.js'
import Breadcrumbs from '../components/Breadcrumbs.jsx'

const CLIENT_UI_BASE = import.meta.env.VITE_CLIENT_UI_BASE || 'http://localhost:3000'

export default function SuperadminPage() {
  const [tenants, setTenants] = useState({ tenants: [], total: 0 })
  const [err, setErr] = useState(null)
  const [createId, setCreateId] = useState('')
  const [createName, setCreateName] = useState('')
  const [newKey, setNewKey] = useState(null)
  const [confirmDelete, setConfirmDelete] = useState('')

  const load = useCallback(() => {
    if (!api.proofs.hasAdminKey()) return
    setErr(null)
    api.gatewayAdmin.listTenants(null, 50, 0)
      .then((r) => setTenants({ tenants: r.tenants || [], total: r.total ?? r.tenants?.length ?? 0 }))
      .catch((e) => setErr(e.message))
  }, [])

  useEffect(() => { load() }, [load])

  const doCreate = () => {
    if (!createId.trim()) return
    setErr(null)
    api.gatewayAdmin.createTenant({ tenant_id: createId.trim(), display_name: createName.trim() || createId.trim() })
      .then(() => { setCreateId(''); setCreateName(''); load() })
      .catch((e) => setErr(e.message))
  }

  const doCreateKey = (tenantId) => {
    setErr(null)
    setNewKey(null)
    api.gatewayAdmin.createKey(tenantId)
      .then((r) => setNewKey({ tenantId, key: r.key, keyId: r.key_id }))
      .catch((e) => setErr(e.message))
  }

  const doImpersonate = (tenantId) => {
    setErr(null)
      api.gatewayAdmin.impersonate({ tenant_id: tenantId, role: 'operator' })
      .then((r) => {
        const url = `${CLIENT_UI_BASE}/login?impersonation=${encodeURIComponent(r.token)}&tenant_id=${encodeURIComponent(tenantId)}`
        window.location.assign(url)
      })
      .catch((e) => setErr(e.message))
  }

  const doExport = (tenantId) => {
    setErr(null)
    api.gatewayAdmin.exportTenant(tenantId)
      .then((data) => {
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
        const a = document.createElement('a')
        a.href = URL.createObjectURL(blob)
        a.download = `tenant-${tenantId}-export.json`
        a.click()
        URL.revokeObjectURL(a.href)
      })
      .catch((e) => setErr(e.message))
  }

  const doDelete = (tenantId) => {
    if (confirmDelete !== tenantId) { setErr('Type tenant_id to confirm'); return }
    setErr(null)
    api.gatewayAdmin.deleteTenant(tenantId, tenantId)
      .then(() => { setConfirmDelete(''); load() })
      .catch((e) => setErr(e.message))
  }

  if (!api.proofs.hasAdminKey()) {
    return (
      <Layout title="Superadmin">
        <Breadcrumbs items={[{ label: 'Home', href: '#/' }, { label: 'Superadmin' }]} />
        <p style={{ color: 'var(--warn)' }}>Superadmin browser session required. Sign in with a superadmin account to manage tenants.</p>
      </Layout>
    )
  }

  return (
    <Layout title="Superadmin — Tenants">
      <Breadcrumbs items={[{ label: 'Home', href: '#/' }, { label: 'Superadmin' }]} />
      {err && <p style={{ color: 'var(--danger)' }}>{err}</p>}
      {newKey && (
        <div style={{ marginBottom: 16, padding: 12, background: 'var(--panel-2)', borderRadius: 8, border: '1px solid var(--accent)' }}>
          <strong>New API key for {newKey.tenantId}</strong> (shown once):
          <pre style={{ marginTop: 8, wordBreak: 'break-all' }}>{newKey.key}</pre>
          <button type="button" onClick={() => setNewKey(null)}>Close</button>
        </div>
      )}
      <section>
        <h3>Create tenant</h3>
        <input value={createId} onChange={(e) => setCreateId(e.target.value)} placeholder="tenant_id" style={{ marginRight: 8 }} />
        <input value={createName} onChange={(e) => setCreateName(e.target.value)} placeholder="display_name" style={{ marginRight: 8 }} />
        <button type="button" onClick={doCreate}>Create</button>
      </section>
      <section style={{ marginTop: 24 }}>
        <h3>Tenants ({tenants.total})</h3>
        <table className="table">
          <thead>
            <tr>
              <th>tenant_id</th>
              <th>display_name</th>
              <th>status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {tenants.tenants.map((t) => (
              <tr key={t.tenant_id}>
                <td>{t.tenant_id}</td>
                <td>{t.display_name}</td>
                <td>{t.status}</td>
                <td>
                  <button type="button" onClick={() => doCreateKey(t.tenant_id)}>Create key</button>
                  {' '}
                  <button type="button" onClick={() => doImpersonate(t.tenant_id)}>Impersonate</button>
                  {' '}
                  <button type="button" onClick={() => doExport(t.tenant_id)}>Export</button>
                  {' '}
                  {confirmDelete === t.tenant_id ? (
                    <>
                      <input value={confirmDelete} onChange={(e) => setConfirmDelete(e.target.value)} placeholder="type tenant_id" size={12} />
                      <button type="button" onClick={() => doDelete(t.tenant_id)}>Confirm delete</button>
                      <button type="button" onClick={() => setConfirmDelete('')}>Cancel</button>
                    </>
                  ) : (
                    <button type="button" onClick={() => setConfirmDelete(t.tenant_id)}>Delete</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </Layout>
  )
}
