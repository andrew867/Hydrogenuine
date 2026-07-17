import React, { useCallback, useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import Breadcrumbs from '../components/Breadcrumbs.jsx'
import SharedEventSummary from '../components/SharedEventSummary.jsx'
import { api } from '../lib/api.js'
import StateNotice from '../components/StateNotice.jsx'
import { Modal, JsonViewer } from 'hg_ui_kit'

export default function GovernancePage() {
  const [data, setData] = useState(null)
  const [contracts, setContracts] = useState({})
  const [demoPath, setDemoPath] = useState(null)
  const [researchRuns, setResearchRuns] = useState([])
  const [evidencePlane, setEvidencePlane] = useState(null)
  const [driftReview, setDriftReview] = useState(null)
  const [err, setErr] = useState(null)
  const [loading, setLoading] = useState(false)
  const [receiptVerification, setReceiptVerification] = useState(null)
  const [policyForm, setPolicyForm] = useState({
    policy_key: 'gate_weights_social',
    title: 'Social Gate Weights',
    category: 'gate',
    description: 'Weights for social gate decisions',
    content: '{"required_flags":["benchmark_receipt"]}',
    rationale: 'Start with explicit benchmark evidence',
    change_summary: 'Initial version',
  })
  const [rootForm, setRootForm] = useState({
    workflow_family: 'social-media',
    title: 'Social constitutional root',
    root_goal: 'Advance the remit without losing judgment.',
    material_constraints: 'Do not spam\nDo not drift off remit',
    approved_subgoals: 'Build relationships\nGather signal when needed',
  })
  const [benchmarkForm, setBenchmarkForm] = useState({
    workflow_family: 'social-media',
    title: 'Social gate set',
    description: 'Baseline social benchmark set',
    weights: '{"p_h":0.3,"p_ai":0.2,"p_h_odei":0.5}',
  })
  const [gateCheckWorkflow, setGateCheckWorkflow] = useState('social-media')
  const [selectedDriftRootId, setSelectedDriftRootId] = useState('')
  const [selectedDriftBaselineId, setSelectedDriftBaselineId] = useState('')
  const [gateStatus, setGateStatus] = useState(null)

  const load = useCallback(() => {
    setLoading(true)
    setErr(null)
    const keys = [
      'dashboard', 'policies', 'roots', 'benchmarkSets', 'evaluations', 'receipts',
      'contracts', 'researchRuns', 'gateStatus', 'driftReview', 'activity',
    ]
    Promise.allSettled([
      api.governance.getDashboard(),
      api.governance.listPolicies(),
      api.governance.listConstitutionalRoots(),
      api.governance.listBenchmarkSets(),
      api.governance.listEvaluations({ limit: 12 }),
      api.governance.listReceipts({ limit: 12 }),
      api.governance.getContracts(),
      api.governance.listResearchRuns({ limit: 8 }),
      api.governance.checkGate(gateCheckWorkflow),
      api.governance.getDriftReview({
        workflow_family: gateCheckWorkflow,
        root_id: selectedDriftRootId || undefined,
        baseline_root_id: selectedDriftBaselineId || undefined,
        limit: 8,
      }),
      api.getRecentActivity(8, 12),
    ])
      .then((results) => {
        const failures = []
        const dashboard = results[0].status === 'fulfilled' ? results[0].value : null
        const policies = results[1].status === 'fulfilled' ? results[1].value : null
        const roots = results[2].status === 'fulfilled' ? results[2].value : null
        const benchmarkSets = results[3].status === 'fulfilled' ? results[3].value : null
        const evaluations = results[4].status === 'fulfilled' ? results[4].value : null
        const receipts = results[5].status === 'fulfilled' ? results[5].value : null
        const contractData = results[6].status === 'fulfilled' ? results[6].value : null
        const researchData = results[7].status === 'fulfilled' ? results[7].value : null
        const gateData = results[8].status === 'fulfilled' ? results[8].value : null
        const driftData = results[9].status === 'fulfilled' ? results[9].value : null
        const activityData = results[10].status === 'fulfilled' ? results[10].value : null
        results.forEach((r, i) => { if (r.status === 'rejected') failures.push(keys[i]) })
        setData({
          dashboard: dashboard || { ok: true, counts: { receipts: 0, policies: 0, constitutional_roots: 0, gate_evaluations: 0, research_runs: 0 }, recent_receipts: [], policies: [], constitutional_roots: [], gate_evaluations: [], continuity_quality: { status: 'missing', entity_count: 0, healthy_count: 0, watch_count: 0, blocked_count: 0, average_quality_score: 0, average_coverage_score: 0, average_attribution_score: 0, average_operator_override_rate: 0, average_promotion_accuracy: 0, summary: 'No continuity quality scores available.' } },
          policies: (policies && policies.policies) || [],
          roots: (roots && roots.roots) || [],
          benchmarkSets: (benchmarkSets && benchmarkSets.benchmark_sets) || [],
          evaluations: (evaluations && evaluations.evaluations) || [],
          receipts: (receipts && receipts.receipts) || [],
        })
        setContracts((contractData && contractData.contracts) || {})
        setResearchRuns((researchData && researchData.runs) || [])
        setGateStatus(gateData || null)
        setDriftReview((driftData && driftData.drift_review) || null)
        setEvidencePlane((activityData && activityData.evidence_timeline) || null)
        if (failures.length > 0) setErr(`Some requests failed: ${failures.join(', ')}. Check API key and backend.`)
        else setErr(null)
      })
      .finally(() => setLoading(false))
  }, [gateCheckWorkflow, selectedDriftBaselineId, selectedDriftRootId])

  useEffect(() => {
    load()
  }, [load])

  const submitPolicy = async () => {
    try {
      await api.governance.createPolicyVersion({ ...policyForm, content: JSON.parse(policyForm.content) })
      load()
    } catch (e) {
      setErr(e.message)
    }
  }

  const submitRoot = async () => {
    try {
      await api.governance.upsertConstitutionalRoot({
        ...rootForm,
        material_constraints: rootForm.material_constraints.split('\n').map((v) => v.trim()).filter(Boolean),
        approved_subgoals: rootForm.approved_subgoals.split('\n').map((v) => v.trim()).filter(Boolean),
      })
      load()
    } catch (e) {
      setErr(e.message)
    }
  }

  const submitBenchmarkSet = async () => {
    try {
      await api.governance.createBenchmarkSet({ ...benchmarkForm, weights: JSON.parse(benchmarkForm.weights) })
      load()
    } catch (e) {
      setErr(e.message)
    }
  }

  const runGateCheck = async () => {
    try {
      setGateStatus(await api.governance.checkGate(gateCheckWorkflow))
    } catch (e) {
      setErr(e.message)
    }
  }

  const loadDemoPath = async () => {
    try {
      setDemoPath(await api.governance.getDemoPath(gateCheckWorkflow))
    } catch (e) {
      setErr(e.message)
    }
  }

  const driftRoots = data?.roots || []
  const driftCurrentRoot = driftReview?.root || null
  const driftBaselineRoot = driftReview?.baseline_root || null

  return (
    <Layout title="Governance">
      <Breadcrumbs items={[{ label: 'Home', href: '#/' }, { label: 'Governance' }]} />
      {err && <StateNotice tone="danger" title="Could not load governance" detail={err} action={<button type="button" onClick={load}>Retry</button>} />}
      {data?.dashboard?.backend_error && <StateNotice tone="muted" title="Backend returned empty data" detail={data.dashboard.backend_error} action={<button type="button" onClick={load}>Retry</button>} />}
      {loading && <StateNotice title="Loading governance spine" detail="Reading receipts, policies, constitutional roots, contracts, and governed research state." />}
      <SharedEventSummary
        eyebrow="Governance spine"
        title="Governance"
        intro="This page keeps policy, drift, release gates, continuity quality, and recovery evidence in one story."
        status={gateStatus?.blocked ? 'Blocked' : driftReview?.status || 'unknown'}
        statusTone={gateStatus?.blocked ? 'danger' : driftReview?.status === 'healthy' ? 'good' : driftReview?.status === 'watch' ? 'warn' : 'neutral'}
        happened={gateStatus ? (gateStatus.blocked ? `Gate blocked: ${gateStatus.reason}` : `Gate eligible: ${gateStatus.reason}`) : 'Release gate has not been checked yet.'}
        when={evidencePlane?.latest?.detail || evidencePlane?.latest?.title || 'No evidence timestamp'}
        why="Governance keeps approvals, drift, policy, and continuity aligned before anything looks like it can ship."
        changed={`Receipts ${data?.dashboard?.counts?.receipts ?? 0} · policies ${data?.dashboard?.counts?.policies ?? 0} · roots ${data?.dashboard?.counts?.constitutional_roots ?? 0} · evaluations ${data?.dashboard?.counts?.gate_evaluations ?? 0}`}
        next="Check the gate, review drift, or verify a receipt."
        context={[
          { label: 'Workflow family', value: gateCheckWorkflow },
          { label: 'Drift', value: driftReview?.status || 'unknown' },
          { label: 'Continuity', value: data?.dashboard?.continuity_quality?.status || 'unknown' },
        ]}
        actions={<button type="button" onClick={load}>Refresh governance</button>}
      />
      <div style={{ marginBottom: 12, color: 'var(--muted)', fontSize: 12 }}>
        Home / Governance / Evidence plane / Release gate
      </div>
      <div style={{ display: 'grid', gap: 16 }}>
        <section style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <div className="card"><strong>{data?.dashboard?.counts?.receipts ?? 0}</strong><div className="muted">Receipts</div></div>
          <div className="card"><strong>{data?.dashboard?.counts?.policies ?? 0}</strong><div className="muted">Policies</div></div>
          <div className="card"><strong>{data?.dashboard?.counts?.constitutional_roots ?? 0}</strong><div className="muted">Constitutional roots</div></div>
          <div className="card"><strong>{data?.dashboard?.counts?.gate_evaluations ?? 0}</strong><div className="muted">Gate evaluations</div></div>
          <div className="card"><strong>{data?.dashboard?.counts?.research_runs ?? 0}</strong><div className="muted">Research runs</div></div>
          <button type="button" onClick={load}>Refresh</button>
        </section>

        {evidencePlane ? (
          <section className="card">
            <h3 style={{ marginTop: 0 }}>Evidence plane</h3>
            <p className="muted" style={{ marginBottom: 0 }}>
              {evidencePlane.counts?.runs || 0} runs, {evidencePlane.counts?.decisions || 0} decisions, {evidencePlane.counts?.notifications || 0} notifications.
              {' '}
              continuity {evidencePlane.counts?.continuity_events || 0}, approvals {evidencePlane.counts?.approval_events || 0}, claims {evidencePlane.counts?.support_claims || 0}.
            </p>
            {evidencePlane.latest ? (
              <p style={{ marginBottom: 0 }}>
                latest: {evidencePlane.latest.title}
                {evidencePlane.latest.detail ? ` · ${evidencePlane.latest.detail}` : ''}
              </p>
            ) : null}
          </section>
        ) : null}

        {data?.dashboard?.continuity_quality ? (
          <section className="card">
            <h3 style={{ marginTop: 0 }}>Continuity quality</h3>
            <p className="muted" style={{ marginBottom: 0 }}>
              {data.dashboard.continuity_quality.summary}
            </p>
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginTop: 12 }}>
              <div><strong>{data.dashboard.continuity_quality.healthy_count ?? 0}</strong><div className="muted">Healthy</div></div>
              <div><strong>{data.dashboard.continuity_quality.watch_count ?? 0}</strong><div className="muted">Watch</div></div>
              <div><strong>{data.dashboard.continuity_quality.blocked_count ?? 0}</strong><div className="muted">Blocked</div></div>
              <div><strong>{Number(data.dashboard.continuity_quality.average_quality_score ?? 0).toFixed(1)}</strong><div className="muted">Avg score</div></div>
              <div><strong>{Number(data.dashboard.continuity_quality.average_coverage_score ?? 0).toFixed(2)}</strong><div className="muted">Coverage</div></div>
              <div><strong>{Number(data.dashboard.continuity_quality.average_attribution_score ?? 0).toFixed(2)}</strong><div className="muted">Attribution</div></div>
              <div><strong>{Number(data.dashboard.continuity_quality.average_operator_override_rate ?? 0).toFixed(2)}</strong><div className="muted">Override rate</div></div>
              <div><strong>{Number(data.dashboard.continuity_quality.average_promotion_accuracy ?? 0).toFixed(2)}</strong><div className="muted">Promotion accuracy</div></div>
            </div>
            {data.dashboard.continuity_quality.worst_entities?.length ? (
              <div style={{ marginTop: 12 }}>
                <div className="muted" style={{ marginBottom: 8 }}>Lowest scoring lanes</div>
                <div style={{ display: 'grid', gap: 8 }}>
                  {data.dashboard.continuity_quality.worst_entities.map((item) => (
                    <div key={item.entity_id} style={{ border: '1px solid var(--border)', borderRadius: 12, padding: 12 }}>
                      <strong>{item.display_name || item.entity_id}</strong>
                      <div className="muted">{item.status || 'unknown'} · {Number(item.quality_score ?? 0).toFixed(1)}</div>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
          </section>
        ) : null}

        <section className="card">
          <h3 style={{ marginTop: 0 }}>Mimicry controls</h3>
          {(() => {
            const mimicryPolicy = (data?.policies || []).find((policy) => policy.policy_key === 'mimicry_controls')
            if (!mimicryPolicy) {
              return <p className="muted" style={{ marginBottom: 0 }}>No mimicry policy configured yet. Create one below to cap style depth, emotion, and grounding.</p>
            }
            return (
              <div style={{ display: 'grid', gap: 8 }}>
                <div><strong>{mimicryPolicy.title}</strong></div>
                <div className="muted">{mimicryPolicy.policy_key} · {mimicryPolicy.category}</div>
                <div className="muted">Current: {mimicryPolicy.version_number ? `v${mimicryPolicy.version_number} (${mimicryPolicy.state})` : 'none'}</div>
                <div className="muted">{mimicryPolicy.change_summary || 'No change summary.'}</div>
              </div>
            )
          })()}
        </section>

        <section className="card">
          <h3 style={{ marginTop: 0 }}>Drift review</h3>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'end' }}>
            <label>
              <div className="muted">Current root</div>
              <select value={selectedDriftRootId} onChange={(e) => setSelectedDriftRootId(e.target.value)}>
                <option value="">Latest</option>
                {driftRoots.map((root) => (
                  <option key={root.root_id} value={root.root_id}>
                    {root.workflow_family} · {root.title}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <div className="muted">Baseline</div>
              <select value={selectedDriftBaselineId} onChange={(e) => setSelectedDriftBaselineId(e.target.value)}>
                <option value="">Previous</option>
                {driftRoots.map((root) => (
                  <option key={root.root_id} value={root.root_id}>
                    {root.workflow_family} · {root.title}
                  </option>
                ))}
              </select>
            </label>
            <button type="button" onClick={load}>Refresh</button>
          </div>
          {driftReview ? (
            <div style={{ display: 'grid', gap: 8, marginTop: 12 }}>
              <div><strong>Status:</strong> {driftReview.status}</div>
              <div className="muted">{driftReview.comparison?.summary || 'No comparison available.'}</div>
              <div className="muted">Max score: {Number(driftReview.max_score || 0).toFixed(3)} · Safeguards: {(driftReview.active_safeguards || []).length}</div>
              <div className="muted">
                {driftCurrentRoot ? `${driftCurrentRoot.workflow_family} · ${driftCurrentRoot.title}` : 'No current root'}
                {driftBaselineRoot ? ` vs ${driftBaselineRoot.workflow_family} · ${driftBaselineRoot.title}` : ''}
              </div>
              <div className="muted">Recommended action: {driftReview.recommended_action || 'none'}</div>
              <div style={{ display: 'grid', gap: 8 }}>
                {(driftReview.recent_drift_events || []).map((event) => (
                  <div key={event.event_id} style={{ border: '1px solid var(--border)', borderRadius: 12, padding: 12 }}>
                    <strong>{event.title}</strong>
                    <div className="muted">{event.timestamp} · {event.severity || 'watch'}</div>
                    <div>{event.detail || event.summary || 'Drift event recorded.'}</div>
                    {event.href ? <div className="muted"><a href={event.href}>Open root</a></div> : null}
                  </div>
                ))}
                {!driftReview.recent_drift_events?.length ? <div className="muted">No recent drift events.</div> : null}
              </div>
            </div>
          ) : (
            <div className="muted" style={{ marginTop: 12 }}>No drift review loaded.</div>
          )}
        </section>

        <section className="card">
          <h3 style={{ marginTop: 0 }}>Release gate</h3>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'end' }}>
            <label>
              <div className="muted">Workflow family</div>
              <input value={gateCheckWorkflow} onChange={(e) => setGateCheckWorkflow(e.target.value)} />
            </label>
            <button type="button" onClick={runGateCheck}>Check gate</button>
          </div>
          {gateStatus && (
            <div style={{ marginTop: 12 }}>
              <strong>{gateStatus.blocked ? 'Blocked' : 'Eligible'}</strong>
              <div className="muted">{gateStatus.reason}</div>
              <div className="muted">Environment: {gateStatus.environment} · Backup ok: {String(gateStatus.backup_ok)}</div>
            </div>
          )}
        </section>

        <section className="card">
          <h3 style={{ marginTop: 0 }}>Proof-of-life path</h3>
          <button type="button" onClick={loadDemoPath} style={{ marginBottom: 12 }}>Load example demo path</button>
          {demoPath ? (
            <div style={{ display: 'grid', gap: 8 }}>
              <div><strong>Root exists:</strong> {demoPath.constitutional_root ? 'yes' : 'no'}</div>
              <div><strong>Drift detected:</strong> {demoPath.drift_detected ? 'yes' : 'no'}</div>
              <div><strong>Policy evaluated:</strong> {demoPath.policy_evaluated ? 'yes' : 'no'}</div>
              <div><strong>Gate verdict:</strong> {demoPath.gate_verdict?.verdict || 'none'}</div>
              <div><strong>Receipt visible:</strong> {demoPath.receipt_visible?.receipt_kind || 'none'}</div>
              <div><strong>Export ready:</strong> {demoPath.export_ready ? 'yes' : 'no'}</div>
            </div>
          ) : <div className="muted">No demo path loaded.</div>}
        </section>

        <section className="card">
          <h3 style={{ marginTop: 0 }}>Create policy draft</h3>
          <div style={{ display: 'grid', gap: 8, gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
            <input value={policyForm.policy_key} onChange={(e) => setPolicyForm((s) => ({ ...s, policy_key: e.target.value }))} placeholder="policy key" />
            <input value={policyForm.title} onChange={(e) => setPolicyForm((s) => ({ ...s, title: e.target.value }))} placeholder="title" />
            <input value={policyForm.category} onChange={(e) => setPolicyForm((s) => ({ ...s, category: e.target.value }))} placeholder="category" />
            <input value={policyForm.description} onChange={(e) => setPolicyForm((s) => ({ ...s, description: e.target.value }))} placeholder="description" />
            <input value={policyForm.rationale} onChange={(e) => setPolicyForm((s) => ({ ...s, rationale: e.target.value }))} placeholder="rationale" />
            <input value={policyForm.change_summary} onChange={(e) => setPolicyForm((s) => ({ ...s, change_summary: e.target.value }))} placeholder="change summary" />
          </div>
          <textarea value={policyForm.content} onChange={(e) => setPolicyForm((s) => ({ ...s, content: e.target.value }))} rows={4} style={{ width: '100%', marginTop: 8 }} />
          <button type="button" onClick={submitPolicy} style={{ marginTop: 8 }}>Create draft</button>
          <div style={{ marginTop: 12, display: 'grid', gap: 8 }}>
            {(data?.policies || []).map((policy) => (
              <div key={`${policy.policy_key}-${policy.current_version_id || 'none'}`} style={{ border: '1px solid var(--border)', borderRadius: 12, padding: 12 }}>
                <strong>{policy.title}</strong>
                <div className="muted">{policy.policy_key} · {policy.category}</div>
                <div className="muted">Current: {policy.version_number ? `v${policy.version_number} (${policy.state})` : 'none'}</div>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 8 }}>
                  {policy.current_version_id && <button type="button" onClick={() => api.governance.activatePolicyVersion(policy.current_version_id, 'operator').then(load).catch((e) => setErr(e.message))}>Re-activate current</button>}
                  <button type="button" onClick={() => api.governance.rollbackPolicy(policy.policy_key, 'operator').then(load).catch((e) => setErr(e.message))}>Rollback</button>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="card">
          <h3 style={{ marginTop: 0 }}>Constitutional roots</h3>
          <div style={{ display: 'grid', gap: 8, gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
            <input value={rootForm.workflow_family} onChange={(e) => setRootForm((s) => ({ ...s, workflow_family: e.target.value }))} placeholder="workflow family" />
            <input value={rootForm.title} onChange={(e) => setRootForm((s) => ({ ...s, title: e.target.value }))} placeholder="title" />
            <input value={rootForm.root_goal} onChange={(e) => setRootForm((s) => ({ ...s, root_goal: e.target.value }))} placeholder="root goal" />
          </div>
          <div style={{ display: 'grid', gap: 8, gridTemplateColumns: '1fr 1fr', marginTop: 8 }}>
            <textarea value={rootForm.material_constraints} onChange={(e) => setRootForm((s) => ({ ...s, material_constraints: e.target.value }))} rows={4} />
            <textarea value={rootForm.approved_subgoals} onChange={(e) => setRootForm((s) => ({ ...s, approved_subgoals: e.target.value }))} rows={4} />
          </div>
          <button type="button" onClick={submitRoot} style={{ marginTop: 8 }}>Save constitutional root</button>
          <div style={{ marginTop: 12, display: 'grid', gap: 8 }}>
            {(data?.roots || []).map((root) => (
              <div key={root.root_id} style={{ border: '1px solid var(--border)', borderRadius: 12, padding: 12 }}>
                <strong>{root.title}</strong>
                <div className="muted">{root.workflow_family} · drift {root.drift_severity}</div>
                <div>{root.root_goal}</div>
              </div>
            ))}
          </div>
        </section>

        <section className="card">
          <h3 style={{ marginTop: 0 }}>Gate benchmark sets</h3>
          <div style={{ display: 'grid', gap: 8, gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
            <input value={benchmarkForm.workflow_family} onChange={(e) => setBenchmarkForm((s) => ({ ...s, workflow_family: e.target.value }))} placeholder="workflow family" />
            <input value={benchmarkForm.title} onChange={(e) => setBenchmarkForm((s) => ({ ...s, title: e.target.value }))} placeholder="title" />
            <input value={benchmarkForm.description} onChange={(e) => setBenchmarkForm((s) => ({ ...s, description: e.target.value }))} placeholder="description" />
          </div>
          <textarea value={benchmarkForm.weights} onChange={(e) => setBenchmarkForm((s) => ({ ...s, weights: e.target.value }))} rows={3} style={{ width: '100%', marginTop: 8 }} />
          <button type="button" onClick={submitBenchmarkSet} style={{ marginTop: 8 }}>Create benchmark set</button>
          <div style={{ marginTop: 12, display: 'grid', gap: 8 }}>
            {(data?.benchmarkSets || []).map((setItem) => (
              <div key={setItem.benchmark_set_id} style={{ border: '1px solid var(--border)', borderRadius: 12, padding: 12 }}>
                <strong>{setItem.title}</strong>
                <div className="muted">{setItem.workflow_family}</div>
                <div className="muted">{setItem.description || 'No description'}</div>
              </div>
            ))}
          </div>
        </section>

        <section className="card">
          <h3 style={{ marginTop: 0 }}>Recent evaluations and receipts</h3>
          <div style={{ display: 'grid', gap: 8 }}>
            {(data?.evaluations || []).map((evaluation) => (
              <div key={evaluation.evaluation_id} style={{ border: '1px solid var(--border)', borderRadius: 12, padding: 12 }}>
                <strong>{evaluation.workflow_family}</strong>
                <div className="muted">{evaluation.verdict} · sigma {Number(evaluation.sigma || 0).toFixed(3)} · score {Number(evaluation.weighted_score || 0).toFixed(3)}</div>
              </div>
            ))}
            {(data?.receipts || []).map((receipt) => (
              <div key={receipt.receipt_id} style={{ border: '1px solid var(--border)', borderRadius: 12, padding: 12 }}>
                <strong>{receipt.receipt_kind}</strong>
                <div className="muted">{receipt.subject_kind} · {receipt.subject_id}</div>
                <div className="muted">{receipt.verification_status} · {receipt.created_at}</div>
                <button type="button" onClick={() => api.governance.exportReceipt(receipt.receipt_id).then((payload) => setReceiptVerification(payload.verification || payload)).catch((e) => setErr(e.message))}>Verify/export</button>
              </div>
            ))}
          </div>
        </section>

        <section className="card">
          <h3 style={{ marginTop: 0 }}>Frozen contracts</h3>
          <div style={{ display: 'grid', gap: 8 }}>
            {Object.keys(contracts).map((name) => (
              <div key={name} style={{ border: '1px solid var(--border)', borderRadius: 12, padding: 12 }}>
                <strong>{name}</strong>
                <div className="muted">schema loaded</div>
              </div>
            ))}
            {!Object.keys(contracts).length && <div className="muted">No contract schemas loaded.</div>}
          </div>
        </section>

        <section className="card">
          <h3 style={{ marginTop: 0 }}>Governed research runs</h3>
          <div style={{ display: 'grid', gap: 8 }}>
            {researchRuns.map((run) => (
              <div key={run.research_run_id} style={{ border: '1px solid var(--border)', borderRadius: 12, padding: 12 }}>
                <strong>{run.title}</strong>
                <div className="muted">{run.workspace_kind} · {run.chat_id}</div>
                <div>{run.assistant_excerpt || run.query_text || 'No excerpt'}</div>
              </div>
            ))}
            {!researchRuns.length && <div className="muted">No governed research runs synced yet.</div>}
          </div>
        </section>
      </div>
      <Modal open={!!receiptVerification} onClose={() => setReceiptVerification(null)}>
        <div style={{ padding: 16, maxWidth: 720 }}>
          <h2 style={{ marginTop: 0 }}>Receipt verification</h2>
          <JsonViewer value={receiptVerification || {}} />
          <div style={{ marginTop: 12 }}>
            <button type="button" onClick={() => setReceiptVerification(null)}>Close</button>
          </div>
        </div>
      </Modal>
    </Layout>
  )
}
