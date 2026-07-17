import React, { useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import { api } from '../lib/api.js'
import { formatDateTime } from '../lib/timezone.js'
import StateNotice from '../components/StateNotice.jsx'

export default function Activity() {
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  const [loading, setLoading] = useState(true)
  const [actionKey, setActionKey] = useState('')
  const [projectionView, setProjectionView] = useState('compact')

  const load = async () => {
    setErr(null)
    setLoading(true)
    try {
      const r = await api.getActivityProjection({ limit_runs: 10, limit_decisions: 20, view: projectionView })
      setData(r)
    } catch (e) {
      setErr(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [projectionView])

  const runGovernanceAction = async (item, action) => {
    const context = item?.governance_actions || {}
    const platform = context.platform
    const operationalAgentId = context.operational_agent_id
    if (!platform || !operationalAgentId) return
    const nextKey = `${item.timestamp || 'ts'}:${item.kind || 'kind'}:${action}`
    setActionKey(nextKey)
    setErr(null)
    try {
      if (action === 'approve_resume') {
        await api.approveOperationalResumeCheckpoint(platform, operationalAgentId, {
          approved_by: 'operator_console',
          note: 'approved from recent activity',
        })
      } else if (action === 'acknowledge_recovery') {
        await api.acknowledgeOperationalContinuityRecovery(platform, operationalAgentId, {
          acknowledged_by: 'operator_console',
          note: 'acknowledged from recent activity',
        })
      } else if (action === 'verify_rebuild') {
        await api.verifyOperationalPostRebuild(platform, operationalAgentId, {
          verified_by: 'operator_console',
          note: 'verified from recent activity',
        })
      }
      await load()
    } catch (e) {
      setErr(e.message)
    } finally {
      setActionKey('')
    }
  }

  if (err) {
    return (
      <Layout title="Recent activity">
        <StateNotice tone="danger" title="Could not load recent activity" detail={err} action={<button type="button" onClick={load}>Retry</button>} />
      </Layout>
    )
  }
  if (loading || !data) {
    return (
      <Layout title="Recent activity">
        <StateNotice title="Loading activity" detail="Collecting recent runs, decisions, and overseer state." />
      </Layout>
    )
  }

  const runs = data.recent_runs || []
  const decisions = data.recent_decisions || []
  const notifications = data.recent_notifications || []
  const projection = data.activity_projection || null
  const activeProjection = projection?.active || null
  const timelineEvents = activeProjection?.timeline || data.recent_timeline_events || []
  const evidenceTimeline = data.evidence_timeline || null
  const overseer = data.overseer

  return (
    <Layout title="Recent activity">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <p style={{ margin: 0, color: 'var(--muted)' }}>
          {runs.length} recent runs, {decisions.length} recent decisions, {notifications.length} recent notifications.
        </p>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <button type="button" onClick={() => setProjectionView((view) => (view === 'compact' ? 'expanded' : 'compact'))}>
            {projectionView === 'compact' ? 'Show expanded' : 'Show compact'}
          </button>
          <button type="button" onClick={load}>Refresh</button>
        </div>
      </div>
      {projection?.since_last_wake ? (
        <section style={{ marginBottom: 24, padding: 12, border: '1px solid var(--border)', borderRadius: 12 }}>
          <h2 style={{ fontSize: 18, marginBottom: 8 }}>Since last wake</h2>
          <p style={{ margin: 0, color: 'var(--muted)' }}>{projection.since_last_wake.summary}</p>
          {projection.since_last_wake.anchor ? (
            <p style={{ margin: '8px 0 0', color: 'var(--muted)' }}>
              anchor: {projection.since_last_wake.anchor.title}
              {projection.since_last_wake.anchor.detail ? ` · ${projection.since_last_wake.anchor.detail}` : ''}
            </p>
          ) : null}
        </section>
      ) : null}
      {evidenceTimeline ? (
        <section style={{ marginBottom: 24, padding: 12, border: '1px solid var(--border)', borderRadius: 12 }}>
          <h2 style={{ fontSize: 18, marginBottom: 8 }}>Evidence plane</h2>
          <p style={{ margin: 0, color: 'var(--muted)' }}>
            {evidenceTimeline.counts?.runs || 0} runs, {evidenceTimeline.counts?.decisions || 0} decisions, {evidenceTimeline.counts?.notifications || 0} notifications.
          </p>
          <p style={{ margin: '8px 0 0', color: 'var(--muted)' }}>
            continuity {evidenceTimeline.counts?.continuity_events || 0}, approvals {evidenceTimeline.counts?.approval_events || 0}, decision claims {evidenceTimeline.counts?.support_claims || 0}, provenance {evidenceTimeline.counts?.provenance_events || 0}.
          </p>
          {evidenceTimeline.latest ? (
            <p style={{ margin: '8px 0 0' }}>
              latest: {evidenceTimeline.latest.title}
              {evidenceTimeline.latest.detail ? ` · ${evidenceTimeline.latest.detail}` : ''}
            </p>
          ) : null}
        </section>
      ) : null}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 18, marginBottom: 8 }}>
          Recent timeline events {projection?.active?.mode ? `(${projection.active.mode})` : ''}
        </h2>
        {timelineEvents.length === 0 ? (
          <p>No timeline events.</p>
        ) : (
          <div style={{ overflowX: 'auto', maxWidth: '100%' }}>
          <table width="100%" cellPadding="8" style={{ borderCollapse: 'collapse', minWidth: 720 }}>
            <thead>
              <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
                <th>Timestamp</th>
                <th>Type</th>
                <th>Title</th>
                <th>Detail</th>
                <th>Why</th>
              </tr>
            </thead>
            <tbody>
              {timelineEvents.map((item, i) => (
                <tr key={`${item.event_id || item.timestamp || 'ts'}-${i}`} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td>{formatDateTime(item.timestamp)}</td>
                  <td>{item.event_type || '—'}</td>
                  <td>
                    {item.href ? <a href={item.href}>{item.title || '—'}</a> : (item.title || '—')}
                  </td>
                  <td>{item.detail || '—'}</td>
                  <td>{item.provenance_href ? <a href={item.provenance_href}>open reply</a> : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        )}
      </section>
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 18, marginBottom: 8 }}>Recent runs</h2>
        {runs.length === 0 ? (
          <p>No runs.</p>
        ) : (
          <div style={{ overflowX: 'auto', maxWidth: '100%' }}>
          <table width="100%" cellPadding="8" style={{ borderCollapse: 'collapse', minWidth: 720 }}>
            <thead>
              <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
                <th>run_id</th>
                <th>status</th>
                <th>started</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r) => (
                <tr key={r.run_id} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td><a href={`#/runs/${r.run_id}`}>{r.run_id}</a></td>
                  <td>{r.status || '—'}</td>
                  <td>{formatDateTime(r.started_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        )}
      </section>
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 18, marginBottom: 8 }}>Recent notifications</h2>
        {notifications.length === 0 ? (
          <p>No operator-facing notifications.</p>
        ) : (
          <div style={{ overflowX: 'auto', maxWidth: '100%' }}>
          <table width="100%" cellPadding="8" style={{ borderCollapse: 'collapse', minWidth: 720 }}>
            <thead>
              <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
                <th>Timestamp</th>
                <th>Task</th>
                <th>Kind</th>
                <th>Governance</th>
                <th>Message</th>
              </tr>
            </thead>
            <tbody>
              {notifications.map((item, i) => (
                <tr key={`${item.timestamp || 'ts'}-${i}`} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td>{formatDateTime(item.timestamp)}</td>
                  <td>{item.task_name ? <a href={`#/entities/${item.task_name}`}>{item.task_name}</a> : '—'}</td>
                  <td>{item.kind || '—'}</td>
                  <td>
                    <div>{item.governance_label || '—'}</div>
                    <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                      {item.governance_detail || '—'}
                    </div>
                    {item.review_release_state?.action_hint ? (
                      <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                        next: {item.review_release_state.action_hint}
                      </div>
                    ) : null}
                    {item.review_release_state?.release_blockers?.length ? (
                      <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                        blockers: {item.review_release_state.release_blockers.join(', ')}
                      </div>
                    ) : null}
                    <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                      {item.approval_href ? <a href={item.approval_href}>open approval</a> : '—'}
                    </div>
                    {item.governance_actions ? (
                      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 6 }}>
                        {item.governance_actions.can_approve_resume ? (
                          <button
                            type="button"
                            disabled={actionKey === `${item.timestamp || 'ts'}:${item.kind || 'kind'}:approve_resume`}
                            onClick={() => runGovernanceAction(item, 'approve_resume')}
                          >
                            {actionKey === `${item.timestamp || 'ts'}:${item.kind || 'kind'}:approve_resume` ? 'Approving…' : 'Approve resume'}
                          </button>
                        ) : null}
                        {item.governance_actions.can_acknowledge_recovery ? (
                          <button
                            type="button"
                            disabled={actionKey === `${item.timestamp || 'ts'}:${item.kind || 'kind'}:acknowledge_recovery`}
                            onClick={() => runGovernanceAction(item, 'acknowledge_recovery')}
                          >
                            {actionKey === `${item.timestamp || 'ts'}:${item.kind || 'kind'}:acknowledge_recovery` ? 'Acknowledging…' : 'Acknowledge recovery'}
                          </button>
                        ) : null}
                        {item.governance_actions.can_verify_rebuild ? (
                          <button
                            type="button"
                            disabled={actionKey === `${item.timestamp || 'ts'}:${item.kind || 'kind'}:verify_rebuild`}
                            onClick={() => runGovernanceAction(item, 'verify_rebuild')}
                          >
                            {actionKey === `${item.timestamp || 'ts'}:${item.kind || 'kind'}:verify_rebuild` ? 'Verifying…' : 'Verify rebuild'}
                          </button>
                        ) : null}
                      </div>
                    ) : null}
                  </td>
                  <td>
                    <div>{item.message || '—'}</div>
                    <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                      {item.operational_agent_id || item.social_account_id || item.transport || '—'}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        )}
      </section>
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 18, marginBottom: 8 }}>Recent decisions</h2>
        {decisions.length === 0 ? (
          <p>No decisions.</p>
        ) : (
          <div style={{ overflowX: 'auto', maxWidth: '100%' }}>
          <table width="100%" cellPadding="8" style={{ borderCollapse: 'collapse', minWidth: 720 }}>
            <thead>
              <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
                <th>Entity</th>
                <th>Timestamp</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {decisions.map((d, i) => (
                <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td><a href={`#/entities/${d.entity}`}>{d.entity}</a></td>
                  <td>{formatDateTime(d.timestamp)}</td>
                  <td>{d.action ? String(d.action).slice(0, 60) + (d.action.length > 60 ? '…' : '') : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        )}
      </section>
      {overseer && (overseer.latest_state != null || overseer.timeseries_count_24h != null) && (
        <section>
          <h2 style={{ fontSize: 18, marginBottom: 8 }}>Overseer</h2>
          {overseer.timeseries_count_24h != null && (
            <p>Timeseries events (24h): {overseer.timeseries_count_24h}</p>
          )}
          {overseer.latest_state != null && (
            <pre style={{ fontSize: 12, overflow: 'auto', maxHeight: 200 }}>
              {JSON.stringify(overseer.latest_state, null, 2)}
            </pre>
          )}
        </section>
      )}
    </Layout>
  )
}


