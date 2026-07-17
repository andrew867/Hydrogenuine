import React, { useCallback, useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import Breadcrumbs from '../components/Breadcrumbs.jsx'
import StateNotice from '../components/StateNotice.jsx'
import { PageSkeleton } from '../components/PageStates.jsx'
import { api } from '../lib/api.js'

export default function AdvancedModels() {
  const [dashboard, setDashboard] = useState(null)
  const [selected, setSelected] = useState(null)
  const [detail, setDetail] = useState(null)
  const [err, setErr] = useState(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(() => {
    setErr(null)
    setLoading(true)
    api.getAdvancedModelsDashboard()
      .then((data) => {
        setDashboard(data)
        if (data.models?.length && !selected) {
          setSelected(data.models[0].model_id)
        }
      })
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false))
  }, [selected])

  useEffect(() => {
    api.seedAdvancedModelsDemo().finally(load)
  }, [load])

  useEffect(() => {
    if (!selected) return
    api.getAdvancedModelDetail(selected)
      .then((data) => setDetail(data))
      .catch((e) => setErr(e.message))
  }, [selected, dashboard])

  return (
    <Layout title="Advanced models">
      <Breadcrumbs items={[{ label: 'Home', href: '#/home' }, { label: 'Advanced models' }]} />
      <h1>Wave 2 Advanced Models</h1>
      <p>Varifocal routing, temporal auth, dark-state detection, optoacoustic linking, KPZ prediction, exceptional points.</p>
      <div style={{ marginBottom: 12 }}>
        <button type="button" onClick={() => api.seedAdvancedModelsDemo().then(load)}>Seed demo</button>
        {' '}
        <button type="button" onClick={load}>Refresh</button>
      </div>
      {err && <StateNotice tone="danger" title="Advanced models error" detail={err} />}
      {loading ? <PageSkeleton label="Loading" /> : null}
      {!loading && dashboard && (
        <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: 24 }}>
          <aside>
            <h2>Models</h2>
            <ul style={{ listStyle: 'none', padding: 0 }}>
              {(dashboard.models || []).map((m) => (
                <li key={m.model_id} style={{ marginBottom: 8 }}>
                  <button
                    type="button"
                    onClick={() => setSelected(m.model_id)}
                    style={{
                      width: '100%',
                      textAlign: 'left',
                      padding: 8,
                      border: selected === m.model_id ? '2px solid #3b82f6' : '1px solid #e2e8f0',
                      borderRadius: 6,
                      background: '#fff',
                      cursor: 'pointer',
                    }}
                  >
                    <strong>{m.name}</strong>
                    <div style={{ fontSize: 12, color: '#64748b' }}>
                      {m.enabled ? 'enabled' : 'disabled'} · {m.shadow ? 'shadow' : 'live'}
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          </aside>
          <section>
            <h2>Recommendations</h2>
            <ul>
              {(dashboard.recommendations || []).map((r, i) => (
                <li key={`rec-${i}`}>
                  {r.type}: {r.action || r.latent_class || `size ${r.recommended_size}`}
                  {r.requires_approval && ' (approval required)'}
                </li>
              ))}
            </ul>
            {detail?.model && (
              <>
                <h2>{detail.model.name}</h2>
                <p>{detail.model.description}</p>
                <pre style={{ background: '#f8fafc', padding: 12, borderRadius: 8, fontSize: 12 }}>
                  {JSON.stringify(detail.model.diagnostics || {}, null, 2)}
                </pre>
              </>
            )}
            <h3>Evidence links</h3>
            <ul>
              {Object.entries(dashboard.evidence_links || {}).map(([k, v]) => (
                <li key={k}><a href={v}>{k}</a></li>
              ))}
            </ul>
          </section>
        </div>
      )}
    </Layout>
  )
}
