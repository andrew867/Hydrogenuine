import React, { useCallback, useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import { api } from '../lib/api.js'
import Breadcrumbs from '../components/Breadcrumbs.jsx'
import StatusChip from '../components/StatusChip.jsx'
import AuditToast from '../components/AuditToast.jsx'
import { formatDateTime } from '../lib/timezone.js'
import JsonBlock from '../components/JsonBlock.jsx'

export default function ProductDeadLetter({ onLogout }) {
  const [data, setData] = useState({ items: [], total: 0 })
  const [err, setErr] = useState(null)
  const [selectedId, setSelectedId] = useState(null)
  const [detail, setDetail] = useState(null)
  const [toast, setToast] = useState(null)
  const [replaying, setReplaying] = useState(false)

  const load = useCallback(() => {
    api.product.listDeadletters().then(setData).catch((e) => setErr(e.message))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const openDetail = (id) => {
    setSelectedId(id)
    setDetail(null)
    api.product.getDeadletter(id).then(setDetail).catch((e) => setErr(e.message))
  }

  const replay = async () => {
    if (!selectedId) return
    if (!window.confirm(`Replay incident ${selectedId} in shadow mode?`)) return
    setReplaying(true)
    setErr(null)
    try {
      const result = await api.product.replayIncident(selectedId, { shadow: true })
      setToast(`Replay accepted (shadow): ${result.ok ? 'ok' : 'see response'}`)
      load()
      openDetail(selectedId)
    } catch (e) {
      setErr(e.message)
    } finally {
      setReplaying(false)
    }
  }

  return (
    <Layout title="Dead-letter (Product)" onLogout={onLogout}>
      <Breadcrumbs items={[{ label: 'Home', href: '#/' }, { label: 'Incidents' }]} />
      {err && <div style={{ color: 'var(--danger)' }}>{err}</div>}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 360px', gap: 16 }}>
        <table width="100%" cellPadding="8" style={{ borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
              <th>ID</th>
              <th>Workflow</th>
              <th>Status</th>
              <th>Started</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((d, i) => (
              <tr
                key={d.id || i}
                style={{
                  borderBottom: '1px solid var(--border)',
                  cursor: 'pointer',
                  background: selectedId === d.id ? 'var(--surface-hover)' : undefined,
                }}
                onClick={() => openDetail(d.id)}
              >
                <td>{d.id ?? '—'}</td>
                <td>{d.graph_id || '—'}</td>
                <td><StatusChip status={d.status} /></td>
                <td>{formatDateTime(d.started_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <aside style={{ border: '1px solid var(--border)', borderRadius: 12, padding: 12 }}>
          <h2 style={{ fontSize: 16, marginTop: 0 }}>Incident detail</h2>
          {!selectedId ? (
            <p style={{ color: 'var(--muted)', fontSize: 13 }}>Select an incident to inspect workflow, error, and replay.</p>
          ) : !detail ? (
            <p style={{ color: 'var(--muted)', fontSize: 13 }}>Loading…</p>
          ) : (
            <>
              <p><StatusChip status={detail.status} /> {detail.graph_id}</p>
              <p style={{ fontSize: 13 }}>Error: {detail.error || '—'}</p>
              <p style={{ fontSize: 13 }}>Ended: {formatDateTime(detail.ended_at)}</p>
              <button type="button" onClick={replay} disabled={replaying} style={{ marginBottom: 12 }}>
                {replaying ? 'Replaying…' : 'Replay (shadow)'}
              </button>
              <JsonBlock value={detail} />
            </>
          )}
        </aside>
      </div>
      <p style={{ fontSize: 12, color: 'var(--muted)' }}>Total: {data.total}</p>
      <AuditToast message={toast} onDismiss={() => setToast(null)} />
    </Layout>
  )
}
