import React, { useEffect, useState } from 'react'
import { EnvBadge, ImpersonationBanner, NotificationBell, SkipToContent, applyBrand, primaryRoleLabel, useNotificationStream, useSession } from 'hg_ui_kit'
import { clearProductApiKey } from '../lib/auth.js'
import { fetchAuthConfig, GATEWAY_V1_BASE, logoutBrowserSession, startOidcLogout } from '../lib/gatewayAuth.js'

const NAV_GROUPS = [
  {
    title: 'Overview',
    items: [
      { label: 'Dashboard', href: '#/' },
      { label: 'Runs', href: '#/runs' },
      { label: 'Workflows', href: '#/workflows' },
    ],
  },
  {
    title: 'Governance',
    items: [
      { label: 'Approvals', href: '#/approvals' },
      { label: 'Dead-letter', href: '#/dead-letter' },
      { label: 'Templates', href: '#/templates' },
      { label: 'Profile', href: '#/profile' },
      { label: 'System', href: '#/system' },
    ],
  },
  {
    title: 'Evidence (operator console)',
    items: [
      { label: 'Timeline', href: '/operator/#/timeline', external: true },
      { label: 'Proofs', href: '/operator/#/proofs', external: true },
      { label: 'Recovery', href: '/operator/#/recovery', external: true },
      { label: 'Activity', href: '/operator/#/activity', external: true },
    ],
  },
]

const PRODUCT_API_BASE = import.meta.env.VITE_PRODUCT_API_BASE || 'http://localhost:8080/api/product/v1'

export default function Layout({ title, children, onLogout }) {
  const { session } = useSession({ meUrl: `${GATEWAY_V1_BASE}/auth/me` })
  const [envLabel, setEnvLabel] = useState('')
  const [runtimeMode, setRuntimeMode] = useState('')
  const [activeHash, setActiveHash] = useState(window.location.hash || '#/')
  const [brandName, setBrandName] = useState('Product Console')
  const [navOpen, setNavOpen] = useState(false)
  const { items: notifications } = useNotificationStream({
    streamUrl: `${GATEWAY_V1_BASE}/stream/notifications`,
    enabled: Boolean(session),
    headers: () => ({}),
  })

  useEffect(() => {
    fetch(`${GATEWAY_V1_BASE}/ui/brand`, { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null))
      .then((brand) => {
        if (!brand) return
        if (brand.display_name) setBrandName(brand.display_name)
        const palette = brand.palettes?.dark || brand.theme || {}
        const vars = applyBrand(
          {
            accent: palette.accent || palette.primaryColor,
            surfaceBase: palette.surfaceBase || palette.backgroundColor,
            textPrimary: palette.textPrimary,
          },
          { contrastGuard: true },
        )
        Object.entries(vars).forEach(([key, value]) => document.documentElement.style.setProperty(key, value))
        if (brand.favicon_url) {
          let link = document.querySelector('link[rel="icon"]')
          if (!link) {
            link = document.createElement('link')
            link.rel = 'icon'
            document.head.appendChild(link)
          }
          link.href = brand.favicon_url
        }
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    fetch(`${PRODUCT_API_BASE}/env`)
      .then((r) => r.json())
      .then((d) => {
        setEnvLabel(d.env || '')
        if (d.action_mode) {
          setRuntimeMode(d.action_mode)
        } else if (d.live_actions_enabled) {
          setRuntimeMode('live')
        } else {
          setRuntimeMode('shadow')
        }
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
      return path === '/'
    }
    const target = href.replace(/^#/, '')
    return path === target || path.startsWith(`${target}/`)
  }

  const handleLogout = async () => {
    clearProductApiKey()
    onLogout?.()
    try {
      const cfg = await fetchAuthConfig().catch(() => ({}))
      await logoutBrowserSession().catch(() => undefined)
      if (cfg?.oidc_enabled) {
        startOidcLogout(`${window.location.origin}/#/login?logged_out=1`)
        return
      }
    } catch {
      // fall through to local login route
    }
    window.location.hash = '#/login?logged_out=1'
  }

  return (
    <div className="app-shell">
      <SkipToContent />
      {session?.impersonating ? (
        <ImpersonationBanner
          tenantId={session.impersonation_tenant_id}
          onExit={() => { window.location.hash = '#/profile' }}
        />
      ) : null}
      <header className="shell-header">
        <div className="brand">
          <div>
            <span>Product Console</span>
            <h1>{title}</h1>
          </div>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
            <button
              type="button"
              className="nav-menu-btn"
              aria-expanded={navOpen}
              aria-controls="product-nav-grid"
              onClick={() => setNavOpen((open) => !open)}
            >
              Menu
            </button>
            <EnvBadge env={envLabel} mode={runtimeMode || 'shadow'} systemHref="#/system" />
            <NotificationBell
              items={notifications}
              onOpenItem={(item) => {
                if (item.href) window.location.hash = `#${item.href}`
              }}
            />
            <span className="tag" data-testid="product-role-label">{primaryRoleLabel(session)}</span>
            <button type="button" onClick={handleLogout}>Log out</button>
          </div>
        </div>
        <div id="product-nav-grid" className={`nav-grid ${navOpen ? 'is-open' : ''}`}>
          {NAV_GROUPS.map((group) => (
            <div className="nav-group" key={group.title}>
              <div className="nav-group-title">{group.title}</div>
              <div className="nav-links">
                {group.items.map((item) => (
                  <a
                    key={item.label}
                    className={`nav-link ${!item.external && isActive(item.href) ? 'active' : ''}`}
                    href={item.href}
                    onClick={() => !item.external && setNavOpen(false)}
                    {...(item.external ? { target: '_blank', rel: 'noreferrer' } : {})}
                  >
                    {item.label}
                  </a>
                ))}
              </div>
            </div>
          ))}
        </div>
      </header>
      <hr />
      <main id="main-content" tabIndex={-1}>
        {children}
      </main>
    </div>
  )
}


