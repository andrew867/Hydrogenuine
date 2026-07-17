import React, { useEffect, useState } from 'react'
import { fetchAuthConfig, fetchAuthMe, isLoggedOutHash, startOidcLogin } from '../lib/gatewayAuth.js'
import { setProductApiKey } from '../lib/auth.js'

export default function ProductLogin({ onLoggedIn }) {
  const [err, setErr] = useState(null)
  const [oidcEnabled, setOidcEnabled] = useState(false)
  const [devKey, setDevKey] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    Promise.all([fetchAuthConfig().catch(() => ({})), fetchAuthMe().catch(() => null)])
      .then(([cfg, me]) => {
        if (cancelled) return
        setOidcEnabled(Boolean(cfg?.oidc_enabled))
        if (me?.roles?.length && !isLoggedOutHash()) onLoggedIn?.()
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [onLoggedIn])

  const handleSso = () => {
    setErr(null)
    try {
      startOidcLogin(`${window.location.pathname}${window.location.hash || '#/'}`)
    } catch (e) {
      setErr(e.message || 'Unable to start SSO')
    }
  }

  const handleDevKey = (event) => {
    event.preventDefault()
    const trimmed = devKey.trim()
    if (!trimmed) return
    setProductApiKey(trimmed)
    onLoggedIn?.()
  }

  if (loading) {
    return <div className="login-shell"><div className="login-card"><p className="muted">Checking session…</p></div></div>
  }

  return (
    <div className="login-shell">
      <div className="login-card">
        <div className="login-kicker">Hydrogenuine</div>
        <h1>Product Console</h1>
        <p className="muted" style={{ marginTop: 0 }}>
          Sign in with your organization SSO. Product access requires operator, tenant admin, or superadmin role.
        </p>
        {oidcEnabled ? (
          <button type="button" className="btn-primary" onClick={handleSso}>
            Continue with SSO
          </button>
        ) : (
          <p className="muted">SSO is not enabled on this gateway. Contact your administrator.</p>
        )}
        {import.meta.env.DEV ? (
          <form onSubmit={handleDevKey} className="login-form" style={{ marginTop: 16 }}>
            <label htmlFor="product-dev-key">Dev-only product API key</label>
            <input
              id="product-dev-key"
              type="password"
              value={devKey}
              onChange={(event) => setDevKey(event.target.value)}
              placeholder="Bearer key (development only)"
              autoComplete="off"
            />
            <div className="login-actions">
              <button type="submit" disabled={!devKey.trim()}>Use dev key</button>
            </div>
          </form>
        ) : null}
        {isLoggedOutHash() ? (
          <p className="muted" style={{ marginTop: 12 }}>
            You are signed out. Choose SSO when you want to continue.
          </p>
        ) : null}
        {err ? <p style={{ color: 'var(--danger)' }}>{err}</p> : null}
      </div>
    </div>
  )
}
