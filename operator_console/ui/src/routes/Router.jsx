import React, { Suspense, useEffect, useState } from 'react'
import { HashRouter, Routes, Route, Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { Skeleton } from 'hg_ui_kit'
import { api, getBrowserSession } from '../lib/api.js'
import { OPERATOR_ROUTE_MANIFEST } from './manifest.js'

function ShellSkeleton() {
  return (
    <div className="app-shell" style={{ padding: 24 }}>
      <Skeleton height={28} width="40%" />
      <div style={{ marginTop: 16 }}>
        <Skeleton height={240} />
      </div>
    </div>
  )
}

function PageFallback() {
  return (
    <div style={{ padding: 24 }}>
      <Skeleton height={20} width="30%" />
      <Skeleton height={160} style={{ marginTop: 12 }} />
    </div>
  )
}

function RequireAuth() {
  const location = useLocation()
  const navigate = useNavigate()
  const [ready, setReady] = useState(false)
  const [allowed, setAllowed] = useState(false)

  useEffect(() => {
    let active = true
    api.auth
      .getMe()
      .then((session) => {
        if (!active) return
        const roles = session?.roles ?? getBrowserSession()?.roles ?? []
        const ok = Array.isArray(roles) && roles.some((role) => ['operator', 'tenant_admin', 'superadmin'].includes(role))
        setAllowed(ok)
        if (!ok) {
          const returnUrl = `#${location.pathname}${location.search}`
          navigate(`/login?returnUrl=${encodeURIComponent(returnUrl)}`, { replace: true })
        }
      })
      .catch(() => {
        if (!active) return
        setAllowed(false)
        navigate('/login', { replace: true })
      })
      .finally(() => {
        if (active) setReady(true)
      })
    return () => {
      active = false
    }
  }, [location.pathname, location.search, navigate])

  if (!ready || !allowed) return <ShellSkeleton />
  return <Outlet />
}

function AdminRoute({ children }) {
  const allowed = api.proofs.hasProofAccess()
  if (!allowed) {
    return (
      <div className="app-shell" style={{ padding: 24 }}>
        <p>Superadmin access required for this page.</p>
      </div>
    )
  }
  return children
}

function RoutedApp() {
  return (
    <Suspense fallback={<PageFallback />}>
      <Routes>
        {OPERATOR_ROUTE_MANIFEST.filter((row) => row.public).map((row) => (
          <Route key={row.path} path={row.path} element={<row.Component />} />
        ))}
        <Route element={<RequireAuth />}>
          {OPERATOR_ROUTE_MANIFEST.filter((row) => !row.public).map((row) => {
            const element = row.adminOnly ? (
              <AdminRoute>
                <row.Component />
              </AdminRoute>
            ) : (
              <row.Component />
            )
            return <Route key={`${row.path}-${row.page}`} path={row.path} element={element} />
          })}
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  )
}

export default function OperatorRouter() {
  return (
    <HashRouter>
      <RoutedApp />
    </HashRouter>
  )
}
