import React, { useEffect, useState } from 'react'
import { api } from '../lib/api.js'

const CLIENT_UI_BASE = import.meta.env.VITE_CLIENT_UI_BASE || 'http://localhost:3000'

export default function TenantSwitcher({ session }) {
  const [tenants, setTenants] = useState([])
  const [err, setErr] = useState(null)

  const isSuperadmin = Array.isArray(session?.roles) && session.roles.includes('superadmin')
  useEffect(() => {
    if (!isSuperadmin || !api.proofs.hasAdminKey()) return
    api.gatewayAdmin.listTenants(null, 50, 0)
      .then((r) => setTenants(r?.tenants ?? []))
      .catch((e) => setErr(e.message))
  }, [isSuperadmin])

  if (!isSuperadmin) return null

  const onSwitch = (tenantId) => {
    if (!tenantId) return
    setErr(null)
    api.gatewayAdmin.impersonate({ tenant_id: tenantId, role: 'operator' })
      .then((r) => {
        const url = `${CLIENT_UI_BASE}/login?impersonation=${encodeURIComponent(r.token)}&tenant_id=${encodeURIComponent(tenantId)}`
        window.open(url, '_blank', 'noopener,noreferrer')
      })
      .catch((e) => setErr(e.message))
  }

  return (
    <label className="tag" style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
      <span>Tenant</span>
      <select
        data-testid="operator-tenant-switcher"
        defaultValue={session?.tenant_id ?? ''}
        onChange={(e) => onSwitch(e.target.value)}
        style={{ fontSize: 12 }}
      >
        <option value="">Switch tenant…</option>
        {tenants.map((t) => (
          <option key={t.tenant_id} value={t.tenant_id}>
            {t.display_name || t.tenant_id}
          </option>
        ))}
      </select>
      {err ? <span style={{ color: 'var(--danger)', fontSize: 11 }}>{err}</span> : null}
    </label>
  )
}
