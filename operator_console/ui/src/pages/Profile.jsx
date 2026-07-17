import React, { useEffect, useMemo, useState } from 'react'
import { ThemeToggle } from 'hg_ui_kit'
import Layout from '../components/Layout.jsx'
import Breadcrumbs from '../components/Breadcrumbs.jsx'
import {
  getBrowserTimeZone,
  getEffectiveTimeZone,
  getTimeZoneOverride,
  setTimeZoneOverride,
  clearTimeZoneOverride,
  listSupportedTimeZones,
  formatDateTime,
} from '../lib/timezone.js'

export default function Profile() {
  const [override, setOverride] = useState(getTimeZoneOverride() || '')
  const [manual, setManual] = useState(getTimeZoneOverride() || '')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (!saved) return
    const t = setTimeout(() => setSaved(false), 1400)
    return () => clearTimeout(t)
  }, [saved])

  const browserTz = getBrowserTimeZone()
  const effectiveTz = getEffectiveTimeZone()
  const tzList = useMemo(() => listSupportedTimeZones(), [])

  const save = () => {
    const value = override || manual
    if (!value || !String(value).trim()) {
      clearTimeZoneOverride()
      setOverride('')
      setManual('')
    } else {
      setTimeZoneOverride(String(value).trim())
      setOverride(String(value).trim())
      setManual(String(value).trim())
    }
    setSaved(true)
  }

  return (
    <Layout title="Profile">
      <Breadcrumbs items={[{ label: 'Home', href: '#/' }, { label: 'Profile' }]} />
      <section className="section-card" style={{ marginBottom: 16 }}>
        <ThemeToggle />
      </section>
      <section className="section-card" style={{ marginBottom: 16 }}>
        <h2 style={{ fontSize: 18, marginBottom: 10 }}>Time zone preferences</h2>
        <p style={{ marginTop: 0, color: 'var(--muted)' }}>
          Default uses browser locale time. You can set an override for consistent cross-device display.
        </p>
        <table cellPadding="8" style={{ borderCollapse: 'collapse', marginBottom: 12 }}>
          <tbody>
            <tr><td><strong>Browser time zone</strong></td><td><code>{browserTz}</code></td></tr>
            <tr><td><strong>Effective time zone</strong></td><td><code>{effectiveTz}</code></td></tr>
            <tr><td><strong>Now (effective)</strong></td><td>{formatDateTime(new Date())}</td></tr>
          </tbody>
        </table>
        <div style={{ display: 'grid', gap: 10, maxWidth: 560 }}>
          <label>
            <div style={{ marginBottom: 4, fontSize: 12, color: 'var(--muted)' }}>Select time zone override</div>
            <select value={override} onChange={(e) => setOverride(e.target.value)}>
              <option value="">Auto (Browser)</option>
              {tzList.map((tz) => (
                <option key={tz} value={tz}>{tz}</option>
              ))}
            </select>
          </label>
          <label>
            <div style={{ marginBottom: 4, fontSize: 12, color: 'var(--muted)' }}>Or enter custom IANA zone</div>
            <input
              value={manual}
              onChange={(e) => setManual(e.target.value)}
              placeholder="e.g. America/St_Johns"
            />
          </label>
          <div style={{ display: 'flex', gap: 8 }}>
            <button type="button" onClick={save}>Save preference</button>
            <button type="button" onClick={() => { clearTimeZoneOverride(); setOverride(''); setManual(''); setSaved(true) }}>
              Reset to auto
            </button>
            {saved && <span style={{ color: 'var(--accent-2)', alignSelf: 'center' }}>Saved</span>}
          </div>
        </div>
      </section>
    </Layout>
  )
}
