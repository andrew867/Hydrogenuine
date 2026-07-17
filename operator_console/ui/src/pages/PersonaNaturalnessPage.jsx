import React, { useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import StateNotice from '../components/StateNotice.jsx'
import { api } from '../lib/api.js'

const HISTORY_LIMIT = 8

function MetricCard({ label, value, detail }) {
  return (
    <div className="card">
      <div style={{ color: 'var(--muted)', fontSize: 12, marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 24, fontWeight: 700 }}>{value}</div>
      {detail ? <div style={{ marginTop: 6, color: 'var(--muted)', fontSize: 12 }}>{detail}</div> : null}
    </div>
  )
}

function CompactList({ title, items }) {
  const entries = Object.entries(items || {})
  return (
    <div className="card">
      <h3 style={{ marginTop: 0, marginBottom: 8 }}>{title}</h3>
      {entries.length === 0 ? (
        <div style={{ color: 'var(--muted)', fontSize: 13 }}>No data yet.</div>
      ) : (
        <div style={{ display: 'grid', gap: 6 }}>
          {entries.map(([key, value]) => (
            <div key={key} style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
              <span>{key}</span>
              <strong>{value}</strong>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function PersonaNaturalnessPage() {
  const [personas, setPersonas] = useState([])
  const [operationalItems, setOperationalItems] = useState([])
  const [catalogError, setCatalogError] = useState(null)
  const [loadingCatalog, setLoadingCatalog] = useState(true)
  const [selectedFingerprintId, setSelectedFingerprintId] = useState('')
  const [selectedSkinId, setSelectedSkinId] = useState('')
  const [hours, setHours] = useState('168')
  const [previewPrompt, setPreviewPrompt] = useState('')
  const [candidateResponse, setCandidateResponse] = useState('')
  const [previewResult, setPreviewResult] = useState(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [evalResult, setEvalResult] = useState(null)
  const [evalLoading, setEvalLoading] = useState(false)
  const [summaryResult, setSummaryResult] = useState(null)
  const [autonomySummary, setAutonomySummary] = useState(null)
  const [historyItems, setHistoryItems] = useState([])
  const [autonomyHistoryItems, setAutonomyHistoryItems] = useState([])
  const [effectiveHours, setEffectiveHours] = useState('168')
  const [summaryLoading, setSummaryLoading] = useState(false)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyError, setHistoryError] = useState(null)
  const [swarmRunId, setSwarmRunId] = useState('')
  const [swarmResult, setSwarmResult] = useState(null)
  const [autonomySwarmResult, setAutonomySwarmResult] = useState(null)
  const [swarmLoading, setSwarmLoading] = useState(false)
  const [swarmError, setSwarmError] = useState(null)

  const selectedPersona =
    personas.find((persona) => persona.fingerprint_id === selectedFingerprintId) || null
  const selectedOperationalItem =
    operationalItems.find((item) => item.fingerprint_id === selectedFingerprintId) || null

  const loadCatalog = async () => {
    setCatalogError(null)
    setLoadingCatalog(true)
    try {
      const [response, operationalResponse] = await Promise.all([
        api.listPersonas(),
        api.getOperationalPersonas().catch(() => ({ items: [] })),
      ])
      const rows = response.personas || []
      const operationalRows = operationalResponse.items || []
      setPersonas(rows)
      setOperationalItems(operationalRows)
      if (!selectedFingerprintId && rows.length > 0) {
        const preferredOperational = operationalRows.find((item) => item.fingerprint_id && rows.some((persona) => persona.fingerprint_id === item.fingerprint_id))
        const initialPersona = preferredOperational
          ? rows.find((persona) => persona.fingerprint_id === preferredOperational.fingerprint_id)
          : rows[0]
        setSelectedFingerprintId(initialPersona?.fingerprint_id || '')
        setSelectedSkinId((initialPersona?.skins || [])[0]?.id || '')
      }
    } catch (error) {
      setCatalogError(error.message)
    } finally {
      setLoadingCatalog(false)
    }
  }

  useEffect(() => {
    loadCatalog()
  }, [])

  useEffect(() => {
    if (!selectedFingerprintId) return
    const params = { fingerprint_id: selectedFingerprintId, hours }
    if (selectedSkinId) params.skin_id = selectedSkinId
    let cancelled = false

    const loadAnalytics = async () => {
      setSummaryLoading(true)
      setHistoryError(null)
      let historyHours = String(hours)
      try {
        let summaryParams = params
        let [summaryResponse, autonomySummaryResponse] = await Promise.all([
          api.getPersonaNaturalnessSummary(summaryParams),
          api.getPersonaAutonomySummary(summaryParams),
        ])
        const summaryTurns = summaryResponse.summary?.total_turns || 0
        const autonomyTurns = autonomySummaryResponse.summary?.total_turns || 0
        if (selectedOperationalItem && summaryTurns === 0 && autonomyTurns === 0 && Number(hours) < 720) {
          summaryParams = { ...params, hours: '720' }
          ;[summaryResponse, autonomySummaryResponse] = await Promise.all([
            api.getPersonaNaturalnessSummary(summaryParams),
            api.getPersonaAutonomySummary(summaryParams),
          ])
        }
        if (cancelled) return
        historyHours = String(summaryParams.hours || hours)
        setEffectiveHours(historyHours)
        setSummaryResult(summaryResponse.summary || null)
        setAutonomySummary(autonomySummaryResponse.summary || null)
      } catch (error) {
        if (cancelled) return
        setHistoryError(error.message)
        setEffectiveHours(String(hours))
        setSummaryResult(null)
        setAutonomySummary(null)
      } finally {
        if (!cancelled) setSummaryLoading(false)
      }
      setHistoryLoading(true)
      try {
        const historyParams = { ...params, hours: historyHours, limit: HISTORY_LIMIT }
        const [historyResponse, autonomyHistoryResponse] = await Promise.all([
          api.getPersonaNaturalnessHistory(historyParams),
          api.getPersonaAutonomyHistory(historyParams),
        ])
        if (cancelled) return
        setHistoryItems(historyResponse.history?.items || [])
        setAutonomyHistoryItems(autonomyHistoryResponse.history?.items || [])
      } catch (error) {
        if (cancelled) return
        setHistoryError(error.message)
        setHistoryItems([])
        setAutonomyHistoryItems([])
      } finally {
        if (!cancelled) setHistoryLoading(false)
      }
    }

    loadAnalytics()
    return () => {
      cancelled = true
    }
  }, [selectedFingerprintId, selectedSkinId, hours])

  const handlePreview = async () => {
    if (!selectedFingerprintId || !previewPrompt.trim()) return
    setPreviewLoading(true)
    setPreviewResult(null)
    try {
      const response = await api.previewPersonaNaturalness({
        fingerprint_id: selectedFingerprintId,
        skin_id: selectedSkinId || null,
        user_content: previewPrompt,
        candidate_response: candidateResponse.trim() || null,
      })
      setPreviewResult(response.preview || null)
    } catch (error) {
      setPreviewResult({ error: error.message })
    } finally {
      setPreviewLoading(false)
    }
  }

  const handleEvaluate = async () => {
    if (!selectedFingerprintId || !previewPrompt.trim()) return
    setEvalLoading(true)
    setEvalResult(null)
    try {
      const response = await api.evaluatePersonaNaturalness({
        fingerprint_id: selectedFingerprintId,
        skin_id: selectedSkinId || null,
        scenarios: [
          {
            scenario_id: 'manual_preview',
            user_content: previewPrompt,
            candidate_response: candidateResponse.trim() || '',
          },
          {
            scenario_id: 'followup_variance',
            user_content: `${previewPrompt} Give me the sharper version.`,
            transcript: [{ role: 'assistant', content: candidateResponse.trim() || 'Placeholder response.' }],
            candidate_response: candidateResponse.trim() || '',
          },
        ],
      })
      setEvalResult(response.evaluation || null)
    } catch (error) {
      setEvalResult({ error: error.message })
    } finally {
      setEvalLoading(false)
    }
  }

  const handleLoadSwarm = async () => {
    if (!swarmRunId.trim()) return
    setSwarmLoading(true)
    setSwarmError(null)
    setSwarmResult(null)
    setAutonomySwarmResult(null)
    try {
      const [response, autonomyResponse] = await Promise.all([
        api.getPersonaNaturalnessSwarm(swarmRunId.trim(), { hours }),
        api.getPersonaAutonomySwarm(swarmRunId.trim(), { hours }),
      ])
      setSwarmResult(response.swarm || null)
      setAutonomySwarmResult(autonomyResponse.swarm || null)
    } catch (error) {
      setSwarmError(error.message)
    } finally {
      setSwarmLoading(false)
    }
  }

  return (
    <Layout title="Persona Naturalness">
      <p style={{ marginBottom: 16, color: 'var(--muted)' }}>
        Preview, evaluate, and inspect historical naturalness behavior without digging through raw event logs.
      </p>

      {catalogError ? (
        <StateNotice tone="danger" title="Could not load persona catalog" detail={catalogError} action={<button type="button" onClick={loadCatalog}>Retry</button>} />
      ) : null}
      {loadingCatalog ? (
        <StateNotice title="Loading persona catalog" detail="Fetching fingerprints, skins, and recent analytics." />
      ) : null}
      {!loadingCatalog && !catalogError && personas.length === 0 ? (
        <StateNotice title="No personas available" detail="The persona catalog is empty for this environment." action={<button type="button" onClick={loadCatalog}>Reload</button>} />
      ) : null}

      {!loadingCatalog && operationalItems.length > 0 ? (
        <section style={{ marginBottom: 20 }}>
          <h2 style={{ fontSize: 18, marginBottom: 10 }}>Operational quick picks</h2>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {operationalItems.map((item) => (
              <button
                key={item.platform}
                type="button"
                onClick={() => {
                  if (!item.fingerprint_id) return
                  setSelectedFingerprintId(item.fingerprint_id)
                  const match = personas.find((persona) => persona.fingerprint_id === item.fingerprint_id)
                  setSelectedSkinId((match?.skins || [])[0]?.id || '')
                }}
              >
                {item.platform} · {item.fingerprint_name || item.fingerprint_id || 'unbound'}
              </button>
            ))}
          </div>
        </section>
      ) : null}

      <section style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'end' }}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 4, minWidth: 260 }}>
            <span>Persona</span>
            <select
              value={selectedFingerprintId}
              disabled={loadingCatalog || personas.length === 0}
              onChange={(event) => {
                const value = event.target.value
                setSelectedFingerprintId(value)
                const match = personas.find((persona) => persona.fingerprint_id === value)
                setSelectedSkinId((match?.skins || [])[0]?.id || '')
              }}
            >
              {personas.map((persona) => (
                <option key={persona.fingerprint_id} value={persona.fingerprint_id}>
                  {persona.name} ({persona.fingerprint_id})
                </option>
              ))}
            </select>
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 4, minWidth: 220 }}>
            <span>Skin</span>
            <select value={selectedSkinId} onChange={(event) => setSelectedSkinId(event.target.value)}>
              <option value="">None</option>
              {(selectedPersona?.skins || []).map((skin) => (
                <option key={skin.id} value={skin.id}>
                  {skin.name} ({skin.id})
                </option>
              ))}
            </select>
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 4, minWidth: 140 }}>
            <span>Hours</span>
            <input value={hours} onChange={(event) => setHours(event.target.value)} />
          </label>
        </div>
        {selectedOperationalItem ? (
          <div className="card" style={{ marginTop: 12 }}>
            <strong>{selectedOperationalItem.platform}</strong>
            <div style={{ color: 'var(--muted)', fontSize: 13, marginTop: 6 }}>
              approval posture: {selectedOperationalItem.approval_posture || 'unknown'} · pending approvals: {selectedOperationalItem.pending_approvals ?? 0}
            </div>
            <div style={{ color: 'var(--muted)', fontSize: 13, marginTop: 4 }}>
              session: {selectedOperationalItem.operational_session_target || '—'} · last wake: {selectedOperationalItem.last_wake_at || '—'}
            </div>
            <div style={{ color: 'var(--muted)', fontSize: 12, marginTop: 4 }}>
              analytics window: last {effectiveHours} hours
            </div>
          </div>
        ) : null}
      </section>

      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 18, marginBottom: 12 }}>Summary</h2>
        {historyError ? <StateNotice tone="danger" title="Could not load analytics" detail={historyError} /> : null}
        {summaryLoading ? <StateNotice title="Loading analytics" detail="Fetching summary metrics first, then recent turns." /> : null}
        {summaryResult ? (
          <div style={{ display: 'grid', gap: 12 }}>
            <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))' }}>
              <MetricCard label="Turns" value={summaryResult.total_turns} detail={`${summaryResult.unique_personas} personas`} />
              <MetricCard label="Sample Overlap" value={summaryResult.average_sample_overlap?.toFixed?.(3) ?? summaryResult.average_sample_overlap} />
              <MetricCard label="Recent Overlap" value={summaryResult.average_recent_overlap?.toFixed?.(3) ?? summaryResult.average_recent_overlap} />
              <MetricCard label="Regeneration Rate" value={`${Math.round((summaryResult.regeneration_rate || 0) * 100)}%`} />
              <MetricCard label="Rescue Rate" value={`${Math.round((summaryResult.regeneration_rescue_rate || 0) * 100)}%`} />
              <MetricCard label="Tic Frequency" value={summaryResult.tic_frequency?.toFixed?.(2) ?? summaryResult.tic_frequency} />
            </div>
            <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
              <CompactList title="Entry Points" items={summaryResult.entry_point_distribution} />
              <CompactList title="Stress Mix" items={summaryResult.stress_distribution} />
              <CompactList title="Issue Buckets" items={summaryResult.top_issue_buckets} />
            </div>
            {summaryResult.total_turns === 0 ? (
              <StateNotice title="No naturalness telemetry yet" detail="This persona has no captured naturalness turns in the selected window. The operational quick picks above help jump straight to active runtime personas." />
            ) : null}
          </div>
        ) : null}
        {!summaryLoading && !historyError && !summaryResult ? (
          <StateNotice title="No naturalness summary available" detail="Select an operational persona or widen the time window to load analytics." />
        ) : null}
      </section>

      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 18, marginBottom: 12 }}>Autonomy Summary</h2>
        {autonomySummary ? (
          <div style={{ display: 'grid', gap: 12 }}>
            <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))' }}>
              <MetricCard label="Autonomy Turns" value={autonomySummary.total_turns} />
              <MetricCard label="Callback Rate" value={`${Math.round((autonomySummary.callback_rate || 0) * 100)}%`} />
              <MetricCard label="Notice Rate" value={`${Math.round((autonomySummary.proactive_notice_rate || 0) * 100)}%`} />
              <MetricCard label="Evolution Rate" value={`${Math.round((autonomySummary.position_evolution_rate || 0) * 100)}%`} />
            </div>
            <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
              <CompactList title="Arc States" items={autonomySummary.arc_distribution} />
              <CompactList title="Engagement Modes" items={autonomySummary.engagement_distribution} />
              <CompactList title="Uncertainty Mix" items={autonomySummary.uncertainty_distribution} />
              <CompactList title="Relationships" items={autonomySummary.relationship_distribution} />
            </div>
            {autonomySummary.total_turns === 0 ? (
              <StateNotice title="No autonomy telemetry yet" detail="No autonomy directives have been recorded for this persona in the selected window." />
            ) : null}
          </div>
        ) : null}
        {!summaryLoading && !historyError && !autonomySummary ? (
          <StateNotice title="No autonomy summary available" detail="No autonomy telemetry is available for the current persona selection." />
        ) : null}
      </section>

      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 18, marginBottom: 8 }}>Preview And Evaluate</h2>
        <textarea
          value={previewPrompt}
          onChange={(event) => setPreviewPrompt(event.target.value)}
          placeholder="User prompt for persona preview"
          rows={4}
          style={{ width: '100%', maxWidth: 900, marginBottom: 8 }}
        />
        <textarea
          value={candidateResponse}
          onChange={(event) => setCandidateResponse(event.target.value)}
          placeholder="Optional candidate response to validate"
          rows={4}
          style={{ width: '100%', maxWidth: 900, marginBottom: 8 }}
        />
        <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
          <button type="button" onClick={handlePreview} disabled={previewLoading || !selectedFingerprintId || !previewPrompt.trim()}>
            {previewLoading ? 'Previewing…' : 'Preview'}
          </button>
          <button type="button" onClick={handleEvaluate} disabled={evalLoading || !selectedFingerprintId || !previewPrompt.trim()}>
            {evalLoading ? 'Evaluating…' : 'Evaluate'}
          </button>
        </div>
        {previewResult?.error ? <StateNotice tone="danger" title="Preview failed" detail={previewResult.error} /> : null}
        {previewResult?.turn ? (
          <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))' }}>
            <div className="card">
              <h3 style={{ marginTop: 0 }}>Turn Debug</h3>
              <pre style={{ whiteSpace: 'pre-wrap', fontSize: 12 }}>{JSON.stringify({
                input_assessment: previewResult.turn.input_assessment,
                stress_assessment: previewResult.turn.stress_assessment,
                reasoning_plan: previewResult.turn.reasoning_plan,
                voice_directives: previewResult.turn.voice_directives,
                autonomy: previewResult.autonomy,
              }, null, 2)}</pre>
            </div>
            <div className="card">
              <h3 style={{ marginTop: 0 }}>Prompt Excerpt</h3>
              <pre style={{ whiteSpace: 'pre-wrap', fontSize: 12 }}>{previewResult.turn.system_prompt}</pre>
            </div>
            <div className="card">
              <h3 style={{ marginTop: 0 }}>Validation</h3>
              <pre style={{ whiteSpace: 'pre-wrap', fontSize: 12 }}>{JSON.stringify(previewResult.validation || previewResult.response_blueprint, null, 2)}</pre>
            </div>
          </div>
        ) : null}
        {evalResult?.error ? <StateNotice tone="danger" title="Evaluation failed" detail={evalResult.error} /> : null}
        {evalResult?.results ? (
          <div className="card" style={{ marginTop: 12 }}>
            <h3 style={{ marginTop: 0 }}>Evaluation Summary</h3>
            <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', marginBottom: 12 }}>
              <MetricCard label="Scenarios" value={evalResult.scenario_count} />
              <MetricCard label="Invalid" value={evalResult.invalid_count} />
              <MetricCard label="Sample Overlap" value={evalResult.avg_sample_overlap} />
              <MetricCard label="Recent Overlap" value={evalResult.avg_recent_overlap} />
            </div>
            <div style={{ overflowX: 'auto', maxWidth: '100%' }}>
            <table cellPadding="8" style={{ borderCollapse: 'collapse', width: '100%', minWidth: 760 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)' }}>
                  <th style={{ textAlign: 'left' }}>Scenario</th>
                  <th style={{ textAlign: 'left' }}>Entry</th>
                  <th style={{ textAlign: 'left' }}>Register</th>
                  <th style={{ textAlign: 'left' }}>Stress</th>
                  <th style={{ textAlign: 'left' }}>Arc</th>
                  <th style={{ textAlign: 'left' }}>Uncertainty</th>
                  <th style={{ textAlign: 'left' }}>Issues</th>
                </tr>
              </thead>
              <tbody>
                {evalResult.results.map((result) => (
                  <tr key={result.scenario_id} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td>{result.scenario_id}</td>
                    <td>{result.entry_point}</td>
                    <td>{result.register}</td>
                    <td>{result.stress_level}</td>
                    <td>{result.arc_state || '—'}</td>
                    <td>{result.uncertainty_level || '—'}</td>
                    <td>{(result.validation?.issues || []).join(', ') || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          </div>
        ) : null}
      </section>

      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 18, marginBottom: 8 }}>Recent Autonomy Turns</h2>
        {autonomyHistoryItems.length === 0 && !historyLoading ? (
          <StateNotice title="No recent autonomy turns" detail="Run a few persona turns to populate autonomy traces." />
        ) : null}
        {autonomyHistoryItems.length > 0 ? (
          <div className="card">
            <div style={{ overflowX: 'auto', maxWidth: '100%' }}>
            <table cellPadding="8" style={{ borderCollapse: 'collapse', width: '100%', minWidth: 760 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)' }}>
                  <th style={{ textAlign: 'left' }}>Created</th>
                  <th style={{ textAlign: 'left' }}>Arc</th>
                  <th style={{ textAlign: 'left' }}>Mode</th>
                  <th style={{ textAlign: 'left' }}>Uncertainty</th>
                  <th style={{ textAlign: 'left' }}>Relationship</th>
                </tr>
              </thead>
              <tbody>
                {autonomyHistoryItems.map((item) => (
                  <tr key={item.turn_id} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td>{item.created_at}</td>
                    <td>{item.arc_state}</td>
                    <td>{item.engagement_mode}</td>
                    <td>{item.uncertainty_level}</td>
                    <td>{item.relationship_type || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          </div>
        ) : null}
      </section>

      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 18, marginBottom: 8 }}>Recent Turns</h2>
        {historyItems.length === 0 && !historyLoading ? (
          <StateNotice title="No recent turns" detail="Run a few persona turns or widen the time window to populate analytics." />
        ) : null}
        {historyItems.length > 0 ? (
          <div className="card">
            <div style={{ overflowX: 'auto', maxWidth: '100%' }}>
            <table cellPadding="8" style={{ borderCollapse: 'collapse', width: '100%', minWidth: 760 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)' }}>
                  <th style={{ textAlign: 'left' }}>Created</th>
                  <th style={{ textAlign: 'left' }}>Chat</th>
                  <th style={{ textAlign: 'left' }}>Entry</th>
                  <th style={{ textAlign: 'left' }}>Register</th>
                  <th style={{ textAlign: 'left' }}>Stress</th>
                  <th style={{ textAlign: 'left' }}>Issues</th>
                </tr>
              </thead>
              <tbody>
                {historyItems.map((item) => (
                  <tr key={item.turn_id} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td>{item.created_at}</td>
                    <td><code>{item.chat_id}</code></td>
                    <td>{item.chosen_entry_point}</td>
                    <td>{item.chosen_register}</td>
                    <td>{item.stress_level}</td>
                    <td>{(item.issues || []).map((issue) => issue.issue_code).join(', ') || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          </div>
        ) : null}
      </section>

      <section>
        <h2 style={{ fontSize: 18, marginBottom: 8 }}>Swarm Drill-Down</h2>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
          <input
            value={swarmRunId}
            onChange={(event) => setSwarmRunId(event.target.value)}
            placeholder="Paste swarm_run_id"
            style={{ flex: '1 1 320px' }}
          />
          <button type="button" onClick={handleLoadSwarm} disabled={swarmLoading || !swarmRunId.trim()}>
            {swarmLoading ? 'Loading…' : 'Load swarm'}
          </button>
        </div>
        {swarmError ? <StateNotice tone="danger" title="Could not load swarm analytics" detail={swarmError} /> : null}
        {swarmResult ? (
          <div style={{ display: 'grid', gap: 12 }}>
            <div className="card">
              <h3 style={{ marginTop: 0 }}>Swarm Summary</h3>
              <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))' }}>
                <MetricCard label="Turns" value={swarmResult.summary?.total_turns || 0} />
                <MetricCard label="Members" value={swarmResult.members?.length || 0} />
                <MetricCard label="Sample Overlap" value={swarmResult.summary?.average_sample_overlap?.toFixed?.(3) ?? swarmResult.summary?.average_sample_overlap ?? 0} />
                <MetricCard label="Recent Overlap" value={swarmResult.summary?.average_recent_overlap?.toFixed?.(3) ?? swarmResult.summary?.average_recent_overlap ?? 0} />
              </div>
            </div>
            <div className="card">
              <h3 style={{ marginTop: 0 }}>Members</h3>
              <div style={{ overflowX: 'auto', maxWidth: '100%' }}>
              <table cellPadding="8" style={{ borderCollapse: 'collapse', width: '100%', minWidth: 760 }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border)' }}>
                    <th style={{ textAlign: 'left' }}>Role</th>
                    <th style={{ textAlign: 'left' }}>Chat</th>
                    <th style={{ textAlign: 'left' }}>Persona</th>
                    <th style={{ textAlign: 'left' }}>Turns</th>
                    <th style={{ textAlign: 'left' }}>Entry Mix</th>
                  </tr>
                </thead>
                <tbody>
                  {[swarmResult.orchestrator, ...(swarmResult.members || [])].filter(Boolean).map((item) => (
                    <tr key={`${item.swarm_role}-${item.chat_id}`} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td>{item.swarm_role}</td>
                      <td><code>{item.chat_id}</code></td>
                      <td>{item.fingerprint_id || '—'}</td>
                      <td>{item.turn_count || 0}</td>
                      <td>{Object.entries(item.entry_points || {}).map(([key, value]) => `${key}:${value}`).join(', ') || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              </div>
            </div>
            {autonomySwarmResult ? (
              <div className="card">
                <h3 style={{ marginTop: 0 }}>Autonomy Relationships</h3>
                <div style={{ overflowX: 'auto', maxWidth: '100%' }}>
                <table cellPadding="8" style={{ borderCollapse: 'collapse', width: '100%', minWidth: 760 }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border)' }}>
                      <th style={{ textAlign: 'left' }}>Role</th>
                      <th style={{ textAlign: 'left' }}>Chat</th>
                      <th style={{ textAlign: 'left' }}>Turns</th>
                      <th style={{ textAlign: 'left' }}>Relationships</th>
                      <th style={{ textAlign: 'left' }}>Modes</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[autonomySwarmResult.orchestrator, ...(autonomySwarmResult.members || [])].filter(Boolean).map((item) => (
                      <tr key={`autonomy-${item.swarm_role}-${item.chat_id}`} style={{ borderBottom: '1px solid var(--border)' }}>
                        <td>{item.swarm_role}</td>
                        <td><code>{item.chat_id}</code></td>
                        <td>{item.turn_count || 0}</td>
                        <td>{Object.entries(item.relationship_types || {}).map(([key, value]) => `${key}:${value}`).join(', ') || '—'}</td>
                        <td>{Object.entries(item.engagement_modes || {}).map(([key, value]) => `${key}:${value}`).join(', ') || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                </div>
              </div>
            ) : null}
          </div>
        ) : null}
      </section>
    </Layout>
  )
}
