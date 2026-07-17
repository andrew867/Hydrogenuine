import React, { useCallback, useEffect, useState } from 'react'
import { useVisibilityAwareInterval } from 'hg_ui_kit'
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  BarChart,
  Bar,
} from 'recharts'
import Layout from '../components/Layout.jsx'
import StatusChip from '../components/StatusChip.jsx'
import Breadcrumbs from '../components/Breadcrumbs.jsx'
import { api } from '../lib/api.js'
import { formatDateTime } from '../lib/timezone.js'

export default function ProductDashboard({ onLogout }) {
  const [metrics, setMetrics] = useState(null)
  const [runs, setRuns] = useState({ items: [], total: 0 })
  const [workflows, setWorkflows] = useState({ items: [], total: 0 })
  const [err, setErr] = useState(null)
  const [reports, setReports] = useState({ items: [], latest_pdf: null, latest_png: null })

  const loadDashboard = useCallback(() => {
    api.product.getMetricsSummary('daily').then(setMetrics).catch((e) => setErr(e.message))
    api.product.listRuns({ limit: 10 }).then(setRuns).catch(() => {})
    api.product.listWorkflows({ limit: 20 }).then(setWorkflows).catch(() => {})
    api.product.getMetricsReports(20).then(setReports).catch(() => {})
  }, [])

  useEffect(() => {
    loadDashboard()
  }, [loadDashboard])

  useVisibilityAwareInterval({
    intervalMs: 60_000,
    onTick: loadDashboard,
  })

  const parity = metrics?.pdf_dashboard || {}
  const violationTrend = Array.isArray(parity.violation_trend) ? parity.violation_trend : []
  const budgetTrend = Array.isArray(parity.budget_trend) ? parity.budget_trend : []
  const modeDistribution = parity.mode_distribution && typeof parity.mode_distribution === 'object'
    ? Object.entries(parity.mode_distribution).map(([mode, count]) => ({ mode, count }))
    : []

  const downloadReport = async (reportRef) => {
    try {
      const blob = await api.product.getMetricsReportBlob(reportRef)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = reportRef.split('/').slice(-1)[0] || 'dashboard-report'
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      setErr(e.message)
    }
  }

  return (
    <Layout title="Dashboard (Product)" onLogout={onLogout}>
      <Breadcrumbs items={[{ label: 'Home', href: '#/' }, { label: 'Dashboard' }]} />
      <p className="muted" style={{ fontSize: 13, marginBottom: 16 }}>
        After meaningful actions, inspect timeline and provenance in the{' '}
        <a href="/operator/#/timeline" target="_blank" rel="noreferrer" className="nav-link">operator timeline</a>
        {' '}or{' '}
        <a href="/operator/#/proofs" target="_blank" rel="noreferrer" className="nav-link">proofs</a> surfaces.
      </p>
      {err && <div style={{ color: 'var(--danger)' }}>{err}</div>}
      <div className="card-grid" style={{ marginBottom: 24 }}>
        <div className="card">
          <div className="muted" style={{ fontSize: 12 }}>Workflows</div>
          <div style={{ fontSize: 24, fontWeight: 600 }}>{workflows.total}</div>
        </div>
        <div className="card">
          <div className="muted" style={{ fontSize: 12 }}>Indexed runs</div>
          <div style={{ fontSize: 24, fontWeight: 600 }}>{runs.total}</div>
        </div>
        {metrics?.cost && (
          <div className="card">
            <div className="muted" style={{ fontSize: 12 }}>Cost (24h)</div>
            <div style={{ fontSize: 24, fontWeight: 600 }}>{metrics.cost.runs_24h ?? '—'}</div>
          </div>
        )}
        <div className="card">
          <div className="muted" style={{ fontSize: 12 }}>Cycles in window</div>
          <div style={{ fontSize: 24, fontWeight: 600 }}>{parity.cycles_in_window ?? 0}</div>
        </div>
        <div className="card">
          <div className="muted" style={{ fontSize: 12 }}>Agents observed</div>
          <div style={{ fontSize: 24, fontWeight: 600 }}>{parity.agents_observed ?? 0}</div>
        </div>
      </div>
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 16, marginBottom: 8 }}>Window summary</h2>
        <div className="section-card">
          <div className="muted">
            Latest timestamp: {formatDateTime(parity.latest_timestamp)}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 16, marginTop: 12 }}>
            <div>
              <div className="muted" style={{ marginBottom: 6, fontSize: 12 }}>Violation trend</div>
              {violationTrend.length > 0 ? (
                <div style={{ width: '100%', height: 220 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={violationTrend}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="timestamp" hide />
                      <YAxis />
                      <Tooltip labelFormatter={(value) => formatDateTime(value)} />
                      <Area type="monotone" dataKey="violations" stroke="#ff6b6b" fill="rgba(255,107,107,0.25)" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="muted">No violation trend data in this window.</div>
              )}
            </div>
            <div>
              <div className="muted" style={{ marginBottom: 6, fontSize: 12 }}>Budget trend</div>
              {budgetTrend.length > 0 ? (
                <div style={{ width: '100%', height: 220 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={budgetTrend}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="timestamp" hide />
                      <YAxis />
                      <Tooltip labelFormatter={(value) => formatDateTime(value)} />
                      <Area type="monotone" dataKey="chaos_remaining" stroke="#7aa8ff" fill="rgba(122,168,255,0.25)" />
                      <Area type="monotone" dataKey="credibility_earned" stroke="#8df0a4" fill="rgba(141,240,164,0.22)" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="muted">No budget trend data in this window.</div>
              )}
            </div>
            <div>
              <div className="muted" style={{ marginBottom: 6, fontSize: 12 }}>Mode distribution</div>
              {modeDistribution.length > 0 ? (
                <div style={{ width: '100%', height: 220 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={modeDistribution}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="mode" />
                      <YAxis />
                      <Tooltip />
                      <Bar dataKey="count" fill="#f6c177" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="muted">No mode distribution data in this window.</div>
              )}
            </div>
          </div>
        </div>
      </section>
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 16, marginBottom: 8 }}>Dashboard reports</h2>
        <div className="section-card">
          {reports.latest_pdf && (
            <button type="button" onClick={() => downloadReport(reports.latest_pdf.ref)} style={{ marginRight: 10 }}>
              Download latest PDF
            </button>
          )}
          {reports.latest_png && (
            <button type="button" onClick={() => downloadReport(reports.latest_png.ref)}>
              Download latest PNG
            </button>
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
                    <td><button type="button" onClick={() => downloadReport(r.ref)}>Download</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="muted" style={{ marginTop: 8 }}>No reports found yet.</div>
          )}
        </div>
      </section>
      <section>
        <h2 style={{ fontSize: 16, marginBottom: 8 }}>Recent runs</h2>
        <table width="100%" cellPadding="8" style={{ borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
              <th>Run</th>
              <th>Workflow</th>
              <th>Status</th>
              <th>Started</th>
            </tr>
          </thead>
          <tbody>
            {runs.items.map((r) => (
              <tr key={r.run_id} style={{ borderBottom: '1px solid var(--border)' }}>
                <td><a href={`#/runs/${r.run_id}`}>{r.run_id?.slice(0, 8)}…</a></td>
                <td>{r.graph_id || '—'}</td>
                <td><StatusChip status={r.status} /></td>
                <td>{formatDateTime(r.started_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </Layout>
  )
}


