const STORAGE_KEY = 'hg.ui.timezone.override'
const STORAGE_PROFILE_TZ = 'hg.ui.timezone.profile'
const EVENT_NAME = 'hg:timezone-change'

export function getBrowserTimeZone() {
  try {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone
    return tz && String(tz).trim() ? String(tz).trim() : 'UTC'
  } catch {
    return 'UTC'
  }
}

export function getTimeZoneOverride() {
  try {
    const value = localStorage.getItem(STORAGE_KEY)
    return value && String(value).trim() ? String(value).trim() : null
  } catch {
    return null
  }
}

export function setTimeZoneOverride(value) {
  try {
    const normalized = value && String(value).trim() ? String(value).trim() : ''
    if (!normalized) localStorage.removeItem(STORAGE_KEY)
    else localStorage.setItem(STORAGE_KEY, normalized)
  } catch {
    // no-op
  }
  try {
    window.dispatchEvent(new CustomEvent(EVENT_NAME))
  } catch {
    // no-op
  }
}

export function clearTimeZoneOverride() {
  setTimeZoneOverride('')
}

/** Profile/principal timezone from backend (set when principals are loaded). */
export function getProfileTimeZone() {
  try {
    const value = localStorage.getItem(STORAGE_PROFILE_TZ)
    return value && String(value).trim() ? String(value).trim() : null
  } catch {
    return null
  }
}

export function setProfileTimeZone(value) {
  try {
    const normalized = value && String(value).trim() ? String(value).trim() : ''
    if (!normalized) localStorage.removeItem(STORAGE_PROFILE_TZ)
    else localStorage.setItem(STORAGE_PROFILE_TZ, normalized)
  } catch {
    // no-op
  }
  try {
    window.dispatchEvent(new CustomEvent(EVENT_NAME))
  } catch {
    // no-op
  }
}

/** Prefer: user override > profile/principal timezone > browser > UTC. */
export function getEffectiveTimeZone() {
  return getTimeZoneOverride() || getProfileTimeZone() || getBrowserTimeZone()
}

export function listSupportedTimeZones() {
  try {
    if (typeof Intl.supportedValuesOf === 'function') {
      return Intl.supportedValuesOf('timeZone')
    }
  } catch {
    // no-op
  }
  return [
    'UTC',
    'America/New_York',
    'America/Chicago',
    'America/Denver',
    'America/Los_Angeles',
    'America/St_Johns',
    'Europe/London',
    'Europe/Berlin',
    'Asia/Tokyo',
  ]
}

function toDate(value) {
  if (value == null) return null
  if (value instanceof Date) return Number.isNaN(value.getTime()) ? null : value
  if (typeof value === 'number' && Number.isFinite(value)) {
    const ms = value > 10_000_000_000 ? value : value * 1000
    const d = new Date(ms)
    return Number.isNaN(d.getTime()) ? null : d
  }
  if (typeof value === 'string') {
    const trimmed = value.trim()
    if (!trimmed) return null
    const numeric = Number(trimmed)
    if (Number.isFinite(numeric)) {
      const ms = numeric > 10_000_000_000 ? numeric : numeric * 1000
      const d = new Date(ms)
      return Number.isNaN(d.getTime()) ? null : d
    }
    const d = new Date(trimmed)
    return Number.isNaN(d.getTime()) ? null : d
  }
  return null
}

export function formatDateTime(value, options = {}) {
  const d = toDate(value)
  if (!d) return options.fallback ?? '—'
  const tz = options.timeZone || getEffectiveTimeZone()
  const formatOptions = {
    dateStyle: options.dateStyle || 'short',
    timeStyle: options.timeStyle || 'short',
    timeZone: tz,
  }
  try {
    return new Intl.DateTimeFormat(undefined, formatOptions).format(d)
  } catch {
    return d.toISOString()
  }
}

export function formatDateOnly(value, options = {}) {
  const d = toDate(value)
  if (!d) return options.fallback ?? '—'
  const tz = options.timeZone || getEffectiveTimeZone()
  try {
    return new Intl.DateTimeFormat(undefined, { dateStyle: options.dateStyle || 'medium', timeZone: tz }).format(d)
  } catch {
    return d.toISOString().slice(0, 10)
  }
}

export function subscribeTimeZoneChange(handler) {
  if (typeof window === 'undefined' || typeof handler !== 'function') return () => {}
  const wrapped = () => handler(getEffectiveTimeZone())
  window.addEventListener(EVENT_NAME, wrapped)
  return () => window.removeEventListener(EVENT_NAME, wrapped)
}
