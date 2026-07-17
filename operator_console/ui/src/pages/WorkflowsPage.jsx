import React, { useCallback, useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import { api } from '../lib/api.js'
import { withReturnUrl } from '../lib/navigationContext.js'

function formatRunTime(value) {
  if (value == null || value === '') return '—'
  try {
    const d = typeof value === 'number' ? new Date(value * 1000) : new Date(value)
    if (Number.isNaN(d.getTime())) return '—'
    return d.toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })
  } catch {
    return String(value)
  }
}

function agencyControlLabel(summary) {
  const mode = summary?.effective_mode || summary?.mode
  if (mode === 'held') return 'Held'
  if (mode === 'review_only') return 'Review only'
  if (mode === 'normal') return 'Normal'
  return '—'
}

function outboundBudgetLabel(summary) {
  if (!summary || summary.daily_outbound_budget == null) return 'No budget'
  const recent = summary.recent_outbound_action_count ?? 0
  const budget = summary.daily_outbound_budget
  if (summary.outbound_budget_exhausted) {
    return `${recent}/${budget} exhausted`
  }
  return `${recent}/${budget}`
}

function reviewHandoffLabel(summary) {
  if (!summary || !summary.count) return '—'
  return `${summary.pending_count || summary.count} pending`
}

function workflowStatusLabel(summary) {
  if (!summary) return '—'
  const status = summary.status || summary.latest_run_status || 'idle'
  const runId = summary.latest_run_id ? `run ${summary.latest_run_id}` : 'no runs'
  const nodes = summary.node_state_summary?.counts?.nodes ?? 0
  return `${status} · ${runId} · ${nodes} node${nodes === 1 ? '' : 's'}`
}

function commitmentLabel(summary) {
  if (!summary || !summary.count) return '—'
  const status = summary.status === 'overdue' ? 'overdue' : summary.status === 'pending' ? 'open' : summary.status || 'done'
  return `${summary.open_count || 0} open · ${status}`
}

function confidenceLabel(summary) {
  if (!summary || (!summary.confidence_level && summary.confidence_score == null)) return '—'
  return `${summary.confidence_level || 'uncertain'} / ${summary.confidence_score ?? 0}/100`
}

function crewDynamicsLabel(summary) {
  if (!summary || summary.status === 'missing') return '—'
  const style = summary.coordination_style || 'unknown'
  const members = summary.swarm_member_count ?? 0
  return `${style} / ${members} member${members === 1 ? '' : 's'}`
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
  if (summary?.invalidated) return 'Resume approval invalidated'
  return 'Resume not approved'
}

function releaseGateLabel(summary) {
  if (!summary) return '—'
  if (summary.ok) return 'Eligible'
  if (summary.code === 'missing_verdict') return 'Missing verdict'
  if (summary.code === 'stale_verdict') return 'Stale verdict'
  if (summary.code === 'backup_required') return 'Backup required'
  if (summary.code === 'blocked') return 'Blocked'
  return 'Gate blocked'
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

export default function WorkflowsPage() {
  const [workflows, setWorkflows] = useState([])
  const [err, setErr] = useState(null)
  const [detail, setDetail] = useState(null)
  const [checkResults, setCheckResults] = useState(null)
  const [templates, setTemplates] = useState([])
  const [scheduledJobs, setScheduledJobs] = useState([])
  const [triggering, setTriggering] = useState(null)
  const [refreshingApprovalId, setRefreshingApprovalId] = useState(null)
  const [approvingResumeJobId, setApprovingResumeJobId] = useState(null)
  const [acknowledgingRecoveryJobId, setAcknowledgingRecoveryJobId] = useState(null)
  const [recordingRebuildJobId, setRecordingRebuildJobId] = useState(null)
  const [verifyingRebuildJobId, setVerifyingRebuildJobId] = useState(null)
  const [grantingVerdictJobId, setGrantingVerdictJobId] = useState(null)

  const load = useCallback(() => {
    setErr(null)
    api.listWorkflows()
      .then((r) => r.ok !== false && r.workflows && setWorkflows(r.workflows))
      .catch((e) => setErr(e.message))
    api.listTemplates()
      .then((r) => r.ok !== false && r.templates && setTemplates(r.templates))
      .catch(() => {})
    api.listScheduledJobs()
      .then((r) => r.ok !== false && r.jobs && setScheduledJobs(r.jobs))
      .catch(() => {})
  }, [])

  useEffect(() => { load() }, [load])

  // Refresh scheduled jobs (no server restart needed; list is read from workspace at request time)
  const onRefresh = () => { setScheduledJobs([]); load() }

  const showDetail = (workflowId) => {
    setCheckResults(null)
    api.getWorkflow(workflowId)
      .then((r) => r.ok !== false && r.workflow && setDetail(r.workflow))
      .catch((e) => setErr(e.message))
  }

  const runChecks = (workflowId) => {
    setErr(null)
    api.runAcceptanceChecks(workflowId, {})
      .then((r) => r.ok !== false && r.results && setCheckResults(r.results))
      .catch((e) => setErr(e.message))
  }

  const loadTemplate = async (templateId) => {
    setErr(null)
    try {
      const res = await api.getTemplate(templateId)
      if (res.ok && res.dag) {
        localStorage.setItem('openclaw_dag_draft', JSON.stringify(res.dag, null, 2))
        window.location.hash = withReturnUrl('#/run')
      }
    } catch (e) {
      setErr(e.message)
    }
  }

  const openBuilder = (jobId) => {
    localStorage.setItem('openclaw_builder_job_id', jobId)
    window.location.hash = '#/builder'
  }

  const onRunNow = (jobId) => {
    setTriggering(jobId)
    setErr(null)
    api.triggerScheduledJob(jobId)
      .then(() => load())
      .catch((e) => setErr(e.message))
      .finally(() => setTriggering(null))
  }

  const refreshReviewHandoff = (job) => {
    const approvalId = job?.review_handoff_summary?.latest?.approval_id
    if (!approvalId) return
    setRefreshingApprovalId(approvalId)
    setErr(null)
    api.refreshEntityApprovalRequest(approvalId, {
      note: refreshNote(job?.review_handoff_summary?.refresh_reasons || [], 'refreshed from workflows surface'),
      decided_by: 'operator_console',
      refresh_reason_codes: job?.review_handoff_summary?.refresh_reasons || [],
    })
      .then(() => load())
      .catch((e) => setErr(e.message))
      .finally(() => setRefreshingApprovalId(null))
  }

  const approveOperationalResume = (job) => {
    if (!job?.platform || !job?.operational_agent_id) return
    setApprovingResumeJobId(job.job_id)
    setErr(null)
    api.approveOperationalResumeCheckpoint(job.platform, job.operational_agent_id, {
      approved_by: 'operator_console',
      note: 'operator approved resume from workflows surface after continuity checks',
    })
      .then(() => load())
      .catch((e) => setErr(e.message))
      .finally(() => setApprovingResumeJobId(null))
  }

  const acknowledgeContinuityRecovery = (job) => {
    if (!job?.platform || !job?.operational_agent_id) return
    setAcknowledgingRecoveryJobId(job.job_id)
    setErr(null)
    api.acknowledgeOperationalContinuityRecovery(job.platform, job.operational_agent_id, {
      acknowledged_by: 'operator_console',
      note: 'acknowledged from workflows surface',
    })
      .then(() => load())
      .catch((e) => setErr(e.message))
      .finally(() => setAcknowledgingRecoveryJobId(null))
  }

  const recordPostRebuild = (job) => {
    if (!job?.platform || !job?.operational_agent_id) return
    setRecordingRebuildJobId(job.job_id)
    setErr(null)
    api.recordOperationalPostRebuild(job.platform, job.operational_agent_id, {
      recorded_by: 'operator_console',
      note: 'recorded from workflows surface',
    })
      .then(() => load())
      .catch((e) => setErr(e.message))
      .finally(() => setRecordingRebuildJobId(null))
  }

  const verifyPostRebuild = (job) => {
    if (!job?.platform || !job?.operational_agent_id) return
    setVerifyingRebuildJobId(job.job_id)
    setErr(null)
    api.verifyOperationalPostRebuild(job.platform, job.operational_agent_id, {
      verified_by: 'operator_console',
      note: 'verified from workflows surface',
    })
      .then(() => load())
      .catch((e) => setErr(e.message))
      .finally(() => setVerifyingRebuildJobId(null))
  }

  const grantReleaseVerdict = (job) => {
    const workflowFamily = job?.workflow_id || job?.job_id
    if (!workflowFamily) return
    setGrantingVerdictJobId(job.job_id)
    setErr(null)
    api.governance.createReleaseVerdict({
      workflow_family: workflowFamily,
      target_kind: 'workflow',
      target_id: workflowFamily,
      verdict: 'eligible',
      reason: `Operator granted release verdict from workflows surface for ${job.job_id}`,
      stale_after_hours: 168,
    })
      .then(() => load())
      .catch((e) => setErr(e.message))
      .finally(() => setGrantingVerdictJobId(null))
  }

  return (
    <Layout title="Workflows">
      {err && <p style={{ color: 'var(--danger)' }}>{err}</p>}
      <section className="section-card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>Workflow templates</h3>
        <p className="muted" style={{ marginTop: 0 }}>
          Load a template into the Run DAG editor and customize it before execution.
        </p>
        <div style={{ overflowX: 'auto', maxWidth: '100%' }}>
          <table style={{ minWidth: 720 }}>
            <thead>
              <tr>
                <th>template_id</th>
                <th>graph_id</th>
                <th>nodes</th>
                <th>description</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {templates.map((t) => (
                <tr key={t.template_id}>
                  <td style={{ wordBreak: 'break-word' }}>{t.template_id}</td>
                  <td style={{ wordBreak: 'break-word' }}>{t.graph_id || '—'}</td>
                  <td>{t.node_count ?? '—'}</td>
                  <td style={{ minWidth: 220 }}>{t.description || '—'}</td>
                  <td>
                    <button type="button" onClick={() => loadTemplate(t.template_id)}>Load in Run DAG</button>
                  </td>
                </tr>
              ))}
              {!templates.length && (
                <tr>
                  <td colSpan={5} className="muted">No templates available.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
      <section className="section-card">
        <p className="muted" style={{ marginTop: 0 }}>
          Need structure edits for scheduled workflow DAGs? Use <a href="#/builder">Visual Builder</a>.
        </p>
        <h3 style={{ marginTop: 0 }}>Registered workflows</h3>
        <div style={{ overflowX: 'auto', maxWidth: '100%' }}>
          <table style={{ minWidth: 760 }}>
            <thead>
              <tr>
                <th>workflow_id</th>
                <th>display_name</th>
                <th>category</th>
                <th>readiness</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {workflows.map((w) => (
                <tr key={w.workflow_id}>
                  <td style={{ wordBreak: 'break-word' }}>{w.workflow_id}</td>
                  <td>{w.display_name}</td>
                  <td>{w.category}</td>
                  <td>{w.readiness}</td>
                  <td>
                    <button type="button" onClick={() => showDetail(w.workflow_id)}>Detail</button>
                    <button type="button" onClick={() => runChecks(w.workflow_id)}>Run checks</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section className="section-card" style={{ marginTop: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <h3 style={{ marginTop: 0 }}>Scheduled jobs</h3>
          <button type="button" onClick={onRefresh} className="btn secondary">Refresh</button>
          <span className="muted" style={{ fontSize: '0.9rem' }}>From workspace; refresh to pick up new jobs (no restart).</span>
        </div>
        <div style={{ overflowX: 'auto', maxWidth: '100%' }}>
          <table style={{ minWidth: 980, tableLayout: 'fixed', width: '100%' }}>
            <thead>
              <tr>
                <th>job_id</th>
                <th>dag_path</th>
                <th>exists</th>
                <th>graph_id</th>
                <th>nodes</th>
                <th>Schedule recurrence</th>
                <th>Agency control</th>
                <th>Continuity recovery</th>
                <th>Review handoff</th>
                <th>Commitments</th>
                <th>Confidence</th>
                <th>Crew dynamics</th>
                <th>Release gate</th>
                <th>Workflow status</th>
                <th>Last run</th>
                <th>Next run</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {scheduledJobs.map((j) => (
                <tr key={j.job_id}>
                  <td style={{ wordBreak: 'break-word', maxWidth: 220 }}>{j.job_id}</td>
                  <td style={{ wordBreak: 'break-word', minWidth: 300, maxWidth: 420 }}>{j.dag_path}</td>
                  <td>{j.exists ? 'yes' : 'no'}</td>
                  <td style={{ wordBreak: 'break-word', maxWidth: 220 }}>{j.graph_id || '—'}</td>
                  <td>{j.node_count ?? '—'}</td>
                  <td style={{ whiteSpace: 'nowrap' }}>{j.schedule_recurrence ?? '—'}</td>
                  <td>
                    <div>{agencyControlLabel(j.agency_control)}</div>
                    <div className="muted" style={{ fontSize: 12 }}>
                      {j.agency_control?.reason || '—'}
                    </div>
                    <div className="muted" style={{ fontSize: 12 }}>
                      {outboundBudgetLabel(j.agency_control)}
                    </div>
                    <div className="muted" style={{ fontSize: 12 }}>
                      {j.agency_control?.outbound_budget_next_reset_at || '—'}
                    </div>
                  </td>
                  <td>
                    <div>{continuityRecoveryReadinessLabel(j.continuity_recovery_readiness)}</div>
                    <div className="muted" style={{ fontSize: 12 }}>
                      {(j.continuity_recovery_readiness?.blocking || []).join(', ') || (j.continuity_recovery_readiness?.cautions || []).join(', ') || 'no recovery blockers'}
                    </div>
                    <div className="muted" style={{ fontSize: 12 }}>
                      {j.continuity_recovery_readiness?.acknowledged
                        ? `ack ${j.continuity_recovery_readiness.acknowledged_by || 'operator'}`
                        : (j.continuity_recovery_readiness?.can_acknowledge ? 'ack required before resume' : 'not acknowledged')}
                    </div>
                    <div className="muted" style={{ fontSize: 12 }}>
                      {(j.continuity_repair_plan?.open_checks || []).join(', ') || 'repair plan clear'}
                    </div>
                    <div className="muted" style={{ fontSize: 12 }}>
                      {postRebuildCheckLabel(j.post_rebuild_continuity_check)}
                    </div>
                    <div className="muted" style={{ fontSize: 12 }}>
                      {operationalResumeLabel(j.operational_resume_governance_summary)}
                      {j.operational_resume_governance_summary?.required_actions?.length
                        ? ` · ${j.operational_resume_governance_summary.required_actions.join(', ')}`
                        : ''}
                    </div>
                    <div className="muted" style={{ fontSize: 12 }}>
                      {operationalResumeCheckpointLabel(j.operational_resume_checkpoint)}
                    </div>
                    <div className="muted" style={{ fontSize: 12 }}>
                      {j.continuity_repair_observation?.observation_required
                        ? `repair observation: ${j.continuity_repair_observation.status}${j.continuity_repair_observation.latest_observed_at ? ` · ${j.continuity_repair_observation.latest_observed_at}` : ''}`
                          : 'repair observation not required'}
                      </div>
                      <div className="muted" style={{ fontSize: 12 }}>
                        {j.identity_resume_procedure?.open_steps?.length
                          ? `identity resume: ${j.identity_resume_procedure.open_steps.join(', ')}`
                          : 'identity resume ready'}
                      </div>
                    </td>
                  <td>
                    <div>{reviewHandoffLabel(j.review_handoff_summary)}</div>
                    <div className="muted" style={{ fontSize: 12 }}>
                      {j.review_handoff_summary?.latest?.approval_href ? (
                        <a href={j.review_handoff_summary.latest.approval_href}>{j.review_handoff_summary?.latest?.approval_id || 'open approval'}</a>
                      ) : (
                        j.review_handoff_summary?.latest?.approval_id || '—'
                      )}
                    </div>
                    <div className="muted" style={{ fontSize: 12 }}>
                      {j.review_handoff_summary?.latest?.status || '—'}{j.review_handoff_summary?.latest?.decision_note ? ` · ${j.review_handoff_summary.latest.decision_note}` : ''}
                    </div>
                    <div className="muted" style={{ fontSize: 12 }}>
                      {j.review_handoff_summary?.release_ready ? 'releasable now' : ((j.review_handoff_summary?.release_blockers || []).join(', ') || '—')}
                    </div>
                    <div className="muted" style={{ fontSize: 12 }}>
                      {j.review_handoff_summary?.latest?.latest_release_attempt
                        ? `last release: ${j.review_handoff_summary.latest.latest_release_attempt.status || 'unknown'}${j.review_handoff_summary.latest.latest_release_attempt.reason ? ` · ${j.review_handoff_summary.latest.latest_release_attempt.reason}` : ''}`
                        : 'last release: —'}
                    </div>
                    <div className="muted" style={{ fontSize: 12 }}>
                      {j.review_handoff_summary?.refresh_recommended
                        ? `refresh suggested · ${(j.review_handoff_summary?.refresh_reasons || []).join(', ')}`
                        : 'refresh suggested: no'}
                    </div>
                    <div className="muted" style={{ fontSize: 12 }}>
                      {j.review_handoff_summary?.latest?.refreshed_from_approval_id
                        ? `refreshed from ${j.review_handoff_summary.latest.refreshed_from_approval_id}${j.review_handoff_summary?.latest?.refresh_note ? ` · ${j.review_handoff_summary.latest.refresh_note}` : ''}${j.review_handoff_summary?.latest?.refresh_reason_codes?.length ? ` · ${j.review_handoff_summary.latest.refresh_reason_codes.join(', ')}` : ''}`
                        : 'refresh lineage: —'}
                    </div>
                    <div className="muted" style={{ fontSize: 12 }}>
                      {j.review_handoff_summary?.latest?.resolution_context?.rationale
                        ? `rationale: ${j.review_handoff_summary.latest.resolution_context.rationale}`
                        : 'rationale: —'}
                    </div>
                    <div className="muted" style={{ fontSize: 12 }}>
                      {j.review_handoff_summary?.latest?.resolution_context?.release_scope
                        ? `scope: ${j.review_handoff_summary.latest.resolution_context.release_scope}`
                        : 'scope: —'}
                    </div>
                    <div className="muted" style={{ fontSize: 12 }}>
                      {j.review_handoff_summary?.latest?.resolution_context?.followup_expectation
                        ? `follow-up: ${j.review_handoff_summary.latest.resolution_context.followup_expectation}`
                        : 'follow-up: —'}
                    </div>
                    <div className="muted" style={{ fontSize: 12 }}>
                      {j.review_handoff_summary?.latest?.followup_summary?.window_hours
                        ? `follow-up window: ${j.review_handoff_summary.latest.followup_summary.window_hours}h`
                        : 'follow-up window: —'}
                    </div>
                    <div className="muted" style={{ fontSize: 12 }}>
                    {j.review_handoff_summary?.latest?.followup_summary?.expected
                      ? `follow-up status: ${j.review_handoff_summary.latest.followup_summary.status}${j.review_handoff_summary?.latest?.followup_summary?.due_at ? ` · due ${j.review_handoff_summary.latest.followup_summary.due_at}` : ''}${j.review_handoff_summary?.latest?.followup_summary?.observation_detail ? ` · ${j.review_handoff_summary.latest.followup_summary.observation_detail}` : ''}`
                      : 'follow-up status: —'}
                  </div>
                  {j.review_handoff_summary?.workflow_status_summary ? (
                    <div className="muted" style={{ fontSize: 12 }}>
                      workflow: {workflowStatusLabel(j.review_handoff_summary.workflow_status_summary)}
                      {j.review_handoff_summary.workflow_status_summary?.latest_run_href ? (
                        <> · <a href={j.review_handoff_summary.workflow_status_summary.latest_run_href}>latest run</a></>
                      ) : null}
                    </div>
                  ) : null}
                  {j.review_handoff_summary?.refresh_recommended && j.review_handoff_summary?.latest?.approval_id ? (
                      <div style={{ marginTop: 6 }}>
                        <button
                          type="button"
                          onClick={() => refreshReviewHandoff(j)}
                          disabled={refreshingApprovalId === j.review_handoff_summary.latest.approval_id}
                        >
                          {refreshingApprovalId === j.review_handoff_summary.latest.approval_id ? 'Refreshing…' : 'Refresh handoff'}
                        </button>
                      </div>
                    ) : null}
                  </td>
                  <td>
                    <div>{commitmentLabel(j.commitment_summary)}</div>
                    <div className="muted" style={{ fontSize: 12 }}>
                      {j.commitment_summary?.latest_commitment?.title || '—'}
                    </div>
                    <div className="muted" style={{ fontSize: 12 }}>
                      {j.commitment_summary?.latest_commitment?.due_at || '—'}
                    </div>
                    <div className="muted" style={{ fontSize: 12 }}>
                      {j.commitment_summary?.overdue_count ? `${j.commitment_summary.overdue_count} overdue` : '—'}
                    </div>
                  </td>
                  <td>
                    <div>{confidenceLabel(j.confidence_summary)}</div>
                    <div className="muted" style={{ fontSize: 12 }}>
                      {j.confidence_summary?.summary || '—'}
                    </div>
                  </td>
                  <td>
                    <div>{crewDynamicsLabel(j.crew_dynamics_summary)}</div>
                    <div className="muted" style={{ fontSize: 12 }}>
                      {j.crew_dynamics_summary?.workflow_id || '—'}
                    </div>
                    <div className="muted" style={{ fontSize: 12 }}>
                      {j.crew_dynamics_summary?.swarm_run_id || '—'}
                    </div>
                    <div className="muted" style={{ fontSize: 12 }}>
                      {j.crew_dynamics_summary?.coordination_style_source || '—'}
                    </div>
                  </td>
                  <td>
                    <div>{releaseGateLabel(j.release_gate_summary)}</div>
                    <div className="muted" style={{ fontSize: 12 }}>
                      {j.release_gate_summary?.reason || '—'}
                    </div>
                    <div className="muted" style={{ fontSize: 12 }}>
                      {j.release_gate_summary?.environment || '—'}
                    </div>
                  </td>
                  <td>
                    <div>{workflowStatusLabel(j.workflow_status_summary || j.review_handoff_summary?.workflow_status_summary)}</div>
                    <div className="muted" style={{ fontSize: 12 }}>
                      {j.workflow_status_summary?.latest_run_href || j.review_handoff_summary?.workflow_status_summary?.latest_run_href ? (
                        <a href={(j.workflow_status_summary || j.review_handoff_summary?.workflow_status_summary)?.latest_run_href}>
                          {(j.workflow_status_summary || j.review_handoff_summary?.workflow_status_summary)?.latest_run_id || 'open activity'}
                        </a>
                      ) : '—'}
                    </div>
                    <div className="muted" style={{ fontSize: 12 }}>
                      {(() => {
                        const nodeSummary = (j.workflow_status_summary || j.review_handoff_summary?.workflow_status_summary)?.node_state_summary?.counts || {}
                        const total = nodeSummary.nodes ?? 0
                        return total > 0
                          ? `nodes ${nodeSummary.done || 0} done · ${nodeSummary.failed || 0} failed · ${nodeSummary.blocked || 0} blocked`
                          : 'node state unavailable'
                      })()}
                    </div>
                  </td>
                  <td style={{ whiteSpace: 'nowrap' }}>{formatRunTime(j.last_run)}</td>
                  <td style={{ whiteSpace: 'nowrap' }}>{formatRunTime(j.next_run)}</td>
                  <td>
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                      {(() => {
                        const releaseGateBlocked = j.release_gate_summary?.ok === false
                        const continuityBlocked = j.continuity_recovery_readiness?.status === 'blocked'
                        const continuityAckRequired = j.continuity_recovery_readiness?.status === 'caution' && !j.continuity_recovery_readiness?.resume_permitted
                        const resumeCheckpointRequired = Boolean(j.operational_resume_checkpoint_required)
                        const disabled = triggering !== null || releaseGateBlocked || j.agency_control?.effective_mode === 'held' || j.agency_control?.outbound_budget_exhausted || continuityBlocked || continuityAckRequired || resumeCheckpointRequired
                        const title = releaseGateBlocked
                          ? (j.release_gate_summary?.reason || 'Blocked by release gate')
                          : j.agency_control?.effective_mode === 'held'
                          ? (j.agency_control?.reason || 'Held by agency control')
                          : j.agency_control?.outbound_budget_exhausted
                            ? (
                                j.agency_control?.reason
                                || `Outbound budget exhausted (${j.agency_control?.recent_outbound_action_count ?? 0}/${j.agency_control?.daily_outbound_budget ?? 0})`
                                + (j.agency_control?.outbound_budget_next_reset_at ? ` until ${formatRunTime(j.agency_control.outbound_budget_next_reset_at)}` : '')
                              )
                            : continuityBlocked
                              ? ((j.continuity_recovery_readiness?.blocking || []).join(', ') || 'Blocked by continuity recovery state')
                            : continuityAckRequired
                              ? ((j.continuity_recovery_readiness?.cautions || []).join(', ') || 'Continuity recovery acknowledgment required before resume')
                            : resumeCheckpointRequired
                              ? (j.operational_resume_checkpoint?.invalidated_reason
                                  ? `Fresh operational resume checkpoint required: ${j.operational_resume_checkpoint.invalidated_reason}`
                                  : 'Fresh operational resume checkpoint required before run')
                            : 'Run this workflow now'
                        return (
                      <button
                        type="button"
                        onClick={() => onRunNow(j.job_id)}
                        disabled={disabled}
                        title={title}
                      >
                        {triggering === j.job_id ? 'Starting…' : 'Run now'}
                      </button>
                        )
                      })()}
                      {j.operational_resume_checkpoint_required && j.platform && j.operational_agent_id ? (
                        <button
                          type="button"
                          onClick={() => approveOperationalResume(j)}
                          disabled={approvingResumeJobId === j.job_id}
                          title="Approve a fresh operational resume checkpoint for this lane"
                        >
                          {approvingResumeJobId === j.job_id ? 'Approving resume…' : 'Approve resume'}
                        </button>
                      ) : null}
                      {j.continuity_recovery_readiness?.can_acknowledge && !j.continuity_recovery_readiness?.acknowledged && j.platform && j.operational_agent_id ? (
                        <button
                          type="button"
                          onClick={() => acknowledgeContinuityRecovery(j)}
                          disabled={acknowledgingRecoveryJobId === j.job_id}
                          title="Acknowledge bounded continuity recovery for this lane"
                        >
                          {acknowledgingRecoveryJobId === j.job_id ? 'Acknowledging…' : 'Acknowledge recovery'}
                        </button>
                      ) : null}
                      {!j.post_rebuild_continuity_check?.verification_required && j.platform && j.operational_agent_id ? (
                        <button
                          type="button"
                          onClick={() => recordPostRebuild(j)}
                          disabled={recordingRebuildJobId === j.job_id}
                          title="Record that this lane now needs post-rebuild verification"
                        >
                          {recordingRebuildJobId === j.job_id ? 'Recording rebuild…' : 'Record rebuild'}
                        </button>
                      ) : null}
                      {j.post_rebuild_continuity_check?.verification_required && !j.post_rebuild_continuity_check?.verified && j.platform && j.operational_agent_id ? (
                        <button
                          type="button"
                          onClick={() => verifyPostRebuild(j)}
                          disabled={verifyingRebuildJobId === j.job_id || j.post_rebuild_continuity_check?.status === 'blocked'}
                          title="Verify post-rebuild continuity for this lane"
                        >
                          {verifyingRebuildJobId === j.job_id ? 'Verifying rebuild…' : 'Verify rebuild'}
                        </button>
                      ) : null}
                      {j.release_gate_summary?.ok === false && ['missing_verdict', 'stale_verdict'].includes(j.release_gate_summary?.code) ? (
                        <button
                          type="button"
                          onClick={() => grantReleaseVerdict(j)}
                          disabled={grantingVerdictJobId === j.job_id}
                          title="Create a fresh eligible release verdict for this canonical workflow family"
                        >
                          {grantingVerdictJobId === j.job_id ? 'Granting verdict…' : 'Grant release verdict'}
                        </button>
                      ) : null}
                      <button type="button" onClick={() => openBuilder(j.job_id)}>Open in Visual Builder</button>
                    </div>
                  </td>
                </tr>
              ))}
              {!scheduledJobs.length && (
                <tr>
                  <td colSpan={17} className="muted">No scheduled jobs found.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
      {detail && (
        <section className="section-card" style={{ marginTop: 16 }}>
          <h3>Workflow: {detail.workflow_id}</h3>
          <pre style={{ background: '#0b1118', padding: 12, overflow: 'auto', borderRadius: 8, border: '1px solid var(--border)' }}>
            {JSON.stringify(detail, null, 2)}
          </pre>
        </section>
      )}
      {checkResults && (
        <section className="section-card" style={{ marginTop: 16 }}>
          <h3>Acceptance check results</h3>
          <ul>
            {checkResults.map((c, i) => (
              <li key={i}>{c.check_id}: {c.passed ? 'pass' : 'fail'} — {c.message}</li>
            ))}
          </ul>
        </section>
      )}
    </Layout>
  )
}
