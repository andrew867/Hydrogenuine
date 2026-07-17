import React, { useEffect, useMemo, useState } from 'react'
import Layout from '../components/Layout.jsx'
import Breadcrumbs from '../components/Breadcrumbs.jsx'
import SharedEventSummary from '../components/SharedEventSummary.jsx'
import StateNotice from '../components/StateNotice.jsx'
import { api } from '../lib/api.js'

function safeJsonParse(value, fallback) {
  try {
    return value ? JSON.parse(value) : fallback
  } catch (_) {
    return fallback
  }
}

function trustLevel(record, payload) {
  const latestStatus = String(record?.latest_status || record?.verification_status || payload?.verification_status || 'unknown').toLowerCase()
  const confidence = Number(payload?.confidence ?? record?.confidence ?? 0)
  if (latestStatus === 'promoted' && confidence >= 0.8) return 'trusted'
  if (latestStatus === 'promoted' || latestStatus === 'escalated') return 'reviewed'
  if (latestStatus === 'discarded') return 'rejected'
  if (confidence >= 0.7) return 'provisional'
  return 'needs review'
}

function nextStepGuidance(record, payload) {
  const latestStatus = String(record?.latest_status || record?.verification_status || payload?.verification_status || 'unknown').toLowerCase()
  const confidence = Number(payload?.confidence ?? record?.confidence ?? 0)
  const sourceCount = Array.isArray(payload?.source_links) ? payload.source_links.length : 0
  if (latestStatus === 'promoted') {
    return 'Keep it in trusted review and watch for a newer cycle.'
  }
  if (latestStatus === 'escalated') {
    return 'Assign a human follow-up and keep the artifact out of trusted memory.'
  }
  if (latestStatus === 'discarded') {
    return 'Leave it rejected unless new evidence changes the call.'
  }
  if (confidence >= 0.7 && sourceCount > 0) {
    return 'Review the sources and promote only if the finding still holds.'
  }
  return 'Add sources and verification before promotion.'
}

export default function ReflectionArtifactsPage() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [runningCycles, setRunningCycles] = useState(false)
  const [reviewingAction, setReviewingAction] = useState('')
  const [error, setError] = useState('')
  const [records, setRecords] = useState([])
  const [selectedId, setSelectedId] = useState('')
  const [selected, setSelected] = useState(null)
  const [cycleStatus, setCycleStatus] = useState(null)
  const [reviewedBy, setReviewedBy] = useState('operator_console')
  const [reviewNote, setReviewNote] = useState('')
  const [form, setForm] = useState({
    artifact_id: '',
    title: '',
    summary: '',
    confidence: '0.5',
    verification_status: 'provisional',
    reviewed_by: '',
    promoted_at: '',
    source_event_ids: '[]',
    source_memory_ids: '[]',
    source_links: '[]',
    findings_json: '{\n  "summary": ""\n}',
  })

  const selectedVersions = useMemo(() => selected?.versions || [], [selected])
  const selectedPayload = useMemo(() => {
    if (!selected?.payload_json) return {}
    if (typeof selected.payload_json === 'string') return safeJsonParse(selected.payload_json, {})
    return selected.payload_json || {}
  }, [selected])

  useEffect(() => {
    const nextReviewedBy = selectedPayload.reviewed_by || selected?.reviewed_by || 'operator_console'
    setReviewedBy(String(nextReviewedBy || 'operator_console'))
    setReviewNote('')
  }, [selectedPayload.reviewed_by, selected?.reviewed_by, selectedId])

  const load = async (preferredId = selectedId) => {
    setLoading(true)
    setError('')
    try {
      const payload = await api.getReflectionArtifacts()
      const nextRecords = payload?.artifacts || []
      const cyclePayload = await api.getReflectionCycleStatus()
      setRecords(nextRecords)
      setCycleStatus(cyclePayload || null)
      const nextId = preferredId || nextRecords[0]?.artifact_id || ''
      setSelectedId(nextId)
      if (nextId) {
        const detail = await api.getReflectionArtifact(nextId)
        setSelected(detail?.artifact || null)
      } else {
        setSelected(null)
      }
    } catch (err) {
      setError(err?.message || 'Could not load reflection artifacts')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const handleSubmit = async (event) => {
    event.preventDefault()
    setSaving(true)
    setError('')
    try {
      const payload = {
        artifact_id: form.artifact_id.trim(),
        title: form.title.trim(),
        summary: form.summary.trim(),
        confidence: Number(form.confidence || 0),
        verification_status: form.verification_status.trim() || 'provisional',
        reviewed_by: form.reviewed_by.trim() || null,
        promoted_at: form.promoted_at.trim() || null,
        source_event_ids: safeJsonParse(form.source_event_ids, []),
        source_memory_ids: safeJsonParse(form.source_memory_ids, []),
        source_links: safeJsonParse(form.source_links, []),
        findings_json: safeJsonParse(form.findings_json, {}),
      }
      const created = await api.createReflectionArtifact(payload)
      const nextId = created?.artifact?.artifact_id || payload.artifact_id
      await load(nextId)
      setForm((current) => ({
        ...current,
        artifact_id: '',
        title: '',
        summary: '',
        reviewed_by: '',
        promoted_at: '',
        source_event_ids: '[]',
        source_memory_ids: '[]',
        source_links: '[]',
        findings_json: '{\n  "summary": ""\n}',
      }))
    } catch (err) {
      setError(err?.message || 'Could not create reflection artifact')
    } finally {
      setSaving(false)
    }
  }

  const handleRunCycles = async () => {
    setRunningCycles(true)
    setError('')
    try {
      await api.runReflectionCycles({ force: true })
      await load()
    } catch (err) {
      setError(err?.message || 'Could not run reflection cycles')
    } finally {
      setRunningCycles(false)
    }
  }

  const runReviewAction = async (action) => {
    if (!selectedId) return
    setReviewingAction(action)
    setError('')
    try {
      const body = {
        reviewed_by: reviewedBy.trim() || 'operator_console',
        note: reviewNote.trim() || `${action} from reflection artifacts page`,
      }
      if (action === 'promote') {
        await api.promoteReflectionArtifact(selectedId, body)
      } else if (action === 'discard') {
        await api.discardReflectionArtifact(selectedId, body)
      } else if (action === 'escalate') {
        await api.escalateReflectionArtifact(selectedId, body)
      }
      await load(selectedId)
    } catch (err) {
      setError(err?.message || `Could not ${action} reflection artifact`)
    } finally {
      setReviewingAction('')
    }
  }

  return (
    <Layout title="Reflections">
      <Breadcrumbs items={[{ label: 'Home', href: '#/' }, { label: 'Reflections' }]} />
      {error ? <StateNotice tone="danger" title="Could not load reflection artifacts" detail={error} action={<button type="button" onClick={load}>Retry</button>} /> : null}
      {loading ? <StateNotice title="Loading reflection artifacts" detail="Reading typed reflection records from the gateway registry." /> : null}

      <SharedEventSummary
        eyebrow="Reflection store"
        title="Reflections"
        intro="Typed reflection artifacts stay provisional until promoted, and review actions stay in the same event trail."
        status={selected?.latest_status || selected?.verification_status || 'unknown'}
        statusTone={selected?.latest_status === 'promoted' ? 'good' : selected?.latest_status === 'discarded' ? 'danger' : selected?.latest_status === 'escalated' ? 'warn' : 'neutral'}
        happened={selected?.title || 'Create a reflection or pick one from the store.'}
        when={selectedVersions[0]?.created_at || cycleStatus?.ts || 'No cycle timestamp'}
        why="Reflection cycles make source-linked artifacts available for operator review before they become trusted memory."
        changed={`Artifacts ${records.length} · selected versions ${selectedVersions.length} · promoted ${records.filter((item) => item.latest_status === 'promoted').length} · cycle failures ${(cycleStatus?.cycles || []).filter((item) => item.status === 'failed').length}`}
        next={selected ? nextStepGuidance(selected, selectedPayload) : 'Run reflection cycles or create a reflection artifact to seed the store.'}
        context={[
          { label: 'Selected artifact', value: selectedId || 'none' },
          { label: 'Trust level', value: selected ? trustLevel(selected, selectedPayload) : '—' },
          { label: 'Cycles due', value: (cycleStatus?.cycles || []).filter((item) => item.due).length },
        ]}
        actions={(
          <button type="button" onClick={handleRunCycles} disabled={runningCycles}>
            {runningCycles ? 'Running cycles…' : 'Run reflection cycles'}
          </button>
        )}
      />

      <section className="section-card" style={{ marginBottom: 16 }}>
        <div className="eyebrow">Reflection registry</div>
        <h2 style={{ margin: '6px 0 8px' }}>Inspect the store, then create or promote what belongs in review.</h2>
        <p className="muted" style={{ margin: 0, maxWidth: 900 }}>
          Reflection artifacts stay provisional until promoted. Their confidence, verification status, source links,
          and provenance live in the gateway registry rather than trusted memory.
        </p>
        <div style={{ display: 'flex', gap: 12, marginTop: 16, flexWrap: 'wrap' }}>
          <button type="button" onClick={handleRunCycles} disabled={runningCycles}>
            {runningCycles ? 'Running cycles…' : 'Run reflection cycles'}
          </button>
          <div className="muted" style={{ alignSelf: 'center' }}>
            {cycleStatus?.cycles?.length || 0} cycle definitions · {(cycleStatus?.cycles || []).filter((item) => item.due).length} due
          </div>
        </div>
      </section>

      <div className="card-grid" style={{ marginBottom: 16 }}>
        <div className="card"><strong>{records.length}</strong><div className="muted">Reflections</div></div>
        <div className="card"><strong>{selectedVersions.length}</strong><div className="muted">Selected versions</div></div>
        <div className="card"><strong>{records.filter((item) => item.latest_status === 'promoted').length}</strong><div className="muted">Promoted</div></div>
        <div className="card"><strong>{(cycleStatus?.cycles || []).filter((item) => item.status === 'failed').length}</strong><div className="muted">Cycle failures</div></div>
      </div>

      {cycleStatus?.errors?.length ? (
        <section className="section-card" style={{ marginBottom: 16 }}>
          <div className="eyebrow">Cycle telemetry</div>
          <h3 style={{ marginTop: 0 }}>Recent reflection cycle issues</h3>
          <div style={{ display: 'grid', gap: 8 }}>
            {cycleStatus.errors.map((item) => (
              <div key={`${item.cycle}-${item.error}`} className="card">
                <strong>{item.title || item.cycle}</strong>
                <div className="muted">{item.status || 'failed'}</div>
                <div style={{ marginTop: 4 }}>{item.error}</div>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {cycleStatus?.cycles?.length ? (
        <section className="section-card" style={{ marginBottom: 16 }}>
          <div className="eyebrow">Reflection cycles</div>
          <h3 style={{ marginTop: 0 }}>Scheduled reflection jobs and cooldown state.</h3>
          <div className="card-grid">
            {cycleStatus.cycles.map((cycle) => (
              <div key={cycle.cycle} className="card">
                <div className="eyebrow">{cycle.status || 'unknown'}</div>
                <strong>{cycle.title}</strong>
                <div className="muted" style={{ fontSize: 12 }}>{cycle.cycle}</div>
                <div style={{ marginTop: 8, display: 'grid', gap: 4 }}>
                  <div><span className="muted">Due:</span> {cycle.due ? 'yes' : 'no'}</div>
                  <div><span className="muted">Cooldown:</span> {cycle.cooldown_remaining_seconds == null ? 'ready' : `${cycle.cooldown_remaining_seconds}s`}</div>
                  <div><span className="muted">Last run:</span> {cycle.last_run_at || '—'}</div>
                  <div><span className="muted">Last error:</span> {cycle.last_error || '—'}</div>
                </div>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      <div className="split-grid" style={{ marginBottom: 16 }}>
        <section className="section-card">
          <h3 style={{ marginTop: 0 }}>Create reflection</h3>
          <form onSubmit={handleSubmit} style={{ display: 'grid', gap: 12 }}>
            <label className="stack" style={{ display: 'grid', gap: 4 }}>
              <span className="eyebrow">Artifact ID</span>
              <input value={form.artifact_id} onChange={(event) => setForm({ ...form, artifact_id: event.target.value })} placeholder="reflection:entity:cycle:001" />
            </label>
            <label className="stack" style={{ display: 'grid', gap: 4 }}>
              <span className="eyebrow">Title</span>
              <input value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} placeholder="Reflection title" />
            </label>
            <label className="stack" style={{ display: 'grid', gap: 4 }}>
              <span className="eyebrow">Summary</span>
              <textarea value={form.summary} onChange={(event) => setForm({ ...form, summary: event.target.value })} rows={3} placeholder="Short reflection summary" />
            </label>
            <div className="card-grid">
              <label className="stack" style={{ display: 'grid', gap: 4 }}>
                <span className="eyebrow">Confidence</span>
                <input type="number" step="0.05" min="0" max="1" value={form.confidence} onChange={(event) => setForm({ ...form, confidence: event.target.value })} />
              </label>
              <label className="stack" style={{ display: 'grid', gap: 4 }}>
                <span className="eyebrow">Verification</span>
                <input value={form.verification_status} onChange={(event) => setForm({ ...form, verification_status: event.target.value })} placeholder="provisional" />
              </label>
            </div>
            <div className="card-grid">
              <label className="stack" style={{ display: 'grid', gap: 4 }}>
                <span className="eyebrow">Reviewed by</span>
                <input value={form.reviewed_by} onChange={(event) => setForm({ ...form, reviewed_by: event.target.value })} placeholder="operator or reviewer" />
              </label>
              <label className="stack" style={{ display: 'grid', gap: 4 }}>
                <span className="eyebrow">Promoted at</span>
                <input value={form.promoted_at} onChange={(event) => setForm({ ...form, promoted_at: event.target.value })} placeholder="2026-03-24T00:00:00Z" />
              </label>
            </div>
            <label className="stack" style={{ display: 'grid', gap: 4 }}>
              <span className="eyebrow">Source event IDs JSON</span>
              <textarea value={form.source_event_ids} onChange={(event) => setForm({ ...form, source_event_ids: event.target.value })} rows={2} />
            </label>
            <label className="stack" style={{ display: 'grid', gap: 4 }}>
              <span className="eyebrow">Source memory IDs JSON</span>
              <textarea value={form.source_memory_ids} onChange={(event) => setForm({ ...form, source_memory_ids: event.target.value })} rows={2} />
            </label>
            <label className="stack" style={{ display: 'grid', gap: 4 }}>
              <span className="eyebrow">Source links JSON</span>
              <textarea value={form.source_links} onChange={(event) => setForm({ ...form, source_links: event.target.value })} rows={3} />
            </label>
            <label className="stack" style={{ display: 'grid', gap: 4 }}>
              <span className="eyebrow">Findings JSON</span>
              <textarea value={form.findings_json} onChange={(event) => setForm({ ...form, findings_json: event.target.value })} rows={6} />
            </label>
            <button type="submit" disabled={saving || !form.artifact_id.trim() || !form.title.trim() || !form.summary.trim()}>
              {saving ? 'Saving…' : 'Save reflection'}
            </button>
          </form>
        </section>

        <section className="section-card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
            <h3 style={{ marginTop: 0 }}>Reflections</h3>
            <button type="button" onClick={() => load()}>
              Refresh
            </button>
          </div>
          <div style={{ display: 'grid', gap: 10 }}>
            {records.map((item) => (
              <button
                key={item.artifact_id}
                type="button"
                onClick={() => setSelectedId(item.artifact_id) || void load(item.artifact_id)}
                className={`card ${selectedId === item.artifact_id ? 'card-selected' : ''}`}
                style={{ textAlign: 'left' }}
              >
                <div className="eyebrow">{item.verification_status || item.latest_status || 'unknown'}</div>
                <div style={{ fontWeight: 700 }}>{item.title}</div>
                <div className="muted" style={{ fontSize: 12 }}>{item.artifact_id}</div>
              </button>
            ))}
            {records.length === 0 ? <StateNotice title="No reflections yet" detail="Create one with the form to seed the DB-backed store." /> : null}
          </div>
        </section>
      </div>

      {selected ? (
        <section className="section-card">
          <h3 style={{ marginTop: 0 }}>{selected.title}</h3>
          <div className="muted" style={{ fontSize: 12, marginBottom: 12 }}>{selected.artifact_id}</div>
          <div className="card-grid">
            <div className="card"><div className="eyebrow">Confidence</div><div>{selectedPayload.confidence ?? selected.confidence ?? '—'}</div></div>
            <div className="card"><div className="eyebrow">Status</div><div>{selected.latest_status || selected.verification_status || 'unknown'}</div></div>
            <div className="card"><div className="eyebrow">Reviewed by</div><div>{selectedPayload.reviewed_by || selected.reviewed_by || '—'}</div></div>
            <div className="card"><div className="eyebrow">Source links</div><div>{(selectedPayload.source_links || []).length}</div></div>
            <div className="card"><div className="eyebrow">Trust level</div><div>{trustLevel(selected, selectedPayload)}</div></div>
          </div>
          <div className="card" style={{ marginTop: 16 }}>
            <div className="eyebrow">Review flow</div>
            <div className="muted" style={{ marginTop: 4 }}>
              Promote keeps the artifact in trusted review, discard marks it rejected, and escalate marks it for manual follow-up. Each action writes a new version and emits an activity event.
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <label className="stack" style={{ display: 'grid', gap: 4 }}>
                <span className="eyebrow">Reviewed by</span>
                <input value={reviewedBy} onChange={(event) => setReviewedBy(event.target.value)} placeholder="operator_console" />
              </label>
              <label className="stack" style={{ display: 'grid', gap: 4 }}>
                <span className="eyebrow">Review note</span>
                <input value={reviewNote} onChange={(event) => setReviewNote(event.target.value)} placeholder="Optional audit note" />
              </label>
            </div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 12 }}>
              <button type="button" disabled={reviewingAction === 'promote'} onClick={() => runReviewAction('promote')}>
                {reviewingAction === 'promote' ? 'Promoting…' : 'Promote'}
              </button>
              <button type="button" disabled={reviewingAction === 'discard'} onClick={() => runReviewAction('discard')}>
                {reviewingAction === 'discard' ? 'Discarding…' : 'Discard'}
              </button>
              <button type="button" disabled={reviewingAction === 'escalate'} onClick={() => runReviewAction('escalate')}>
                {reviewingAction === 'escalate' ? 'Escalating…' : 'Escalate'}
              </button>
            </div>
            <div className="card" style={{ marginTop: 12 }}>
              <div className="eyebrow">Next step</div>
              <div>{nextStepGuidance(selected, selectedPayload)}</div>
            </div>
          </div>
          <div style={{ display: 'grid', gap: 12, marginTop: 16 }}>
            <div className="card">
              <div className="eyebrow">Summary</div>
              <div>{selectedPayload.summary || selected.summary || '—'}</div>
            </div>
            <div className="card">
              <div className="eyebrow">Findings</div>
              <pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{JSON.stringify(selectedPayload.findings_json || selected.findings_json || {}, null, 2)}</pre>
            </div>
            <div className="card">
              <div className="eyebrow">Source links</div>
              <ul style={{ margin: '8px 0 0 18px' }}>
                {(selectedPayload.source_links || []).map((link, idx) => (
                  <li key={`${link.href || idx}-${idx}`}>
                    <strong>{link.kind || 'link'}</strong>{link.href ? ` · ${link.href}` : ''}{link.label ? ` · ${link.label}` : ''}
                  </li>
                ))}
              </ul>
            </div>
            <div className="card">
              <div className="eyebrow">Versions</div>
              <div style={{ display: 'grid', gap: 8 }}>
                {selectedVersions.map((version) => (
                  <div key={version.version_id} className="card">
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
                      <strong>v{version.version_number}</strong>
                      <span className="muted">{version.state}</span>
                    </div>
                    <div className="muted" style={{ fontSize: 12 }}>{version.change_summary || version.created_at}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>
      ) : null}
    </Layout>
  )
}
