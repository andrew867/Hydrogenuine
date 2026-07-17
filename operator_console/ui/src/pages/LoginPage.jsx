import React, { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api, getBrowserSession } from '../lib/api.js'

function normalizeReturnUrl(raw) {
  let url = raw || '#/'
  if (!url.startsWith('#')) url = (url.startsWith('/') ? '#' : '#/') + url
  return url
}

function isLoggedOutState() {
  try {
    const params = new URLSearchParams(window.location.hash.split('?')[1] || '')
    return params.get('logged_out') === '1'
  } catch (_) {
    return false
  }
}

export default function LoginPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const returnUrl = normalizeReturnUrl(searchParams.get('returnUrl'))
  const [err, setErr] = useState(null)
  const [ssoLoading, setSsoLoading] = useState(false)
  const [demoLoading, setDemoLoading] = useState(false)
  const [oidcEnabled, setOidcEnabled] = useState(false)
  const [demoLoginEnabled, setDemoLoginEnabled] = useState(false)
  const [oidcChecked, setOidcChecked] = useState(false)
  const [loggedOut, setLoggedOut] = useState(false)
  const [sessionProbeDone, setSessionProbeDone] = useState(false)
  const [browserSession, setBrowserSession] = useState(() => getBrowserSession())
  const hasOperatorBrowserSession = !!(browserSession && Array.isArray(browserSession.roles) && browserSession.roles.some((role) => ['operator', 'tenant_admin', 'superadmin'].includes(role)))
  const hasMismatchedBrowserSession = !!(browserSession && !hasOperatorBrowserSession)

  useEffect(() => {
    const syncLoggedOut = () => setLoggedOut(isLoggedOutState())
    syncLoggedOut()
    window.addEventListener('hashchange', syncLoggedOut)
    return () => window.removeEventListener('hashchange', syncLoggedOut)
  }, [])

  useEffect(() => {
    let cancelled = false
    api.auth.getConfig()
      .then((cfg) => {
        if (!cancelled) {
          setOidcEnabled(Boolean(cfg?.oidc_enabled))
          setDemoLoginEnabled(Boolean(cfg?.demo_login_enabled))
        }
      })
      .catch(() => {
        if (!cancelled) {
          setOidcEnabled(false)
          setDemoLoginEnabled(false)
        }
      })
      .finally(() => {
        if (!cancelled) setOidcChecked(true)
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    api.auth.getMe()
      .then((session) => {
        if (!cancelled) setBrowserSession(session || getBrowserSession())
      })
      .catch(() => {
        if (!cancelled) setBrowserSession(getBrowserSession())
      })
      .finally(() => {
        if (!cancelled) setSessionProbeDone(true)
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!sessionProbeDone || loggedOut) return
    if (hasOperatorBrowserSession) {
      const target = returnUrl.replace(/^#/, '')
      navigate(target || '/', { replace: true })
    }
  }, [hasOperatorBrowserSession, loggedOut, navigate, returnUrl, sessionProbeDone])

  useEffect(() => {
    if (!sessionProbeDone || !oidcChecked || !oidcEnabled || loggedOut) return
    if (hasOperatorBrowserSession || hasMismatchedBrowserSession) {
      return
    }
    handleOidc()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasMismatchedBrowserSession, hasOperatorBrowserSession, loggedOut, oidcChecked, oidcEnabled, sessionProbeDone])

  const handleOidc = async () => {
    setErr(null)
    setSsoLoading(true)
    try {
      const cfg = await api.auth.getConfig()
      if (!cfg?.oidc_enabled) throw new Error('OIDC is not enabled in the gateway')
      const redirect = `${window.location.origin}/#${returnUrl.replace(/^#/, '')}`
      window.location.assign(`${new URL('/v1/auth/oidc/start', api.proofs.base).toString()}?frontend_redirect_uri=${encodeURIComponent(redirect)}`)
    } catch (e) {
      setErr(e.message || 'Unable to start SSO login')
      setSsoLoading(false)
    }
  }

  const handleDemoLogin = async () => {
    setErr(null)
    setDemoLoading(true)
    try {
      await api.auth.demoLogin()
      navigate(returnUrl.replace(/^#/, '') || '/', { replace: true })
    } catch (e) {
      setErr(e.message || 'Demo login failed')
    } finally {
      setDemoLoading(false)
    }
  }

  return (
    <div className="app-shell" style={{ maxWidth: 420, margin: '48px auto', padding: 24 }}>
      <header className="shell-header" style={{ marginBottom: 24 }}>
        <h1>Operator Console</h1>
        <p style={{ color: 'var(--muted)', fontSize: 14 }}>
          {oidcEnabled
            ? 'SSO is the primary browser login path.'
            : demoLoginEnabled
              ? 'Deterministic demo login is available for local operator sessions.'
              : 'SSO is unavailable right now. Check the gateway and Keycloak configuration.'}
        </p>
        {loggedOut ? (
          <p style={{ color: 'var(--muted)', fontSize: 12 }}>
            You are signed out. Choose SSO or demo login when you want to continue.
          </p>
        ) : null}
        {hasMismatchedBrowserSession ? (
          <p style={{ color: 'var(--muted)', fontSize: 12 }}>
            Your current browser session is not allowed in the operator console. Sign in with an operator, tenant admin, or superadmin account.
          </p>
        ) : null}
      </header>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {oidcEnabled ? (
          <button type="button" className="btn-primary" disabled={ssoLoading} onClick={handleOidc}>
            {ssoLoading ? 'Redirecting…' : 'Continue with SSO'}
          </button>
        ) : null}
        {demoLoginEnabled ? (
          <button type="button" className="btn-primary" disabled={demoLoading} onClick={handleDemoLogin}>
            {demoLoading ? 'Signing in…' : 'Continue with demo operator'}
          </button>
        ) : null}
      </div>
      {err && <p style={{ color: 'var(--danger)', fontSize: 14 }}>{err}</p>}
      <p style={{ marginTop: 16, fontSize: 12, color: 'var(--muted)' }}>
        Browser sessions back the console login. See <code>docs/demo/OPERATOR_FLOW.md</code> for the canonical operator path.
      </p>
    </div>
  )
}
