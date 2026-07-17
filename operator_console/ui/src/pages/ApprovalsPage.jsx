import React, { useCallback, useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import { api } from '../lib/api.js'
import StateNotice from '../components/StateNotice.jsx'
import { PageSkeleton } from '../components/PageStates.jsx'

const formatTimestamp = (value) => {
  if (!value) return 'n/a'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toISOString().replace('T', ' ').replace('Z', ' UTC')
}

const approvalReleaseWindow = (approval) => {
  const hours = approval?.preview_json?.release_window_hours
  if (hours == null || hours === '') return null
  const numeric = Number(hours)
  return Number.isFinite(numeric) && numeric > 0 ? numeric : null
}

const approvalApprovedUntil = (approval) => {
  const hours = approvalReleaseWindow(approval)
  if (!hours || !approval?.decided_at) return null
  const decided = new Date(approval.decided_at)
  if (Number.isNaN(decided.getTime())) return null
  return new Date(decided.getTime() + (hours * 60 * 60 * 1000))
}

const approvalExpired = (approval) => {
  if ((approval?.status || '').toLowerCase() !== 'approved') return false
  const approvedUntil = approvalApprovedUntil(approval)
  if (!approvedUntil) return false
  return approvedUntil.getTime() <= Date.now()
}

const approvalRefreshContext = (approval) => {
  const preview = approval?.preview_json || approval?.payload?.preview_json || approval?.payload || {}
  const context = typeof preview.refresh_context === 'object' && preview.refresh_context ? preview.refresh_context : {}
  const fromApprovalId = context.from_approval_id || preview.refreshed_from_approval_id || ''
  const note = context.note || preview.refresh_note || ''
  const refreshedBy = context.refreshed_by || preview.refreshed_by || ''
  const sourceStatus = context.source_status || ''
  const rawReasonCodes = Array.isArray(context.reason_codes) ? context.reason_codes : (Array.isArray(preview.refresh_reason_codes) ? preview.refresh_reason_codes : [])
  const reasonCodes = rawReasonCodes.map((value) => String(value || '').trim()).filter(Boolean)
  if (!fromApprovalId && !note && !refreshedBy && !sourceStatus && reasonCodes.length === 0) return null
  return { fromApprovalId, note, refreshedBy, sourceStatus, reasonCodes }
}

const approvalResolutionContext = (approval) => {
  const preview = approval?.preview_json || approval?.payload?.preview_json || approval?.payload || {}
  const context = typeof preview.resolution_context === 'object' && preview.resolution_context ? preview.resolution_context : {}
  const rationale = context.rationale || ''
  const releaseScope = context.release_scope || ''
  const followupExpectation = context.followup_expectation || ''
  const rawFollowupWindowHours = context.followup_window_hours
  const followupWindowHours = rawFollowupWindowHours == null || rawFollowupWindowHours === '' ? null : Number(rawFollowupWindowHours)
  if (!rationale && !releaseScope && !followupExpectation && !Number.isFinite(followupWindowHours)) return null
  return {
    rationale,
    releaseScope,
    followupExpectation,
    followupWindowHours: Number.isFinite(followupWindowHours) && followupWindowHours > 0 ? followupWindowHours : null,
  }
}

const approvalFollowupSummary = (approval) => {
  const context = approvalResolutionContext(approval)
  if (!context?.followupExpectation) return null
  const decidedAt = approval?.decided_at ? new Date(approval.decided_at) : null
  if (!decidedAt || Number.isNaN(decidedAt.getTime())) {
    return {
      status: 'pending',
      dueAt: null,
      windowHours: context.followupWindowHours,
      expectation: context.followupExpectation,
    }
  }
  const windowHours = context.followupWindowHours || 24
  const dueAt = new Date(decidedAt.getTime() + (windowHours * 60 * 60 * 1000))
  const status = dueAt.getTime() <= Date.now() ? 'overdue' : 'pending'
  return {
    status,
    dueAt,
    windowHours,
    expectation: context.followupExpectation,
  }
}

const workflowStatusLabel = (summary) => {
  if (!summary) return '—'
  const status = summary.status || summary.latest_run_status || 'idle'
  const runId = summary.latest_run_id ? `run ${summary.latest_run_id}` : 'no runs'
  const nodes = summary.node_state_summary?.counts?.nodes ?? 0
  return `${status} · ${runId} · ${nodes} node${nodes === 1 ? '' : 's'}`
}

const approvalRefreshReasonCodes = (approval) => {
  const releaseState = approval?.review_release_state || {}
  const codes = []
  if (approvalExpired(approval)) codes.push('approval_expired')
  const followup = approvalFollowupSummary(approval)
  if (followup?.status === 'overdue') codes.push('followup_overdue')
  for (const blocker of Array.isArray(releaseState.release_blockers) ? releaseState.release_blockers : []) {
    if (blocker === 'operational_resume_checkpoint_required') codes.push('operational_resume_checkpoint_required')
    if (blocker === 'continuity_recovery') codes.push('continuity_recovery')
    if (blocker === 'continuity_recovery_ack_required') codes.push('continuity_recovery_ack_required')
  }
  return codes
}

const refreshNote = (reasonCodes, fallback) => {
  const codes = Array.isArray(reasonCodes) ? reasonCodes : []
  if (codes.includes('operational_resume_checkpoint_required')) return 'resume approval required before release'
  if (codes.includes('continuity_recovery_ack_required')) return 'continuity recovery acknowledgment required'
  if (codes.includes('continuity_recovery')) return 'continuity recovery blocked'
  if (codes.includes('followup_overdue')) return 'follow-up overdue'
  if (codes.includes('approval_expired')) return 'approval expired'
  if (codes.includes('approval_release_held')) return 'release blocked by hold'
  if (codes.includes('approval_release_lane_policy_blocked')) return 'release blocked by lane policy'
  if (codes.includes('approval_release_outbound_budget_exhausted')) return 'release blocked by outbound budget'
  return fallback
}

const parseApprovalRouteFilters = () => {
  try {
    const raw = window.location.hash.split('?')[1] || ''
    const params = new URLSearchParams(raw)
    return {
      workflowId: params.get('workflow_id') || '',
      approvalId: params.get('approval_id') || '',
    }
  } catch {
    return { workflowId: '', approvalId: '' }
  }
}

const entityApprovalIdForItem = (item) => {
  if (!item || typeof item !== 'object') return ''
  if (item.entity_approval_id) return String(item.entity_approval_id)
  if (item.approval_id) return String(item.approval_id)
  const kind = String(item.kind || '').toLowerCase()
  if ((kind === 'entity_approval' || kind === 'approval') && item.id) return String(item.id)
  return ''
}

const updateApprovalRoute = (workflowId, approvalId) => {
  const params = new URLSearchParams()
  if (workflowId) params.set('workflow_id', workflowId)
  if (approvalId) params.set('approval_id', approvalId)
  window.location.hash = `#/approvals?${params.toString()}`
}

export default function ApprovalsPage() {
  const routeFilters = parseApprovalRouteFilters()
  const [items, setItems] = useState([])
  const [err, setErr] = useState(null)
  const [evalWorkflowId, setEvalWorkflowId] = useState('fourclaw-auto-post')
  const [filterWorkflowId, setFilterWorkflowId] = useState(routeFilters.workflowId)
  const [selectedApprovalId, setSelectedApprovalId] = useState(routeFilters.approvalId)
  const [dedup, setDedup] = useState(null)
  const [entityApproval, setEntityApproval] = useState(null)
  const [entityApprovalBusy, setEntityApprovalBusy] = useState(false)
  const [resumeBusy, setResumeBusy] = useState(false)
  const [recoveryAckBusy, setRecoveryAckBusy] = useState(false)
  const [recordingRebuildBusy, setRecordingRebuildBusy] = useState(false)
  const [verifyingRebuildBusy, setVerifyingRebuildBusy] = useState(false)
  const [queueActionKey, setQueueActionKey] = useState('')
  const [evalResult, setEvalResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [statusFilter, setStatusFilter] = useState('all')
  const [kindFilter, setKindFilter] = useState('all')
  const [settings, setSettings] = useState(null)
  const [evidenceTimeline, setEvidenceTimeline] = useState(null)
  const [policySaving, setPolicySaving] = useState(false)
  const [decisionNote, setDecisionNote] = useState('')
  const [decisionRationale, setDecisionRationale] = useState('')
  const [decisionReleaseScope, setDecisionReleaseScope] = useState('')
  const [decisionFollowupExpectation, setDecisionFollowupExpectation] = useState('')
  const [decisionFollowupWindowHours, setDecisionFollowupWindowHours] = useState('')

  const loadPolicy = useCallback(() => {
    api.gatewayV1
      .getTenantMeSettings()
      .then((result) => setSettings(result))
      .catch((e) => setErr(e.message))
  }, [])

  const load = useCallback((workflowId = filterWorkflowId, status = statusFilter) => {
    setErr(null)
    setLoading(true)
    const params = { limit: 100, status }
    if (workflowId) params.workflow_id = workflowId
    api
      .getApprovalsQueue(params)
      .then((r) => {
        setItems(Array.isArray(r.items) ? r.items : [])
        setEvidenceTimeline(r.evidence_timeline || null)
      })
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false))
  }, [filterWorkflowId, statusFilter])

  const loadDedup = useCallback((workflowId = filterWorkflowId) => {
    if (!workflowId) {
      setDedup(null)
      return
    }
    api
      .getWorkflowDedup(workflowId, 50)
      .then((r) => setDedup(r))
      .catch((e) => setErr(e.message))
  }, [filterWorkflowId])

  useEffect(() => {
    load(filterWorkflowId, statusFilter)
    loadDedup(filterWorkflowId)
    loadPolicy()
  }, [filterWorkflowId, statusFilter, load, loadDedup, loadPolicy])

  useEffect(() => {
    const syncFromHash = () => {
      const next = parseApprovalRouteFilters()
      setFilterWorkflowId(next.workflowId)
      setSelectedApprovalId(next.approvalId)
    }
    window.addEventListener('hashchange', syncFromHash)
    return () => window.removeEventListener('hashchange', syncFromHash)
  }, [])

  useEffect(() => {
    const approvalId = selectedApprovalId.trim()
    if (!approvalId) {
      setEntityApproval(null)
      return
    }
    api.getEntityApprovalRequest(approvalId)
      .then((result) => setEntityApproval(result))
      .catch(() => setEntityApproval(null))
  }, [selectedApprovalId])

  const selectedApprovedUntil = approvalApprovedUntil(entityApproval)
  const selectedRefreshContext = approvalRefreshContext(entityApproval)
  const selectedResolutionContext = approvalResolutionContext(entityApproval)
  const selectedFollowupSummary = approvalFollowupSummary(entityApproval)
  const selectedRefreshReasonCodes = approvalRefreshReasonCodes(entityApproval)
  const selectedReleaseState = entityApproval?.review_release_state || null
  const selectedRefreshRecommended = Boolean(selectedReleaseState?.refresh_recommended || selectedRefreshReasonCodes.length)

  useEffect(() => {
    if (!entityApproval) {
      setDecisionNote('')
      setDecisionRationale('')
      setDecisionReleaseScope('')
      setDecisionFollowupExpectation('')
      setDecisionFollowupWindowHours('')
      return
    }
    setDecisionNote(entityApproval.decision_note || '')
    setDecisionRationale(selectedResolutionContext?.rationale || '')
    setDecisionReleaseScope(selectedResolutionContext?.releaseScope || '')
    setDecisionFollowupExpectation(selectedResolutionContext?.followupExpectation || '')
    setDecisionFollowupWindowHours(selectedResolutionContext?.followupWindowHours ? String(selectedResolutionContext.followupWindowHours) : '')
  }, [entityApproval, selectedResolutionContext])

  const evaluate = () => {
    setErr(null)
    setEvalResult(null)
    api
      .evaluateApproval(evalWorkflowId, {})
      .then((r) => setEvalResult(r))
      .catch((e) => setErr(e.message))
  }

  const visibleItems = items.filter((item) => {
    const status = (item.status || item.decision || 'pending').toString().toLowerCase()
    const kind = item.kind || 'other'
    if (statusFilter !== 'all' && status !== statusFilter.toLowerCase()) return false
    if (kindFilter !== 'all' && kind !== kindFilter) return false
    return true
  })
  const distinctKinds = Array.from(new Set(items.map((item) => item.kind || 'other'))).sort()
  const approvalRules = Array.isArray(settings?.approval_rules) ? settings.approval_rules : []
  const highlightedApprovalId = selectedApprovalId.trim()
  const autoApprovedItems = items
    .filter((item) => (item.status || item.decision || '').toLowerCase() === 'approved' && String(item.resolutionNote || '').toLowerCase().includes('auto-approved by policy'))
    .slice(0, 12)

  const updateRule = (index, key, value) => {
    const next = approvalRules.map((rule, idx) => (idx === index ? { ...rule, [key]: value } : rule))
    setSettings((current) => ({ ...(current || {}), approval_rules: next }))
  }

  const savePolicy = async () => {
    if (!settings) return
    setPolicySaving(true)
    setErr(null)
    try {
      await api.gatewayV1.patchTenantMeSettings({
        first_turn_approval_required: settings.first_turn_approval_required,
        auto_approve_kinds: settings.auto_approve_kinds || [],
        approval_rules: approvalRules,
      })
      loadPolicy()
      load(filterWorkflowId, 'all')
    } catch (e) {
      setErr(e.message)
    } finally {
      setPolicySaving(false)
    }
  }

  const addRule = (mode = 'post') => {
    const id = `rule-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
    const next = [
      ...approvalRules,
      {
        id,
        label: mode === 'reply' ? 'Auto approve social replies' : 'Auto approve social posts',
        enabled: true,
        decision: 'auto_approve',
        kinds: ['social_write'],
        risks: ['high'],
        workflow_ids: [],
        platforms: [],
        modes: [mode],
      },
    ]
    setSettings((current) => ({ ...(current || {}), approval_rules: next }))
  }

  const removeRule = (index) => {
    const next = approvalRules.filter((_, idx) => idx !== index)
    setSettings((current) => ({ ...(current || {}), approval_rules: next }))
  }

  const actOnEntityApproval = async (decision) => {
    const approvalId = selectedApprovalId.trim()
    if (!approvalId) return
    setEntityApprovalBusy(true)
    setErr(null)
    try {
      if (decision === 'approve') {
        await api.approveEntityApprovalRequest(approvalId, {
          note: decisionNote || 'approved from operator approvals page',
          decided_by: 'operator_console',
          rationale: decisionRationale,
          release_scope: decisionReleaseScope,
          followup_expectation: decisionFollowupExpectation,
          followup_window_hours: decisionFollowupWindowHours ? Number(decisionFollowupWindowHours) : undefined,
        })
      } else if (decision === 'reject') {
        await api.rejectEntityApprovalRequest(approvalId, {
          note: decisionNote || 'rejected from operator approvals page',
          decided_by: 'operator_console',
          rationale: decisionRationale,
          release_scope: decisionReleaseScope,
          followup_expectation: decisionFollowupExpectation,
          followup_window_hours: decisionFollowupWindowHours ? Number(decisionFollowupWindowHours) : undefined,
        })
      } else if (decision === 'request_edit') {
        await api.requestEditEntityApprovalRequest(approvalId, {
          note: decisionNote || 'request edit from operator approvals page',
          decided_by: 'operator_console',
          rationale: decisionRationale,
          release_scope: decisionReleaseScope,
          followup_expectation: decisionFollowupExpectation,
          followup_window_hours: decisionFollowupWindowHours ? Number(decisionFollowupWindowHours) : undefined,
        })
      } else if (decision === 'refresh') {
        const refreshed = await api.refreshEntityApprovalRequest(approvalId, {
          note: refreshNote(selectedRefreshReasonCodes, 'refreshed from operator approvals page'),
          decided_by: 'operator_console',
          refresh_reason_codes: selectedRefreshReasonCodes,
        })
        setEntityApproval(refreshed)
        setSelectedApprovalId(refreshed?.approval_id || '')
        if (refreshed?.approval_id) {
          const params = new URLSearchParams()
          if (refreshed.workflow_id) params.set('workflow_id', refreshed.workflow_id)
          params.set('approval_id', refreshed.approval_id)
          window.location.hash = `#/approvals?${params.toString()}`
        }
        load(filterWorkflowId, statusFilter)
        return
      }
      const refreshed = await api.getEntityApprovalRequest(approvalId)
      setEntityApproval(refreshed)
    } catch (e) {
      setErr(e.message)
    } finally {
      setEntityApprovalBusy(false)
    }
  }

  const approveResumeForSelectedApproval = async () => {
    const releaseState = selectedReleaseState || {}
    if (!releaseState.platform || !releaseState.operational_agent_id) return
    setResumeBusy(true)
    setErr(null)
    try {
      await api.approveOperationalResumeCheckpoint(releaseState.platform, releaseState.operational_agent_id, {
        approved_by: 'operator_console',
        note: 'approved from approvals page',
      })
      const refreshed = await api.getEntityApprovalRequest(selectedApprovalId.trim())
      setEntityApproval(refreshed)
    } catch (e) {
      setErr(e.message)
    } finally {
      setResumeBusy(false)
    }
  }

  const acknowledgeRecoveryForSelectedApproval = async () => {
    const releaseState = selectedReleaseState || {}
    if (!releaseState.platform || !releaseState.operational_agent_id) return
    setRecoveryAckBusy(true)
    setErr(null)
    try {
      await api.acknowledgeOperationalContinuityRecovery(releaseState.platform, releaseState.operational_agent_id, {
        acknowledged_by: 'operator_console',
        note: 'acknowledged from approvals page',
      })
      const refreshed = await api.getEntityApprovalRequest(selectedApprovalId.trim())
      setEntityApproval(refreshed)
    } catch (e) {
      setErr(e.message)
    } finally {
      setRecoveryAckBusy(false)
    }
  }

  const recordRebuildForSelectedApproval = async () => {
    const releaseState = selectedReleaseState || {}
    if (!releaseState.platform || !releaseState.operational_agent_id) return
    setRecordingRebuildBusy(true)
    setErr(null)
    try {
      await api.recordOperationalPostRebuild(releaseState.platform, releaseState.operational_agent_id, {
        recorded_by: 'operator_console',
        note: 'recorded from approvals page',
      })
      const refreshed = await api.getEntityApprovalRequest(selectedApprovalId.trim())
      setEntityApproval(refreshed)
    } catch (e) {
      setErr(e.message)
    } finally {
      setRecordingRebuildBusy(false)
    }
  }

  const verifyRebuildForSelectedApproval = async () => {
    const releaseState = selectedReleaseState || {}
    if (!releaseState.platform || !releaseState.operational_agent_id) return
    setVerifyingRebuildBusy(true)
    setErr(null)
    try {
      await api.verifyOperationalPostRebuild(releaseState.platform, releaseState.operational_agent_id, {
        verified_by: 'operator_console',
        note: 'verified from approvals page',
      })
      const refreshed = await api.getEntityApprovalRequest(selectedApprovalId.trim())
      setEntityApproval(refreshed)
    } catch (e) {
      setErr(e.message)
    } finally {
      setVerifyingRebuildBusy(false)
    }
  }

  const focusApprovalItem = (item) => {
    const approvalId = entityApprovalIdForItem(item)
    if (!approvalId) return
    setSelectedApprovalId(approvalId)
    updateApprovalRoute(item.workflow_id || filterWorkflowId, approvalId)
  }

  const refreshSelectedEntityApproval = useCallback(async (approvalId) => {
    if (!approvalId) return
    try {
      const refreshed = await api.getEntityApprovalRequest(approvalId)
      setEntityApproval(refreshed)
    } catch {
      setEntityApproval(null)
    }
  }, [])

  const runQueueGovernanceAction = async (item, action) => {
    const releaseState = item?.review_release_state || {}
    const platform = releaseState.platform
    const operationalAgentId = releaseState.operational_agent_id
    if (!platform || !operationalAgentId) return
    const approvalId = entityApprovalIdForItem(item)
    const actionKey = `${item?.id || approvalId || 'row'}:${action}`
    setQueueActionKey(actionKey)
    setErr(null)
    try {
      if (action === 'approve_resume') {
        await api.approveOperationalResumeCheckpoint(platform, operationalAgentId, {
          approved_by: 'operator_console',
          note: 'approved from approvals queue',
        })
      } else if (action === 'acknowledge_recovery') {
        await api.acknowledgeOperationalContinuityRecovery(platform, operationalAgentId, {
          acknowledged_by: 'operator_console',
          note: 'acknowledged from approvals queue',
        })
      } else if (action === 'record_rebuild') {
        await api.recordOperationalPostRebuild(platform, operationalAgentId, {
          recorded_by: 'operator_console',
          note: 'recorded from approvals queue',
        })
      } else if (action === 'verify_rebuild') {
        await api.verifyOperationalPostRebuild(platform, operationalAgentId, {
          verified_by: 'operator_console',
          note: 'verified from approvals queue',
        })
      }
      await load(filterWorkflowId, statusFilter)
      if (approvalId) await refreshSelectedEntityApproval(approvalId)
    } catch (e) {
      setErr(e.message)
    } finally {
      setQueueActionKey('')
    }
  }

  return (
    <Layout title="Approvals">
      {err && <StateNotice tone="danger" title="Could not load approvals" detail={err} action={<button type="button" onClick={() => load(filterWorkflowId)}>Retry</button>} />}
      <p style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        Runtime approvals, policy-driven auto-approvals, and human queue history all come from the same store now.
        {loading && <span data-testid="hg-page-skeleton" className="muted" style={{ marginLeft: 4 }} aria-busy="true">Refreshing…</span>}
      </p>
      {evidenceTimeline ? (
        <section className="card" style={{ marginBottom: 16 }}>
          <h3 style={{ marginTop: 0 }}>Evidence plane</h3>
          <p className="muted" style={{ marginBottom: 0 }}>
            {evidenceTimeline.counts?.runs || 0} runs, {evidenceTimeline.counts?.decisions || 0} decisions, {evidenceTimeline.counts?.notifications || 0} notifications.
            {' '}
            continuity {evidenceTimeline.counts?.continuity_events || 0}, approvals {evidenceTimeline.counts?.approval_events || 0}, decision claims {evidenceTimeline.counts?.support_claims || 0}.
          </p>
          {evidenceTimeline.latest ? (
            <p style={{ marginBottom: 0 }}>
              latest: {evidenceTimeline.latest.title}
              {evidenceTimeline.latest.detail ? ` · ${evidenceTimeline.latest.detail}` : ''}
            </p>
          ) : null}
        </section>
      ) : null}
      <section className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
          <div>
            <h3 style={{ marginTop: 0 }}>Auto-Approval Policy</h3>
            <p className="muted" style={{ marginBottom: 0 }}>
              Use targeted rules instead of hidden env flags. Match by kind, risk, workflow, platform, and post/reply mode.
            </p>
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button type="button" onClick={() => addRule('post')}>Add social post rule</button>
            <button type="button" onClick={() => addRule('reply')}>Add social reply rule</button>
            <button type="button" onClick={savePolicy} disabled={policySaving || !settings}>
              {policySaving ? 'Saving…' : 'Save policy'}
            </button>
          </div>
        </div>
        {settings && (
          <div style={{ marginTop: 12, display: 'grid', gap: 12 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <input
                type="checkbox"
                checked={Boolean(settings.first_turn_approval_required)}
                onChange={(e) => setSettings((current) => ({ ...(current || {}), first_turn_approval_required: e.target.checked }))}
              />
              <span>Require approval before first reply</span>
            </label>
            {approvalRules.length === 0 ? (
              <div className="muted">No targeted rules yet. Pending social writes will stay human-reviewed until you add one.</div>
            ) : (
              approvalRules.map((rule, index) => (
                <div key={rule.id || index} style={{ border: '1px solid var(--border)', borderRadius: 16, padding: 12 }}>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center', marginBottom: 8 }}>
                    <input
                      value={rule.label || ''}
                      onChange={(e) => updateRule(index, 'label', e.target.value)}
                      placeholder="Rule label"
                      style={{ flex: '1 1 220px' }}
                    />
                    <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <input
                        type="checkbox"
                        checked={rule.enabled !== false}
                        onChange={(e) => updateRule(index, 'enabled', e.target.checked)}
                      />
                      Enabled
                    </label>
                    <button type="button" onClick={() => removeRule(index)}>Remove</button>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 8 }}>
                    <label>
                      <div className="muted">Kinds</div>
                      <input value={(rule.kinds || []).join(', ')} onChange={(e) => updateRule(index, 'kinds', e.target.value.split(',').map((value) => value.trim()).filter(Boolean))} />
                    </label>
                    <label>
                      <div className="muted">Risks</div>
                      <input value={(rule.risks || []).join(', ')} onChange={(e) => updateRule(index, 'risks', e.target.value.split(',').map((value) => value.trim()).filter(Boolean))} />
                    </label>
                    <label>
                      <div className="muted">Workflow IDs</div>
                      <input value={(rule.workflow_ids || []).join(', ')} onChange={(e) => updateRule(index, 'workflow_ids', e.target.value.split(',').map((value) => value.trim()).filter(Boolean))} />
                    </label>
                    <label>
                      <div className="muted">Platforms</div>
                      <input value={(rule.platforms || []).join(', ')} onChange={(e) => updateRule(index, 'platforms', e.target.value.split(',').map((value) => value.trim()).filter(Boolean))} />
                    </label>
                    <label>
                      <div className="muted">Modes</div>
                      <input value={(rule.modes || []).join(', ')} onChange={(e) => updateRule(index, 'modes', e.target.value.split(',').map((value) => value.trim()).filter(Boolean))} />
                    </label>
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </section>
      <section style={{ marginBottom: 16 }}>
        <label htmlFor="approval-workflow-filter">Workflow filter</label>
        <div style={{ display: 'flex', gap: 8, marginTop: 6, flexWrap: 'wrap' }}>
          <input
            id="approval-workflow-filter"
            value={filterWorkflowId}
            onChange={(e) => setFilterWorkflowId(e.target.value)}
            placeholder="workflow_id"
            style={{ flex: '1 1 220px' }}
          />
          <button type="button" onClick={() => load(filterWorkflowId)}>
            Refresh approvals
          </button>
          <button type="button" onClick={() => loadDedup(filterWorkflowId)}>
            Refresh dedupe
          </button>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} aria-label="Filter by status">
            <option value="pending">Waiting approval (pending)</option>
            <option value="approved">Approved</option>
            <option value="denied">Denied</option>
            <option value="all">All statuses</option>
          </select>
          <select value={kindFilter} onChange={(e) => setKindFilter(e.target.value)}>
            <option value="all">All kinds</option>
            {distinctKinds.map((kind) => <option key={kind} value={kind}>{kind}</option>)}
          </select>
        </div>
      </section>
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 16 }}>
        <div className="card"><strong>{items.length}</strong><div className="muted">Queue items</div></div>
        <div className="card"><strong>{visibleItems.length}</strong><div className="muted">Visible after filters</div></div>
        <div className="card"><strong>{items.filter((item) => (item.status || item.decision || 'pending').toString().toLowerCase() === 'pending').length}</strong><div className="muted">Pending</div></div>
        <div className="card"><strong>{autoApprovedItems.length}</strong><div className="muted">Recent auto approvals</div></div>
      </div>
      {entityApproval && (
        <section className="card" style={{ marginBottom: 16 }}>
          <h3 style={{ marginTop: 0 }}>Selected Review Handoff</h3>
          <div><strong>{entityApproval.approval_id}</strong></div>
          <div className="muted" style={{ marginTop: 4 }}>
            entity {entityApproval.entity_id || '—'} · workflow {entityApproval.workflow_id || '—'} · status {entityApproval.status || 'pending'}
          </div>
          {entityApproval.decided_at ? (
            <div className="muted" style={{ marginTop: 4 }}>
              decided {formatTimestamp(entityApproval.decided_at)} by {entityApproval.decided_by || 'unknown'}{entityApproval.decision_note ? ` · ${entityApproval.decision_note}` : ''}
            </div>
          ) : null}
          {approvalReleaseWindow(entityApproval) ? (
            <div className="muted" style={{ marginTop: 4 }}>
              release window {approvalReleaseWindow(entityApproval)}h · approved until {formatTimestamp(selectedApprovedUntil)}
              {approvalExpired(entityApproval) ? ' · expired' : ''}
            </div>
          ) : null}
          <div className="muted" style={{ marginTop: 4 }}>
            {entityApproval.preview_json?.summary || entityApproval.preview_json?.draft_text || 'No preview summary'}
          </div>
          {selectedRefreshContext ? (
            <div className="muted" style={{ marginTop: 4 }}>
              refreshed from {selectedRefreshContext.fromApprovalId || 'unknown'}{selectedRefreshContext.sourceStatus ? ` · prior ${selectedRefreshContext.sourceStatus}` : ''}{selectedRefreshContext.refreshedBy ? ` · by ${selectedRefreshContext.refreshedBy}` : ''}{selectedRefreshContext.note ? ` · ${selectedRefreshContext.note}` : ''}{selectedRefreshContext.reasonCodes?.length ? ` · ${selectedRefreshContext.reasonCodes.join(', ')}` : ''}
            </div>
          ) : null}
          {selectedResolutionContext ? (
            <div className="muted" style={{ marginTop: 4 }}>
              {selectedResolutionContext.rationale ? `rationale: ${selectedResolutionContext.rationale}` : 'rationale: —'}
              {selectedResolutionContext.releaseScope ? ` · scope: ${selectedResolutionContext.releaseScope}` : ''}
              {selectedResolutionContext.followupExpectation ? ` · follow-up: ${selectedResolutionContext.followupExpectation}` : ''}
              {selectedResolutionContext.followupWindowHours ? ` · window: ${selectedResolutionContext.followupWindowHours}h` : ''}
            </div>
          ) : null}
          {selectedFollowupSummary ? (
            <div className="muted" style={{ marginTop: 4 }}>
              {`follow-up status: ${selectedFollowupSummary.status}`}
              {selectedFollowupSummary.dueAt ? ` · due ${formatTimestamp(selectedFollowupSummary.dueAt)}` : ''}
            </div>
          ) : null}
          {selectedReleaseState ? (
            <div className="muted" style={{ marginTop: 4 }}>
              release {selectedReleaseState.release_ready ? 'ready' : 'blocked'}
              {selectedReleaseState.release_blockers?.length ? ` · ${selectedReleaseState.release_blockers.join(', ')}` : ''}
              {selectedReleaseState.release_next_eligible_at ? ` · next ${formatTimestamp(selectedReleaseState.release_next_eligible_at)}` : ''}
            </div>
          ) : null}
          {selectedReleaseState?.operational_resume_checkpoint?.invalidated_reason ? (
            <div className="muted" style={{ marginTop: 4 }}>
              resume invalidation: {selectedReleaseState.operational_resume_checkpoint.invalidated_reason}
            </div>
          ) : null}
          {selectedReleaseState?.continuity_recovery_readiness?.status ? (
            <div className="muted" style={{ marginTop: 4 }}>
              recovery {selectedReleaseState.continuity_recovery_readiness.status}
              {selectedReleaseState.continuity_recovery_readiness.acknowledged ? ` · acknowledged by ${selectedReleaseState.continuity_recovery_readiness.acknowledged_by || 'operator'}` : ''}
              {selectedReleaseState.continuity_recovery_readiness.cautions?.length ? ` · ${selectedReleaseState.continuity_recovery_readiness.cautions.join(', ')}` : ''}
            </div>
          ) : null}
          {selectedReleaseState?.post_rebuild_continuity_check?.status ? (
            <div className="muted" style={{ marginTop: 4 }}>
              rebuild {selectedReleaseState.post_rebuild_continuity_check.status}
              {selectedReleaseState.post_rebuild_continuity_check.rebuild_recorded_at ? ` · recorded ${formatTimestamp(selectedReleaseState.post_rebuild_continuity_check.rebuild_recorded_at)}` : ''}
              {selectedReleaseState.post_rebuild_continuity_check.verified_at ? ` · verified ${formatTimestamp(selectedReleaseState.post_rebuild_continuity_check.verified_at)}` : ''}
            </div>
          ) : null}
          {selectedReleaseState?.action_hint ? (
            <div className="muted" style={{ marginTop: 4 }}>
              next action: {selectedReleaseState.action_hint}
            </div>
          ) : null}
          {entityApproval?.workflow_status_summary ? (
            <div className="muted" style={{ marginTop: 4 }}>
              workflow: {workflowStatusLabel(entityApproval.workflow_status_summary)}
              {entityApproval.workflow_status_summary?.latest_run_href ? ` · ${entityApproval.workflow_status_summary.latest_run_href}` : ''}
            </div>
          ) : null}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 8, marginTop: 12 }}>
            <label>
              <div className="muted">Decision note</div>
              <input value={decisionNote} onChange={(e) => setDecisionNote(e.target.value)} placeholder="Operator note" />
            </label>
            <label>
              <div className="muted">Release scope</div>
              <input value={decisionReleaseScope} onChange={(e) => setDecisionReleaseScope(e.target.value)} placeholder="single supervised post" />
            </label>
            <label>
              <div className="muted">Follow-up window (h)</div>
              <input value={decisionFollowupWindowHours} onChange={(e) => setDecisionFollowupWindowHours(e.target.value)} placeholder="6" />
            </label>
            <label style={{ gridColumn: '1 / -1' }}>
              <div className="muted">Rationale</div>
              <input value={decisionRationale} onChange={(e) => setDecisionRationale(e.target.value)} placeholder="continuity verified" />
            </label>
            <label style={{ gridColumn: '1 / -1' }}>
              <div className="muted">Follow-up expectation</div>
              <input value={decisionFollowupExpectation} onChange={(e) => setDecisionFollowupExpectation(e.target.value)} placeholder="watch replies for 1h" />
            </label>
          </div>
          {entityApproval.status === 'pending' && (
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 12 }}>
              <button type="button" disabled={entityApprovalBusy} onClick={() => actOnEntityApproval('approve')}>
                {entityApprovalBusy ? 'Working…' : 'Approve'}
              </button>
              <button type="button" disabled={entityApprovalBusy} onClick={() => actOnEntityApproval('request_edit')}>
                Request edit
              </button>
              <button type="button" disabled={entityApprovalBusy} onClick={() => actOnEntityApproval('reject')}>
                Reject
              </button>
            </div>
          )}
          {entityApproval.status !== 'pending' && (
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 12 }}>
              {selectedRefreshRecommended ? (
                <button type="button" disabled={entityApprovalBusy} onClick={() => actOnEntityApproval('refresh')}>
                  {entityApprovalBusy ? 'Working…' : (approvalExpired(entityApproval) ? 'Refresh expired handoff' : 'Refresh handoff')}
                </button>
              ) : null}
              {selectedReleaseState?.release_blockers?.includes('operational_resume_checkpoint_required') && selectedReleaseState?.platform && selectedReleaseState?.operational_agent_id ? (
                <button type="button" disabled={resumeBusy} onClick={approveResumeForSelectedApproval}>
                  {resumeBusy ? 'Approving resume…' : 'Approve resume'}
                </button>
              ) : null}
              {selectedReleaseState?.release_blockers?.includes('continuity_recovery_ack_required')
                && selectedReleaseState?.continuity_recovery_readiness?.can_acknowledge
                && !selectedReleaseState?.continuity_recovery_readiness?.acknowledged
                && selectedReleaseState?.platform
                && selectedReleaseState?.operational_agent_id ? (
                  <button type="button" disabled={recoveryAckBusy} onClick={acknowledgeRecoveryForSelectedApproval}>
                    {recoveryAckBusy ? 'Acknowledging…' : 'Acknowledge recovery'}
                  </button>
                ) : null}
              {!selectedReleaseState?.post_rebuild_continuity_check?.verification_required
                && selectedReleaseState?.platform
                && selectedReleaseState?.operational_agent_id ? (
                  <button type="button" disabled={recordingRebuildBusy} onClick={recordRebuildForSelectedApproval}>
                    {recordingRebuildBusy ? 'Recording rebuild…' : 'Record rebuild'}
                  </button>
                ) : null}
              {selectedReleaseState?.post_rebuild_continuity_check?.verification_required
                && !selectedReleaseState?.post_rebuild_continuity_check?.verified
                && selectedReleaseState?.platform
                && selectedReleaseState?.operational_agent_id ? (
                  <button
                    type="button"
                    disabled={verifyingRebuildBusy || selectedReleaseState?.post_rebuild_continuity_check?.status === 'blocked'}
                    onClick={verifyRebuildForSelectedApproval}
                  >
                    {verifyingRebuildBusy ? 'Verifying rebuild…' : 'Verify rebuild'}
                  </button>
                ) : null}
            </div>
          )}
        </section>
      )}
      {autoApprovedItems.length > 0 && (
        <section style={{ marginBottom: 16 }}>
          <h3>Recent Auto Approvals</h3>
          <div style={{ display: 'grid', gap: 8 }}>
            {autoApprovedItems.map((item) => (
              <div key={`auto-${item.id}`} className="card">
                <strong>{item.title || item.summary || item.id}</strong>
                <div className="muted">{item.summary || item.origin?.label || item.workflow_id || 'n/a'}</div>
                <div className="muted">{formatTimestamp(item.resolvedAt || item.createdAt)}</div>
              </div>
            ))}
          </div>
        </section>
      )}
      {!loading && items.length === 0 ? (
        <StateNotice
          title={statusFilter === 'pending' ? 'No pending approvals' : 'No approval queue items'}
          detail={statusFilter === 'pending' ? 'Nothing currently waiting for approval. Use Approved or Denied to see history, or All statuses.' : 'Nothing in the queue. This can be normal when auto-approval or no-write workflows dominate.'}
        />
      ) : !loading && visibleItems.length === 0 ? (
        <StateNotice
          title={statusFilter === 'pending' ? 'No pending approvals' : 'No items match filters'}
          detail={statusFilter === 'pending' ? 'No items are waiting. Switch to Approved, Denied, or All statuses to see history.' : 'Switch to another status filter or All statuses to see items.'}
        />
      ) : (
        <table className="table full-width">
          <thead>
            <tr>
              <th>ID</th>
              <th>Status</th>
              <th>Kind</th>
              <th>Requested by</th>
              <th>Origin</th>
              <th>Timestamp</th>
              <th>Summary / note</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading && visibleItems.length === 0 ? (
              <tr><td colSpan={8} style={{ padding: 24 }}><PageSkeleton label="Loading approvals" rows={3} /></td></tr>
            ) : visibleItems.map((item) => (
              <tr
                key={item.id || `${item.workflow_id}-${item.timestamp}` || item.workflow_id}
                style={highlightedApprovalId && item.id === highlightedApprovalId ? { outline: '2px solid var(--accent)', outlineOffset: '-2px' } : undefined}
              >
                <td>{item.id || '—'}</td>
                <td>{item.status || item.decision || 'pending'}</td>
                <td>{item.kind || 'other'}</td>
                <td>{item.requestedBy || item.requested_by || 'unknown'}</td>
                <td>{item.origin?.label || item.workflow_id || item.workflow || item.chat_id || item.run_id || 'unknown'}</td>
                <td>{formatTimestamp(item.createdAt || item.timestamp)}</td>
                <td>
                  <div>{item.summary || item.rationale || item.title || 'n/a'}</div>
                  {item.review_release_state?.action_hint ? (
                    <div className="muted" style={{ fontSize: 12 }}>
                      next: {item.review_release_state.action_hint}
                    </div>
                  ) : null}
                  {item.review_release_state?.release_blockers?.length ? (
                    <div className="muted" style={{ fontSize: 12 }}>
                      blockers: {item.review_release_state.release_blockers.join(', ')}
                    </div>
                  ) : null}
                  {approvalRefreshContext(item) ? (
                    <div className="muted" style={{ fontSize: 12 }}>
                      refreshed from {approvalRefreshContext(item).fromApprovalId || 'unknown'}{approvalRefreshContext(item).note ? ` · ${approvalRefreshContext(item).note}` : ''}
                      {approvalRefreshContext(item).reasonCodes?.length ? ` · ${approvalRefreshContext(item).reasonCodes.join(', ')}` : ''}
                    </div>
                  ) : null}
                  {approvalResolutionContext(item) ? (
                    <div className="muted" style={{ fontSize: 12 }}>
                      {approvalResolutionContext(item).rationale ? `rationale: ${approvalResolutionContext(item).rationale}` : 'rationale: —'}
                    </div>
                  ) : null}
                  {approvalFollowupSummary(item) ? (
                    <div className="muted" style={{ fontSize: 12 }}>
                      {`follow-up ${approvalFollowupSummary(item).status}`}
                      {approvalFollowupSummary(item).dueAt ? ` · due ${formatTimestamp(approvalFollowupSummary(item).dueAt)}` : ''}
                    </div>
                  ) : null}
                  {item.workflow_status_summary ? (
                    <div className="muted" style={{ fontSize: 12 }}>
                      workflow: {workflowStatusLabel(item.workflow_status_summary)}
                    </div>
                  ) : null}
                </td>
                <td>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    {entityApprovalIdForItem(item) ? (
                      <button type="button" onClick={() => focusApprovalItem(item)}>
                        Open handoff
                      </button>
                    ) : null}
                    {item.review_release_state?.release_blockers?.includes('operational_resume_checkpoint_required')
                      && item.review_release_state?.platform
                      && item.review_release_state?.operational_agent_id ? (
                        <button
                          type="button"
                          disabled={queueActionKey === `${item.id || entityApprovalIdForItem(item) || 'row'}:approve_resume`}
                          onClick={() => runQueueGovernanceAction(item, 'approve_resume')}
                        >
                          {queueActionKey === `${item.id || entityApprovalIdForItem(item) || 'row'}:approve_resume` ? 'Approving…' : 'Approve resume'}
                        </button>
                      ) : null}
                    {item.review_release_state?.release_blockers?.includes('continuity_recovery_ack_required')
                      && item.review_release_state?.continuity_recovery_readiness?.can_acknowledge
                      && !item.review_release_state?.continuity_recovery_readiness?.acknowledged
                      && item.review_release_state?.platform
                      && item.review_release_state?.operational_agent_id ? (
                        <button
                          type="button"
                          disabled={queueActionKey === `${item.id || entityApprovalIdForItem(item) || 'row'}:acknowledge_recovery`}
                          onClick={() => runQueueGovernanceAction(item, 'acknowledge_recovery')}
                        >
                          {queueActionKey === `${item.id || entityApprovalIdForItem(item) || 'row'}:acknowledge_recovery` ? 'Acknowledging…' : 'Acknowledge recovery'}
                        </button>
                      ) : null}
                    {!item.review_release_state?.post_rebuild_continuity_check?.verification_required
                      && item.review_release_state?.platform
                      && item.review_release_state?.operational_agent_id ? (
                        <button
                          type="button"
                          disabled={queueActionKey === `${item.id || entityApprovalIdForItem(item) || 'row'}:record_rebuild`}
                          onClick={() => runQueueGovernanceAction(item, 'record_rebuild')}
                        >
                          {queueActionKey === `${item.id || entityApprovalIdForItem(item) || 'row'}:record_rebuild` ? 'Recording…' : 'Record rebuild'}
                        </button>
                      ) : null}
                    {item.review_release_state?.post_rebuild_continuity_check?.verification_required
                      && !item.review_release_state?.post_rebuild_continuity_check?.verified
                      && item.review_release_state?.platform
                      && item.review_release_state?.operational_agent_id ? (
                        <button
                          type="button"
                          disabled={
                            queueActionKey === `${item.id || entityApprovalIdForItem(item) || 'row'}:verify_rebuild`
                            || item.review_release_state?.post_rebuild_continuity_check?.status === 'blocked'
                          }
                          onClick={() => runQueueGovernanceAction(item, 'verify_rebuild')}
                        >
                          {queueActionKey === `${item.id || entityApprovalIdForItem(item) || 'row'}:verify_rebuild` ? 'Verifying…' : 'Verify rebuild'}
                        </button>
                      ) : null}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {dedup && (
        <section style={{ marginTop: 16 }}>
          <h3>Dedupe ledger</h3>
          <p>
            Workflow: <code>{dedup.workflow_id}</code> | Entries: <strong>{dedup.total ?? 0}</strong> |
            Latest run: <code>{dedup.run_summary?.latest_run_id || 'n/a'}</code> (
            {dedup.run_summary?.latest_status || 'unknown'})
          </p>
          {Array.isArray(dedup.items) && dedup.items.length > 0 ? (
            <table className="table full-width">
              <thead>
                <tr>
                  <th>Idempotency key</th>
                  <th>Tool</th>
                  <th>Timestamp</th>
                  <th>Usage</th>
                </tr>
              </thead>
              <tbody>
                {dedup.items.map((entry) => (
                  <tr key={entry.idempotency_key}>
                    <td><code>{entry.idempotency_key}</code></td>
                    <td>{entry.tool_name || 'n/a'}</td>
                    <td>{formatTimestamp(entry.timestamp)}</td>
                    <td>{JSON.stringify(entry.usage || {})}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p>No dedupe entries for this workflow.</p>
          )}
        </section>
      )}
      <section style={{ marginTop: 24 }}>
        <h3>Evaluate approval</h3>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <input
            value={evalWorkflowId}
            onChange={(e) => setEvalWorkflowId(e.target.value)}
            placeholder="workflow_id"
            style={{ flex: '1 1 220px' }}
          />
          <button type="button" onClick={evaluate}>
            Evaluate
          </button>
        </div>
        {evalResult && (
          <div style={{ marginTop: 8 }}>
            <pre style={{ background: 'var(--panel-2)', padding: 12, marginTop: 8 }}>
              {JSON.stringify(evalResult, null, 2)}
            </pre>
          </div>
        )}
      </section>
    </Layout>
  )
}
