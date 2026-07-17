const GATEWAY_V1_BASE = (() => {
  try {
    const apiBase = import.meta.env.VITE_API_BASE || 'http://localhost:8080/api/v1'
    return new URL(apiBase).origin + '/v1'
  } catch {
    return 'http://localhost:8080/v1'
  }
})()

export async function fetchAuthConfig() {
  const res = await fetch(`${GATEWAY_V1_BASE}/auth/config`, { credentials: 'include' })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function fetchAuthMe() {
  const res = await fetch(`${GATEWAY_V1_BASE}/auth/me`, { credentials: 'include' })
  if (res.status === 401) return null
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export function startOidcLogin(returnUrl) {
  const redirect = `${window.location.origin}${returnUrl || '/'}`
  window.location.assign(
    `${GATEWAY_V1_BASE}/auth/oidc/start?frontend_redirect_uri=${encodeURIComponent(redirect)}`,
  )
}

export function startOidcLogout(returnUrl) {
  window.location.assign(
    `${GATEWAY_V1_BASE}/auth/oidc/logout?frontend_redirect_uri=${encodeURIComponent(returnUrl)}`,
  )
}

export async function logoutBrowserSession() {
  await fetch(`${GATEWAY_V1_BASE}/auth/logout`, { method: 'POST', credentials: 'include' })
}

export function isLoggedOutHash() {
  try {
    const params = new URLSearchParams(window.location.hash.split('?')[1] || '')
    return params.get('logged_out') === '1'
  } catch {
    return false
  }
}

export { GATEWAY_V1_BASE }
