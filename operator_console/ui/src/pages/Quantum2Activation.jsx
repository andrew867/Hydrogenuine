import React, { useCallback, useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import Breadcrumbs from '../components/Breadcrumbs.jsx'
import StateNotice from '../components/StateNotice.jsx'
import { PageSkeleton } from '../components/PageStates.jsx'
import { api } from '../lib/api.js'

const MODE_LABEL = {
  off: 'Off',
  shadow: 'Shadow',
  live: 'Live',
  canary: 'Canary',
}

function recommendationTone(rec) {
  if (rec === 'eligible_for_staged_activation') return 'success'
  if (rec === 'stay_shadow') return 'warning'
  return 'muted'
}

export default function Quantum2Activation() {
  const [state, setState] = useState(null)
  const [history, setHistory] = useState([])
  const [selected, setSelected] = useState(null)
  const [divergence, setDivergence] = useState(null)
  const [err, setErr] = useState(null)
  const [loading, setLoading] = useState(true)
  const [rationale, setRationale] = useState('')
  const [signOff, setSignOff] = useState(false)
  const [msg, setMsg] = useState(null)
  const [goNoGo, setGoNoGo] = useState(null)
  const [liveSummary, setLiveSummary] = useState(null)
  const [workloadRunning, setWorkloadRunning] = useState(false)
  const [validationReport, setValidationReport] = useState(null)
  const [validationRunning, setValidationRunning] = useState(false)

  const load = useCallback(() => {
    setErr(null)
    setLoading(true)
    Promise.all([api.getQuantum2ActivationState(), api.getQuantum2ActivationHistory()])
      .then(([dashboard, hist]) => {
        setState(dashboard)
        setHistory(hist.entries || [])
      })
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load])

  const loadDivergence = (component) => {
    setSelected(component)
    setDivergence(null)
    api.getQuantum2Divergence(component)
      .then((data) => setDivergence(data))
      .catch((e) => setErr(e.message))
  }

  const act = (fn) => {
    setMsg(null)
    setErr(null)
    fn()
      .then((data) => {
        setMsg(`${data.component}: now ${data.mode || 'updated'}`)
        load()
        if (selected) loadDivergence(selected)
      })
      .catch((e) => setErr(e.message))
  }

  const modules = state?.modules || []
  const cg = state?.control_group || {}

  return (
    <Layout title="Quantum-2 activation">
      <Breadcrumbs
        items={[
          { label: 'Home', href: '#/home' },
          { label: 'Governance', href: '#/governance' },
          { label: 'Quantum-2 activation' },
        ]}
      />
      <h1>Quantum-2 staged activation</h1>
      <p>
        Operator-driven shadow → live flips per module. Gate memo:
        {' '}
        <code>docs/reports/quantum2_experiment_gate_results.md</code>
      </p>
      <div style={{ marginBottom: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <button type="button" onClick={load}>Refresh</button>
        <button
          type="button"
          disabled={workloadRunning}
          onClick={() => {
            setWorkloadRunning(true)
            setMsg(null)
            api.runQuantum2ShadowWorkloads()
              .then((data) => {
                setGoNoGo(data.go_no_go)
                setMsg(`Shadow workloads: ${data.batch?.runs?.length ?? 0} runs, ${data.batch?.shadow_summary?.total_events ?? 0} events`)
                load()
              })
              .catch((e) => setErr(e.message))
              .finally(() => setWorkloadRunning(false))
          }}
        >
          {workloadRunning ? 'Running workloads…' : 'Run production shadow workloads'}
        </button>
        <button
          type="button"
          onClick={() => act(() => api.flipQuantum2CodecLive({ rationale, actor_id: 'operator' }))}
        >
          Flip fingerprint_codec live
        </button>
        <button
          type="button"
          disabled={validationRunning}
          onClick={() => {
            setValidationRunning(true)
            setMsg(null)
            setErr(null)
            api.runQuantum2ProductionValidation()
              .then((data) => {
                setValidationReport(data.divergence_report)
                setMsg(`Production validation: ${data.divergence_report?.ok ? 'pass' : 'review'} — ${data.runs?.length ?? 0} workloads`)
                load()
              })
              .catch((e) => setErr(e.message))
              .finally(() => setValidationRunning(false))
          }}
        >
          {validationRunning ? 'Validating…' : 'Run production validation'}
        </button>
        <button
          type="button"
          onClick={() => {
            api.getQuantum2ValidationStatus()
              .then((data) => setValidationReport(data.divergence_report))
              .catch((e) => setErr(e.message))
          }}
        >
          Validation status
        </button>
        <button
          type="button"
          onClick={() => {
            setMsg(null)
            setErr(null)
            api.flipQuantum2ShadowFirstLive({ rationale, actor_id: 'operator' })
              .then((data) => {
                const verified = (data.verifications || []).filter((v) => v.live_verified).length
                setMsg(`Shadow_first live: ${verified}/${(data.verifications || []).length} verified`)
                load()
              })
              .catch((e) => setErr(e.message))
          }}
        >
          Flip shadow_first modules live
        </button>
      </div>
      {err && <StateNotice tone="danger" title="Activation error" detail={err} />}
      {msg && <StateNotice tone="success" title="Updated" detail={msg} />}
      {loading ? <PageSkeleton label="Loading activation state" /> : null}
      {!loading && state && (
        <>
          {liveSummary?.live_modules?.length > 0 && (
            <section style={{ marginBottom: 24 }}>
              <h2>Live modules</h2>
              <p style={{ color: '#64748b' }}>
                {liveSummary.live_count} live:
                {' '}
                {liveSummary.live_modules.join(', ')}
              </p>
            </section>
          )}
          <section style={{ marginBottom: 24 }}>
            <h2>Control group (L3)</h2>
            <p style={{ color: '#64748b' }}>
              Treatment: {cg.treatment_total ?? 0} · Control: {cg.control_total ?? 0}
              {' '}
              · Shadow events total: {state.shadow_summary?.total_events ?? 0}
            </p>
          </section>
          {validationReport?.checks && (
            <section style={{ marginBottom: 24 }}>
              <h2>Post-live validation</h2>
              <p style={{ color: '#64748b' }}>
                Status: {validationReport.ok ? 'pass' : 'review'}
                {' '}
                · Runs logged: {validationReport.validation_run_count ?? 0}
              </p>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    <th align="left">Check</th>
                    <th align="left">Pass</th>
                  </tr>
                </thead>
                <tbody>
                  {validationReport.checks.map((row) => (
                    <tr key={row.name}>
                      <td>{row.name}</td>
                      <td>{row.pass ? 'yes' : 'no'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}
          {goNoGo?.assessments && (
            <section style={{ marginBottom: 24 }}>
              <h2>Go / no-go</h2>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    <th align="left">Module</th>
                    <th align="left">Ready for live</th>
                    <th align="left">Blockers</th>
                  </tr>
                </thead>
                <tbody>
                  {goNoGo.assessments.map((row) => (
                    <tr key={row.component}>
                      <td>{row.component}</td>
                      <td>{row.ready_for_live ? 'yes' : 'no'}</td>
                      <td>{(row.blockers || []).join('; ') || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}
          <section style={{ marginBottom: 24 }}>
            <h2>Modules</h2>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  <th align="left">Module</th>
                  <th align="left">Mode</th>
                  <th align="left">Gate</th>
                  <th align="left">Recommendation</th>
                  <th align="left">Shadow events</th>
                  <th align="left">Actions</th>
                </tr>
              </thead>
              <tbody>
                {modules.map((m) => (
                  <tr key={m.component}>
                    <td>{m.label || m.component}</td>
                    <td>{MODE_LABEL[m.mode] || m.mode}</td>
                    <td>{m.gate_prediction || '—'}</td>
                    <td>
                      <StateNotice
                        tone={recommendationTone(m.recommendation)}
                        title={m.recommendation}
                        detail=""
                      />
                    </td>
                    <td>{m.shadow_events ?? 0}</td>
                    <td>
                      <button type="button" onClick={() => loadDivergence(m.component)}>Review</button>
                      {' '}
                      <button
                        type="button"
                        onClick={() => act(() => api.enableQuantum2Shadow(m.component, { rationale }))}
                      >
                        Shadow
                      </button>
                      {' '}
                      <button
                        type="button"
                        onClick={() => act(() => api.promoteQuantum2Live(m.component, { rationale, sign_off: signOff }))}
                      >
                        Live
                      </button>
                      {' '}
                      <button
                        type="button"
                        onClick={() => act(() => api.disableQuantum2Module(m.component, { rationale }))}
                      >
                        Off
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
          <section style={{ marginBottom: 16 }}>
            <label>
              Rationale
              <input
                type="text"
                value={rationale}
                onChange={(e) => setRationale(e.target.value)}
                style={{ display: 'block', width: '100%', marginTop: 4 }}
                placeholder="Why this activation change"
              />
            </label>
            <label style={{ display: 'block', marginTop: 8 }}>
              <input
                type="checkbox"
                checked={signOff}
                onChange={(e) => setSignOff(e.target.checked)}
              />
              {' '}
              Operator sign-off (required for live promotion)
            </label>
          </section>
          {divergence && (
            <section style={{ marginBottom: 24 }}>
              <h2>Divergence review: {selected}</h2>
              <p>
                Divergent events: {divergence.shadow?.divergent_events ?? 0}
                {' '}
                / {divergence.shadow?.total_events ?? 0}
              </p>
              <pre style={{ background: '#f8fafc', padding: 12, overflow: 'auto', maxHeight: 240 }}>
                {JSON.stringify(divergence.shadow?.recent || [], null, 2)}
              </pre>
            </section>
          )}
          <section>
            <h2>Activation audit log</h2>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  <th align="left">Time</th>
                  <th align="left">Action</th>
                  <th align="left">Component</th>
                  <th align="left">Actor</th>
                </tr>
              </thead>
              <tbody>
                {[...history].reverse().map((row) => (
                  <tr key={`${row.recorded_at}-${row.component}-${row.action}`}>
                    <td>{row.recorded_at}</td>
                    <td>{row.action}</td>
                    <td>{row.component}</td>
                    <td>{row.actor_id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </>
      )}
    </Layout>
  )
}
