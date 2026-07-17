export function normalizeHashHref(value, fallback = '#/') {
  if (!value) return fallback
  if (value.startsWith('#')) return value
  if (value.startsWith('/')) return `#${value}`
  return `#/${value}`
}

export function readHashQueryParams(hash = window.location.hash || '#/') {
  const raw = hash.replace(/^#/, '')
  const query = raw.split('?')[1] || ''
  return new URLSearchParams(query)
}

export function getHashQueryParam(name, fallback = '') {
  try {
    return readHashQueryParams().get(name) || fallback
  } catch (_) {
    return fallback
  }
}

export function getCurrentHashWithoutReturnUrl() {
  const hash = window.location.hash || '#/'
  const raw = hash.replace(/^#/, '')
  const [pathPart, queryPart = ''] = raw.split('?')
  const params = new URLSearchParams(queryPart)
  params.delete('returnUrl')
  const query = params.toString()
  const path = pathPart || '/'
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `#${normalizedPath}${query ? `?${query}` : ''}`
}

export function buildHashHref(path, params = {}) {
  const href = normalizeHashHref(path)
  const query = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value == null || value === '') return
    query.set(key, String(value))
  })
  const qs = query.toString()
  return qs ? `${href}?${qs}` : href
}

export function withReturnUrl(path, returnUrl = getCurrentHashWithoutReturnUrl()) {
  return buildHashHref(path, { returnUrl })
}
