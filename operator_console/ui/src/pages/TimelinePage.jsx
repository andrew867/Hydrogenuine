import React, { useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import Breadcrumbs from '../components/Breadcrumbs.jsx'
import SharedEventSummary from '../components/SharedEventSummary.jsx'
import { api } from '../lib/api.js'
import { formatDateTime } from '../lib/timezone.js'
import StateNotice from '../components/StateNotice.jsx'

function eventSummary(ev) {
  if (!ev) return '—'
  const payload = typeof ev.payload_json === 'string'
    ? (() => { try { return JSON.parse(ev.payload_json) } catch { return {} } })()
    : (ev.payload_json || {})
  const candidates = [
    payload.summary,
    payload.title,
    payload.detail,
    payload.message,
    payload.reason,
    payload.label,
    payload.status,
  ]
  for (const value of candidates) {
    const text = String(value || '').trim()
    if (text) return text
  }
  if (ev.event_type === 'drift.detected') return 'Drift event'
  if (String(ev.event_type || '').startsWith('reflection.artifact.')) return 'Reflection review event'
  return ev.event_type || 'event'
}

export default function TimelinePage() {
  const [runId, setRunId] = useState('')
  const [chatId, setChatId] = useState('')
  const [types, setTypes] = useState('')
  const [events, setEvents] = useState(null)
  const [evidence, setEvidence] = useState(null)
  const [replay, setReplay] = useState(null)
  const [evidencePlane, setEvidencePlane] = useState(null)
  const [activityProjection, setActivityProjection] = useState(null)
  const [err, setErr] = useState(null)
  const [selectedEvent, setSelectedEvent] = useState(null)
  const [loading, setLoading] = useState(false)

  const loadTimeline = () => {
    setErr(null)
    setLoading(true)
    const params = { limit: 100 }
    if (runId) params.run_id = runId
    if (chatId) params.chat_id = chatId
    if (types) params.types = types
    api.gatewayV1.getTimeline(params)
      .then((r) => setEvents(r.events || []))
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false))
  }

  const loadEvidence = () => {
    const params = { limit: 100 }
    if (runId) params.run_id = runId
    if (chatId) params.chat_id = chatId
    api.gatewayV1.getEvidence(params)
      .then((r) => setEvidence(r.evidence || []))
      .catch(() => setEvidence([]))
  }

  const loadReplay = () => {
    if (!runId) return
    api.gatewayV1.getReplay(runId)
      .then((r) => setReplay(r))
      .catch(() => setReplay(null))
  }

  const loadEvidencePlane = () => {
    api.getActivityProjection({ limit_runs: 8, limit_decisions: 12, run_id: runId || undefined, chat_id: chatId || undefined, view: 'expanded' })
      .then((r) => {
        setActivityProjection(r || null)
        setEvidencePlane((r && r.active && r.active.status) ? r.active : null)
      })
      .catch(() => setEvidencePlane(null))
  }

  useEffect(() => {
    loadTimeline()
    loadEvidencePlane()
  }, [])

  const onRun = () => {
    loadTimeline()
    loadEvidence()
    if (runId) loadReplay()
    loadEvidencePlane()
  }

  return (
    <Layout title="Timeline">
      <Breadcrumbs items={[{ label: 'Home', href: '#/' }, { label: 'Timeline' }]} />
      <SharedEventSummary
        eyebrow="Timeline spine"
        title="Timeline"
        intro="This page is the spine. It shows the same event story across runs, chats, approvals, reflections, and recovery."
        status={evidencePlane?.status || activityProjection?.active?.status || 'unknown'}
        statusTone={evidencePlane?.status === 'healthy' ? 'good' : evidencePlane?.status === 'degraded' ? 'danger' : evidencePlane?.status === 'watch' ? 'warn' : 'neutral'}
        happened={evidencePlane?.latest?.title || 'Load a run or chat to focus the timeline.'}
        when={selectedEvent ? formatDateTime(selectedEvent.ts) : (activityProjection?.since_last_wake?.summary || 'No event selected')}
        why="Gateway audit events and the evidence plane are projected into the same story."
        changed={`Runs ${activityProjection?.expanded?.counts?.runs || 0} · decisions ${activityProjection?.expanded?.counts?.decisions || 0} · notifications ${activityProjection?.expanded?.counts?.notifications || 0} · approvals ${activityProjection?.expanded?.counts?.approval_events || 0}`}
        next="Load a run_id or chat_id, then select an event to inspect its payload."
        context={[
          { label: 'Run', value: runId || '—' },
          { label: 'Chat', value: chatId || '—' },
          { label: 'Selected event', value: selectedEvent?.event_type || '—' },
        ]}
      />
      {evidencePlane ? (
        <section style={{ marginBottom: 16, padding: 12, border: '1px solid var(--border)', borderRadius: 12 }}>
          <h2 style={{ fontSize: 16, marginTop: 0 }}>Evidence plane</h2>
          <p style={{ marginBottom: 0, color: 'var(--muted)' }}>
            {activityProjection?.expanded?.counts?.runs || 0} runs, {activityProjection?.expanded?.counts?.decisions || 0} decisions, {activityProjection?.expanded?.counts?.notifications || 0} notifications.
            {' '}
            continuity {activityProjection?.expanded?.counts?.continuity_events || 0}, approvals {activityProjection?.expanded?.counts?.approval_events || 0}.
          </p>
          {activityProjection?.since_last_wake ? (
            <p style={{ marginBottom: 0, color: 'var(--muted)' }}>
              since last wake: {activityProjection.since_last_wake.summary}
            </p>
          ) : null}
          {evidencePlane?.latest ? (
            <p style={{ marginBottom: 0 }}>
              latest: {evidencePlane.latest.title}
              {evidencePlane.latest.detail ? ` · ${evidencePlane.latest.detail}` : ''}
            </p>
          ) : null}
        </section>
      ) : null}
      <section style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          <input
            placeholder="run_id"
            value={runId}
            onChange={(e) => setRunId(e.target.value)}
            style={{ width: 220 }}
          />
          <input
            placeholder="chat_id"
            value={chatId}
            onChange={(e) => setChatId(e.target.value)}
            style={{ width: 220 }}
          />
          <input
            placeholder="event types (comma)"
            value={types}
            onChange={(e) => setTypes(e.target.value)}
            style={{ width: 180 }}
          />
          <button type="button" onClick={onRun}>Load</button>
        </div>
      </section>
      {err && <StateNotice tone="danger" title="Could not load timeline" detail={err} action={<button type="button" onClick={onRun}>Retry</button>} />}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 320px', gap: 16, minHeight: 400 }}>
        <div>
          <h2 style={{ fontSize: 16, marginBottom: 8 }}>Events</h2>
          {loading || events === null ? (
            <StateNotice title="Loading timeline events" detail="Reading recent audit and replay events from the gateway analytics store." />
          ) : events.length === 0 ? (
            <StateNotice title="No timeline events" detail="Try a specific run_id or chat_id, or wait for new chat and DAG activity." />
          ) : (
            <div style={{ overflowX: 'auto', maxWidth: '100%' }}>
            <table width="100%" cellPadding={6} style={{ borderCollapse: 'collapse', fontSize: 13, minWidth: 720 }}>
              <thead>
                <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
                  <th>ts</th>
                  <th>event_type</th>
                  <th>summary</th>
                  <th>run_id / chat_id</th>
                </tr>
              </thead>
              <tbody>
                {events.map((ev) => (
                  <tr
                    key={ev.event_id}
                    style={{
                      borderBottom: '1px solid var(--border)',
                      cursor: 'pointer',
                      background: selectedEvent?.event_id === ev.event_id ? 'var(--surface-hover)' : undefined,
                    }}
                    onClick={() => setSelectedEvent(ev)}
                  >
                    <td>{formatDateTime(ev.ts)}</td>
                    <td>{ev.event_type}</td>
                    <td>{eventSummary(ev)}</td>
                    <td>{ev.run_id || ev.chat_id || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          )}
        </div>
        <div>
          <h2 style={{ fontSize: 16, marginBottom: 8 }}>Event details</h2>
          {selectedEvent ? (
            <div style={{ fontSize: 12, wordBreak: 'break-all' }}>
              <p><strong>event_id</strong> {selectedEvent.event_id}</p>
              {selectedEvent.run_id ? (
                <p><a href={`#/runs/${encodeURIComponent(selectedEvent.run_id)}`}>Open run evidence</a></p>
              ) : null}
              <p><strong>payload_sha256</strong> {selectedEvent.payload_sha256}</p>
              <p><strong>event_sha256</strong> {selectedEvent.event_sha256}</p>
              <pre style={{ whiteSpace: 'pre-wrap', maxHeight: 200, overflow: 'auto', marginTop: 8 }}>
                {typeof selectedEvent.payload_json === 'string'
                  ? selectedEvent.payload_json
                  : JSON.stringify(selectedEvent.payload_json, null, 2)}
              </pre>
            </div>
          ) : (
            <p>Select an event.</p>
          )}
          {replay && runId && (
            <>
              <h3 style={{ fontSize: 14, marginTop: 16 }}>Replay (run_id)</h3>
              <p>chain_ok: {replay.chain_ok ? 'yes' : 'no'}</p>
              {replay.errors?.length > 0 && (
                <ul style={{ margin: 0, paddingLeft: 18 }}>{replay.errors.map((e, i) => <li key={i}>{e}</li>)}</ul>
              )}
            </>
          )}
          {evidence != null && evidence.length > 0 && (
            <>
              <h3 style={{ fontSize: 14, marginTop: 16 }}>Evidence ({evidence.length})</h3>
              <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12 }}>
                {evidence.slice(0, 10).map((e) => (
                  <li key={e.ledger_id}>{e.evidence_type} {e.content_sha256?.slice(0, 12)}…</li>
                ))}
                {evidence.length > 10 && <li>… and {evidence.length - 10} more</li>}
              </ul>
            </>
          )}
        </div>
      </div>
    </Layout>
  )
}
