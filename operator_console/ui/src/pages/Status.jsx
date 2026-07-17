import React, { useCallback, useEffect, useState } from 'react'
import { useTheme, useVisibilityAwareInterval } from 'hg_ui_kit'
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import Layout from '../components/Layout.jsx'
import Breadcrumbs from '../components/Breadcrumbs.jsx'
import { api } from '../lib/api.js'
import { PageSkeleton } from '../components/PageStates.jsx'
import { formatDateTime } from '../lib/timezone.js'

const HOURS_OPTIONS = [6, 24, 48, 168]

export default function Status() {
  const { resolved } = useTheme()
  const chartMuted = resolved === 'light' ? '#64748b' : '#9aa3b2'
  const chartGrid = resolved === 'light' ? '#e2e8f0' : '#283144'
  const [hours, setHours] = useState(24)
  const [dashboard, setDashboard] = useState(null)
  const [dashboardErr, setDashboardErr] = useState(null)
  const [autonomy, setAutonomy] = useState(null)
  const [autonomyErr, setAutonomyErr] = useState(null)
  const [saving, setSaving] = useState(false)
  const [saveErr, setSaveErr] = useState(null)
  const [reports, setReports] = useState({ items: [], latest_pdf: null, latest_png: null })
  const [embedPngUrl, setEmbedPngUrl] = useState(null)
  const [embedPdfUrl, setEmbedPdfUrl] = useState(null)

  const loadDashboard = useCallback(() => {
    setDashboardErr(null)
    api.getStatusDashboard(hours)
      .then((r) => setDashboard(r))
      .catch((e) => setDashboardErr(e.message))
  }, [hours])

  const loadAutonomy = useCallback(() => {
    setAutonomyErr(null)
    api.getAutonomy()
      .then((r) => {
        if (r.ok !== false) setAutonomy(r)
        else setAutonomyErr(r.error || 'Failed to load autonomy')
      })
      .catch((e) => setAutonomyErr(e.message))
  }, [])

  useEffect(() => { loadDashboard() }, [loadDashboard])
  useEffect(() => { loadAutonomy() }, [loadAutonomy])
  useEffect(() => {
    api.getStatusReports(20).then(setReports).catch(() => {})
  }, [])

  useVisibilityAwareInterval({
    intervalMs: 60_000,
    onTick: () => {
      loadDashboard()
      loadAutonomy()
      api.getStatusReports(20).then(setReports).catch(() => {})
    },
  })

  useEffect(() => {
    if (!reports.latest_png?.ref) {
      setEmbedPngUrl(null)
      return
    }
    let revoked = false
    api.getStatusReportBlob(reports.latest_png.ref).then((blob) => {
      if (revoked) return
      setEmbedPngUrl(URL.createObjectURL(blob))
    }).catch(() => {})
    return () => { revoked = true }
  }, [reports.latest_png?.ref])

  useEffect(() => {
    if (!reports.latest_pdf?.ref) {
      setEmbedPdfUrl(null)
      return
    }
    let revoked = false
    api.getStatusReportBlob(reports.latest_pdf.ref).then((blob) => {
      if (revoked) return
      setEmbedPdfUrl(URL.createObjectURL(blob))
    }).catch(() => {})
    return () => { revoked = true }
  }, [reports.latest_pdf?.ref])

  const chartData = (dashboard?.timeseries || []).map((entry) => {
      const chaos = entry.budgets?.chaos
      const cred = entry.budgets?.credibility
      return {
      time: entry.timestamp,
      label: formatDateTime(entry.timestamp, { fallback: '' }),
      chaos_remaining: chaos?.remaining ?? null,
      credibility_earned: cred?.earned ?? null,
    }
  }).filter((d) => d.chaos_remaining != null || d.credibility_earned != null)

  const parity = dashboard?.pdf_dashboard || {}
  const violationTrend = Array.isArray(parity.violation_trend) ? parity.violation_trend : []
  const modeDistribution = parity.mode_distribution && typeof parity.mode_distribution === 'object'
    ? Object.entries(parity.mode_distribution).map(([mode, count]) => ({ mode, count }))
    : []

  const handleSafetyGateChange = (checked) => {
    if (!autonomy) return
    setSaving(true)
    setSaveErr(null)
    api.patchAutonomy({ outbound_safety_gate_enabled: checked })
      .then((r) => {
        if (r.ok !== false) setAutonomy((prev) => ({ ...prev, ...r }))
        else setSaveErr(r.error || 'Save failed')
      })
      .catch((e) => setSaveErr(e.message))
      .finally(() => setSaving(false))
  }

  const handleEntityDagChange = (value) => {
    if (!autonomy) return
    setSaving(true)
    setSaveErr(null)
    api.patchAutonomy({ entity_dag_change_control: value })
      .then((r) => {
        if (r.ok !== false) setAutonomy((prev) => ({ ...prev, ...r }))
        else setSaveErr(r.error || 'Save failed')
      })
      .catch((e) => setSaveErr(e.message))
      .finally(() => setSaving(false))
  }

  const downloadReport = async (reportRef) => {
    try {
      const blob = await api.getStatusReportBlob(reportRef)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = reportRef.split('/').slice(-1)[0] || 'dashboard-report'
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      setDashboardErr(e.message)
    }
  }

  const viewReportInNewTab = async (reportRef) => {
    try {
      const blob = await api.getStatusReportBlob(reportRef)
      const url = URL.createObjectURL(blob)
      window.location.assign(url)
      setTimeout(() => URL.revokeObjectURL(url), 60000)
    } catch (e) {
      setDashboardErr(e.message)
    }
  }

  const summary = dashboard?.summary || {}
  const latestState = dashboard?.latest_state || summary?.latest_state
  const analysisCapabilities = dashboard?.analysis_capabilities || summary?.analysis_capabilities

  return (
    <Layout title="Status">
      <Breadcrumbs items={[{ label: 'Home', href: '#/' }, { label: 'Status' }]} />
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 18, marginBottom: 8 }}>Dashboard</h2>
        <p style={{ marginBottom: 8 }}>
          Time range:{' '}
          {HOURS_OPTIONS.map((h) => (
            <button
              key={h}
              type="button"
              onClick={() => setHours(h)}
              style={{
                marginRight: 8,
                fontWeight: hours === h ? 'bold' : 'normal',
              }}
            >
              {h}h
            </button>
          ))}
          <button type="button" onClick={loadDashboard} style={{ marginLeft: 8 }}>
            Refresh
          </button>
        </p>
        {dashboardErr && (
          <div style={{ color: 'var(--danger)', marginBottom: 8 }}>{dashboardErr}</div>
        )}
        {dashboard && (
          <>
            <p style={{ marginBottom: 8 }}>
              Latest state: {latestState?.timestamp ? formatDateTime(latestState.timestamp) : '—'}
              {' '}
              | Timeseries points (selected window): {(dashboard.timeseries || []).length}
              {summary.timeseries_count_24h != null && (
                <> | Timeseries count (24h): {summary.timeseries_count_24h}</>
              )}
            </p>
            {chartData.length > 0 ? (
              <div style={{ width: '100%', height: 280 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={chartGrid} />
                    <XAxis
                      dataKey="label"
                      tick={{ fontSize: 10 }}
                      interval="preserveStartEnd"
                    />
                    <YAxis yAxisId="left" tick={{ fontSize: 10 }} />
                    <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 10 }} />
                    <Tooltip
                      labelFormatter={(_, payload) => formatDateTime(payload[0]?.payload?.time)}
                      formatter={(value) => [value, '']}
                    />
                    <Area
                      yAxisId="left"
                      type="monotone"
                      dataKey="chaos_remaining"
                      name="Chaos remaining"
                      stroke="#8884d8"
                      fill="#8884d8"
                      fillOpacity={0.3}
                    />
                    <Area
                      yAxisId="right"
                      type="monotone"
                      dataKey="credibility_earned"
                      name="Credibility earned"
                      stroke="#82ca9d"
                      fill="#82ca9d"
                      fillOpacity={0.3}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <p>No timeseries data in the selected window.</p>
            )}
            <div style={{ marginTop: 14, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12 }}>
              <div className="card">
                <div className="muted" style={{ fontSize: 11 }}>Cycles in window</div>
                <div style={{ fontSize: 20, fontWeight: 600 }}>{parity.cycles_in_window ?? 0}</div>
              </div>
              <div className="card">
                <div className="muted" style={{ fontSize: 11 }}>Agents observed</div>
                <div style={{ fontSize: 20, fontWeight: 600 }}>{parity.agents_observed ?? 0}</div>
              </div>
              <div className="card">
                <div className="muted" style={{ fontSize: 11 }}>Latest timestamp</div>
                <div style={{ fontSize: 12, fontFamily: 'monospace' }}>{formatDateTime(parity.latest_timestamp)}</div>
              </div>
              <div className="card">
                <div className="muted" style={{ fontSize: 11 }}>Optional analysis</div>
                <div style={{ fontSize: 20, fontWeight: 600 }}>
                  {analysisCapabilities?.degraded_count != null
                    ? `${analysisCapabilities.degraded_count}/${analysisCapabilities.agents_total || 0} degraded`
                    : 'Unknown'}
                </div>
              </div>
            </div>
            {analysisCapabilities && (
              <div className="section-card" style={{ marginTop: 12 }}>
                <div className="muted" style={{ marginBottom: 6, fontSize: 12 }}>Optional analysis capability status</div>
                <div style={{ marginBottom: 8 }}>
                  {analysisCapabilities.summary || 'No capability summary available.'}
                </div>
                {Array.isArray(analysisCapabilities.reasons) && analysisCapabilities.reasons.length > 0 && (
                  <ul style={{ margin: '0 0 8px 18px' }}>
                    {analysisCapabilities.reasons.slice(0, 5).map((reason) => (
                      <li key={reason}><code>{reason}</code></li>
                    ))}
                  </ul>
                )}
                {Array.isArray(analysisCapabilities.degraded_agents) && analysisCapabilities.degraded_agents.length > 0 && (
                  <div className="muted" style={{ fontSize: 12 }}>
                    Affected agents: {analysisCapabilities.degraded_agents.join(', ')}
                  </div>
                )}
              </div>
            )}
            <div style={{ marginTop: 12, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 12 }}>
              <div className="section-card">
                <div className="muted" style={{ marginBottom: 6, fontSize: 12 }}>Violation trend</div>
                {violationTrend.length > 0 ? (
                  <div style={{ width: '100%', height: 220 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={violationTrend}>
                        <CartesianGrid strokeDasharray="3 3" stroke={chartGrid} />
                        <XAxis dataKey="timestamp" hide />
                        <YAxis />
                        <Tooltip />
                        <Area type="monotone" dataKey="violations" stroke="#ff6b6b" fill="rgba(255,107,107,0.25)" />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                ) : <div className="muted">No violation trend data.</div>}
              </div>
              <div className="section-card">
                <div className="muted" style={{ marginBottom: 6, fontSize: 12 }}>Mode distribution</div>
                {modeDistribution.length > 0 ? (
                  <div style={{ width: '100%', height: 220 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={modeDistribution}>
                        <CartesianGrid strokeDasharray="3 3" stroke={chartGrid} />
                        <XAxis dataKey="mode" />
                        <YAxis />
                        <Tooltip />
                        <Bar dataKey="count" fill="#f6c177" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                ) : <div className="muted">No mode distribution data.</div>}
              </div>
            </div>
          </>
        )}
        {!dashboard && !dashboardErr && <PageSkeleton label="Loading dashboard" />}
      </section>

      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 18, marginBottom: 8 }}>Dashboard reports</h2>
        <div className="section-card">
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 12 }}>
            {reports.latest_pdf && (
              <>
                <button type="button" onClick={() => viewReportInNewTab(reports.latest_pdf.ref)}>View latest PDF</button>
                <button type="button" onClick={() => downloadReport(reports.latest_pdf.ref)} className="btn secondary">Download PDF</button>
              </>
            )}
            {reports.latest_png && (
              <>
                <button type="button" onClick={() => viewReportInNewTab(reports.latest_png.ref)}>View latest PNG</button>
                <button type="button" onClick={() => downloadReport(reports.latest_png.ref)} className="btn secondary">Download PNG</button>
              </>
            )}
          </div>
          {reports.latest_png && (
            <div style={{ marginBottom: 16 }}>
              <div className="muted" style={{ fontSize: 12, marginBottom: 6 }}>Latest dashboard (PNG)</div>
              {embedPngUrl && (
                <img
                  src={embedPngUrl}
                  alt="Dashboard"
                  style={{ maxWidth: '100%', height: 'auto', border: '1px solid var(--border)', borderRadius: 8 }}
                />
              )}
            </div>
          )}
          {reports.latest_pdf && (
            <div style={{ marginBottom: 16 }}>
              <div className="muted" style={{ fontSize: 12, marginBottom: 6 }}>Latest dashboard (PDF)</div>
              {embedPdfUrl && (
                <iframe
                  title="Dashboard PDF"
                  style={{ width: '100%', height: 480, border: '1px solid var(--border)', borderRadius: 8 }}
                  src={embedPdfUrl}
                />
              )}
            </div>
          )}
          {Array.isArray(reports.items) && reports.items.length > 0 ? (
            <table width="100%" cellPadding="8" style={{ borderCollapse: 'collapse', marginTop: 12 }}>
              <thead>
                <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
                  <th>Name</th>
                  <th>Type</th>
                  <th>Modified</th>
                  <th>Size</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {reports.items.slice(0, 12).map((r) => (
                  <tr key={r.ref} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td>{r.name}</td>
                    <td>{r.kind}</td>
                    <td>{formatDateTime(r.modified_at)}</td>
                    <td>{r.size || 0}</td>
                    <td>
                      <button type="button" onClick={() => viewReportInNewTab(r.ref)}>View</button>
                      <button type="button" onClick={() => downloadReport(r.ref)} className="btn secondary" style={{ marginLeft: 8 }}>Download</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="muted" style={{ marginTop: 8 }}>No reports available yet.</div>
          )}
        </div>
      </section>

      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 18, marginBottom: 8 }}>Autonomy</h2>
        {autonomyErr && (
          <div style={{ color: 'var(--danger)', marginBottom: 8 }}>{autonomyErr}</div>
        )}
        {saveErr && (
          <div style={{ color: 'var(--danger)', marginBottom: 8 }}>{saveErr}</div>
        )}
        {autonomy && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <input
                type="checkbox"
                checked={!!autonomy.outbound_safety_gate_enabled}
                onChange={(e) => handleSafetyGateChange(e.target.checked)}
                disabled={saving}
              />
              Outbound safety gate enabled
            </label>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span>Entity DAG change control:</span>
              <select
                value={autonomy.entity_dag_change_control ?? 'pass-through'}
                onChange={(e) => handleEntityDagChange(e.target.value)}
                disabled={saving}
              >
                <option value="off">off</option>
                <option value="on">on</option>
                <option value="pass-through">pass-through</option>
              </select>
              {saving && <span style={{ color: 'var(--muted)' }}>Saving…</span>}
            </div>
          </div>
        )}
        {!autonomy && !autonomyErr && <PageSkeleton label="Loading autonomy config" rows={2} />}
      </section>
    </Layout>
  )
}


