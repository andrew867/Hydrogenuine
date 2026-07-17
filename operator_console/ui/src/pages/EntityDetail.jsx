import React, { useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import Breadcrumbs from '../components/Breadcrumbs.jsx'
import SharedEventSummary from '../components/SharedEventSummary.jsx'
import { api } from '../lib/api.js'
import { withReturnUrl } from '../lib/navigationContext.js'
import { PageSkeleton } from '../components/PageStates.jsx'

function continuityLabel(summary) {
  const status = summary?.status
  if (status === 'degraded') return 'Continuity degraded'
  if (status === 'healthy') return 'Continuity healthy'
  if (status === 'missing') return 'Session missing'
  if (status === 'unbound') return 'No session bound'
  return 'Continuity unknown'
}

function continuityInjuryLabel(summary) {
  const status = summary?.status
  if (status === 'active') return 'Continuity injury active'
  if (status === 'recovered') return 'Continuity recovered'
  if (status === 'none') return 'No recent continuity injury'
  return 'Continuity injury unknown'
}

function readinessLabel(summary) {
  if (!summary) return 'Readiness unknown'
  return summary.ready ? 'Ready' : 'Blocked'
}

function proofLabel(summary) {
  if (!summary || !summary.artifact_count) return 'No proof'
  return `${summary.latest_artifact_type || 'proof'} | ${summary.artifact_count}`
}

function researchDeliveryLabel(summary) {
  if (!summary || !summary.delivery_count) return 'No research deliveries'
  return `${summary.delivery_count} research deliver${summary.delivery_count === 1 ? 'y' : 'ies'}`
}

function notificationLabel(summary) {
  if (!summary || !summary.count) return 'No notifications'
  return `${summary.count} recent notification${summary.count === 1 ? '' : 's'}`
}

function lastActivityLabel(summary) {
  if (!summary || !summary.last_seen_at) return 'No recent activity'
  return `${summary.last_seen_kind || 'activity'}${summary.stale ? ' · stale' : ''}`
}

function profileSummaryLabel(profile) {
  if (!profile) return 'No profile'
  const overview = profile.overview || {}
  const memory = profile.memory || {}
  const continuity = profile.continuity?.continuity_recovery_readiness?.status || 'unknown'
  const continuityView = profile.continuity_view?.summary || 'no continuity view'
  const quality = profile.continuity_quality_summary?.status || profile.continuity?.continuity_quality_summary?.status || 'unknown'
  const reflection = profile.reflection_status?.status || 'unknown'
  const runs = overview.latest_run_count ?? 0
  return `${runs} run${runs === 1 ? '' : 's'} · memory ${memory.status || 'unknown'} · continuity ${continuity} · quality ${quality} · view ${continuityView} · reflection ${reflection}`
}

function latestRunLabel(run) {
  if (!run) return 'No recent runs'
  const status = run.status || 'unknown'
  const workflow = run.workflow_id || 'workflow?'
  return `${run.run_id || 'run?'} · ${workflow} · ${status}`
}

function identityContinuityLabel(summary) {
  const status = summary?.status
  if (status === 'healthy') return 'Identity continuity healthy'
  if (status === 'partial') return 'Identity continuity partial'
  if (status === 'missing') return 'Identity continuity missing'
  return 'Identity continuity unknown'
}

function continuityIncidentLabel(summary) {
  const status = summary?.status
  if (status === 'active') return 'Continuity incident active'
  if (status === 'recovered') return 'Continuity incident recovered'
  if (status === 'clean') return 'No active continuity incident'
  return 'Continuity incident unknown'
}

function continuityRecoveryReadinessLabel(summary) {
  const status = summary?.status
  if (status === 'blocked') return 'Recovery blocked'
  if (status === 'caution') return 'Recovery caution'
  if (status === 'ready') return 'Recovery ready'
  return 'Recovery unknown'
}

function postRebuildCheckLabel(summary) {
  const status = summary?.status
  if (status === 'verified') return 'Verified after rebuild'
  if (status === 'pending') return 'Verification pending'
  if (status === 'blocked') return 'Verification blocked'
  if (status === 'not_required') return 'No rebuild recorded'
  return 'Unknown'
}

function operationalResumeLabel(summary) {
  const status = summary?.status
  if (status === 'ready') return 'Operational resume ready'
  if (status === 'caution') return 'Operational resume caution'
  if (status === 'blocked') return 'Operational resume blocked'
  return 'Operational resume unknown'
}

function operationalResumeCheckpointLabel(summary) {
  if (summary?.approved) return `Approved${summary?.approved_by ? ` by ${summary.approved_by}` : ''}`
  return 'Not approved'
}

function presenceLabel(summary) {
  const mode = summary?.initiative_mode
  if (mode === 'self_timed_override') return 'Self-timed override'
  if (mode === 'bounded_sleep') return 'Bounded sleep'
  if (mode === 'scheduled_only') return 'Scheduled only'
  return 'Presence unknown'
}

function affectActionLabel(summary) {
  if (!summary || summary.status === 'missing') return 'Unavailable'
  const arc = summary?.action_state?.dominant_arc_state || 'arc?'
  const mode = summary?.action_state?.dominant_engagement_mode || 'mode?'
  const trust = summary?.affective_state?.trust_band
  return trust == null ? `${arc} / ${mode}` : `${arc} / ${mode} / trust ${trust}`
}

function selfModelLabel(summary) {
  if (!summary || summary.status !== 'healthy') return 'Self-model unavailable'
  return `${summary.dominant_arc_state || 'arc?'} / ${summary.dominant_engagement_mode || 'mode?'}`
}

function confidenceLabel(summary) {
  if (!summary || (!summary.confidence_level && summary.confidence_score == null)) return 'Confidence unavailable'
  return `${summary.confidence_level || 'uncertain'} / ${summary.confidence_score ?? 0}/100`
}

function mimicryLabel(summary) {
  if (!summary || !summary.status) return 'Mimicry unavailable'
  const depth = summary.max_mimicry_depth != null ? Number(summary.max_mimicry_depth).toFixed(2) : '—'
  const emotion = summary.max_emotional_intensity != null ? Number(summary.max_emotional_intensity).toFixed(2) : '—'
  return `${summary.status} / depth ${depth} / emotion ${emotion}`
}

function continuityQualityLabel(summary) {
  if (!summary || !summary.status) return 'Continuity quality unavailable'
  return `${summary.status} / ${summary.quality_score ?? 0}/100`
}

function continuityNextActionLabel(summary) {
  if (!summary) return 'Next action unavailable'
  return summary.next_action || 'review continuity'
}

function continuityStaleFactsLabel(summary) {
  if (!summary || !(summary.stale_facts || []).length) return 'No stale facts'
  return (summary.stale_facts || []).join(' · ')
}

function sameFingerprintLabel(summary) {
  if (!summary || !summary.status) return 'Same-fingerprint unavailable'
  const decision = summary.decision || 'unknown'
  return `${summary.status} · ${decision}`
}

function selfLocationFreshnessLabel(freshness) {
  if (!freshness) return 'Freshness unknown'
  const state = freshness.freshness_state || 'unknown'
  const wake = freshness.last_wake_at || 'no wake anchor'
  const activity = freshness.last_activity_at || 'no recent activity'
  return `${state} · wake ${wake} · activity ${activity}`
}

function selfLocationBranchLabel(location) {
  if (!location) return 'Branch state unavailable'
  const scope = location.scope || 'unknown'
  const session = location.session_target || 'shared session?'
  const operational = location.operational_session_target || 'no operational branch'
  return `${scope} · ${operational !== session ? operational : session}`
}

function relationshipLabel(summary) {
  if (!summary || summary.status !== 'healthy') return 'Relationship memory unavailable'
  return `${summary.dominant_relationship_type || 'relationship?'} / ${summary.recent_counterpart_count || 0} counterparts`
}

function crewDynamicsLabel(summary) {
  if (!summary || summary.status === 'missing') return 'Crew dynamics unavailable'
  const style = summary.coordination_style || 'unknown'
  const members = summary.swarm_member_count ?? 0
  return `${style} / ${members} member${members === 1 ? '' : 's'}`
}

function rationaleLabel(summary) {
  if (!summary || !summary.current_trigger) return 'Rationale unavailable'
  return summary.current_trigger
}

function commitmentLabel(summary) {
  if (!summary || !summary.count) return 'No commitments'
  const status = summary.status === 'overdue' ? 'overdue' : summary.status === 'pending' ? 'open' : summary.status || 'done'
  return `${summary.open_count || 0} open · ${status}`
}

function reviewHandoffLabel(summary) {
  if (!summary || !summary.count) return 'No review handoff'
  return `${summary.pending_count || summary.count} pending review${(summary.pending_count || summary.count) === 1 ? '' : 's'}`
}

function agencyControlLabel(summary) {
  const mode = summary?.effective_mode || summary?.mode
  if (mode === 'held') return 'Held'
  if (mode === 'review_only') return 'Review only'
  if (mode === 'normal') return 'Normal'
  return 'Agency control unknown'
}

function outboundBudgetLabel(summary) {
  if (!summary || summary.daily_outbound_budget == null) return 'No outbound budget'
  const recent = summary.recent_outbound_action_count ?? 0
  const budget = summary.daily_outbound_budget
  const windowHours = summary.outbound_actions_window_hours ?? 24
  const remaining = summary.outbound_budget_remaining ?? Math.max(0, budget - recent)
  const status = summary.outbound_budget_exhausted ? 'exhausted' : `${remaining} left`
  return `${recent}/${budget} in ${windowHours}h · ${status}`
}

function socialPostureLabel(summary) {
  if (!summary) return '—'
  const posture = summary.posture || 'unknown'
  const mode = summary.effective_mode || 'normal'
  return `${posture} | ${mode}`
}

function refreshNote(reasonCodes, fallback) {
  const codes = Array.isArray(reasonCodes) ? reasonCodes : []
  if (codes.includes('followup_overdue')) return 'follow-up overdue'
  if (codes.includes('approval_expired')) return 'approval expired'
  if (codes.includes('approval_release_held')) return 'release blocked by hold'
  if (codes.includes('approval_release_lane_policy_blocked')) return 'release blocked by lane policy'
  if (codes.includes('approval_release_outbound_budget_exhausted')) return 'release blocked by outbound budget'
  return fallback
}

export default function EntityDetail({ entityId }) {
  const [entity, setEntity] = useState(null)
  const [graph, setGraph] = useState(null)
  const [persona, setPersona] = useState(null)
  const [personaTab, setPersonaTab] = useState('soul')
  const [err, setErr] = useState(null)
  const [refreshingApproval, setRefreshingApproval] = useState(false)
  const [approvingResume, setApprovingResume] = useState(false)
  const [acknowledgingRecovery, setAcknowledgingRecovery] = useState(false)
  const [recordingRebuild, setRecordingRebuild] = useState(false)
  const [verifyingRebuild, setVerifyingRebuild] = useState(false)
  const profile = entity?.profile || {}
  const latestRun = profile.latest_runs?.[0] || null
  const launchWorkflowHref = withReturnUrl('#/run')
  const latestRunHref = latestRun?.run_id ? `#/runs/${encodeURIComponent(latestRun.run_id)}` : null
  const approvalsHref = entity?.review_handoff_summary?.latest?.approval_href
    || (entity?.review_handoff_summary?.latest?.task_name
      ? `#/approvals?workflow_id=${encodeURIComponent(entity.review_handoff_summary.latest.task_name)}`
      : '#/approvals')
  const go = (href) => { window.location.hash = href }

  const formatWakeTokens = (info) => {
    if (!info) return '—'
    const total = info.total_estimate ?? '—'
    const mem = (info.memory_estimated_tokens != null && info.memory_cap != null)
      ? `${info.memory_estimated_tokens}/${info.memory_cap}`
      : '—'
    return `${total} (mem ${mem})`
  }

  useEffect(() => {
    if (!entityId) return
    api.getEntity(entityId)
      .then((r) => setEntity(r))
      .catch((e) => setErr(e.message))
    api.getEntityGraph(entityId)
      .then((r) => setGraph(r.ok ? r : null))
      .catch(() => setGraph(null))
    api.getEntityPersona(entityId)
      .then((r) => setPersona(r.ok ? r : null))
      .catch(() => setPersona(null))
  }, [entityId])

  const refreshReviewHandoff = async () => {
    const approvalId = entity?.review_handoff_summary?.latest?.approval_id
    if (!approvalId) return
    setRefreshingApproval(true)
    setErr(null)
    try {
      const refreshed = await api.refreshEntityApprovalRequest(approvalId, {
        note: refreshNote(entity?.review_handoff_summary?.refresh_reasons || [], 'refreshed from entity detail'),
        decided_by: 'operator_console',
        refresh_reason_codes: entity?.review_handoff_summary?.refresh_reasons || [],
      })
      const nextId = refreshed?.approval_id || approvalId
      const workflowId = entity?.review_handoff_summary?.latest?.task_name || entity?.job_id || entity?.id
      const params = new URLSearchParams()
      if (workflowId) params.set('workflow_id', workflowId)
      params.set('approval_id', nextId)
      window.location.hash = `#/approvals?${params.toString()}`
      const nextEntity = await api.getEntity(entityId)
      setEntity(nextEntity)
    } catch (e) {
      setErr(e.message)
    } finally {
      setRefreshingApproval(false)
    }
  }

  const approveResumeCheckpoint = async () => {
    if (!entity?.platform || !entity?.operational_agent_id) return
    setApprovingResume(true)
    setErr(null)
    try {
      await api.approveOperationalResumeCheckpoint(entity.platform, entity.operational_agent_id, {
        approved_by: 'operator_console',
        note: 'approved from entity detail',
      })
      const nextEntity = await api.getEntity(entityId)
      setEntity(nextEntity)
    } catch (e) {
      setErr(e.message)
    } finally {
      setApprovingResume(false)
    }
  }

  const acknowledgeContinuityRecovery = async () => {
    if (!entity?.platform || !entity?.operational_agent_id) return
    setAcknowledgingRecovery(true)
    setErr(null)
    try {
      await api.acknowledgeOperationalContinuityRecovery(entity.platform, entity.operational_agent_id, {
        acknowledged_by: 'operator_console',
        note: 'acknowledged from entity detail',
      })
      const nextEntity = await api.getEntity(entityId)
      setEntity(nextEntity)
    } catch (e) {
      setErr(e.message)
    } finally {
      setAcknowledgingRecovery(false)
    }
  }

  const recordPostRebuild = async () => {
    if (!entity?.platform || !entity?.operational_agent_id) return
    setRecordingRebuild(true)
    setErr(null)
    try {
      await api.recordOperationalPostRebuild(entity.platform, entity.operational_agent_id, {
        recorded_by: 'operator_console',
        note: 'recorded from entity detail',
      })
      const nextEntity = await api.getEntity(entityId)
      setEntity(nextEntity)
    } catch (e) {
      setErr(e.message)
    } finally {
      setRecordingRebuild(false)
    }
  }

  const verifyPostRebuild = async () => {
    if (!entity?.platform || !entity?.operational_agent_id) return
    setVerifyingRebuild(true)
    setErr(null)
    try {
      await api.verifyOperationalPostRebuild(entity.platform, entity.operational_agent_id, {
        verified_by: 'operator_console',
        note: 'verified from entity detail',
      })
      const nextEntity = await api.getEntity(entityId)
      setEntity(nextEntity)
    } catch (e) {
      setErr(e.message)
    } finally {
      setVerifyingRebuild(false)
    }
  }

  if (err) {
    return (
      <Layout title="Entity profile">
        <div style={{ color: 'var(--danger)' }}>{err}</div>
      </Layout>
    )
  }
  if (!entity) {
    return (
      <Layout title="Entity profile">
        <PageSkeleton label="Loading entity profile" />
      </Layout>
    )
  }

  return (
    <Layout title="Entity profile">
      <Breadcrumbs items={[{ label: 'Home', href: '#/' }, { label: 'Entities', href: '#/entities' }, { label: 'Entity profile' }, { label: entity.id }]} />
      <p><a href="#/entities">← Back to Entities</a></p>
      <SharedEventSummary
        eyebrow="Entity state sheet"
        title={profile.overview?.display_name || entity.id}
        intro="This is the canonical snapshot for identity, memory, continuity, approvals, recent work, reflections, and recovery."
        status={identityContinuityLabel(entity.identity_continuity_summary)}
        statusTone={entity.identity_continuity_summary?.status === 'healthy' ? 'good' : entity.identity_continuity_summary?.status === 'partial' ? 'warn' : entity.identity_continuity_summary?.status === 'missing' ? 'danger' : 'neutral'}
        happened={profile.continuity_view?.since_last_wake?.summary || profile.continuity_view?.summary || 'No recent continuity changes'}
        when={selfLocationFreshnessLabel(entity.self_location?.freshness || entity.presence_initiative_summary)}
        why={rationaleLabel(entity.action_rationale_summary)}
        changed={`Continuity ${continuityQualityLabel(profile.continuity?.continuity_quality_summary || entity.continuity_quality_summary)} · approvals ${profile.approvals?.pending_approvals ?? 0} pending · reflection ${profile.reflection_status?.status || 'unknown'}`}
        next={profile.continuity_view?.next_action || continuityNextActionLabel(profile.continuity_view)}
        context={[
          { label: 'Entity', value: entity.id },
          { label: 'Platform', value: profile.overview?.platform || entity.platform || '—' },
          { label: 'Mode', value: profile.overview?.mode || entity.mode || '—' },
          { label: 'Latest run', value: latestRun?.run_id || '—', href: latestRunHref || undefined },
          { label: 'Latest approval', value: entity.review_handoff_summary?.latest?.approval_id || '—', href: entity.review_handoff_summary?.latest?.approval_href || undefined },
        ]}
        actions={(
          <>
            <button type="button" onClick={() => go(launchWorkflowHref)}>Launch workflow</button>
            {latestRunHref ? <button type="button" onClick={() => go(latestRunHref)}>Open latest run</button> : null}
            <button type="button" onClick={() => go('#/timeline')}>Open timeline</button>
            <button type="button" onClick={() => go(approvalsHref)}>Open approvals</button>
            <button type="button" onClick={() => go('#/reflections')}>Open reflections</button>
            <button type="button" onClick={() => go('#/governance')}>Open governance</button>
          </>
        )}
      />
      <section style={{ marginBottom: 24, padding: 16, border: '1px solid var(--border)', borderRadius: 12, background: 'var(--panel-2)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', alignItems: 'flex-start' }}>
          <div style={{ minWidth: 280, flex: '1 1 420px' }}>
            <div className="muted" style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.08 }}>Entity control center</div>
            <h2 style={{ margin: '6px 0 8px', fontSize: 26, lineHeight: 1.1 }}>{profile.overview?.display_name || entity.id}</h2>
            <div className="muted" style={{ marginBottom: 10 }}>
              {profile.overview?.platform || entity.platform || '—'} · {profile.overview?.mode || entity.mode || '—'}
              {' '}· {profile.overview?.latest_run_count ?? 0} recent run{(profile.overview?.latest_run_count ?? 0) === 1 ? '' : 's'}
            </div>
            <div style={{ fontSize: 14, lineHeight: 1.5 }}>
              {profileSummaryLabel(profile)}
            </div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 12 }}>
              <div className="card"><strong>{identityContinuityLabel(entity.identity_continuity_summary)}</strong><div className="muted">identity</div></div>
              <div className="card"><strong>{continuityRecoveryReadinessLabel(profile.continuity?.continuity_recovery_readiness || entity.continuity_recovery_readiness)}</strong><div className="muted">recovery</div></div>
              <div className="card"><strong>{continuityQualityLabel(profile.continuity?.continuity_quality_summary || entity.continuity_quality_summary)}</strong><div className="muted">quality</div></div>
              <div className="card"><strong>{profile.reflection_status?.status || 'unknown'}</strong><div className="muted">reflection</div></div>
            </div>
          </div>
        </div>
          <div style={{ marginTop: 16, display: 'grid', gap: 8 }}>
            <div className="muted" style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.08 }}>Continuity at a glance</div>
            <div>{profile.continuity_view?.summary || 'No recent continuity changes'}</div>
            <div className="muted" style={{ fontSize: 12 }}>
              {profile.continuity_view?.since_last_wake?.summary || 'No wake anchor yet'}
          </div>
          <div className="muted" style={{ fontSize: 12 }}>
            {(profile.continuity_view?.conflicts || []).join(' · ') || 'No continuity conflicts'}
          </div>
            <div className="muted" style={{ fontSize: 12 }}>
              {(profile.continuity_view?.scheduled_work || []).join(' · ') || 'No scheduled continuity work'}
            </div>
            <div className="muted" style={{ fontSize: 12 }}>
              Next action: {continuityNextActionLabel(profile.continuity_view)}
            </div>
            <div className="muted" style={{ fontSize: 12 }}>
              Stale facts: {continuityStaleFactsLabel(profile.continuity_view)}
            </div>
          </div>
          <div style={{ marginTop: 16, display: 'grid', gap: 8 }}>
            <div className="muted" style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.08 }}>Self-location</div>
            <div className="card-grid">
              <div className="card">
                <strong>{profile.self_location?.role || entity.task_name || entity.id || 'unknown'}</strong>
                <div className="muted">role</div>
              </div>
              <div className="card">
                <strong>{profile.self_location?.mode || entity.mode || 'unknown'}</strong>
                <div className="muted">mode</div>
              </div>
              <div className="card">
                <strong>{(profile.self_location?.goals || []).length ? (profile.self_location.goals[0] || '—') : 'No clear goal'}</strong>
                <div className="muted">goal</div>
              </div>
              <div className="card">
                <strong>{(profile.self_location?.blockers || []).length ? profile.self_location.blockers[0] : 'No active blocker'}</strong>
                <div className="muted">blocker</div>
              </div>
            </div>
            <div className="card-grid">
              <div className="card">
                <strong>{selfLocationFreshnessLabel(profile.self_location?.freshness)}</strong>
                <div className="muted">freshness</div>
              </div>
              <div className="card">
                <strong>{selfLocationBranchLabel(profile.self_location?.active_branch_state)}</strong>
                <div className="muted">branch state</div>
              </div>
              <div className="card">
                <strong>{sameFingerprintLabel(profile.same_fingerprint_summary)}</strong>
                <div className="muted">same-fingerprint</div>
              </div>
            </div>
            <div className="muted" style={{ fontSize: 12 }}>
              {profile.self_location?.memory_scope?.promotion_rule || 'Memory scope not available'}
            </div>
            <div className="muted" style={{ fontSize: 12 }}>
              {profile.same_fingerprint_summary?.summary || 'Same-fingerprint behavior not exposed'}
            </div>
          </div>
      </section>
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 18, marginBottom: 8 }}>Info</h2>
        <table cellPadding="8" style={{ borderCollapse: 'collapse' }}>
          <tbody>
            <tr><td><strong>ID</strong></td><td>{entity.id}</td></tr>
            <tr><td><strong>Job ID</strong></td><td>{entity.job_id || '—'}</td></tr>
            <tr><td><strong>Session target</strong></td><td>{entity.session_target || '—'}</td></tr>
            <tr><td><strong>Platform</strong></td><td>{entity.platform ?? '—'}</td></tr>
            <tr><td><strong>Mode</strong></td><td>{entity.mode ?? '—'}</td></tr>
            <tr><td><strong>Identity continuity</strong></td><td>{identityContinuityLabel(entity.identity_continuity_summary)}</td></tr>
            <tr><td><strong>Continuity incident</strong></td><td>{continuityIncidentLabel(entity.continuity_incident_summary)}{entity.continuity_incident_summary?.latest_event_detail ? ` | ${entity.continuity_incident_summary.latest_event_detail}` : ''}</td></tr>
            <tr><td><strong>Recovery readiness</strong></td><td>{continuityRecoveryReadinessLabel(entity.continuity_recovery_readiness)}</td></tr>
            <tr><td><strong>Recovery blockers</strong></td><td>{(entity.continuity_recovery_readiness?.blocking || []).join(' | ') || '—'}</td></tr>
            <tr><td><strong>Recovery cautions</strong></td><td>{(entity.continuity_recovery_readiness?.cautions || []).join(' | ') || '—'}</td></tr>
            <tr><td><strong>Recovery acknowledged</strong></td><td>{entity.continuity_recovery_readiness?.acknowledged ? `${entity.continuity_recovery_readiness.acknowledged_by || 'operator'} | ${entity.continuity_recovery_readiness.acknowledged_at || '—'}` : 'no'}</td></tr>
            {entity.continuity_recovery_readiness?.can_acknowledge && !entity.continuity_recovery_readiness?.acknowledged && entity.platform && entity.operational_agent_id ? (
              <tr>
                <td><strong>Recovery action</strong></td>
                <td>
                  <button type="button" onClick={acknowledgeContinuityRecovery} disabled={acknowledgingRecovery}>
                    {acknowledgingRecovery ? 'Acknowledging…' : 'Acknowledge recovery'}
                  </button>
                </td>
              </tr>
            ) : null}
            <tr><td><strong>Repair plan</strong></td><td>{entity.continuity_repair_plan?.status || '—'}</td></tr>
            <tr><td><strong>Open repair checks</strong></td><td>{(entity.continuity_repair_plan?.open_checks || []).join(' | ') || '—'}</td></tr>
            <tr><td><strong>Post-rebuild check</strong></td><td>{postRebuildCheckLabel(entity.post_rebuild_continuity_check)}</td></tr>
            <tr><td><strong>Post-rebuild recorded</strong></td><td>{entity.post_rebuild_continuity_check?.rebuild_recorded_at || '—'}</td></tr>
            <tr><td><strong>Post-rebuild verified</strong></td><td>{entity.post_rebuild_continuity_check?.verified_at || '—'}</td></tr>
            {!entity.post_rebuild_continuity_check?.verification_required && entity.platform && entity.operational_agent_id ? (
              <tr>
                <td><strong>Post-rebuild action</strong></td>
                <td>
                  <button type="button" onClick={recordPostRebuild} disabled={recordingRebuild}>
                    {recordingRebuild ? 'Recording rebuild…' : 'Record rebuild'}
                  </button>
                </td>
              </tr>
            ) : null}
            {entity.post_rebuild_continuity_check?.verification_required && !entity.post_rebuild_continuity_check?.verified && entity.platform && entity.operational_agent_id ? (
              <tr>
                <td><strong>Verify rebuild</strong></td>
                <td>
                  <button type="button" onClick={verifyPostRebuild} disabled={verifyingRebuild || entity.post_rebuild_continuity_check?.status === 'blocked'}>
                    {verifyingRebuild ? 'Verifying rebuild…' : 'Verify rebuild'}
                  </button>
                </td>
              </tr>
            ) : null}
            <tr><td><strong>Operational resume</strong></td><td>{operationalResumeLabel(entity.operational_resume_governance_summary)}</td></tr>
            <tr><td><strong>Operational resume actions</strong></td><td>{(entity.operational_resume_governance_summary?.required_actions || []).join(' | ') || '—'}</td></tr>
            <tr><td><strong>Operational resume checkpoint</strong></td><td>{operationalResumeCheckpointLabel(entity.operational_resume_checkpoint)}</td></tr>
            <tr><td><strong>Operational resume approved at</strong></td><td>{entity.operational_resume_checkpoint?.approved_at || '—'}</td></tr>
            <tr><td><strong>Operational resume invalidation</strong></td><td>{entity.operational_resume_checkpoint?.invalidated_reason || '—'}</td></tr>
            {entity.operational_resume_governance_summary?.status === 'ready' && !entity.operational_resume_checkpoint?.approved && entity.platform && entity.operational_agent_id ? (
              <tr>
                <td><strong>Operational resume action</strong></td>
                <td>
                  <button type="button" onClick={approveResumeCheckpoint} disabled={approvingResume}>
                    {approvingResume ? 'Approving resume…' : 'Approve resume'}
                  </button>
                </td>
              </tr>
            ) : null}
            <tr><td><strong>Repair observation</strong></td><td>{entity.continuity_repair_observation?.observation_required ? `${entity.continuity_repair_observation.status}${entity.continuity_repair_observation.latest_observed_at ? ` | ${entity.continuity_repair_observation.latest_observed_at}` : ''}` : 'not required'}</td></tr>
            <tr><td><strong>Identity resume</strong></td><td>{entity.identity_resume_procedure?.status || '—'}</td></tr>
            <tr><td><strong>Identity resume steps</strong></td><td>{(entity.identity_resume_procedure?.open_steps || []).join(' | ') || '—'}</td></tr>
            <tr><td><strong>Continuity anchor</strong></td><td>{entity.identity_continuity_summary?.continuity_anchor || '—'}</td></tr>
            <tr><td><strong>Initialization memo</strong></td><td>{entity.identity_continuity_summary?.initialization_memo_path || '—'}</td></tr>
            <tr><td><strong>Last wake</strong></td><td>{entity.identity_continuity_summary?.last_wake_at || '—'}</td></tr>
            <tr><td><strong>Last sleep</strong></td><td>{entity.identity_continuity_summary?.last_sleep_at || '—'}</td></tr>
            <tr><td><strong>Presence / initiative</strong></td><td>{presenceLabel(entity.presence_initiative_summary)}</td></tr>
            <tr><td><strong>Next earliest wake</strong></td><td>{entity.presence_initiative_summary?.next_earliest_wake_at || '—'}</td></tr>
            <tr><td><strong>Agency budget</strong></td><td>{entity.presence_initiative_summary?.agency_budget ?? '—'}</td></tr>
            <tr><td><strong>Trust band</strong></td><td>{entity.presence_initiative_summary?.trust_band ?? '—'}</td></tr>
            <tr><td><strong>Affect / action</strong></td><td>{affectActionLabel(entity.affect_action_summary)}</td></tr>
            <tr><td><strong>Affect trust</strong></td><td>{entity.affect_action_summary?.affective_state?.trust_band ?? '—'}</td></tr>
            <tr><td><strong>Affect budget</strong></td><td>{entity.affect_action_summary?.affective_state?.agency_budget ?? '—'}</td></tr>
            <tr><td><strong>Latest action mode</strong></td><td>{entity.affect_action_summary?.latest_turn?.engagement_mode || '—'}{entity.affect_action_summary?.latest_turn?.relationship_type ? ` | ${entity.affect_action_summary.latest_turn.relationship_type}` : ''}</td></tr>
            <tr><td><strong>Agency control</strong></td><td>{agencyControlLabel(entity.agency_control_summary)}</td></tr>
            <tr><td><strong>Outbound lane policy</strong></td><td>{entity.agency_control_summary?.outbound_lane_policy || 'unrestricted'}</td></tr>
            <tr><td><strong>Outbound budget</strong></td><td>{outboundBudgetLabel(entity.agency_control_summary)}</td></tr>
            <tr><td><strong>Recent outbound actions</strong></td><td>{entity.agency_control_summary?.recent_outbound_action_count ?? 0}</td></tr>
            <tr><td><strong>Agency control reason</strong></td><td>{entity.agency_control_summary?.reason || '—'}</td></tr>
            <tr><td><strong>Agency control updated</strong></td><td>{entity.agency_control_summary?.updated_at || '—'}</td></tr>
            <tr><td><strong>Social posture</strong></td><td>{socialPostureLabel(entity.social_posture_summary)}</td></tr>
            <tr><td><strong>Reply bias</strong></td><td>{entity.social_posture_summary?.reply_bias || '—'}</td></tr>
            <tr><td><strong>Relationship orientation</strong></td><td>{entity.social_posture_summary?.relationship_orientation || '—'}</td></tr>
            <tr><td><strong>Active social platforms</strong></td><td>{(entity.social_posture_summary?.active_platforms || []).join(' | ') || '—'}</td></tr>
            <tr><td><strong>Self-model</strong></td><td>{selfModelLabel(entity.self_model_summary)}</td></tr>
            <tr><td><strong>Dominant uncertainty</strong></td><td>{entity.self_model_summary?.dominant_uncertainty || '—'}</td></tr>
            <tr><td><strong>Relationship signal</strong></td><td>{entity.self_model_summary?.relationship_signal || '—'}</td></tr>
            <tr><td><strong>Confidence</strong></td><td>{confidenceLabel(entity.confidence_summary)}</td></tr>
            <tr><td><strong>Confidence summary</strong></td><td>{entity.confidence_summary?.summary || '—'}</td></tr>
            <tr><td><strong>Mimicry controls</strong></td><td>{mimicryLabel(entity.mimicry_control_summary)}</td></tr>
            <tr><td><strong>Voice / belief separation</strong></td><td>{entity.voice_belief_separation_summary?.summary || '—'}</td></tr>
            <tr><td><strong>Continuity quality</strong></td><td>{continuityQualityLabel(entity.continuity_quality_summary)}</td></tr>
            <tr><td><strong>Quality coverage / attribution</strong></td><td>{Number(entity.continuity_quality_summary?.coverage_score ?? 0).toFixed(2)} / {Number(entity.continuity_quality_summary?.attribution_score ?? 0).toFixed(2)}</td></tr>
            <tr><td><strong>Callback rate</strong></td><td>{entity.self_model_summary?.callback_rate ?? '—'}</td></tr>
            <tr><td><strong>Proactive notice rate</strong></td><td>{entity.self_model_summary?.proactive_notice_rate ?? '—'}</td></tr>
            <tr><td><strong>Relationship memory</strong></td><td>{relationshipLabel(entity.relationship_memory_summary)}</td></tr>
            <tr><td><strong>Top counterpart</strong></td><td>{entity.relationship_memory_summary?.top_counterparts?.[0]?.counterpart_fingerprint_id || '—'}</td></tr>
            <tr><td><strong>Crew dynamics</strong></td><td>{crewDynamicsLabel(entity.crew_dynamics_summary)}</td></tr>
            <tr><td><strong>Crew workflow</strong></td><td>{entity.crew_dynamics_summary?.workflow_id || '—'}</td></tr>
            <tr><td><strong>Crew swarm</strong></td><td>{entity.crew_dynamics_summary?.swarm_run_id || '—'}</td></tr>
            <tr><td><strong>Crew coordination source</strong></td><td>{entity.crew_dynamics_summary?.coordination_style_source || '—'}</td></tr>
            <tr><td><strong>Why acting now</strong></td><td>{rationaleLabel(entity.action_rationale_summary)}</td></tr>
            <tr><td><strong>Current goal</strong></td><td>{entity.action_rationale_summary?.current_goal || '—'}</td></tr>
            <tr><td><strong>Reason chain</strong></td><td>{(entity.action_rationale_summary?.reason_chain || []).join(' | ') || '—'}</td></tr>
            <tr><td><strong>Commitments</strong></td><td>{commitmentLabel(entity.commitment_summary)}</td></tr>
            <tr><td><strong>Latest commitment</strong></td><td>{entity.commitment_summary?.latest_commitment?.title || '—'}{entity.commitment_summary?.latest_commitment?.due_at ? ` | due ${entity.commitment_summary.latest_commitment.due_at}` : ''}</td></tr>
            <tr><td><strong>Review handoff</strong></td><td>{reviewHandoffLabel(entity.review_handoff_summary)}</td></tr>
            <tr>
              <td><strong>Latest approval</strong></td>
              <td>
                {entity.review_handoff_summary?.latest?.approval_href ? (
                  <a href={entity.review_handoff_summary.latest.approval_href}>{entity.review_handoff_summary?.latest?.approval_id || 'open approval'}</a>
                ) : (
                  entity.review_handoff_summary?.latest?.approval_id || '—'
                )}
              </td>
            </tr>
            <tr><td><strong>Review status</strong></td><td>{entity.review_handoff_summary?.latest?.status || '—'}</td></tr>
            <tr><td><strong>Review note</strong></td><td>{entity.review_handoff_summary?.latest?.decision_note || '—'}</td></tr>
            <tr><td><strong>Release blockers</strong></td><td>{entity.review_handoff_summary?.release_ready ? 'none' : ((entity.review_handoff_summary?.release_blockers || []).join(' | ') || '—')}</td></tr>
            <tr><td><strong>Next eligible release</strong></td><td>{entity.review_handoff_summary?.release_next_eligible_at || '—'}</td></tr>
            <tr><td><strong>Last release attempt</strong></td><td>{entity.review_handoff_summary?.latest?.latest_release_attempt ? `${entity.review_handoff_summary.latest.latest_release_attempt.status || 'unknown'}${entity.review_handoff_summary.latest.latest_release_attempt.reason ? ` | ${entity.review_handoff_summary.latest.latest_release_attempt.reason}` : ''}` : '—'}</td></tr>
            <tr><td><strong>Refresh suggested</strong></td><td>{entity.review_handoff_summary?.refresh_recommended ? ((entity.review_handoff_summary?.refresh_reasons || []).join(' | ') || 'yes') : 'no'}</td></tr>
            <tr><td><strong>Refresh lineage</strong></td><td>{entity.review_handoff_summary?.latest?.refreshed_from_approval_id ? `${entity.review_handoff_summary.latest.refreshed_from_approval_id}${entity.review_handoff_summary?.latest?.refresh_note ? ` | ${entity.review_handoff_summary.latest.refresh_note}` : ''}${entity.review_handoff_summary?.latest?.refresh_reason_codes?.length ? ` | ${entity.review_handoff_summary.latest.refresh_reason_codes.join(', ')}` : ''}` : '—'}</td></tr>
            <tr><td><strong>Release rationale</strong></td><td>{entity.review_handoff_summary?.latest?.resolution_context?.rationale || '—'}</td></tr>
            <tr><td><strong>Release scope</strong></td><td>{entity.review_handoff_summary?.latest?.resolution_context?.release_scope || '—'}</td></tr>
            <tr><td><strong>Follow-up expectation</strong></td><td>{entity.review_handoff_summary?.latest?.resolution_context?.followup_expectation || '—'}</td></tr>
            <tr><td><strong>Follow-up window</strong></td><td>{entity.review_handoff_summary?.latest?.followup_summary?.window_hours ? `${entity.review_handoff_summary.latest.followup_summary.window_hours}h` : '—'}</td></tr>
            <tr><td><strong>Follow-up status</strong></td><td>{entity.review_handoff_summary?.latest?.followup_summary?.expected ? `${entity.review_handoff_summary.latest.followup_summary.status}${entity.review_handoff_summary?.latest?.followup_summary?.due_at ? ` | due ${entity.review_handoff_summary.latest.followup_summary.due_at}` : ''}${entity.review_handoff_summary?.latest?.followup_summary?.observation_detail ? ` | ${entity.review_handoff_summary.latest.followup_summary.observation_detail}` : ''}` : '—'}</td></tr>
            {entity.review_handoff_summary?.refresh_recommended && entity.review_handoff_summary?.latest?.approval_id ? (
              <tr>
                <td><strong>Refresh action</strong></td>
                <td>
                  <button type="button" onClick={refreshReviewHandoff} disabled={refreshingApproval}>
                    {refreshingApproval ? 'Refreshing…' : 'Refresh handoff'}
                  </button>
                </td>
              </tr>
            ) : null}
            <tr><td><strong>Research deliveries</strong></td><td>{researchDeliveryLabel(entity.research_delivery_summary)}</td></tr>
            <tr><td><strong>Decisions count</strong></td><td>{entity.decisions_count ?? 0}</td></tr>
            <tr><td><strong>Last activity</strong></td><td>{entity.last_activity || '—'}</td></tr>
            <tr><td><strong>Wake tokens</strong></td><td>{formatWakeTokens(entity.wake_context_tokens)}</td></tr>
            {entity.persona_dir && (
              <tr><td><strong>Persona dir</strong></td><td><code>{entity.persona_dir}</code></td></tr>
            )}
          </tbody>
        </table>
      </section>
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 18, marginBottom: 8 }}>Profile</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12 }}>
          <div className="section-card">
            <div className="muted" style={{ fontSize: 11 }}>Overview</div>
            <div>{profile.overview?.display_name || entity.id}</div>
            <div className="muted" style={{ fontSize: 12 }}>
              {profile.overview?.platform || entity.platform || '—'} · {profile.overview?.mode || entity.mode || '—'}
            </div>
            <div className="muted" style={{ fontSize: 12 }}>
              {profile.overview?.latest_run_count ?? 0} recent run{(profile.overview?.latest_run_count ?? 0) === 1 ? '' : 's'}
            </div>
          </div>
          <div className="section-card">
            <div className="muted" style={{ fontSize: 11 }}>Memory</div>
            <div>{profile.memory?.status || 'unknown'}</div>
            <div className="muted" style={{ fontSize: 12 }}>
              {selfModelLabel(profile.memory?.self_model_summary)}
            </div>
            <div className="muted" style={{ fontSize: 12 }}>
              {relationshipLabel(profile.memory?.relationship_memory_summary)}
            </div>
            <div className="muted" style={{ fontSize: 12 }}>
              {confidenceLabel(profile.memory?.confidence_summary)}
            </div>
          </div>
          <div className="section-card">
            <div className="muted" style={{ fontSize: 11 }}>Continuity packet</div>
            <div>{continuityRecoveryReadinessLabel(profile.continuity?.continuity_recovery_readiness)}</div>
            <div className="muted" style={{ fontSize: 12 }}>
              {identityContinuityLabel(profile.continuity?.identity_continuity_summary)}
            </div>
            <div className="muted" style={{ fontSize: 12 }}>
              {operationalResumeLabel(profile.continuity?.operational_resume_governance_summary)}
            </div>
            <div className="muted" style={{ fontSize: 12 }}>
              {operationalResumeCheckpointLabel(profile.continuity?.operational_resume_checkpoint)}
            </div>
          </div>
          <div className="section-card">
            <div className="muted" style={{ fontSize: 11 }}>Continuity view</div>
            <div>{profile.continuity_view?.summary || 'No recent continuity changes'}</div>
            <div className="muted" style={{ fontSize: 12 }}>
              {profile.continuity_view?.since_last_wake?.summary || 'No wake anchor yet'}
            </div>
            <div className="muted" style={{ fontSize: 12 }}>
              {(profile.continuity_view?.conflicts || []).join(' · ') || 'No continuity conflicts'}
            </div>
            <div className="muted" style={{ fontSize: 12 }}>
              {(profile.continuity_view?.scheduled_work || []).join(' · ') || 'No scheduled continuity work'}
            </div>
            <div className="muted" style={{ fontSize: 12 }}>
              {profile.continuity_view?.steering?.agent_id
                ? `steering ${profile.continuity_view.steering.agent_id}${profile.continuity_view.steering.version ? ` v${profile.continuity_view.steering.version}` : ''}${profile.continuity_view.steering.changed_since_last_wake ? ' · changed since wake' : ''}`
                : 'No steering profile'}
            </div>
          </div>
          <div className="section-card">
            <div className="muted" style={{ fontSize: 11 }}>Approvals</div>
            <div>{reviewHandoffLabel(profile.approvals?.review_handoff_summary)}</div>
            <div className="muted" style={{ fontSize: 12 }}>
              {commitmentLabel(profile.approvals?.commitment_summary)}
            </div>
            <div className="muted" style={{ fontSize: 12 }}>
              {profile.approvals?.pending_approvals ?? 0} pending approvals
            </div>
            <div className="muted" style={{ fontSize: 12 }}>
              {profile.approvals?.decisions_count ?? 0} decisions
            </div>
          </div>
          <div className="section-card">
            <div className="muted" style={{ fontSize: 11 }}>Latest runs</div>
            <div>{latestRunLabel(profile.latest_runs?.[0])}</div>
            <div className="muted" style={{ fontSize: 12 }}>
              {(profile.latest_runs || []).slice(1, 3).map((run) => run.run_id).filter(Boolean).join(' · ') || '—'}
            </div>
          </div>
          <div className="section-card">
            <div className="muted" style={{ fontSize: 11 }}>Reflection status</div>
            <div>{profile.reflection_status?.status || 'unknown'}</div>
            <div className="muted" style={{ fontSize: 12 }}>
              {profile.reflection_status?.summary || '—'}
            </div>
          </div>
        </div>
      </section>
      {!!entity.assigned_social_accounts?.length && (
        <section style={{ marginBottom: 24 }}>
          <h2 style={{ fontSize: 18, marginBottom: 8 }}>Assigned accounts</h2>
          <div style={{ display: 'grid', gap: 12 }}>
            {entity.assigned_social_accounts.map((account) => (
              <div key={account.social_account_id || account.account_alias} style={{ background: 'var(--panel-2)', padding: 12, borderRadius: 4 }}>
                <div style={{ fontWeight: 600 }}>{account.account_alias || account.social_account_id}</div>
                <div style={{ color: 'var(--muted)', fontSize: 13, marginTop: 4 }}>
                  {account.platform || entity.platform || 'unknown platform'} · state {account.state || 'unknown'}
                </div>
                <div style={{ marginTop: 8 }}>{proofLabel(account.proof_summary)}</div>
                <div style={{ marginTop: 8 }}>{readinessLabel(account.readiness_summary)}</div>
                <div style={{ color: 'var(--muted)', fontSize: 13, marginTop: 4 }}>
                  {(account.readiness_summary?.blocking || []).join(', ') || 'no blockers'}
                </div>
                <div style={{ color: 'var(--muted)', fontSize: 13, marginTop: 4 }}>
                  {account.proof_summary?.latest_handle || account.proof_summary?.latest_url || 'no handle/url'}
                </div>
                <div style={{ marginTop: 8 }}>{continuityLabel(account.continuity_summary)}</div>
                <div style={{ color: 'var(--muted)', fontSize: 13, marginTop: 4 }}>
                  {account.continuity_summary?.browser_session_id || 'no browser session'}
                </div>
                <div style={{ marginTop: 8 }}>{continuityInjuryLabel(account.continuity_injury_summary)}</div>
                <div style={{ color: 'var(--muted)', fontSize: 13, marginTop: 4 }}>
                  {account.continuity_injury_summary?.last_repair_at
                    ? `repaired ${account.continuity_injury_summary.last_repair_at}`
                    : (account.continuity_injury_summary?.last_injury_reason || 'no recorded injury')}
                </div>
                <div style={{ marginTop: 8 }}>{notificationLabel(account.notification_summary)}</div>
                <div style={{ color: 'var(--muted)', fontSize: 13, marginTop: 4 }}>
                  {account.notification_summary?.latest?.message || 'no recent operator-facing notification'}
                </div>
                <div style={{ marginTop: 8 }}>{lastActivityLabel(account.last_activity_summary)}</div>
                <div style={{ color: 'var(--muted)', fontSize: 13, marginTop: 4 }}>
                  {account.last_activity_summary?.last_seen_at || 'no recent timestamp'}
                </div>
                <div style={{ color: 'var(--muted)', fontSize: 13, marginTop: 4 }}>
                  {account.last_activity_summary?.last_seen_detail || 'no recent detail'}
                </div>
                {account.continuity_summary?.degraded_reason ? (
                  <div style={{ color: 'var(--muted)', fontSize: 13, marginTop: 4 }}>
                    {account.continuity_summary.degraded_reason}
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        </section>
      )}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 18, marginBottom: 8 }}>Research deliveries</h2>
        {!(entity.research_delivery_summary?.recent_deliveries || []).length ? (
          <p style={{ color: 'var(--muted)' }}>No requester-bound research deliveries recorded for this entity yet.</p>
        ) : (
          <div style={{ display: 'grid', gap: 12 }}>
            {(entity.research_delivery_summary?.recent_deliveries || []).map((delivery, idx) => (
              <div key={`${delivery.file_path || delivery.topic || 'delivery'}-${idx}`} style={{ background: 'var(--panel-2)', padding: 12, borderRadius: 4 }}>
                <div style={{ fontWeight: 600 }}>{delivery.topic || 'Untitled delivery'}</div>
                <div style={{ color: 'var(--muted)', fontSize: 13, marginTop: 4 }}>
                  {delivery.file_path || 'no file path'} · {delivery.delivered_at || 'unknown delivery time'}
                </div>
                {delivery.summary ? (
                  <div style={{ marginTop: 8, color: 'var(--muted)', fontSize: 13 }}>{delivery.summary}</div>
                ) : null}
              </div>
            ))}
          </div>
        )}
      </section>
      {graph && (
        <section style={{ marginBottom: 24 }}>
          <h2 style={{ fontSize: 18, marginBottom: 8 }}>Entity graph</h2>
          {(graph.entities?.length > 0 || graph.facts?.length > 0) ? (
            <>
              {graph.entities?.length > 0 && (
                <>
                  <h3 style={{ fontSize: 14, marginTop: 12 }}>Entities ({graph.entities.length})</h3>
                  <table cellPadding="8" style={{ borderCollapse: 'collapse', width: '100%' }}>
                    <thead>
                      <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
                        <th>Name</th><th>Type</th><th>Summary</th>
                      </tr>
                    </thead>
                    <tbody>
                      {graph.entities.map((e) => (
                        <tr key={e.id} style={{ borderBottom: '1px solid var(--border)' }}>
                          <td>{e.name}</td>
                          <td>{e.type}</td>
                          <td>{e.summary_excerpt ? String(e.summary_excerpt).slice(0, 80) + (e.summary_excerpt.length > 80 ? '…' : '') : '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              )}
              {graph.facts?.length > 0 && (
                <>
                  <h3 style={{ fontSize: 14, marginTop: 12 }}>Facts (up to 500)</h3>
                  <table cellPadding="8" style={{ borderCollapse: 'collapse', width: '100%' }}>
                    <thead>
                      <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
                        <th>Entity</th><th>Fact</th><th>Category</th>
                      </tr>
                    </thead>
                    <tbody>
                      {graph.facts.map((f) => (
                        <tr key={f.id} style={{ borderBottom: '1px solid var(--border)' }}>
                          <td>{f.entity_name}</td>
                          <td>{String(f.fact).slice(0, 120)}{f.fact?.length > 120 ? '…' : ''}</td>
                          <td>{f.category || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              )}
            </>
          ) : (
            <p>No entity graph data (agent_memory.db missing or empty).</p>
          )}
        </section>
      )}
      {entity.persona_dir && persona && (
        <section style={{ marginBottom: 24 }}>
          <h2 style={{ fontSize: 18, marginBottom: 8 }}>Persona</h2>
          <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
            {['soul', 'heart', 'identity'].map((tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => setPersonaTab(tab)}
                style={{ fontWeight: personaTab === tab ? 'bold' : 'normal' }}
              >
                {tab === 'soul' ? 'SOUL' : tab === 'heart' ? 'HEART' : 'IDENTITY'}
              </button>
            ))}
          </div>
          <pre style={{ whiteSpace: 'pre-wrap', background: 'var(--panel-2)', padding: 12, borderRadius: 4, maxHeight: 300, overflow: 'auto' }}>
            {persona[personaTab] || '(empty)'}
          </pre>
        </section>
      )}
    </Layout>
  )
}


