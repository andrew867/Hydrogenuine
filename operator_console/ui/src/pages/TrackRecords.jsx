import React, { useCallback, useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import Breadcrumbs from '../components/Breadcrumbs.jsx'
import StateNotice from '../components/StateNotice.jsx'
import { PageSkeleton } from '../components/PageStates.jsx'
import { api } from '../lib/api.js'

function MetricCell({ value }) {
  if (value === 'insufficient_data' || value == null) {
    return <span style={{ color: '#94a3b8' }}>n&lt;20</span>
  }
  if (typeof value === 'number') {
    return <span>{(value * 100).toFixed(1)}%</span>
  }
  return <span>{String(value)}</span>
}

export default function TrackRecords() {
  const [entities, setEntities] = useState([])
  const [selected, setSelected] = useState(null)
  const [detail, setDetail] = useState(null)
  const [err, setErr] = useState(null)
  const [loading, setLoading] = useState(true)

  const loadList = useCallback(() => {
    setErr(null)
    setLoading(true)
    api.syncLearningCorpus()
      .then(() => api.getLearningTrackRecords())
      .then((data) => {
        const list = data.entities || []
        setEntities(list)
        if (!selected && list.length) {
          setSelected(list[0].entity_id)
        }
      })
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false))
  }, [selected])

  useEffect(() => {
    loadList()
  }, [loadList])

  useEffect(() => {
    if (!selected) return
    api.getLearningTrackRecord(selected)
      .then((data) => setDetail(data))
      .catch((e) => setErr(e.message))
  }, [selected])

  return (
    <Layout>
      <Breadcrumbs
        items={[
          { label: 'Operations', value: '#/home' },
          { label: 'Track records', value: '#/learning-track-records' },
        ]}
      />
      <h1>Entity Track Records</h1>
      <p>Rolling performance ledgers (7d / 30d / lifetime). Conclusions require n≥20 samples.</p>
      {err && <StateNotice tone="danger" title="Track records error" detail={err} />}
      {loading ? <PageSkeleton label="Loading" /> : null}
      {!loading && entities.length === 0 && (
        <StateNotice tone="muted" title="No entities" detail="Mine proof corpus first (sync on load)." />
      )}
      {!loading && entities.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: '220px 1fr', gap: 24, marginTop: 16 }}>
          <ul style={{ listStyle: 'none', padding: 0 }}>
            {entities.map((e) => (
              <li key={e.entity_id}>
                <button
                  type="button"
                  onClick={() => setSelected(e.entity_id)}
                  style={{ fontWeight: selected === e.entity_id ? 700 : 400 }}
                >
                  {e.entity_id}
                </button>
              </li>
            ))}
          </ul>
          <div>
            {detail && (
              <>
                <h2>{detail.entity_id}</h2>
                {['7d', '30d', 'lifetime'].map((window) => {
                  const w = detail.windows?.[window]
                  if (!w) return null
                  return (
                    <div key={window} style={{ marginBottom: 24 }}>
                      <h3>{window} (n={w.sample_count}{w.sufficient_data ? '' : ', insufficient'})</h3>
                      <table className="data-table">
                        <tbody>
                          {Object.entries(w.metrics || {}).map(([k, v]) => (
                            <tr key={k}>
                              <td>{k}</td>
                              <td><MetricCell value={v} /></td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )
                })}
              </>
            )}
          </div>
        </div>
      )}
    </Layout>
  )
}
