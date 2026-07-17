/** Hash-router URL query helpers for operator console (#/path?sort=…). */

export function readHashSearch() {
  if (typeof window === 'undefined') return ''
  const hash = window.location.hash || '#/'
  const qIndex = hash.indexOf('?')
  return qIndex >= 0 ? hash.slice(qIndex) : ''
}

export function writeHashSearch(search, { replace = true } = {}) {
  if (typeof window === 'undefined') return
  const hash = window.location.hash || '#/'
  const qIndex = hash.indexOf('?')
  const path = qIndex >= 0 ? hash.slice(0, qIndex) : hash
  const next = search ? `${path}${search.startsWith('?') ? search : `?${search}`}` : path
  if (window.location.hash === next) return
  if (replace) window.history.replaceState(null, '', next)
  else window.location.hash = next.slice(1)
}
