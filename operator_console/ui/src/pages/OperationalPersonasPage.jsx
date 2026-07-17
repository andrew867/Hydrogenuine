import React, { useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import { api } from '../lib/api.js'
import StateNotice from '../components/StateNotice.jsx'

function formatTimestamp(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString()
}

function memoryHealthLabel(health) {
  const status = health?.status
  if (status === 'healthy') return 'Healthy'
  if (status === 'partial') return 'Partial'
  return 'Missing'
}

function proofLabel(summary) {
  if (!summary || !summary.artifact_count) return 'No proof'
  return `${summary.latest_artifact_type || 'proof'} | ${summary.artifact_count}`
}

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
  if (status === 'active') return 'Injured'
  if (status === 'recovered') return 'Recovered'
  if (status === 'none') return 'Clean'
  return '—'
}

function readinessLabel(summary) {
  if (!summary) return 'Readiness unknown'
  return summary.ready ? 'Ready' : 'Blocked'
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
  const reflection = profile.reflection_status?.status || 'unknown'
  const runs = overview.latest_run_count ?? 0
  return `${runs} run${runs === 1 ? '' : 's'} · memory ${memory.status || 'unknown'} · continuity ${continuity} · view ${continuityView} · reflection ${reflection}`
}

function identityContinuityLabel(summary) {
  const status = summary?.status
  if (status === 'healthy') return 'Healthy'
  if (status === 'partial') return 'Partial'
  if (status === 'missing') return 'Missing'
  return 'Unknown'
}

function continuityIncidentLabel(summary) {
  const status = summary?.status
  if (status === 'active') return 'Incident active'
  if (status === 'recovered') return 'Recovered'
  if (status === 'clean') return 'Clean'
  return 'Unknown'
}

function continuityRecoveryReadinessLabel(summary) {
  const status = summary?.status
  if (status === 'blocked') return 'Blocked'
  if (status === 'caution') return 'Caution'
  if (status === 'ready') return 'Ready'
  return 'Unknown'
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
  if (mode === 'scheduled_only') return 'Scheduled'
  return 'Unknown'
}

function affectActionLabel(summary) {
  if (!summary || summary.status === 'missing') return 'Unavailable'
  const arc = summary?.action_state?.dominant_arc_state || 'arc?'
  const mode = summary?.action_state?.dominant_engagement_mode || 'mode?'
  const trust = summary?.affective_state?.trust_band
  return trust == null ? `${arc} / ${mode}` : `${arc} / ${mode} / trust ${trust}`
}

function selfModelLabel(summary) {
  if (!summary || summary.status !== 'healthy') return 'Unavailable'
  return `${summary.dominant_arc_state || 'arc?'} / ${summary.dominant_engagement_mode || 'mode?'}`
}

function confidenceLabel(summary) {
  if (!summary || (!summary.confidence_level && summary.confidence_score == null)) return 'Unavailable'
  return `${summary.confidence_level || 'uncertain'} / ${summary.confidence_score ?? 0}/100`
}

function relationshipLabel(summary) {
  if (!summary || summary.status !== 'healthy') return 'Unavailable'
  return `${summary.dominant_relationship_type || 'relationship?'} / ${summary.recent_counterpart_count || 0}`
}

function crewDynamicsLabel(summary) {
  if (!summary || summary.status === 'missing') return 'Unavailable'
  const style = summary.coordination_style || 'unknown'
  const members = summary.swarm_member_count ?? 0
  return `${style} / ${members} member${members === 1 ? '' : 's'}`
}

function rationaleLabel(summary) {
  if (!summary || !summary.current_trigger) return 'Unavailable'
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

function agencyModeLabel(summary) {
  const mode = summary?.effective_mode || summary?.mode
  if (mode === 'held') return 'Held'
  if (mode === 'review_only') return 'Review only'
  if (mode === 'normal') return 'Normal'
  return 'Unknown'
}

function outboundBudgetLabel(summary) {
  if (!summary) return 'No outbound budget'
  if (summary.daily_outbound_budget == null) return 'No outbound budget'
  const recent = summary.recent_outbound_action_count ?? 0
  const budget = summary.daily_outbound_budget
  const windowHours = summary.outbound_actions_window_hours ?? 24
  const remaining = summary.outbound_budget_remaining ?? Math.max(0, budget - recent)
  const status = summary.outbound_budget_exhausted ? 'exhausted' : `${remaining} left`
  return `${recent}/${budget} in ${windowHours}h · ${status}`
}

function socialPostureLabel(summary) {
  if (!summary) return 'Unknown'
  const posture = summary.posture || 'unknown'
  const mode = summary.effective_mode || 'normal'
  return `${posture} / ${mode}`
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

export default function OperationalPersonasPage() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState('')
  const [agencyDrafts, setAgencyDrafts] = useState({})
  const [agencySaving, setAgencySaving] = useState({})
  const [refreshingApprovalId, setRefreshingApprovalId] = useState(null)
  const [acknowledgingRecoveryId, setAcknowledgingRecoveryId] = useState(null)
  const [recordingRebuildId, setRecordingRebuildId] = useState(null)
  const [verifyingRebuildId, setVerifyingRebuildId] = useState(null)
  const [approvingResumeId, setApprovingResumeId] = useState(null)

  const load = () => {
    setLoading(true)
    setErr('')
    api.getOperationalPersonas()
      .then((res) => setItems(res.items || []))
      .catch((e) => setErr(String(e)))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [])

  const ensureAgencyDraft = (item) => {
    const key = item.id
    if (agencyDrafts[key]) return agencyDrafts[key]
    return {
      mode: item.agency_control_summary?.mode || 'normal',
      reason: item.agency_control_summary?.reason || '',
      updated_by: 'operator',
      outbound_lane_policy: item.agency_control_summary?.outbound_lane_policy || 'unrestricted',
      daily_outbound_budget: item.agency_control_summary?.daily_outbound_budget ?? '',
      outbound_actions_window_hours: item.agency_control_summary?.outbound_actions_window_hours ?? 24,
    }
  }

  const updateAgencyDraft = (item, patch) => {
    const key = item.id
    setAgencyDrafts((current) => ({
      ...current,
      [key]: {
        ...ensureAgencyDraft(item),
        ...current[key],
        ...patch,
      },
    }))
  }

  const saveAgencyControl = async (item) => {
    const key = item.id
    const draft = ensureAgencyDraft(item)
    const payload = {
      ...draft,
      daily_outbound_budget: draft.daily_outbound_budget === '' ? null : draft.daily_outbound_budget,
      outbound_actions_window_hours: draft.outbound_actions_window_hours === '' ? 24 : draft.outbound_actions_window_hours,
    }
    setAgencySaving((current) => ({ ...current, [key]: true }))
    setErr('')
    try {
      await api.patchOperationalAgencyControl(item.platform, item.operational_agent_id, payload)
      load()
    } catch (e) {
      setErr(String(e))
    } finally {
      setAgencySaving((current) => ({ ...current, [key]: false }))
    }
  }

  const refreshReviewHandoff = async (item) => {
    const approvalId = item?.review_handoff_summary?.latest?.approval_id
    if (!approvalId) return
    setRefreshingApprovalId(approvalId)
    setErr('')
    try {
      await api.refreshEntityApprovalRequest(approvalId, {
        note: refreshNote(item?.review_handoff_summary?.refresh_reasons || [], 'refreshed from operational identities surface'),
        decided_by: 'operator_console',
        refresh_reason_codes: item?.review_handoff_summary?.refresh_reasons || [],
      })
      load()
    } catch (e) {
      setErr(String(e))
    } finally {
      setRefreshingApprovalId(null)
    }
  }

  const acknowledgeContinuityRecovery = async (item) => {
    setAcknowledgingRecoveryId(item.id)
    setErr('')
    try {
      await api.acknowledgeOperationalContinuityRecovery(item.platform, item.operational_agent_id, {
        acknowledged_by: 'operator_console',
        note: 'operator reviewed recent continuity repair and is allowing bounded resume',
      })
      load()
    } catch (e) {
      setErr(String(e))
    } finally {
      setAcknowledgingRecoveryId(null)
    }
  }

  const recordPostRebuild = async (item) => {
    setRecordingRebuildId(item.id)
    setErr('')
    try {
      await api.recordOperationalPostRebuild(item.platform, item.operational_agent_id, {
        recorded_by: 'operator_console',
        note: 'operator recorded post-rebuild verification requirement',
      })
      load()
    } catch (e) {
      setErr(String(e))
    } finally {
      setRecordingRebuildId(null)
    }
  }

  const verifyPostRebuild = async (item) => {
    setVerifyingRebuildId(item.id)
    setErr('')
    try {
      await api.verifyOperationalPostRebuild(item.platform, item.operational_agent_id, {
        verified_by: 'operator_console',
        note: 'operator verified post-rebuild continuity state',
      })
      load()
    } catch (e) {
      setErr(String(e))
    } finally {
      setVerifyingRebuildId(null)
    }
  }

  const approveOperationalResume = async (item) => {
    setApprovingResumeId(item.id)
    setErr('')
    try {
      await api.approveOperationalResumeCheckpoint(item.platform, item.operational_agent_id, {
        approved_by: 'operator_console',
        note: 'operator approved stack-level resume after checks',
      })
      load()
    } catch (e) {
      setErr(String(e))
    } finally {
      setApprovingResumeId(null)
    }
  }

  return (
    <Layout title="Operational identities">
      {err && <StateNotice tone="danger" title="Could not load operational identities" detail={err} action={<button type="button" onClick={load}>Retry</button>} />}
      <p style={{ color: 'var(--muted)' }}>
        Platform-scoped operational bindings for reusable posting identities. This is the continuity layer that ties
        platform jobs to a shared fingerprint, memory namespace, and approval posture.
      </p>
      {!loading && !err && (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, gap: 12, flexWrap: 'wrap' }}>
          <p style={{ margin: 0, color: 'var(--muted)' }}>
            {items.length} operational identities with linked task, namespace, and approval context.
          </p>
          <button type="button" onClick={load}>Refresh</button>
        </div>
      )}
      {loading ? (
        <StateNotice title="Loading operational identities" detail="Reading persona configs and workflow approval bindings." />
      ) : items.length === 0 ? (
        <StateNotice title="No operational identities" detail="No operational bindings were discovered from the job registry." />
      ) : (
        <div style={{ display: 'grid', gap: 16 }}>
          {items.map((item) => (
            <section key={item.id || `${item.platform}-${item.operational_agent_id || 'na'}`} className="card" style={{ padding: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}>
                <div>
                  <h2 style={{ margin: '0 0 6px 0' }}>{item.display_name || item.platform}</h2>
                  <div style={{ color: 'var(--muted)', fontSize: 13 }}>
                    {item.fingerprint_name || item.fingerprint_id || 'No fingerprint bound'}{item.fingerprint_type ? ` · ${item.fingerprint_type}` : ''}{item.skin_id ? ` · skin ${item.skin_id}` : ''}
                  </div>
                </div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  approval posture: {item.approval_posture || (item.approval_modes || []).join(', ') || 'unknown'}
                </div>
              </div>
              <div style={{ marginTop: 12, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 10 }}>
                <div className="section-card">
                  <div className="muted" style={{ fontSize: 11 }}>Profile</div>
                  <div>{profileSummaryLabel(item.profile)}</div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {item.profile?.overview?.latest_run_id || 'no recent run'}
                  </div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {item.profile?.reflection_status?.summary || 'reflection status unavailable'}
                  </div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {item.profile?.continuity_view?.summary || 'no continuity view'}
                  </div>
                </div>
                <div className="section-card">
                  <div className="muted" style={{ fontSize: 11 }}>Latest linked-task activity</div>
                  <div>{formatTimestamp(item.latest_task_activity)}</div>
                </div>
                <div className="section-card">
                  <div className="muted" style={{ fontSize: 11 }}>Pending approvals</div>
                  <div>{item.pending_approvals ?? 0}</div>
                </div>
                <div className="section-card">
                  <div className="muted" style={{ fontSize: 11 }}>Memory health</div>
                  <div>{memoryHealthLabel(item.memory_health)}</div>
                </div>
                <div className="section-card">
                  <div className="muted" style={{ fontSize: 11 }}>Last wake</div>
                  <div>{formatTimestamp(item.last_wake_at)}</div>
                </div>
                <div className="section-card">
                  <div className="muted" style={{ fontSize: 11 }}>Last sleep</div>
                  <div>{formatTimestamp(item.last_sleep_at)}</div>
                </div>
                <div className="section-card">
                  <div className="muted" style={{ fontSize: 11 }}>Last meditation</div>
                  <div>{formatTimestamp(item.last_meditation_at)}</div>
                </div>
                <div className="section-card">
                  <div className="muted" style={{ fontSize: 11 }}>Research deliveries</div>
                  <div>{researchDeliveryLabel(item.research_delivery_summary)}</div>
                </div>
                <div className="section-card">
                  <div className="muted" style={{ fontSize: 11 }}>Commitments</div>
                  <div>{commitmentLabel(item.commitment_summary)}</div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {item.commitment_summary?.latest_commitment?.title || '—'}
                  </div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {item.commitment_summary?.latest_commitment?.due_at || '—'}
                  </div>
                </div>
                <div className="section-card">
                  <div className="muted" style={{ fontSize: 11 }}>Identity continuity</div>
                  <div>{identityContinuityLabel(item.identity_continuity_summary)}</div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {item.identity_continuity_summary?.continuity_anchor || '—'}
                  </div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {continuityIncidentLabel(item.continuity_incident_summary)}
                    {item.continuity_incident_summary?.latest_event_detail ? ` · ${item.continuity_incident_summary.latest_event_detail}` : ''}
                  </div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {continuityRecoveryReadinessLabel(item.continuity_recovery_readiness)}
                    {((item.continuity_recovery_readiness?.blocking || []).length || (item.continuity_recovery_readiness?.cautions || []).length)
                      ? ` · ${[...(item.continuity_recovery_readiness?.blocking || []), ...(item.continuity_recovery_readiness?.cautions || [])].join(', ')}`
                      : ' · no recovery blockers'}
                  </div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {item.continuity_recovery_readiness?.acknowledged
                      ? `acknowledged by ${item.continuity_recovery_readiness.acknowledged_by || 'operator'}`
                      : 'not acknowledged'}
                  </div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {(item.continuity_repair_plan?.open_checks || []).join(', ') || 'repair plan clear'}
                  </div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {postRebuildCheckLabel(item.post_rebuild_continuity_check)}
                    {item.post_rebuild_continuity_check?.rebuild_recorded_at ? ` · rebuild ${item.post_rebuild_continuity_check.rebuild_recorded_at}` : ''}
                    {item.post_rebuild_continuity_check?.verified_at ? ` · verified ${item.post_rebuild_continuity_check.verified_at}` : ''}
                  </div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {operationalResumeLabel(item.operational_resume_governance_summary)}
                    {item.operational_resume_governance_summary?.required_actions?.length
                      ? ` · ${item.operational_resume_governance_summary.required_actions.join(', ')}`
                      : ' · no outstanding stack actions'}
                  </div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {operationalResumeCheckpointLabel(item.operational_resume_checkpoint)}
                    {item.operational_resume_checkpoint?.approved_at ? ` · ${item.operational_resume_checkpoint.approved_at}` : ''}
                  </div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {item.continuity_repair_observation?.observation_required
                      ? `repair observation: ${item.continuity_repair_observation.status}${item.continuity_repair_observation.latest_observed_at ? ` · ${item.continuity_repair_observation.latest_observed_at}` : ''}`
                      : 'repair observation not required'}
                  </div>
                  <div className="muted" style={{ fontSize: 12 }}>
                  {item.identity_resume_procedure?.open_steps?.length
                      ? `identity resume: ${item.identity_resume_procedure.open_steps.join(', ')}`
                      : 'identity resume ready'}
                  </div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {item.profile?.continuity_view?.since_last_wake?.summary || 'no wake summary'}
                  </div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {(item.profile?.continuity_view?.conflicts || []).join(', ') || 'no continuity conflicts'}
                  </div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {(item.profile?.continuity_view?.scheduled_work || []).join(', ') || 'no scheduled continuity work'}
                  </div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {item.profile?.continuity_view?.steering?.agent_id
                      ? `steering ${item.profile.continuity_view.steering.agent_id}${item.profile.continuity_view.steering.version ? ` v${item.profile.continuity_view.steering.version}` : ''}${item.profile.continuity_view.steering.changed_since_last_wake ? ' · changed since wake' : ''}`
                      : 'no steering profile'}
                  </div>
                  {item.continuity_recovery_readiness?.can_acknowledge && !item.continuity_recovery_readiness?.acknowledged ? (
                    <div style={{ marginTop: 6 }}>
                      <button
                        type="button"
                        onClick={() => acknowledgeContinuityRecovery(item)}
                        disabled={acknowledgingRecoveryId === item.id}
                      >
                        {acknowledgingRecoveryId === item.id ? 'Acknowledging…' : 'Acknowledge recovery'}
                      </button>
                    </div>
                  ) : null}
                  {!item.post_rebuild_continuity_check?.verification_required ? (
                    <div style={{ marginTop: 6 }}>
                      <button
                        type="button"
                        onClick={() => recordPostRebuild(item)}
                        disabled={recordingRebuildId === item.id}
                      >
                        {recordingRebuildId === item.id ? 'Recording rebuild…' : 'Record rebuild'}
                      </button>
                    </div>
                  ) : null}
                  {item.post_rebuild_continuity_check?.verification_required && !item.post_rebuild_continuity_check?.verified ? (
                    <div style={{ marginTop: 6 }}>
                      <button
                        type="button"
                        onClick={() => verifyPostRebuild(item)}
                        disabled={verifyingRebuildId === item.id || item.post_rebuild_continuity_check?.status === 'blocked'}
                      >
                        {verifyingRebuildId === item.id ? 'Verifying rebuild…' : 'Verify rebuild'}
                      </button>
                    </div>
                  ) : null}
                  {item.operational_resume_governance_summary?.resume_ready && !item.operational_resume_checkpoint?.approved ? (
                    <div style={{ marginTop: 6 }}>
                      <button
                        type="button"
                        onClick={() => approveOperationalResume(item)}
                        disabled={approvingResumeId === item.id}
                      >
                        {approvingResumeId === item.id ? 'Approving resume…' : 'Approve resume'}
                      </button>
                    </div>
                  ) : null}
                </div>
                <div className="section-card">
                  <div className="muted" style={{ fontSize: 11 }}>Presence / initiative</div>
                  <div>{presenceLabel(item.presence_initiative_summary)}</div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {item.presence_initiative_summary?.next_earliest_wake_at || '—'}
                  </div>
                </div>
                <div className="section-card">
                  <div className="muted" style={{ fontSize: 11 }}>Affect / action</div>
                  <div>{affectActionLabel(item.affect_action_summary)}</div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    trust {item.affect_action_summary?.affective_state?.trust_band ?? '—'} · budget {item.affect_action_summary?.affective_state?.agency_budget ?? '—'}
                  </div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {item.affect_action_summary?.latest_turn?.engagement_mode || '—'}
                    {item.affect_action_summary?.latest_turn?.relationship_type ? ` · ${item.affect_action_summary.latest_turn.relationship_type}` : ''}
                  </div>
                </div>
                <div className="section-card">
                  <div className="muted" style={{ fontSize: 11 }}>Agency control</div>
                  <div>{agencyModeLabel(item.agency_control_summary)}</div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {item.agency_control_summary?.reason || 'no operator override reason'}
                  </div>
                </div>
                <div className="section-card">
                  <div className="muted" style={{ fontSize: 11 }}>Outbound budget</div>
                  <div>{outboundBudgetLabel(item.agency_control_summary)}</div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    policy {item.agency_control_summary?.outbound_lane_policy || 'unrestricted'}
                  </div>
                </div>
                <div className="section-card">
                  <div className="muted" style={{ fontSize: 11 }}>Social posture</div>
                  <div>{socialPostureLabel(item.social_posture_summary)}</div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {item.social_posture_summary?.relationship_orientation || '—'}
                  </div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {item.social_posture_summary?.reply_bias || '—'}
                  </div>
                </div>
                <div className="section-card">
                  <div className="muted" style={{ fontSize: 11 }}>Self-model</div>
                  <div>{selfModelLabel(item.self_model_summary)}</div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {item.self_model_summary?.dominant_uncertainty || '—'}
                  </div>
                </div>
                <div className="section-card">
                  <div className="muted" style={{ fontSize: 11 }}>Confidence</div>
                  <div>{confidenceLabel(item.confidence_summary)}</div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {item.confidence_summary?.summary || '—'}
                  </div>
                </div>
                <div className="section-card">
                  <div className="muted" style={{ fontSize: 11 }}>Relationship memory</div>
                  <div>{relationshipLabel(item.relationship_memory_summary)}</div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {item.relationship_memory_summary?.top_counterparts?.[0]?.counterpart_fingerprint_id || '—'}
                  </div>
                </div>
                <div className="section-card">
                  <div className="muted" style={{ fontSize: 11 }}>Crew dynamics</div>
                  <div>{crewDynamicsLabel(item.crew_dynamics_summary)}</div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {item.crew_dynamics_summary?.workflow_id || '—'}
                  </div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {item.crew_dynamics_summary?.swarm_run_id || 'no swarm'}
                  </div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {item.crew_dynamics_summary?.coordination_style_source || '—'}
                  </div>
                </div>
                <div className="section-card">
                  <div className="muted" style={{ fontSize: 11 }}>Why acting now</div>
                  <div>{rationaleLabel(item.action_rationale_summary)}</div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {item.action_rationale_summary?.reason_chain?.[0] || '—'}
                  </div>
                </div>
                <div className="section-card">
                  <div className="muted" style={{ fontSize: 11 }}>Review handoff</div>
                  <div>{reviewHandoffLabel(item.review_handoff_summary)}</div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {item.review_handoff_summary?.latest?.approval_href ? (
                      <a href={item.review_handoff_summary.latest.approval_href}>{item.review_handoff_summary?.latest?.approval_id || 'open approval'}</a>
                    ) : (
                      item.review_handoff_summary?.latest?.approval_id || '—'
                    )}
                  </div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {item.review_handoff_summary?.latest?.status || '—'}{item.review_handoff_summary?.latest?.decision_note ? ` · ${item.review_handoff_summary.latest.decision_note}` : ''}
                  </div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {item.review_handoff_summary?.release_ready ? 'releasable now' : ((item.review_handoff_summary?.release_blockers || []).join(', ') || '—')}
                  </div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {item.review_handoff_summary?.latest?.latest_release_attempt
                      ? `last release: ${item.review_handoff_summary.latest.latest_release_attempt.status || 'unknown'}${item.review_handoff_summary.latest.latest_release_attempt.reason ? ` · ${item.review_handoff_summary.latest.latest_release_attempt.reason}` : ''}`
                      : 'last release: —'}
                  </div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {item.review_handoff_summary?.refresh_recommended
                      ? `refresh suggested · ${(item.review_handoff_summary?.refresh_reasons || []).join(', ')}`
                      : 'refresh suggested: no'}
                  </div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {item.review_handoff_summary?.latest?.refreshed_from_approval_id
                      ? `refreshed from ${item.review_handoff_summary.latest.refreshed_from_approval_id}${item.review_handoff_summary?.latest?.refresh_note ? ` · ${item.review_handoff_summary.latest.refresh_note}` : ''}${item.review_handoff_summary?.latest?.refresh_reason_codes?.length ? ` · ${item.review_handoff_summary.latest.refresh_reason_codes.join(', ')}` : ''}`
                      : 'refresh lineage: —'}
                  </div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {item.review_handoff_summary?.latest?.resolution_context?.rationale
                      ? `rationale: ${item.review_handoff_summary.latest.resolution_context.rationale}`
                      : 'rationale: —'}
                  </div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {item.review_handoff_summary?.latest?.resolution_context?.release_scope
                      ? `scope: ${item.review_handoff_summary.latest.resolution_context.release_scope}`
                      : 'scope: —'}
                  </div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {item.review_handoff_summary?.latest?.resolution_context?.followup_expectation
                      ? `follow-up: ${item.review_handoff_summary.latest.resolution_context.followup_expectation}`
                      : 'follow-up: —'}
                  </div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {item.review_handoff_summary?.latest?.followup_summary?.window_hours
                      ? `follow-up window: ${item.review_handoff_summary.latest.followup_summary.window_hours}h`
                      : 'follow-up window: —'}
                  </div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {item.review_handoff_summary?.latest?.followup_summary?.expected
                      ? `follow-up status: ${item.review_handoff_summary.latest.followup_summary.status}${item.review_handoff_summary?.latest?.followup_summary?.due_at ? ` · due ${item.review_handoff_summary.latest.followup_summary.due_at}` : ''}${item.review_handoff_summary?.latest?.followup_summary?.observation_detail ? ` · ${item.review_handoff_summary.latest.followup_summary.observation_detail}` : ''}`
                      : 'follow-up status: —'}
                  </div>
                  {item.review_handoff_summary?.refresh_recommended && item.review_handoff_summary?.latest?.approval_id ? (
                    <div style={{ marginTop: 6 }}>
                      <button
                        type="button"
                        onClick={() => refreshReviewHandoff(item)}
                        disabled={refreshingApprovalId === item.review_handoff_summary.latest.approval_id}
                      >
                        {refreshingApprovalId === item.review_handoff_summary.latest.approval_id ? 'Refreshing…' : 'Refresh handoff'}
                      </button>
                    </div>
                  ) : null}
                </div>
              </div>
              <div style={{ overflowX: 'auto', maxWidth: '100%', marginTop: 12 }}>
              <table style={{ width: '100%', minWidth: 760 }}>
                <tbody>
                  <tr><td><strong>persona_set</strong></td><td><code>{item.persona_set}</code></td></tr>
                  <tr><td><strong>operational_agent_id</strong></td><td><code>{item.operational_agent_id || '—'}</code></td></tr>
                  <tr><td><strong>operational_family</strong></td><td><code>{item.operational_family || '—'}</code></td></tr>
                  <tr><td><strong>fingerprint_id</strong></td><td><code>{item.fingerprint_id || '—'}</code></td></tr>
                  <tr><td><strong>session_target</strong></td><td><code>{item.operational_session_target || '—'}</code></td></tr>
                  <tr><td><strong>memory_namespace</strong></td><td><code>{item.memory_namespace || '—'}</code></td></tr>
                  <tr><td><strong>knowledge_namespace</strong></td><td><code>{item.knowledge_namespace || '—'}</code></td></tr>
                  <tr><td><strong>initialization_memo</strong></td><td><code>{item.identity_continuity_summary?.initialization_memo_path || '—'}</code></td></tr>
                  <tr><td><strong>continuity_recovery</strong></td><td><code>{item.continuity_recovery_readiness?.status || '—'}</code></td></tr>
                  <tr><td><strong>continuity_recovery_acknowledged</strong></td><td><code>{String(!!item.continuity_recovery_readiness?.acknowledged)}</code></td></tr>
                  <tr><td><strong>continuity_recovery_ack_by</strong></td><td><code>{item.continuity_recovery_readiness?.acknowledged_by || '—'}</code></td></tr>
                  <tr><td><strong>continuity_repair_plan</strong></td><td><code>{item.continuity_repair_plan?.status || '—'}</code></td></tr>
                  <tr><td><strong>continuity_repair_open_checks</strong></td><td><code>{(item.continuity_repair_plan?.open_checks || []).join(', ') || '—'}</code></td></tr>
                  <tr><td><strong>post_rebuild_check</strong></td><td><code>{item.post_rebuild_continuity_check?.status || '—'}</code></td></tr>
                  <tr><td><strong>post_rebuild_recorded_at</strong></td><td><code>{item.post_rebuild_continuity_check?.rebuild_recorded_at || '—'}</code></td></tr>
                  <tr><td><strong>post_rebuild_verified_at</strong></td><td><code>{item.post_rebuild_continuity_check?.verified_at || '—'}</code></td></tr>
                  <tr><td><strong>operational_resume_governance</strong></td><td><code>{item.operational_resume_governance_summary?.status || '—'}</code></td></tr>
                  <tr><td><strong>operational_resume_required_actions</strong></td><td><code>{(item.operational_resume_governance_summary?.required_actions || []).join(', ') || '—'}</code></td></tr>
                  <tr><td><strong>operational_resume_checkpoint</strong></td><td><code>{item.operational_resume_checkpoint?.approved ? 'approved' : 'not approved'}</code></td></tr>
                  <tr><td><strong>operational_resume_checkpoint_at</strong></td><td><code>{item.operational_resume_checkpoint?.approved_at || '—'}</code></td></tr>
                  <tr><td><strong>continuity_repair_observation</strong></td><td><code>{item.continuity_repair_observation?.observation_required ? `${item.continuity_repair_observation.status}${item.continuity_repair_observation.latest_observed_at ? ` | ${item.continuity_repair_observation.latest_observed_at}` : ''}` : 'not required'}</code></td></tr>
                  <tr><td><strong>identity_resume_procedure</strong></td><td><code>{item.identity_resume_procedure?.status || '—'}</code></td></tr>
                  <tr><td><strong>identity_resume_open_steps</strong></td><td><code>{(item.identity_resume_procedure?.open_steps || []).join(', ') || '—'}</code></td></tr>
                  <tr><td><strong>continuity_recovery_blocking</strong></td><td><code>{(item.continuity_recovery_readiness?.blocking || []).join(', ') || '—'}</code></td></tr>
                  <tr><td><strong>continuity_recovery_cautions</strong></td><td><code>{(item.continuity_recovery_readiness?.cautions || []).join(', ') || '—'}</code></td></tr>
                  <tr><td><strong>agency_budget</strong></td><td><code>{item.presence_initiative_summary?.agency_budget ?? '—'}</code></td></tr>
                  <tr><td><strong>trust_band</strong></td><td><code>{item.presence_initiative_summary?.trust_band ?? '—'}</code></td></tr>
                  <tr><td><strong>agency_mode</strong></td><td><code>{item.agency_control_summary?.effective_mode || 'normal'}</code></td></tr>
                  <tr><td><strong>outbound_lane_policy</strong></td><td><code>{item.agency_control_summary?.outbound_lane_policy || 'unrestricted'}</code></td></tr>
                  <tr><td><strong>daily_outbound_budget</strong></td><td><code>{item.agency_control_summary?.daily_outbound_budget ?? '—'}</code></td></tr>
                  <tr><td><strong>outbound_actions_window_hours</strong></td><td><code>{item.agency_control_summary?.outbound_actions_window_hours ?? '—'}</code></td></tr>
                  <tr><td><strong>recent_outbound_action_count</strong></td><td><code>{item.agency_control_summary?.recent_outbound_action_count ?? 0}</code></td></tr>
                  <tr><td><strong>outbound_budget_remaining</strong></td><td><code>{item.agency_control_summary?.outbound_budget_remaining ?? '—'}</code></td></tr>
                  <tr><td><strong>outbound_budget_exhausted</strong></td><td><code>{String(!!item.agency_control_summary?.outbound_budget_exhausted)}</code></td></tr>
                  <tr><td><strong>agency_reason</strong></td><td><code>{item.agency_control_summary?.reason || '—'}</code></td></tr>
                  <tr><td><strong>agency_updated_at</strong></td><td><code>{item.agency_control_summary?.updated_at || '—'}</code></td></tr>
                  <tr><td><strong>social_posture</strong></td><td><code>{item.social_posture_summary?.posture || '—'}</code></td></tr>
                  <tr><td><strong>reply_bias</strong></td><td><code>{item.social_posture_summary?.reply_bias || '—'}</code></td></tr>
                  <tr><td><strong>relationship_orientation</strong></td><td><code>{item.social_posture_summary?.relationship_orientation || '—'}</code></td></tr>
                  <tr><td><strong>relationship_signal</strong></td><td><code>{item.self_model_summary?.relationship_signal || '—'}</code></td></tr>
                  <tr><td><strong>callback_rate</strong></td><td><code>{item.self_model_summary?.callback_rate ?? '—'}</code></td></tr>
                  <tr><td><strong>confidence_level</strong></td><td><code>{item.confidence_summary?.confidence_level || '—'}</code></td></tr>
                  <tr><td><strong>confidence_score</strong></td><td><code>{item.confidence_summary?.confidence_score ?? '—'}</code></td></tr>
                  <tr><td><strong>top_counterpart</strong></td><td><code>{item.relationship_memory_summary?.top_counterparts?.[0]?.counterpart_fingerprint_id || '—'}</code></td></tr>
                  <tr><td><strong>crew_dynamics</strong></td><td><code>{crewDynamicsLabel(item.crew_dynamics_summary)}</code></td></tr>
                  <tr><td><strong>crew_workflow</strong></td><td><code>{item.crew_dynamics_summary?.workflow_id || '—'}</code></td></tr>
                  <tr><td><strong>crew_swarm</strong></td><td><code>{item.crew_dynamics_summary?.swarm_run_id || '—'}</code></td></tr>
                  <tr><td><strong>coordination_source</strong></td><td><code>{item.crew_dynamics_summary?.coordination_style_source || '—'}</code></td></tr>
                  <tr><td><strong>current_goal</strong></td><td><code>{item.action_rationale_summary?.current_goal || '—'}</code></td></tr>
                  <tr>
                    <td><strong>latest_review_approval</strong></td>
                    <td>
                      {item.review_handoff_summary?.latest?.approval_href ? (
                        <a href={item.review_handoff_summary.latest.approval_href}><code>{item.review_handoff_summary?.latest?.approval_id || 'open approval'}</code></a>
                      ) : (
                        <code>{item.review_handoff_summary?.latest?.approval_id || '—'}</code>
                      )}
                    </td>
                  </tr>
                  <tr><td><strong>catalog_path</strong></td><td><code>{item.fingerprint_path || '—'}</code></td></tr>
                  <tr>
                    <td><strong>memory namespace health</strong></td>
                    <td>
                      {memoryHealthLabel(item.memory_health)}
                      {' · '}
                      agent DBs {item.memory_health?.memory_db_present ?? 0}
                      {' · '}
                      summaries {item.memory_health?.summary_7d_present ?? 0}
                      {' · '}
                      decisions {item.memory_health?.decisions_present ?? 0}
                    </td>
                  </tr>
                </tbody>
              </table>
              </div>
              <div style={{ marginTop: 12 }}>
                <strong>agency control</strong>
                <div className="section-card" style={{ marginTop: 8 }}>
                  <div style={{ display: 'grid', gap: 8, gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))' }}>
                    <label>
                      <div className="muted" style={{ fontSize: 12, marginBottom: 4 }}>Mode</div>
                      <select
                        value={ensureAgencyDraft(item).mode}
                        onChange={(e) => updateAgencyDraft(item, { mode: e.target.value })}
                      >
                        <option value="normal">normal</option>
                        <option value="review_only">review_only</option>
                        <option value="held">held</option>
                      </select>
                    </label>
                    <label>
                      <div className="muted" style={{ fontSize: 12, marginBottom: 4 }}>Outbound lane policy</div>
                      <select
                        value={ensureAgencyDraft(item).outbound_lane_policy}
                        onChange={(e) => updateAgencyDraft(item, { outbound_lane_policy: e.target.value })}
                      >
                        <option value="unrestricted">unrestricted</option>
                        <option value="replies_only">replies_only</option>
                        <option value="drafts_only">drafts_only</option>
                        <option value="blocked">blocked</option>
                      </select>
                    </label>
                    <label>
                      <div className="muted" style={{ fontSize: 12, marginBottom: 4 }}>Updated by</div>
                      <input
                        value={ensureAgencyDraft(item).updated_by}
                        onChange={(e) => updateAgencyDraft(item, { updated_by: e.target.value })}
                        placeholder="operator"
                      />
                    </label>
                    <label>
                      <div className="muted" style={{ fontSize: 12, marginBottom: 4 }}>Daily outbound budget</div>
                      <input
                        type="number"
                        min="0"
                        value={ensureAgencyDraft(item).daily_outbound_budget}
                        onChange={(e) => updateAgencyDraft(item, { daily_outbound_budget: e.target.value === '' ? '' : Number(e.target.value) })}
                        placeholder="unlimited"
                      />
                    </label>
                    <label>
                      <div className="muted" style={{ fontSize: 12, marginBottom: 4 }}>Budget window hours</div>
                      <input
                        type="number"
                        min="1"
                        value={ensureAgencyDraft(item).outbound_actions_window_hours}
                        onChange={(e) => updateAgencyDraft(item, { outbound_actions_window_hours: e.target.value === '' ? 24 : Number(e.target.value) })}
                      />
                    </label>
                  </div>
                  <label style={{ display: 'block', marginTop: 8 }}>
                    <div className="muted" style={{ fontSize: 12, marginBottom: 4 }}>Reason</div>
                    <textarea
                      value={ensureAgencyDraft(item).reason}
                      onChange={(e) => updateAgencyDraft(item, { reason: e.target.value })}
                      rows={2}
                      placeholder="Why this lane is normal, review-only, or held"
                      style={{ width: '100%' }}
                    />
                  </label>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', marginTop: 8, alignItems: 'center' }}>
                    <div className="muted" style={{ fontSize: 12 }}>
                      Global gate {item.agency_control_summary?.global_outbound_safety_gate_enabled ? 'on' : 'off'} · DAG change control {item.agency_control_summary?.global_entity_dag_change_control || '—'}
                    </div>
                    <button type="button" onClick={() => saveAgencyControl(item)} disabled={!!agencySaving[item.id] || !item.operational_agent_id}>
                      {agencySaving[item.id] ? 'Saving…' : 'Save agency control'}
                    </button>
                  </div>
                </div>
              </div>
              <div style={{ marginTop: 12 }}>
                <strong>bound tasks</strong>
                <div style={{ display: 'grid', gap: 8, marginTop: 8 }}>
                  {(item.linked_tasks || []).map((task) => (
                    <div key={task.id} className="section-card" style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
                      <div>
                        <a href={task.entity_href}>{task.id}</a>
                        <div className="muted" style={{ fontSize: 12 }}>
                          session {task.session_target || '—'} · last activity {formatTimestamp(task.last_activity)}
                        </div>
                      </div>
                      <div className="muted" style={{ fontSize: 12 }}>
                        decisions {task.decisions_count ?? 0} · pending approvals {task.pending_approvals ?? 0}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              <div style={{ marginTop: 12 }}>
                <strong>jump links</strong>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, marginTop: 8 }}>
                  <a href={item.jump_links?.approvals || '#/approvals'}>Approvals</a>
                  <a href={item.jump_links?.runs || '#/'}>Runs</a>
                  <a href={item.jump_links?.activity || '#/activity'}>Activity</a>
                  <a href={item.jump_links?.knowledge || '#/knowledge'}>Knowledge</a>
                </div>
              </div>
              <div style={{ marginTop: 12 }}>
                <strong>research delivery</strong>
                {!(item.research_delivery_summary?.recent_deliveries || []).length ? (
                  <div className="muted" style={{ marginTop: 8 }}>No recent requester-bound research deliveries.</div>
                ) : (
                  <div style={{ display: 'grid', gap: 8, marginTop: 8 }}>
                    {(item.research_delivery_summary?.recent_deliveries || []).map((delivery, idx) => (
                      <div key={`${delivery.file_path || delivery.topic || 'delivery'}-${idx}`} className="section-card">
                        <div>{delivery.topic || 'Untitled delivery'}</div>
                        <div className="muted" style={{ fontSize: 12 }}>
                          {delivery.file_path || 'no file path'} · {formatTimestamp(delivery.delivered_at)}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <div style={{ marginTop: 12 }}>
                <strong>assigned accounts</strong>
                {!(item.assigned_social_accounts || []).length ? (
                  <div className="muted" style={{ marginTop: 8 }}>No assigned social accounts.</div>
                ) : (
                  <div style={{ display: 'grid', gap: 8, marginTop: 8 }}>
                    {(item.assigned_social_accounts || []).map((account) => (
                      <div key={account.social_account_id || account.account_alias} className="section-card" style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
                        <div>
                          <div>{account.account_alias || account.social_account_id}</div>
                          <div className="muted" style={{ fontSize: 12 }}>
                            {account.platform || item.platform} · state {account.state || 'unknown'}
                          </div>
                          <div className="muted" style={{ fontSize: 12, marginTop: 8 }}>
                            {readinessLabel(account.readiness_summary)}
                          </div>
                          <div className="muted" style={{ fontSize: 12 }}>
                            {(account.readiness_summary?.blocking || []).join(', ') || 'no blockers'}
                          </div>
                        </div>
                        <div style={{ textAlign: 'right' }}>
                          <div style={{ fontSize: 12 }}>{proofLabel(account.proof_summary)}</div>
                          <div className="muted" style={{ fontSize: 12 }}>
                            {account.proof_summary?.latest_handle || account.proof_summary?.latest_url || 'no handle/url'}
                          </div>
                          <div className="muted" style={{ fontSize: 12 }}>
                            {formatTimestamp(account.proof_summary?.latest_created_at)}
                          </div>
                          <div style={{ fontSize: 12, marginTop: 8 }}>{continuityLabel(account.continuity_summary)}</div>
                          <div className="muted" style={{ fontSize: 12 }}>
                            {account.continuity_summary?.browser_session_id || 'no browser session'}
                          </div>
                          <div className="muted" style={{ fontSize: 12 }}>
                            {continuityInjuryLabel(account.continuity_injury_summary)}
                            {account.continuity_injury_summary?.last_injury_reason ? ` · ${account.continuity_injury_summary.last_injury_reason}` : ''}
                          </div>
                          <div className="muted" style={{ fontSize: 12 }}>
                            {account.continuity_injury_summary?.last_repair_at ? `repaired ${account.continuity_injury_summary.last_repair_at}` : 'no repair recorded'}
                          </div>
                          <div className="muted" style={{ fontSize: 12, marginTop: 8 }}>
                            {notificationLabel(account.notification_summary)}
                          </div>
                          <div className="muted" style={{ fontSize: 12 }}>
                            {account.notification_summary?.latest?.message || 'no recent operator-facing notification'}
                          </div>
                          <div className="muted" style={{ fontSize: 12, marginTop: 8 }}>
                            {lastActivityLabel(account.last_activity_summary)}
                          </div>
                          <div className="muted" style={{ fontSize: 12 }}>
                            {account.last_activity_summary?.last_seen_at || 'no recent timestamp'}
                          </div>
                          {account.continuity_summary?.degraded_reason ? (
                            <div className="muted" style={{ fontSize: 12 }}>
                              {account.continuity_summary.degraded_reason}
                            </div>
                          ) : null}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </section>
          ))}
        </div>
      )}
    </Layout>
  )
}
