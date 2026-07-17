import React, { useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import { api } from '../lib/api.js'
import StateNotice from '../components/StateNotice.jsx'

function continuityLabel(summary) {
  const status = summary?.status
  if (status === 'degraded') return 'Degraded'
  if (status === 'healthy') return 'Healthy'
  if (status === 'missing') return 'Missing'
  if (status === 'unbound') return 'Unbound'
  return '—'
}

function continuityInjuryLabel(summary) {
  const status = summary?.status
  if (status === 'active') return 'Injured'
  if (status === 'recovered') return 'Recovered'
  if (status === 'none') return 'Clean'
  return '—'
}

function readinessLabel(summary) {
  if (!summary) return '—'
  return summary.ready ? 'Ready' : 'Blocked'
}

function proofLabel(summary) {
  if (!summary || !summary.artifact_count) return 'No proof'
  return `${summary.latest_artifact_type || 'proof'} | ${summary.artifact_count}`
}

function researchDeliveryLabel(summary) {
  if (!summary || !summary.delivery_count) return 'No deliveries'
  return `${summary.delivery_count} delivery${summary.delivery_count === 1 ? '' : 'ies'}`
}

function notificationLabel(summary) {
  if (!summary || !summary.count) return 'No notifications'
  return `${summary.count} recent notification${summary.count === 1 ? '' : 's'}`
}

function lastActivityLabel(summary) {
  if (!summary || !summary.last_seen_at) return 'No recent activity'
  return `${summary.last_seen_kind || 'activity'}${summary.stale ? ' | stale' : ''}`
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

function identityContinuityLabel(summary) {
  const status = summary?.status
  if (status === 'healthy') return 'Healthy'
  if (status === 'partial') return 'Partial'
  if (status === 'missing') return 'Missing'
  return '—'
}

function continuityIncidentLabel(summary) {
  const status = summary?.status
  if (status === 'active') return 'Incident active'
  if (status === 'recovered') return 'Recovered'
  if (status === 'clean') return 'Clean'
  return '—'
}

function continuityRecoveryReadinessLabel(summary) {
  const status = summary?.status
  if (status === 'blocked') return 'Blocked'
  if (status === 'caution') return 'Caution'
  if (status === 'ready') return 'Ready'
  return '—'
}

function postRebuildCheckLabel(summary) {
  const status = summary?.status
  if (status === 'verified') return 'Verified after rebuild'
  if (status === 'pending') return 'Verification pending'
  if (status === 'blocked') return 'Verification blocked'
  if (status === 'not_required') return 'No rebuild recorded'
  return '—'
}

function operationalResumeLabel(summary) {
  const status = summary?.status
  if (status === 'ready') return 'Resume ready'
  if (status === 'caution') return 'Resume caution'
  if (status === 'blocked') return 'Resume blocked'
  return 'Resume unknown'
}

function operationalResumeCheckpointLabel(summary) {
  if (summary?.approved) return 'Resume approved'
  return 'Resume not approved'
}

function presenceLabel(summary) {
  const mode = summary?.initiative_mode
  if (!mode) return '—'
  if (mode === 'self_timed_override') return 'Self-timed override'
  if (mode === 'bounded_sleep') return 'Bounded sleep'
  if (mode === 'scheduled_only') return 'Scheduled'
  return mode
}

function affectActionLabel(summary) {
  if (!summary || summary.status === 'missing') return 'No affect/action'
  const arc = summary?.action_state?.dominant_arc_state || 'arc?'
  const mode = summary?.action_state?.dominant_engagement_mode || 'mode?'
  const trust = summary?.affective_state?.trust_band
  return trust == null ? `${arc} | ${mode}` : `${arc} | ${mode} | trust ${trust}`
}

function selfModelLabel(summary) {
  if (!summary || summary.status !== 'healthy') return 'No model'
  return `${summary.dominant_arc_state || 'arc?'} | ${summary.dominant_engagement_mode || 'mode?'}`
}

function confidenceLabel(summary) {
  if (!summary || (!summary.confidence_level && summary.confidence_score == null)) return 'No confidence'
  return `${summary.confidence_level || 'uncertain'} | ${summary.confidence_score ?? 0}/100`
}

function mimicryLabel(summary) {
  if (!summary || !summary.status) return 'No mimicry'
  const depth = summary.max_mimicry_depth != null ? Number(summary.max_mimicry_depth).toFixed(2) : '—'
  const emotion = summary.max_emotional_intensity != null ? Number(summary.max_emotional_intensity).toFixed(2) : '—'
  return `${summary.status} | depth ${depth} | emotion ${emotion}`
}

function continuityQualityLabel(summary) {
  if (!summary || !summary.status) return 'No continuity quality'
  return `${summary.status} | ${summary.quality_score ?? 0}/100`
}

function relationshipLabel(summary) {
  if (!summary || summary.status !== 'healthy') return 'No memory'
  return `${summary.dominant_relationship_type || 'relationship?'} | ${summary.recent_counterpart_count || 0}`
}

function crewDynamicsLabel(summary) {
  if (!summary || summary.status === 'missing') return 'No crew'
  const style = summary.coordination_style || 'unknown'
  const members = summary.swarm_member_count ?? 0
  return `${style} | ${members} member${members === 1 ? '' : 's'}`
}

function rationaleLabel(summary) {
  if (!summary || !summary.current_trigger) return 'No rationale'
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
  if (!mode) return '—'
  if (mode === 'held') return 'Held'
  if (mode === 'review_only') return 'Review only'
  if (mode === 'normal') return 'Normal'
  return mode
}

function outboundBudgetLabel(summary) {
  if (!summary || summary.daily_outbound_budget == null) return 'No budget'
  const recent = summary.recent_outbound_action_count ?? 0
  const budget = summary.daily_outbound_budget
  const status = summary.outbound_budget_exhausted ? 'exhausted' : `${summary.outbound_budget_remaining ?? Math.max(0, budget - recent)} left`
  return `${recent}/${budget} · ${status}`
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

export default function Entities() {
  const [entities, setEntities] = useState([])
  const [err, setErr] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshingApprovalId, setRefreshingApprovalId] = useState(null)
  const [approvingResumeId, setApprovingResumeId] = useState(null)
  const [acknowledgingRecoveryId, setAcknowledgingRecoveryId] = useState(null)
  const [recordingRebuildId, setRecordingRebuildId] = useState(null)
  const [verifyingRebuildId, setVerifyingRebuildId] = useState(null)

  const load = () => {
    setErr(null)
    setLoading(true)
    api.listEntities()
      .then((r) => setEntities(r.entities || []))
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [])

  const refreshReviewHandoff = async (approvalId, refreshReasonCodes = []) => {
    if (!approvalId) return
    setRefreshingApprovalId(approvalId)
    setErr(null)
    try {
      await api.refreshEntityApprovalRequest(approvalId, {
        note: refreshNote(refreshReasonCodes, 'refreshed from entities surface'),
        decided_by: 'operator_console',
        refresh_reason_codes: refreshReasonCodes,
      })
      load()
    } catch (e) {
      setErr(e.message)
    } finally {
      setRefreshingApprovalId(null)
    }
  }

  const approveResumeCheckpoint = async (entity) => {
    if (!entity?.platform || !entity?.operational_agent_id) return
    setApprovingResumeId(entity.id)
    setErr(null)
    try {
      await api.approveOperationalResumeCheckpoint(entity.platform, entity.operational_agent_id, {
        approved_by: 'operator_console',
        note: 'approved from entities surface',
      })
      load()
    } catch (e) {
      setErr(e.message)
    } finally {
      setApprovingResumeId(null)
    }
  }

  const acknowledgeContinuityRecovery = async (entity) => {
    if (!entity?.platform || !entity?.operational_agent_id) return
    setAcknowledgingRecoveryId(entity.id)
    setErr(null)
    try {
      await api.acknowledgeOperationalContinuityRecovery(entity.platform, entity.operational_agent_id, {
        acknowledged_by: 'operator_console',
        note: 'acknowledged from entities surface',
      })
      load()
    } catch (e) {
      setErr(e.message)
    } finally {
      setAcknowledgingRecoveryId(null)
    }
  }

  const recordPostRebuild = async (entity) => {
    if (!entity?.platform || !entity?.operational_agent_id) return
    setRecordingRebuildId(entity.id)
    setErr(null)
    try {
      await api.recordOperationalPostRebuild(entity.platform, entity.operational_agent_id, {
        recorded_by: 'operator_console',
        note: 'recorded from entities surface',
      })
      load()
    } catch (e) {
      setErr(e.message)
    } finally {
      setRecordingRebuildId(null)
    }
  }

  const verifyPostRebuild = async (entity) => {
    if (!entity?.platform || !entity?.operational_agent_id) return
    setVerifyingRebuildId(entity.id)
    setErr(null)
    try {
      await api.verifyOperationalPostRebuild(entity.platform, entity.operational_agent_id, {
        verified_by: 'operator_console',
        note: 'verified from entities surface',
      })
      load()
    } catch (e) {
      setErr(e.message)
    } finally {
      setVerifyingRebuildId(null)
    }
  }

  return (
    <Layout title="Entities">
      {err && <StateNotice tone="danger" title="Could not load entities" detail={err} action={<button type="button" onClick={load}>Retry</button>} />}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <p style={{ margin: 0, color: 'var(--muted)' }}>{entities.length} entities discovered from automation state and memory.</p>
        <button type="button" onClick={load}>Refresh</button>
      </div>
      {loading ? (
        <StateNotice title="Loading entities" detail="Reading known operators and automation sessions." />
      ) : entities.length === 0 ? (
        <StateNotice title="No entities found" detail="This page will populate after automation sessions or entity records are present in operator memory." />
      ) : null}
      {!loading && entities.length > 0 && (
      <div style={{ overflowX: 'auto', maxWidth: '100%' }}>
      <table width="100%" cellPadding="8" style={{ borderCollapse: 'collapse', minWidth: 860 }}>
        <thead>
          <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
            <th>Entity</th>
            <th>Platform</th>
            <th>Mode</th>
            <th>Session target</th>
            <th>Operational target</th>
            <th>Identity continuity</th>
            <th>Recovery readiness</th>
            <th>Presence / initiative</th>
            <th>Affect / action</th>
            <th>Agency control</th>
            <th>Social posture</th>
            <th>Self-model</th>
            <th>Confidence</th>
            <th>Mimicry controls</th>
            <th>Continuity quality</th>
            <th>Relationship memory</th>
            <th>Crew dynamics</th>
            <th>Why now</th>
            <th>Commitments</th>
            <th>Review handoff</th>
            <th>Readiness</th>
            <th>Proof</th>
            <th>Account continuity</th>
            <th>Recent notifications</th>
            <th>Account activity</th>
            <th>Research deliveries</th>
            <th>Decisions</th>
            <th>Last activity</th>
          </tr>
        </thead>
        <tbody>
          {entities.map((e) => (
            <tr key={e.id} style={{ borderBottom: '1px solid var(--border)' }}>
              <td>
                <a href={`#/entities/${e.id}`}>{e.id}</a>
                <div style={{ color: 'var(--muted)', fontSize: 12, marginTop: 4 }}>
                  {profileSummaryLabel(e.profile)}
                </div>
              </td>
              <td>{e.platform ?? '—'}</td>
              <td>{e.mode ?? '—'}</td>
              <td>{e.session_target || '—'}</td>
              <td>{e.operational_session_target || '—'}</td>
              <td>
                <div>{identityContinuityLabel(e.identity_continuity_summary)}</div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  {e.identity_continuity_summary?.continuity_anchor || '—'}
                </div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  {continuityIncidentLabel(e.continuity_incident_summary)}
                  {e.continuity_incident_summary?.latest_event_detail ? ` · ${e.continuity_incident_summary.latest_event_detail}` : ''}
                </div>
              </td>
              <td>
                <div>{continuityRecoveryReadinessLabel(e.continuity_recovery_readiness)}</div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  {(e.continuity_recovery_readiness?.blocking || []).join(', ') || (e.continuity_recovery_readiness?.cautions || []).join(', ') || 'no recovery blockers'}
                </div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  {e.continuity_recovery_readiness?.acknowledged
                    ? `ack ${e.continuity_recovery_readiness.acknowledged_by || 'operator'}`
                    : (e.continuity_recovery_readiness?.can_acknowledge ? 'ack required before resume' : 'not acknowledged')}
                </div>
                  <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                    {(e.continuity_repair_plan?.open_checks || []).join(', ') || 'repair plan clear'}
                  </div>
                  <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                    {postRebuildCheckLabel(e.post_rebuild_continuity_check)}
                  </div>
                  <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                    {operationalResumeLabel(e.operational_resume_governance_summary)}
                    {e.operational_resume_governance_summary?.required_actions?.length
                      ? ` · ${e.operational_resume_governance_summary.required_actions.join(', ')}`
                      : ''}
                  </div>
                  <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                    {operationalResumeCheckpointLabel(e.operational_resume_checkpoint)}
                    {e.operational_resume_checkpoint?.invalidated_reason ? ` · ${e.operational_resume_checkpoint.invalidated_reason}` : ''}
                  </div>
                  <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                    {(() => {
                      if (e.operational_resume_governance_summary?.status === 'ready' && !e.operational_resume_checkpoint?.approved && e.platform && e.operational_agent_id) {
                        return (
                          <button
                            type="button"
                            onClick={() => approveResumeCheckpoint(e)}
                            disabled={approvingResumeId === e.id}
                            title="Approve a fresh operational resume checkpoint for this lane"
                          >
                            {approvingResumeId === e.id ? 'Approving resume…' : 'Approve resume'}
                          </button>
                        )
                      }
                      if (e.continuity_recovery_readiness?.can_acknowledge && !e.continuity_recovery_readiness?.acknowledged && e.platform && e.operational_agent_id) {
                        return (
                          <button
                            type="button"
                            onClick={() => acknowledgeContinuityRecovery(e)}
                            disabled={acknowledgingRecoveryId === e.id}
                            title="Acknowledge bounded continuity recovery for this lane"
                          >
                            {acknowledgingRecoveryId === e.id ? 'Acknowledging…' : 'Acknowledge recovery'}
                          </button>
                        )
                      }
                      if (!e.post_rebuild_continuity_check?.verification_required && e.platform && e.operational_agent_id) {
                        return (
                          <button
                            type="button"
                            onClick={() => recordPostRebuild(e)}
                            disabled={recordingRebuildId === e.id}
                            title="Record that this lane needs post-rebuild verification"
                          >
                            {recordingRebuildId === e.id ? 'Recording rebuild…' : 'Record rebuild'}
                          </button>
                        )
                      }
                      if (e.post_rebuild_continuity_check?.verification_required && !e.post_rebuild_continuity_check?.verified && e.platform && e.operational_agent_id) {
                        return (
                          <button
                            type="button"
                            onClick={() => verifyPostRebuild(e)}
                            disabled={verifyingRebuildId === e.id || e.post_rebuild_continuity_check?.status === 'blocked'}
                            title="Verify post-rebuild continuity for this lane"
                          >
                            {verifyingRebuildId === e.id ? 'Verifying rebuild…' : 'Verify rebuild'}
                          </button>
                        )
                      }
                      return 'resume action: —'
                    })()}
                  </div>
                  <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                    {e.continuity_repair_observation?.observation_required
                      ? `repair observation: ${e.continuity_repair_observation.status}${e.continuity_repair_observation.latest_observed_at ? ` · ${e.continuity_repair_observation.latest_observed_at}` : ''}`
                      : 'repair observation not required'}
                  </div>
                  <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                    {e.identity_resume_procedure?.open_steps?.length
                      ? `identity resume: ${e.identity_resume_procedure.open_steps.join(', ')}`
                      : 'identity resume ready'}
                  </div>
                </td>
              <td>
                <div>{presenceLabel(e.presence_initiative_summary)}</div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  {e.presence_initiative_summary?.next_earliest_wake_at || '—'}
                </div>
              </td>
              <td>
                <div>{affectActionLabel(e.affect_action_summary)}</div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  {e.affect_action_summary?.affective_state?.trust_band ?? '—'} trust · {e.affect_action_summary?.affective_state?.agency_budget ?? '—'} budget
                </div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  {e.affect_action_summary?.latest_turn?.engagement_mode || '—'}
                  {e.affect_action_summary?.latest_turn?.relationship_type ? ` · ${e.affect_action_summary.latest_turn.relationship_type}` : ''}
                </div>
              </td>
              <td>
                <div>{agencyControlLabel(e.agency_control_summary)}</div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  {e.agency_control_summary?.reason || '—'}
                </div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  {e.agency_control_summary?.outbound_lane_policy || 'unrestricted'}
                </div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  {outboundBudgetLabel(e.agency_control_summary)}
                </div>
              </td>
              <td>
                <div>{socialPostureLabel(e.social_posture_summary)}</div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  {e.social_posture_summary?.relationship_orientation || '—'}
                </div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  {e.social_posture_summary?.reply_bias || '—'}
                </div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  {(e.social_posture_summary?.active_platforms || []).join(', ') || '—'}
                </div>
              </td>
              <td>
                <div>{selfModelLabel(e.self_model_summary)}</div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  {e.self_model_summary?.dominant_uncertainty || '—'}
                </div>
              </td>
              <td>
                <div>{confidenceLabel(e.confidence_summary)}</div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  {e.confidence_summary?.summary || '—'}
                </div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  {e.drift_review_summary?.status ? `drift ${e.drift_review_summary.status}` : 'drift review unavailable'}
                </div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  {e.drift_review_summary?.comparison?.summary || '—'}
                </div>
              </td>
              <td>
                <div>{mimicryLabel(e.mimicry_control_summary)}</div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  {e.voice_belief_separation_summary?.summary || '—'}
                </div>
              </td>
              <td>
                <div>{continuityQualityLabel(e.continuity_quality_summary)}</div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  coverage {Number(e.continuity_quality_summary?.coverage_score ?? 0).toFixed(2)} · attribution {Number(e.continuity_quality_summary?.attribution_score ?? 0).toFixed(2)}
                </div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  override {Number(e.continuity_quality_summary?.operator_override_rate ?? 0).toFixed(2)} · promotion {Number(e.continuity_quality_summary?.promotion_accuracy ?? 0).toFixed(2)}
                </div>
              </td>
              <td>
                <div>{relationshipLabel(e.relationship_memory_summary)}</div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  {e.relationship_memory_summary?.top_counterparts?.[0]?.counterpart_fingerprint_id || '—'}
                </div>
              </td>
              <td>
                <div>{crewDynamicsLabel(e.crew_dynamics_summary)}</div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  {e.crew_dynamics_summary?.workflow_id || '—'}
                </div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  {e.crew_dynamics_summary?.swarm_run_id || 'no swarm'}
                </div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  {e.crew_dynamics_summary?.coordination_style_source || '—'}
                </div>
              </td>
              <td>
                <div>{rationaleLabel(e.action_rationale_summary)}</div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  {e.action_rationale_summary?.reason_chain?.[0] || '—'}
                </div>
              </td>
              <td>
                <div>{commitmentLabel(e.commitment_summary)}</div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  {e.commitment_summary?.latest_commitment?.title || '—'}
                </div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  {e.commitment_summary?.latest_commitment?.due_at || '—'}
                </div>
              </td>
              <td>
                <div>{reviewHandoffLabel(e.review_handoff_summary)}</div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  {e.review_handoff_summary?.latest?.approval_href ? (
                    <a href={e.review_handoff_summary.latest.approval_href}>{e.review_handoff_summary?.latest?.approval_id || 'open approval'}</a>
                  ) : (
                    e.review_handoff_summary?.latest?.approval_id || '—'
                  )}
                </div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  {e.review_handoff_summary?.latest?.status || '—'}{e.review_handoff_summary?.latest?.decision_note ? ` · ${e.review_handoff_summary.latest.decision_note}` : ''}
                </div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  {e.review_handoff_summary?.release_ready ? 'releasable now' : ((e.review_handoff_summary?.release_blockers || []).join(', ') || '—')}
                </div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  {e.review_handoff_summary?.latest?.latest_release_attempt
                    ? `last release: ${e.review_handoff_summary.latest.latest_release_attempt.status || 'unknown'}${e.review_handoff_summary.latest.latest_release_attempt.reason ? ` · ${e.review_handoff_summary.latest.latest_release_attempt.reason}` : ''}`
                    : 'last release: —'}
                </div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  {e.review_handoff_summary?.refresh_recommended
                    ? `refresh suggested · ${(e.review_handoff_summary?.refresh_reasons || []).join(', ')}`
                    : 'refresh suggested: no'}
                </div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  {e.review_handoff_summary?.latest?.refreshed_from_approval_id
                    ? `refreshed from ${e.review_handoff_summary.latest.refreshed_from_approval_id}${e.review_handoff_summary?.latest?.refresh_note ? ` · ${e.review_handoff_summary.latest.refresh_note}` : ''}${e.review_handoff_summary?.latest?.refresh_reason_codes?.length ? ` · ${e.review_handoff_summary.latest.refresh_reason_codes.join(', ')}` : ''}`
                    : 'refresh lineage: —'}
                </div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  {e.review_handoff_summary?.latest?.resolution_context?.rationale
                    ? `rationale: ${e.review_handoff_summary.latest.resolution_context.rationale}`
                    : 'rationale: —'}
                </div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  {e.review_handoff_summary?.latest?.resolution_context?.release_scope
                    ? `scope: ${e.review_handoff_summary.latest.resolution_context.release_scope}`
                    : 'scope: —'}
                </div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  {e.review_handoff_summary?.latest?.resolution_context?.followup_expectation
                    ? `follow-up: ${e.review_handoff_summary.latest.resolution_context.followup_expectation}`
                    : 'follow-up: —'}
                </div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  {e.review_handoff_summary?.latest?.followup_summary?.window_hours
                    ? `follow-up window: ${e.review_handoff_summary.latest.followup_summary.window_hours}h`
                    : 'follow-up window: —'}
                </div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  {e.review_handoff_summary?.latest?.followup_summary?.expected
                    ? `follow-up status: ${e.review_handoff_summary.latest.followup_summary.status}${e.review_handoff_summary?.latest?.followup_summary?.due_at ? ` · due ${e.review_handoff_summary.latest.followup_summary.due_at}` : ''}${e.review_handoff_summary?.latest?.followup_summary?.observation_detail ? ` · ${e.review_handoff_summary.latest.followup_summary.observation_detail}` : ''}`
                    : 'follow-up status: —'}
                </div>
                {e.review_handoff_summary?.refresh_recommended && e.review_handoff_summary?.latest?.approval_id ? (
                  <div style={{ marginTop: 6 }}>
                    <button
                      type="button"
                      onClick={() => refreshReviewHandoff(e.review_handoff_summary.latest.approval_id, e.review_handoff_summary?.refresh_reasons || [])}
                      disabled={refreshingApprovalId === e.review_handoff_summary.latest.approval_id}
                    >
                      {refreshingApprovalId === e.review_handoff_summary.latest.approval_id ? 'Refreshing…' : 'Refresh handoff'}
                    </button>
                  </div>
                ) : null}
              </td>
              <td>
                {(e.assigned_social_accounts || []).length ? (
                  <div>
                    {readinessLabel(e.assigned_social_accounts[0]?.readiness_summary)}
                    <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                      {(e.assigned_social_accounts[0]?.readiness_summary?.blocking || []).join(', ') || 'no blockers'}
                    </div>
                  </div>
                ) : '—'}
              </td>
              <td>{(e.assigned_social_accounts || []).length ? proofLabel(e.assigned_social_accounts[0]?.proof_summary) : '—'}</td>
              <td>
                {(e.assigned_social_accounts || []).length ? (
                  <div>
                    {continuityLabel(e.assigned_social_accounts[0]?.continuity_summary)}
                    <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                      {e.assigned_social_accounts[0]?.continuity_summary?.browser_session_id || 'no session'}
                    </div>
                    <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                      {continuityInjuryLabel(e.assigned_social_accounts[0]?.continuity_injury_summary)}
                      {e.assigned_social_accounts[0]?.continuity_injury_summary?.last_injury_reason ? ` · ${e.assigned_social_accounts[0].continuity_injury_summary.last_injury_reason}` : ''}
                    </div>
                  </div>
                ) : '—'}
              </td>
              <td>
                {(e.assigned_social_accounts || []).length ? (
                  <div>
                    {notificationLabel(e.assigned_social_accounts[0]?.notification_summary)}
                    <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                      {e.assigned_social_accounts[0]?.notification_summary?.latest?.message || '—'}
                    </div>
                  </div>
                ) : '—'}
              </td>
              <td>
                {(e.assigned_social_accounts || []).length ? (
                  <div>
                    {lastActivityLabel(e.assigned_social_accounts[0]?.last_activity_summary)}
                    <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                      {e.assigned_social_accounts[0]?.last_activity_summary?.last_seen_at || '—'}
                    </div>
                  </div>
                ) : '—'}
              </td>
              <td>
                <div>{researchDeliveryLabel(e.research_delivery_summary)}</div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  {e.research_delivery_summary?.recent_deliveries?.[0]?.topic || '—'}
                </div>
              </td>
              <td>{e.has_decisions ? 'Yes' : '—'}</td>
              <td>{e.last_activity || '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>
      )}
    </Layout>
  )
}


