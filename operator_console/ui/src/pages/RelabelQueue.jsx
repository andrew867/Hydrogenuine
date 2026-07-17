import React, { useCallback, useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import Breadcrumbs from '../components/Breadcrumbs.jsx'
import StateNotice from '../components/StateNotice.jsx'
import { PageSkeleton } from '../components/PageStates.jsx'
import { api } from '../lib/api.js'

const VERDICTS = ['success', 'rejected', 'partial', 'unknown']

export default function RelabelQueue() {
  const [items, setItems] = useState([])
  const [telemetry, setTelemetry] = useState(null)
  const [err, setErr] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState(null)

  const load = useCallback(() => {
    setErr(null)
    setLoading(true)
    Promise.all([api.syncLearningCorpus(), api.getLearningRelabelQueue(), api.getLearningTelemetry()])
      .then(([, queue, telem]) => {
        setItems(queue.items || [])
        setTelemetry(telem)
      })
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const onRelabel = (signalId, verdict) => {
    setBusyId(signalId)
    api.postLearningRelabel(signalId, { verdict, rationale: 'operator_relabel' })
      .then(() => load())
      .catch((e) => setErr(e.message))
      .finally(() => setBusyId(null))
  }

  return (
    <Layout>
      <Breadcrumbs
        items={[
          { label: 'Operations', value: '#/home' },
          { label: 'Relabel queue', value: '#/learning-relabel' },
        ]}
      />
      <h1>Learning Relabel Queue</h1>
      <p>Low-confidence automated labels and unlabeled signals awaiting operator verdict.</p>
      {telemetry && (
        <p style={{ color: '#64748b' }}>
          Coverage: {(telemetry.hg_learning_label_coverage * 100).toFixed(1)}% ·
          Queue depth: {telemetry.hg_learning_relabel_queue_depth} ·
          Corpus: {telemetry.hg_learning_corpus_size} signals
        </p>
      )}
      {err && <StateNotice tone="danger" title="Relabel queue error" detail={err} />}
      {loading ? <PageSkeleton label="Loading" /> : null}
      {!loading && items.length === 0 && (
        <StateNotice tone="muted" title="Queue empty" detail="All labelable signals have confident labels." />
      )}
      {!loading && items.length > 0 && (
        <table className="data-table" style={{ width: '100%', marginTop: 16 }}>
          <thead>
            <tr>
              <th>Signal</th>
              <th>Type</th>
              <th>Reason</th>
              <th>Effective</th>
              <th>History</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.queue_id}>
                <td><code>{item.signal_id}</code></td>
                <td>{item.signal_type || '—'}</td>
                <td>{item.reason}</td>
                <td>{item.effective_label?.verdict || '—'}</td>
                <td>{(item.label_history || []).length}</td>
                <td style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  {VERDICTS.map((v) => (
                    <button
                      key={v}
                      type="button"
                      disabled={busyId === item.signal_id}
                      onClick={() => onRelabel(item.signal_id, v)}
                    >
                      {v}
                    </button>
                  ))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Layout>
  )
}
