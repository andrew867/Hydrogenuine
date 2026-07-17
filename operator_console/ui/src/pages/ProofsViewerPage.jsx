import React, { useCallback, useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import Breadcrumbs from '../components/Breadcrumbs.jsx'
import SharedEventSummary from '../components/SharedEventSummary.jsx'
import StateNotice from '../components/StateNotice.jsx'
import { api } from '../lib/api.js'
import { getHashQueryParam, normalizeHashHref, withReturnUrl } from '../lib/navigationContext.js'

function statusTone(status) {
  if (status === 'healthy') return 'var(--success)'
  if (status === 'watch' || status === 'recent') return 'var(--warn)'
  if (status === 'stale') return 'var(--warn)'
  if (status === 'degraded' || status === 'missing') return 'var(--danger)'
  return 'var(--muted)'
}

function statusLabel(status) {
  if (!status) return 'unknown'
  if (status === 'healthy') return 'healthy'
  if (status === 'watch') return 'watch'
  if (status === 'stale') return 'stale'
  if (status === 'degraded') return 'degraded'
  if (status === 'recent') return 'recent'
  if (status === 'fresh') return 'fresh'
  if (status === 'missing') return 'missing'
  return String(status)
}

function formatHours(hours) {
  if (hours == null || Number.isNaN(Number(hours))) return '—'
  const value = Number(hours)
  if (value < 1) return `${Math.max(1, Math.round(value * 60))}m`
  if (value < 24) return `${value.toFixed(1)}h`
  return `${Math.round(value)}h`
}

function trustSectionState(metrics, browserSummary, loading, err) {
  if (loading) return 'loading'
  if (err) return 'error'
  if (!browserSummary) return 'empty'
  const status = browserSummary.status
  if (status === 'degraded' || status === 'missing') return 'degraded'
  if (status === 'watch' || status === 'stale') return 'watch'
  return 'healthy'
}

export default function ProofsViewerPage() {
  const [index, setIndex] = useState({ latest: {}, runs: [], metrics: null })
  const [err, setErr] = useState(null)
  const [loading, setLoading] = useState(true)
  const [returnUrl, setReturnUrl] = useState('#/')

  const load = useCallback(() => {
    if (!api.proofs.hasProofAccess()) {
      setErr('Sign in with an operator session to view proofs.')
      setLoading(false)
      return
    }
    setErr(null)
    setLoading(true)
    api.proofs.getIndex()
      .then((data) => setIndex(data || { latest: {}, runs: [] }))
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    const sync = () => setReturnUrl(normalizeHashHref(getHashQueryParam('returnUrl', '#/')))
    sync()
    window.addEventListener('hashchange', sync)
    return () => window.removeEventListener('hashchange', sync)
  }, [])

  const latest = index.latest || {}
  const runs = index.runs || []
  const labels = ['health', 'weather_sweep_10', '4claw_posts_3', 'ticket_triage_5', 'persona_hopper_factcheck', 'investor_demo', 'drift_quarantine_demo', 'prompt_injection_hardening_demo', 'soak_trust_demo']
  const metrics = index.metrics || {}
  const browserSummary = metrics?.browser_summary || null
  const sectionState = trustSectionState(metrics, browserSummary, loading, err)
  const canonicalDemos = metrics?.canonical_demos || []

  return (
    <Layout title="Proofs">
      <Breadcrumbs items={[{ label: 'Home', href: '#/' }, { label: 'Proofs' }]} />
      <p style={{ marginBottom: 16 }}>
        <a href={withReturnUrl('#/proofs/run')} className="nav-link">Run proof</a>
        {' · '}
        Latest proof runs by scenario. Folder paths point to <code>docs/proofs/out/</code>.
      </p>
      {returnUrl !== '#/' && (
        <p style={{ marginBottom: 12 }}>
          <a href={returnUrl} className="nav-link">Back to origin</a>
        </p>
      )}
      <SharedEventSummary
        eyebrow="Proof trust"
        title="Proofs"
        intro="Proof trust should read before the list does. Canonical demos, evidence links, and recovery signals live here."
        status={browserSummary?.status || sectionState}
        statusTone={browserSummary?.status === 'healthy' ? 'good' : browserSummary?.status === 'degraded' ? 'danger' : browserSummary?.status === 'watch' ? 'warn' : 'neutral'}
        happened={browserSummary?.summary || (sectionState === 'empty' ? 'No trust metrics yet — run canonical demos to populate the index.' : 'Latest proof runs and canonical demos are tracked here.')}
        when={browserSummary?.freshness_state || (loading ? 'loading' : 'unknown')}
        why="This is the trust spine for canonical proof scenarios and their evidence links."
        changed={`Demo success ${Math.round((metrics?.demo_success_rate || 0) * 100)}% · backlog ${formatHours(metrics?.backlog_age_hours)} · provenance ${Math.round((metrics?.provenance_availability_rate || 0) * 100)}% · recovery ${Math.round((metrics?.failure_recovery_rate || 0) * 100)}% · continuity ${metrics?.continuity_quality?.quality_score ?? '—'}`}
        next="Open a scenario, then inspect timeline or recovery from the same event story."
        context={[
          { label: 'Latest scenario', value: labels.find((label) => latest[label]) || '—' },
          { label: 'Evidence', value: browserSummary?.evidence_links?.timeline ? 'available' : 'partial' },
          { label: 'Latest runs', value: runs.length || 0 },
        ]}
      />

      <section style={{ marginBottom: 20 }}>
        <h2 style={{ margin: '0 0 8px' }}>Trust at a glance</h2>
        {sectionState === 'loading' && <StateNotice title="Loading trust metrics" detail="Fetching proof index and trust aggregation…" />}
        {sectionState === 'error' && (
          <StateNotice tone="danger" title="Could not load proofs" detail={err} action={<button type="button" onClick={load}>Retry</button>} />
        )}
        {sectionState === 'empty' && (
          <StateNotice
            title="No trust metrics yet"
            detail="Canonical demo scenarios have not been recorded in docs/proofs/index.json. Run proofs from the runner to populate trust cards."
            action={<a href={withReturnUrl('#/proofs/run')} className="nav-link">Run proof</a>}
          />
        )}
        {(sectionState === 'healthy' || sectionState === 'watch' || sectionState === 'degraded') && browserSummary && (
          <>
            {sectionState === 'watch' && (
              <StateNotice tone="warn" title="Trust metrics need attention" detail={browserSummary.summary} />
            )}
            {sectionState === 'degraded' && (
              <StateNotice tone="danger" title="Trust metrics degraded" detail={browserSummary.summary} action={<a href="#/recovery" className="nav-link">Open recovery</a>} />
            )}
            <p className="muted" style={{ margin: '0 0 12px', maxWidth: 820 }}>
              {browserSummary.summary}
            </p>
            <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))' }}>
              <div className="card">
                <div className="eyebrow">Overall status</div>
                <strong style={{ color: statusTone(browserSummary.status) }}>{statusLabel(browserSummary.status)}</strong>
              </div>
              <div className="card">
                <div className="eyebrow">Freshness</div>
                <strong>{statusLabel(browserSummary.freshness_state)}</strong>
              </div>
              <div className="card">
                <div className="eyebrow">Backlog age</div>
                <strong>{formatHours(metrics.backlog_age_hours)}</strong>
              </div>
              <div className="card">
                <div className="eyebrow">Demo success</div>
                <strong>{Math.round((metrics.demo_success_rate || 0) * 100)}%</strong>
              </div>
              <div className="card">
                <div className="eyebrow">Provenance</div>
                <strong>{Math.round((metrics.provenance_availability_rate || 0) * 100)}%</strong>
              </div>
              <div className="card">
                <div className="eyebrow">Review turnaround</div>
                <strong>{metrics.review_turnaround_seconds != null ? `${Math.round(metrics.review_turnaround_seconds)}s` : '—'}</strong>
              </div>
              <div className="card">
                <div className="eyebrow">Continuity quality</div>
                <strong>{metrics.continuity_quality?.quality_score != null ? `${metrics.continuity_quality.quality_score}` : '—'}</strong>
              </div>
              <div className="card">
                <div className="eyebrow">Failure recovery</div>
                <strong>{Math.round((metrics.failure_recovery_rate || 0) * 100)}%</strong>
              </div>
              <div className="card">
                <div className="eyebrow">Evidence links</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 6 }}>
                  <a href={browserSummary.evidence_links?.timeline || '#/timeline'} className="nav-link">Timeline</a>
                  <a href={browserSummary.evidence_links?.recovery || '#/recovery'} className="nav-link">Recovery</a>
                  <a href={browserSummary.evidence_links?.proofs || '#/proofs/run'} className="nav-link">Run proof</a>
                </div>
              </div>
            </div>
          </>
        )}
      </section>

      {!loading && !err && (
        <>
          <h2 style={{ fontSize: 18, marginTop: 16 }}>Latest by scenario</h2>
          <table className="table-basic" style={{ marginTop: 8 }}>
            <thead>
              <tr>
                <th>Scenario</th>
                <th>Folder</th>
                <th>Pass</th>
              </tr>
            </thead>
            <tbody>
              {labels.map((label) => {
                const folder = latest[label]
                const runEntry = runs.filter((r) => r.label === label).slice(-1)[0]
                const pass = runEntry?.checks_passed
                const trust = runEntry?.status
                return (
                  <tr key={label}>
                    <td><code>{label}</code></td>
                    <td>
                      {folder ? (
                        <span title={folder}>{folder.split(/[/\\]/).pop() || folder}</span>
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </td>
                    <td>
                      {folder ? (
                        <span style={{ color: statusTone(trust || (pass === true ? 'healthy' : pass === false ? 'degraded' : 'missing')) }}>
                          {statusLabel(trust || (pass === true ? 'healthy' : pass === false ? 'degraded' : 'missing'))}
                        </span>
                      ) : '—'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          {canonicalDemos.length > 0 ? (
            <>
              <h2 style={{ fontSize: 18, marginTop: 24 }}>Canonical demos</h2>
              <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', marginTop: 8 }}>
                {canonicalDemos.map((demo) => {
                  const runId = demo.run_id || (demo.folder || '').split(/[/\\]/).pop() || ''
                  return (
                    <article className="card" key={`${demo.label}:${runId || demo.folder}`}>
                      <div className="eyebrow">{demo.label}</div>
                      <div style={{ fontWeight: 700, marginBottom: 6, color: statusTone(demo.status) }}>{statusLabel(demo.status)}</div>
                      <div className="muted" style={{ fontSize: 12, marginBottom: 8 }}>{runId || 'no run id'}</div>
                      <div style={{ display: 'grid', gap: 6, fontSize: 13 }}>
                        <div><strong>Freshness:</strong> {demo.freshness_label || '—'}</div>
                        <div><strong>Provenance:</strong> {demo.provenance_label || '—'}</div>
                        <div><strong>Review turnaround:</strong> {demo.review_turnaround_label || '—'}</div>
                        <div><strong>Recovery:</strong> {demo.recovery_label || '—'}</div>
                        <div><strong>Continuity:</strong> {demo.continuity_quality_score != null ? `${demo.continuity_quality_score}` : '—'}</div>
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 10 }}>
                        {runId ? (
                          <>
                            <a className="nav-link" href={api.proofs.getRunFileUrl(runId, 'summary.json')}>Summary</a>
                            <a className="nav-link" href={api.proofs.getRunFileUrl(runId, 'checks.json')}>Checks</a>
                            <a className="nav-link" href={api.proofs.getRunLogsUrl(runId)}>Logs</a>
                          </>
                        ) : null}
                        <a className="nav-link" href="#/timeline">Timeline</a>
                        <a className="nav-link" href="#/recovery">Recovery</a>
                      </div>
                    </article>
                  )
                })}
              </div>
            </>
          ) : (
            <StateNotice title="No canonical demo cards" detail="Trust demo labels are not present in the latest proof index yet." />
          )}
        </>
      )}
    </Layout>
  )
}
