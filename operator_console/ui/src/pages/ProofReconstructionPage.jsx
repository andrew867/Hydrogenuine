import React, { useCallback, useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import Breadcrumbs from '../components/Breadcrumbs.jsx'
import StateNotice from '../components/StateNotice.jsx'
import { api } from '../lib/api.js'

export default function ProofReconstructionPage() {
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(() => {
    setLoading(true)
    setErr(null)
    api.proofReconstruction.getDashboard()
      .then((payload) => setData(payload))
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load])

  const timeline = data?.timeline || []

  return (
    <Layout>
      <Breadcrumbs items={[{ label: 'Evidence', href: '#/proofs' }, { label: 'Proof reconstruction' }]} />
      <h1>Proof reconstruction</h1>
      <p>Reconstruct coordination timeline from optoacoustic proof snapshots without live mesh.</p>
      {loading && <StateNotice state="loading" message="Loading reconstruction…" />}
      {err && <StateNotice state="error" message={err} />}
      {!loading && !err && data && (
        <>
          <div data-testid="reconstruction-summary" style={{ marginBottom: '1rem' }}>
            <strong>Fingerprint:</strong> {data.fingerprint_id || '—'}
            {' · '}
            <strong>Events:</strong> {data.event_count ?? timeline.length}
          </div>
          <table data-testid="reconstruction-timeline" style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th align="left">Proof snapshot</th>
                <th align="left">Mesh event</th>
                <th align="left">Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {timeline.map((row, idx) => (
                <tr key={`${row.proof_snapshot_id}-${idx}`}>
                  <td>{row.proof_snapshot_id}</td>
                  <td>{row.mesh_event_id}</td>
                  <td>{row.mesh_event?.ts ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {timeline.length === 0 && <StateNotice state="empty" message="No reconstruction events yet. Seed demo data from API." />}
        </>
      )}
    </Layout>
  )
}
