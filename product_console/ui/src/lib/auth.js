const PRODUCT_SESSION_KEY = 'hg_product_admin_key'

export function getProductApiKey() {
  if (typeof window === 'undefined') return null
  try {
    return window.sessionStorage.getItem(PRODUCT_SESSION_KEY)
  } catch {
    return null
  }
}

export function setProductApiKey(value) {
  if (typeof window === 'undefined') return
  try {
    if (value) window.sessionStorage.setItem(PRODUCT_SESSION_KEY, value)
    else window.sessionStorage.removeItem(PRODUCT_SESSION_KEY)
  } catch {
    // ignore storage failures
  }
}

export function clearProductApiKey() {
  setProductApiKey(null)
}

export function hasProductAuth() {
  return !!getProductApiKey()
}
