import React, { useCallback, useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import { api } from '../lib/api.js'
import Breadcrumbs from '../components/Breadcrumbs.jsx'
import { AsyncPageBody } from '../components/PageStates.jsx'

export default function TenantAdminPage() {
  const [principals, setPrincipals] = useState([])
  const [settings, setSettings] = useState(null)
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState(null)
  const [includeDisabled, setIncludeDisabled] = useState(false)

  const load = useCallback(() => {
    setErr(null)
    setLoading(true)
    Promise.all([
      api.gatewayV1.listPrincipals(includeDisabled)
        .then((r) => setPrincipals(r.principals || []))
        .catch((e) => setErr(e.message)),
      api.gatewayV1.getTenantMeSettings()
        .then((s) => setSettings(s))
        .catch(() => setSettings(null)),
    ]).finally(() => setLoading(false))
  }, [includeDisabled])

  useEffect(() => { load() }, [load])

  return (
    <Layout title="Tenant Admin">
      <Breadcrumbs items={[{ label: 'Home', href: '#/' }, { label: 'Tenant Admin' }]} />
      <AsyncPageBody
        loading={loading}
        error={err}
        onRetry={load}
        empty={!loading && !err && principals.length === 0}
        emptyTitle="No principals"
        emptyDescription="Invite operators or service principals to populate this tenant."
        loadingLabel="Loading tenant admin"
      >
        {settings && (
          <section style={{ marginBottom: 24 }}>
            <h3>Tenant settings</h3>
            <p><strong>Tenant:</strong> {settings.tenant_id} — {settings.display_name}</p>
          </section>
        )}
        <section>
          <h3>Principals</h3>
          <label><input type="checkbox" checked={includeDisabled} onChange={(e) => setIncludeDisabled(e.target.checked)} /> Include disabled</label>
          <table className="table" style={{ marginTop: 8 }}>
            <thead>
              <tr>
                <th>id</th>
                <th>type</th>
                <th>label</th>
                <th>status</th>
                <th>escalation_chain</th>
              </tr>
            </thead>
            <tbody>
              {principals.map((p) => (
                <tr key={p.id}>
                  <td>{p.id}</td>
                  <td>{p.type}</td>
                  <td>{p.label}</td>
                  <td>{p.status}</td>
                  <td>{(p.escalation_chain || []).join(', ') || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </AsyncPageBody>
    </Layout>
  )
}
