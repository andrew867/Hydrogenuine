import React, { useCallback, useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import { api } from '../lib/api.js'

export default function FaultScenariosPage() {
  const [scenarios, setScenarios] = useState(null)
  const [byWorkflow, setByWorkflow] = useState({})
  const [err, setErr] = useState(null)
  const [workflowId, setWorkflowId] = useState('')
  const [scenarioId, setScenarioId] = useState('')
  const [outcome, setOutcome] = useState(null)

  const load = useCallback(() => {
    setErr(null)
    api.getFaultScenarios()
      .then((r) => {
        if (r.ok !== false) {
          setScenarios(r.scenarios || [])
          setByWorkflow(r.by_workflow || {})
        }
      })
      .catch((e) => setErr(e.message))
  }, [])

  useEffect(() => { load() }, [load])

  const runScenario = () => {
    setErr(null)
    setOutcome(null)
    api.runFaultScenario({ workflow_id: workflowId, scenario_id: scenarioId })
      .then((r) => r.ok !== false && r.outcome && setOutcome(r.outcome))
      .catch((e) => setErr(e.message))
  }

  const workflowOptions = Object.keys(byWorkflow).length ? Object.keys(byWorkflow) : []
  const scenarioOptions = workflowId ? (byWorkflow[workflowId] || scenarios || []) : []

  const loadExample = () => {
    const exampleWorkflow = workflowOptions.includes('social-media')
      ? 'social-media'
      : (workflowOptions[0] || 'social-media')
    const exampleScenario = (byWorkflow[exampleWorkflow] || ['transient_network'])[0] || 'transient_network'
    setWorkflowId(exampleWorkflow)
    setScenarioId(exampleScenario)
  }

  return (
    <Layout title="Fault Scenarios">
      {err && <p style={{ color: 'var(--danger)' }}>{err}</p>}
      <p>Run a fault scenario (fake destinations only; no side effects).</p>
      <div style={{ marginBottom: 12 }}>
        <button type="button" onClick={loadExample}>Load example scenario</button>
      </div>
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
        <label>
          Workflow:
          <select value={workflowId} onChange={(e) => { setWorkflowId(e.target.value); setScenarioId('') }}>
            <option value="">Select workflow…</option>
            {workflowOptions.map((id) => <option key={id} value={id}>{id}</option>)}
          </select>
        </label>
        <label>
          Scenario:
          <select value={scenarioId} onChange={(e) => setScenarioId(e.target.value)} disabled={!workflowId}>
            <option value="">Select scenario…</option>
            {scenarioOptions.map((id) => <option key={id} value={id}>{id}</option>)}
          </select>
        </label>
        <button type="button" onClick={runScenario} disabled={!workflowId || !scenarioId}>Run scenario</button>
      </div>
      {outcome && (
        <section style={{ marginTop: 16 }}>
          <h3>Outcome</h3>
          <pre style={{ background: 'var(--panel-2)', padding: 12, overflow: 'auto' }}>
            {JSON.stringify(outcome, null, 2)}
          </pre>
        </section>
      )}
    </Layout>
  )
}


