import React, { useEffect, useState } from 'react'
import ProductDashboard from './pages/ProductDashboard.jsx'
import ProductTemplates from './pages/ProductTemplates.jsx'
import ProductWorkflows from './pages/ProductWorkflows.jsx'
import ProductRuns from './pages/ProductRuns.jsx'
import ProductRunDetail from './pages/ProductRunDetail.jsx'
import ProductApprovals from './pages/ProductApprovals.jsx'
import ProductDeadLetter from './pages/ProductDeadLetter.jsx'
import ProductProfile from './pages/ProductProfile.jsx'
import ProductSystem from './pages/ProductSystem.jsx'
import ProductLogin from './pages/ProductLogin.jsx'
import { fetchAuthMe, isLoggedOutHash } from './lib/gatewayAuth.js'
import { hasProductAuth } from './lib/auth.js'
import { PageSkeleton } from './components/PageStates.jsx'

function parseHash() {
  const h = window.location.hash.replace(/^#/, '') || '/'
  const parts = h.split('/').filter(Boolean)
  if (parts.length === 0) return { page: 'dashboard' }
  if (parts[0] === 'templates') return { page: 'templates' }
  if (parts[0] === 'workflows' && parts.length === 1) return { page: 'workflows' }
  if (parts[0] === 'workflows' && parts.length === 2) return { page: 'workflowDetail', wfId: parts[1] }
  if (parts[0] === 'runs' && parts.length === 1) return { page: 'runs' }
  if (parts[0] === 'runs' && parts.length === 2) return { page: 'runDetail', runId: parts[1] }
  if (parts[0] === 'approvals') return { page: 'approvals' }
  if (parts[0] === 'dead-letter') return { page: 'deadLetter' }
  if (parts[0] === 'profile') return { page: 'profile' }
  if (parts[0] === 'login') return { page: 'login' }
  return { page: 'dashboard' }
}

function sessionAllowsProduct(roles = []) {
  return roles.some((role) => ['superadmin', 'tenant_admin', 'operator'].includes(role))
}

export default function App() {
  const [route, setRoute] = useState(parseHash())
  const [authenticated, setAuthenticated] = useState(false)
  const [session, setSession] = useState(null)
  const [authReady, setAuthReady] = useState(false)

  useEffect(() => {
    const onHash = () => setRoute(parseHash())
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  useEffect(() => {
    let cancelled = false
    const probe = async () => {
      if (isLoggedOutHash()) {
        setAuthenticated(false)
        setSession(null)
        return
      }
      try {
        const me = await fetchAuthMe()
        if (cancelled) return
        if (me && sessionAllowsProduct(me.roles)) {
          setSession(me)
          setAuthenticated(true)
          return
        }
      } catch {
        // fall through to dev key check
      }
      const dev = hasProductAuth()
      setAuthenticated(dev)
      if (!dev && route.page !== 'login') {
        window.location.hash = '#/login'
      }
      if (dev && route.page === 'login') {
        window.location.hash = '#/'
      }
    }
    probe().finally(() => {
      if (!cancelled) setAuthReady(true)
    })
    return () => {
      cancelled = true
    }
  }, [route.page])

  const handleLoggedIn = () => {
    setAuthenticated(true)
    window.location.hash = '#/'
  }

  const handleLoggedOut = () => {
    setAuthenticated(false)
    setSession(null)
  }

  if (!authReady) {
    return <div className="login-shell"><div className="login-card"><PageSkeleton label="Checking session" rows={2} /></div></div>
  }

  if (!authenticated || route.page === 'login') {
    return <ProductLogin onLoggedIn={handleLoggedIn} />
  }

  if (route.page === 'workflows') return <ProductWorkflows session={session} onLogout={handleLoggedOut} />
  if (route.page === 'workflowDetail') return <ProductWorkflows wfId={route.wfId} session={session} onLogout={handleLoggedOut} />
  if (route.page === 'runs') return <ProductRuns session={session} onLogout={handleLoggedOut} />
  if (route.page === 'runDetail') return <ProductRunDetail runId={route.runId} session={session} onLogout={handleLoggedOut} />
  if (route.page === 'approvals') return <ProductApprovals session={session} onLogout={handleLoggedOut} />
  if (route.page === 'deadLetter') return <ProductDeadLetter session={session} onLogout={handleLoggedOut} />
  if (route.page === 'profile') return <ProductProfile session={session} onLogout={handleLoggedOut} />
  if (route.page === 'system') return <ProductSystem session={session} onLogout={handleLoggedOut} />
  if (route.page === 'templates') return <ProductTemplates session={session} onLogout={handleLoggedOut} />
  return <ProductDashboard session={session} onLogout={handleLoggedOut} />
}
