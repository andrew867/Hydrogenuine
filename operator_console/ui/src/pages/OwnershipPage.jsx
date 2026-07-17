import React, { useCallback, useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import { api } from '../lib/api.js'
import { formatDateTime } from '../lib/timezone.js'
import StateNotice from '../components/StateNotice.jsx'

export default function OwnershipPage() {
  const [conflicts, setConflicts] = useState([])
  const [handoffs, setHandoffs] = useState([])
  const [err, setErr] = useState(null)

  const load = useCallback(() => {
    setErr(null)
    api.getConflicts()
      .then((r) => r.ok !== false && r.conflicts && setConflicts(r.conflicts))
      .catch((e) => setErr(e.message))
    api.getHandoffs()
      .then((r) => r.ok !== false && r.events && setHandoffs(r.events))
      .catch((e) => setErr(e.message))
  }, [])

  useEffect(() => { load() }, [load])

  return (
    <Layout title="Ownership — Conflicts and Handoffs">
      {err && <StateNotice tone="danger" title="Could not load ownership data" detail={err} action={<button type="button" onClick={load}>Retry</button>} />}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <span style={{ color: 'var(--muted)' }}>{conflicts.length} conflicts, {handoffs.length} handoff events.</span>
        <button type="button" onClick={load}>Refresh</button>
      </div>
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 18 }}>Conflicts (contested ownership)</h2>
        {conflicts.length === 0 ? (
          <p>No contested ownership.</p>
        ) : (
          <table style={{ borderCollapse: 'collapse', width: '100%' }}>
            <thead>
              <tr>
                <th style={{ border: '1px solid var(--border)', padding: 8 }}>run_id</th>
                <th style={{ border: '1px solid var(--border)', padding: 8 }}>task_id</th>
                <th style={{ border: '1px solid var(--border)', padding: 8 }}>state</th>
                <th style={{ border: '1px solid var(--border)', padding: 8 }}>contested_claims</th>
              </tr>
            </thead>
            <tbody>
              {conflicts.map((c, i) => (
                <tr key={i}>
                  <td style={{ border: '1px solid var(--border)', padding: 8 }}>
                    <a href={`#/runs/${c.run_id}`} style={{ textDecoration: 'none' }}>{c.run_id}</a>
                  </td>
                  <td style={{ border: '1px solid var(--border)', padding: 8 }}>{c.task_id}</td>
                  <td style={{ border: '1px solid var(--border)', padding: 8 }}>{c.state}</td>
                  <td style={{ border: '1px solid var(--border)', padding: 8 }}>
                    {Array.isArray(c.contested_claims) ? JSON.stringify(c.contested_claims) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
      <section>
        <h2 style={{ fontSize: 18 }}>Handoffs (offer/accept/decline/release)</h2>
        {handoffs.length === 0 ? (
          <p>No handoff events.</p>
        ) : (
          <table style={{ borderCollapse: 'collapse', width: '100%' }}>
            <thead>
              <tr>
                <th style={{ border: '1px solid var(--border)', padding: 8 }}>run_id</th>
                <th style={{ border: '1px solid var(--border)', padding: 8 }}>task_id</th>
                <th style={{ border: '1px solid var(--border)', padding: 8 }}>type</th>
                <th style={{ border: '1px solid var(--border)', padding: 8 }}>actor</th>
                <th style={{ border: '1px solid var(--border)', padding: 8 }}>ts</th>
              </tr>
            </thead>
            <tbody>
              {handoffs.map((e, i) => (
                <tr key={i}>
                  <td style={{ border: '1px solid var(--border)', padding: 8 }}>
                    <a href={`#/runs/${e.run_id}`} style={{ textDecoration: 'none' }}>{e.run_id}</a>
                  </td>
                  <td style={{ border: '1px solid var(--border)', padding: 8 }}>{e.task_id}</td>
                  <td style={{ border: '1px solid var(--border)', padding: 8 }}>{e.type}</td>
                  <td style={{ border: '1px solid var(--border)', padding: 8 }}>{e.actor}</td>
                  <td style={{ border: '1px solid var(--border)', padding: 8 }}>{e.ts != null ? formatDateTime(e.ts) : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </Layout>
  )
}


