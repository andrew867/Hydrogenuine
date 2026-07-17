import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { EnvBadge, ImpersonationBanner, NotificationBell, RecognitionActiveBadge, SkipToContent, primaryRoleLabel, useConsentIndicator, useNotificationStream, useSession } from 'hg_ui_kit'
import { api, clearBrowserSession, getBrowserSession } from '../lib/api.js'
import { setProfileTimeZone, getProfileTimeZone } from '../lib/timezone.js'
import { withReturnUrl } from '../lib/navigationContext.js'
import { OPERATOR_NAV_GROUPS } from '../routes/manifest.js'
import { createShortcutController } from '../lib/shortcuts.js'
import ShortcutCheatSheet from './ShortcutCheatSheet.jsx'
import TenantSwitcher from './TenantSwitcher.jsx'
import OperatorCommandPalette from './OperatorCommandPalette.jsx'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8080/api/v1'
const GATEWAY_ME_URL = (() => {
  try {
    return `${new URL(API_BASE).origin}/v1/auth/me`
  } catch {
    return 'http://localhost:8080/v1/auth/me'
  }
})()

async function logout() {
  try {
    if (getBrowserSession()) {
      api.auth.oidcLogout(`${window.location.origin}/#/login?logged_out=1`)
      return
    }
    await api.auth.logout()
  } catch (_) {}
  clearBrowserSession()
  window.location.hash = '#/login'
}

function useProfileTimezone(session) {
  useEffect(() => {
    if (!session) return
    if (getProfileTimeZone()) return
    api.gatewayV1.listPrincipals()
      .then((r) => {
        const list = r?.principals ?? r
        if (!Array.isArray(list) || list.length === 0) return
        const withTz = list.find((p) => p?.timezone && String(p.timezone).trim())
        if (withTz?.timezone) setProfileTimeZone(String(withTz.timezone).trim())
      })
      .catch(() => {})
  }, [session])
}

const SHORTCUTS = [
  { label: 'Operations Home', href: '#/home' },
  { label: 'Live Status', href: '#/status' },
  { label: 'Approvals', href: '#/approvals' },
  { label: 'Social Ops', href: '#/social' },
]

export default function Layout({ title, children }) {
  const navigate = useNavigate()
  const { session } = useSession({ meUrl: GATEWAY_ME_URL })
  const [envLabel, setEnvLabel] = useState('')
  const [runtimeMode, setRuntimeMode] = useState('')
  const [safeLocalOnly, setSafeLocalOnly] = useState(false)
  const [activeHash, setActiveHash] = useState(window.location.hash || '#/')
  const [tenantMe, setTenantMe] = useState(null)
  const [shortcutOpen, setShortcutOpen] = useState(false)
  const [navOpen, setNavOpen] = useState(false)
  const { items: notifications } = useNotificationStream({
    streamUrl: api.gatewayV1.notificationsStreamUrl(),
    enabled: Boolean(session),
    headers: () => ({}),
  })
  const consentIndicator = useConsentIndicator({
    statusUrl: `${API_BASE}/consent/status`,
    subjectId: session?.principal_id || '',
    enabled: Boolean(session?.principal_id),
    headers: () => ({}),
    pollMs: 15000,
  })
  useProfileTimezone(session)

  useEffect(() => {
    if (!session) return
    api.gatewayV1.getTenantMe?.()
      .then((row) => setTenantMe(row))
      .catch(() => {})
  }, [session])

  useEffect(() => {
    const onKeyDown = createShortcutController({
      navigate,
      onCheatSheet: () => setShortcutOpen(true),
    })
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [navigate])

  useEffect(() => {
    fetch(`${API_BASE}/config/env`, { credentials: 'include' })
      .then((r) => r.json())
      .then((d) => {
        setEnvLabel(d.env || '')
        setRuntimeMode(d.runtime_mode || '')
        setSafeLocalOnly(Boolean(d.safe_local_only))
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    const onHash = () => setActiveHash(window.location.hash || '#/')
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  const isActive = (href) => {
    const path = (activeHash.replace(/^#/, '') || '/')
    if (href === '#/') {
      return path === '/' || path.startsWith('/runs')
    }
    const target = href.replace(/^#/, '')
    return path === target || path.startsWith(`${target}/`)
  }

  return (
    <div className="app-shell">
      <SkipToContent />
      {tenantMe?.impersonating ? (
        <ImpersonationBanner
          tenantId={tenantMe?.impersonation_tenant_id}
          role={tenantMe?.role}
          onExit={() => { window.location.hash = '#/superadmin' }}
        />
      ) : null}
      <header className="shell-header">
        <div className="brand">
          <span>Operator Console</span>
          <h1>{title}</h1>
          <EnvBadge env={envLabel} mode={runtimeMode} safeLocalOnly={safeLocalOnly} systemHref="#/system" />
          <RecognitionActiveBadge
            active={consentIndicator.recognitionActive}
            effectiveClass={consentIndicator.effectiveClass}
            href="#/consent"
          />
          <NotificationBell
            items={notifications}
            onOpenItem={(item) => {
              if (item.href) window.location.hash = `#${item.href}`
            }}
          />
          <span className="tag" data-testid="operator-role-label">{primaryRoleLabel(session)}</span>
          <TenantSwitcher session={session} />
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
          <button
            type="button"
            className="nav-menu-btn"
            aria-expanded={navOpen}
            aria-controls="operator-nav-grid"
            onClick={() => setNavOpen((open) => !open)}
          >
            Menu
          </button>
          {SHORTCUTS.map((s) => (
            <a key={s.label} className={`nav-link ${isActive(s.href) ? 'active' : ''}`} href={s.href}>
              {s.label}
            </a>
          ))}
          <button type="button" className="btn-secondary" style={{ marginLeft: 8 }} onClick={logout}>
            Log out
          </button>
        </div>
        <div id="operator-nav-grid" className={`nav-grid ${navOpen ? 'is-open' : ''}`}>
          {OPERATOR_NAV_GROUPS.map((group) => (
            <div className="nav-group" key={group.id}>
              <div className="nav-group-title">{group.title}</div>
              <div className="muted" style={{ fontSize: 12, marginBottom: 8 }}>{group.summary}</div>
              <div className="nav-links">
                {group.items.filter((item) => !item.adminOnly || api.proofs.hasProofAccess()).map((item) => {
                  const href = item.preserveReturnUrl ? withReturnUrl(item.href) : item.href
                  return (
                    <a
                      key={item.label}
                      className={`nav-link ${isActive(item.href) ? 'active' : ''}`}
                      href={href}
                      onClick={() => setNavOpen(false)}
                    >
                      {item.label}
                    </a>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      </header>
      <hr />
      <main id="main-content" tabIndex={-1}>
        {children}
      </main>
      <ShortcutCheatSheet open={shortcutOpen} onClose={() => setShortcutOpen(false)} />
      <OperatorCommandPalette navigate={navigate} />
    </div>
  )
}
