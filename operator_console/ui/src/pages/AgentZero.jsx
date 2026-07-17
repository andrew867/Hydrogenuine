import React, { useCallback, useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import Breadcrumbs from '../components/Breadcrumbs.jsx'
import StateNotice from '../components/StateNotice.jsx'
import { api } from '../lib/api.js'

const STATUS_COLORS = {
  REAL: '#2d6a4f',
  SCAFFOLD: '#b08900',
  STUB: '#9d4edd',
  FUTURE_PHASE: '#6c757d',
  DEGRADED: '#e85d04',
  FAILED: '#d00000',
  DISABLED: '#495057',
  GATED: '#0077b6',
}

function Badge({ status }) {
  const color = STATUS_COLORS[status] || '#495057'
  return (
    <span style={{ background: color, color: '#fff', padding: '2px 8px', borderRadius: 4, fontSize: 12 }}>
      {status}
    </span>
  )
}

function Panel({ title, children }) {
  return (
    <section style={{ border: '1px solid #333', borderRadius: 8, padding: 12, marginBottom: 12 }}>
      <h3 style={{ marginTop: 0 }}>{title}</h3>
      {children}
    </section>
  )
}

export default function AgentZero() {
  const [status, setStatus] = useState(null)
  const [subsystems, setSubsystems] = useState([])
  const [events, setEvents] = useState([])
  const [proposals, setProposals] = useState([])
  const [governance, setGovernance] = useState(null)
  const [arousal, setArousal] = useState(null)
  const [recovery, setRecovery] = useState(null)
  const [execution, setExecution] = useState(null)
  const [maintenance, setMaintenance] = useState(null)
  const [proofs, setProofs] = useState(null)
  const [receipts, setReceipts] = useState([])
  const [err, setErr] = useState(null)
  const [loading, setLoading] = useState(false)
  const [eventFilter, setEventFilter] = useState('')

  const load = useCallback(() => {
    setLoading(true)
    setErr(null)
    Promise.allSettled([
      api.agent0.status(),
      api.agent0.subsystems(),
      api.agent0.events({ limit: 30 }),
      api.agent0.proposals(),
      api.agent0.governance(),
      api.agent0.arousal(),
      api.agent0.recovery(),
      api.agent0.execution(),
      api.agent0.maintenance(),
      api.agent0.proofs(),
      api.agent0.receipts({ limit: 20 }),
    ]).then((results) => {
      const failed = results.find((r) => r.status === 'rejected')
      if (failed) setErr(String(failed.reason))
      if (results[0].status === 'fulfilled') setStatus(results[0].value)
      if (results[1].status === 'fulfilled') setSubsystems(results[1].value?.subsystems || [])
      if (results[2].status === 'fulfilled') setEvents(results[2].value?.events || [])
      if (results[3].status === 'fulfilled') setProposals(results[3].value?.proposals || [])
      if (results[4].status === 'fulfilled') setGovernance(results[4].value)
      if (results[5].status === 'fulfilled') setArousal(results[5].value)
      if (results[6].status === 'fulfilled') setRecovery(results[6].value)
      if (results[7].status === 'fulfilled') setExecution(results[7].value)
      if (results[8].status === 'fulfilled') setMaintenance(results[8].value)
      if (results[9].status === 'fulfilled') setProofs(results[9].value)
      if (results[10].status === 'fulfilled') setReceipts(results[10].value?.receipts || [])
    }).finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load])

  const runAction = async (action, label) => {
    if (!status?.state_hash) return
    if (action === 'panic' && !window.confirm('Confirm PANIC — blocks normal runtime paths?')) return
    try {
      const body = { target_hash: status.state_hash, reason: label }
      const result = await api.agent0[action](body)
      window.alert(result.accepted ? `${label} accepted` : `Refused: ${result.refusal_reason}`)
      load()
    } catch (e) {
      window.alert(`Refused: ${e.message}`)
    }
  }

  const filteredEvents = eventFilter
    ? events.filter((e) => (e.type || '').includes(eventFilter) || (e.summary || '').includes(eventFilter))
    : events

  return (
    <Layout>
      <Breadcrumbs items={[{ label: 'Agent #0', href: '#/agent0' }]} />
      <h1>Agent #0 — Runtime Cockpit</h1>
      <p style={{ opacity: 0.85 }}>
        Operator-visible runtime organism. Not the model. Not unrestricted control. Scaffold/stub status is shown honestly.
      </p>
      {err && <StateNotice variant="error" title="Load error">{String(err)}</StateNotice>}
      {loading && <p>Loading…</p>}

      <Panel title="Runtime pulse">
        {status ? (
          <ul style={{ listStyle: 'none', padding: 0 }}>
            <li>Running: {String(status.runtime_running)} | Paused: {String(status.paused)} | PANIC: {String(status.panic)}</li>
            <li>Ticks: {status.tick_count} | Events: {status.event_count}</li>
            <li>State hash: <code>{status.state_hash}</code></li>
            <li>Replay: <strong>{status.replay_health}</strong>{status.replay_chain_error ? ` — ${status.replay_chain_error}` : ''}</li>
            <li>Governance trace: {status.governance_trace_ok == null ? 'n/a' : String(status.governance_trace_ok)}</li>
          </ul>
        ) : (
          <p>No runtime data — replay unavailable until event log exists.</p>
        )}
      </Panel>

      <Panel title="Subsystem map">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 8 }}>
          {subsystems.map((s) => (
            <div key={s.subsystem} style={{ border: '1px solid #444', padding: 8, borderRadius: 6 }}>
              <strong>{s.subsystem}</strong> <Badge status={s.status} />
              {s.blocked?.length > 0 && <div style={{ fontSize: 12, marginTop: 4 }}>Blocked: {s.blocked.join('; ')}</div>}
            </div>
          ))}
        </div>
      </Panel>

      <Panel title="Cognition proposals (proposal-only)">
        {proposals.length === 0 ? <p>No proposals in current log.</p> : (
          <ul>
            {proposals.map((p, i) => (
              <li key={p.proposal_id || i}>
                <Badge status="REAL" /> PROPOSAL-ONLY · NO TOOL HANDLES — {p.summary || p.proposal_id}
              </li>
            ))}
          </ul>
        )}
      </Panel>

      <Panel title="Governance chain">
        {governance ? (
          <ul>
            <li>GPP traces: {governance.gpp_trace_records} | Permits bound: {governance.permits_bound}</li>
            <li>Enforcement: <code>{governance.enforcement}</code></li>
            <li>Hash chain: {governance.hash_chain_status}</li>
          </ul>
        ) : <p>—</p>}
      </Panel>

      <Panel title="AEP pressure (restrict-only)">
        {arousal ? (
          <ul>
            <li>Max severity: {arousal.max_severity}</li>
            <li>Signals: {arousal.signals_recorded} | Modulations: {arousal.modulations}</li>
            <li>Restrict-only: {String(arousal.restrict_only)} | No authority: {String(arousal.no_authority_granted)}</li>
          </ul>
        ) : <p>—</p>}
      </Panel>

      <Panel title="CRR recovery">
        {recovery ? (
          <ul>
            <li>State: {recovery.recovery_state}</li>
            <li>Handler: {recovery.handler_mode}</li>
            <li>Request recovery: {recovery.request_recovery_allowed ? 'allowed (phase1)' : 'disabled (stub)'}</li>
          </ul>
        ) : <p>—</p>}
      </Panel>

      <Panel title="OEA actuation">
        {execution ? (
          <ul>
            <li>UEAK commits: {execution.ueak_commits} | denied: {execution.ueak_denied}</li>
            <li>No broad shell: {String(execution.no_broad_shell)}</li>
            <li>No network default: {String(execution.no_network_default)}</li>
            <li>No social default: {String(execution.no_social_default)}</li>
          </ul>
        ) : <p>—</p>}
      </Panel>

      <Panel title="SRP maintenance">
        {maintenance ? (
          <ul>
            <li>SRP bundles: {maintenance.srp?.bundles_created ?? 0}</li>
            <li>Approval required: {String(maintenance.approval_required)}</li>
            <li>Max-auto enabled: {String(maintenance.max_auto_enabled)}</li>
            <li>Max-auto last state: {maintenance.max_auto?.last_state || '—'}</li>
          </ul>
        ) : <p>—</p>}
      </Panel>

      <Panel title="Event stream">
        <input
          placeholder="Filter type/summary"
          value={eventFilter}
          onChange={(e) => setEventFilter(e.target.value)}
          style={{ marginBottom: 8, width: '100%' }}
        />
        <ul style={{ maxHeight: 240, overflow: 'auto' }}>
          {filteredEvents.map((e) => (
            <li key={e.event_id || e.seq}><code>{e.type}</code> seq={e.seq} — {e.summary}</li>
          ))}
        </ul>
      </Panel>

      <Panel title="Replay / proofs">
        {proofs ? (
          <ul>
            <li>Replay ok: <strong>{String(proofs.replay_ok)}</strong> (not hardcoded)</li>
            <li>Mismatches: {proofs.replay_mismatches?.length ?? 0}</li>
            <li>Runtime dir: <code>{proofs.runtime_dir}</code></li>
          </ul>
        ) : <p>Replay status unavailable.</p>}
      </Panel>

      <Panel title="Operator actions">
        <p style={{ fontSize: 13 }}>Actions bind to current state hash. Dangerous/scaffold actions refuse without authority.</p>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button type="button" onClick={() => runAction('pause', 'pause')}>Pause</button>
          <button type="button" onClick={() => runAction('resume', 'resume')}>Resume</button>
          <button type="button" style={{ background: '#d00000', color: '#fff' }} onClick={() => runAction('panic', 'panic')}>PANIC</button>
          <button type="button" onClick={() => runAction('requestReplay', 'replay')}>Request replay</button>
          <button type="button" disabled title="Requires HG_CRR_PHASE1_HANDLER" onClick={() => runAction('requestRecovery', 'recovery')}>Request recovery</button>
        </div>
      </Panel>

      <Panel title="Operator receipts">
        {receipts.length === 0 ? <p>No operator actions yet.</p> : (
          <ul>
            {receipts.map((r) => (
              <li key={r.action_id}>
                {r.action_type}: {r.accepted ? 'accepted' : `refused (${r.refusal_reason})`}
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </Layout>
  )
}
