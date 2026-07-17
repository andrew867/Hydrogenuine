import React, { useCallback, useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import Breadcrumbs from '../components/Breadcrumbs.jsx'
import StateNotice from '../components/StateNotice.jsx'
import { PageSkeleton } from '../components/PageStates.jsx'
import { api } from '../lib/api.js'

export default function Mediators() {
  const [catalog, setCatalog] = useState(null)
  const [err, setErr] = useState(null)
  const [loading, setLoading] = useState(true)
  const [probeEntity, setProbeEntity] = useState('ent_demo')
  const [probeClass, setProbeClass] = useState('unexpressed_disagreement')
  const [probeResult, setProbeResult] = useState(null)

  const load = useCallback(() => {
    setErr(null)
    setLoading(true)
    api.getMediatorCatalog()
      .then((data) => setCatalog(data))
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load])

  const runProbe = () => {
    setProbeResult(null)
    api.probeMediator({ entity_id: probeEntity, latent_state_class: probeClass, context: {} })
      .then((data) => {
        setProbeResult(data.result)
        load()
      })
      .catch((e) => setErr(e.message))
  }

  return (
    <Layout title="Mediators">
      <Breadcrumbs items={[{ label: 'Home', href: '#/home' }, { label: 'Governance', href: '#/governance' }, { label: 'Mediators' }]} />
      <h1>Latent-State Mediator Registry</h1>
      <p>Engineered coupling channels for entity latent state (Q2-C). User-targeted probes are structurally rejected.</p>
      <div style={{ marginBottom: 12 }}>
        <button type="button" onClick={load}>Refresh</button>
      </div>
      {err && <StateNotice tone="danger" title="Mediators error" detail={err} />}
      {loading ? <PageSkeleton label="Loading" /> : null}
      {!loading && catalog && (
        <>
          <h2>Catalog ({catalog.mediators?.length || 0})</h2>
          <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 24 }}>
            <thead>
              <tr>
                <th align="left">ID</th>
                <th align="left">Latent class</th>
                <th align="left">Mechanism</th>
                <th align="left">Surfacing</th>
              </tr>
            </thead>
            <tbody>
              {(catalog.mediators || []).map((m) => (
                <tr key={m.mediator_id}>
                  <td>{m.mediator_id}</td>
                  <td>{m.latent_state_class}</td>
                  <td>{m.coupling_mechanism}</td>
                  <td>{m.surfacing_policy}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <h2>Probe</h2>
          <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
            <input value={probeEntity} onChange={(e) => setProbeEntity(e.target.value)} placeholder="entity_id" />
            <select value={probeClass} onChange={(e) => setProbeClass(e.target.value)}>
              <option value="unexpressed_disagreement">unexpressed_disagreement</option>
              <option value="suppressed_reasoning">suppressed_reasoning</option>
              <option value="eroding_confidence">eroding_confidence</option>
              <option value="latent_capability">latent_capability</option>
            </select>
            <button type="button" onClick={runProbe}>Run probe</button>
          </div>
          {probeResult && (
            <pre style={{ background: '#f8fafc', padding: 12, borderRadius: 6 }}>{JSON.stringify(probeResult, null, 2)}</pre>
          )}
          <h2>Activation log</h2>
          <pre style={{ background: '#f8fafc', padding: 12, borderRadius: 6, maxHeight: 240, overflow: 'auto' }}>
            {JSON.stringify(catalog.activation_log || [], null, 2)}
          </pre>
        </>
      )}
    </Layout>
  )
}
