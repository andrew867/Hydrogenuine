import React, { useCallback, useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import Breadcrumbs from '../components/Breadcrumbs.jsx'
import SharedEventSummary from '../components/SharedEventSummary.jsx'
import StateNotice from '../components/StateNotice.jsx'
import { PageSkeleton } from '../components/PageStates.jsx'
import { api } from '../lib/api.js'
import { withReturnUrl } from '../lib/navigationContext.js'

export default function SyndromeDashboard() {
  const [dash, setDash] = useState(null)
  const [err, setErr] = useState(null)
  const [loading, setLoading] = useState(true)
  const [actionMsg, setActionMsg] = useState(null)

  const load = useCallback(() => {
    setErr(null)
    setLoading(true)
    api.getSyndromeDashboard()
      .then((data) => setDash(data))
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load])

  const seedDemo = () => {
    api.seedQuantumDemo().then(() => load()).catch((e) => setErr(e.message))
  }

  const approve = (id) => {
    setActionMsg(null)
    api.approveQuantumCorrection(id)
      .then((res) => {
        setActionMsg(`Approved ${id}. Evidence: ${res.evidence_path || 'ledger'}`)
        load()
        if (res.post_action_landing) window.location.hash = withReturnUrl(res.post_action_landing)
      })
      .catch((e) => setErr(e.message))
  }

  const reject = (id) => {
    setActionMsg(null)
    api.rejectQuantumCorrection(id, { rationale: 'operator rejected via syndrome dashboard' })
      .then((res) => {
        setActionMsg(`Rejected ${id}. Evidence: ${res.evidence_path || 'ledger'}`)
        load()
      })
      .catch((e) => setErr(e.message))
  }

  const escalate = (id) => {
    setActionMsg(null)
    api.escalateQuantumCorrection(id, { rationale: 'operator escalated via syndrome dashboard' })
      .then((res) => {
        setActionMsg(`Escalated ${id}. Evidence: ${res.evidence_path || 'ledger'}`)
        load()
        if (res.post_action_landing) window.location.hash = withReturnUrl(res.post_action_landing)
      })
      .catch((e) => setErr(e.message))
  }

  const pending = (dash?.corrections || []).filter((c) => c.status === 'pending')

  return (
    <Layout title="Syndrome dashboard">
      <Breadcrumbs items={[{ label: 'Home', href: '#/home' }, { label: 'Syndrome dashboard' }]} />
      <SharedEventSummary
        eyebrow="Quantum visibility"
        title="Syndrome dashboard"
        intro="LDPC verification status, syndrome locations, and correction approve/reject with audit trail."
        status={dash?.verification_status === 'healthy' ? 'healthy' : 'watch'}
        statusTone={dash?.verification_status === 'healthy' ? 'good' : 'warn'}
        happened={`${dash?.syndromes?.length || 0} syndromes · ${pending.length} pending corrections`}
        when={dash?.generated_at || '—'}
        why="Sparse verification catches contradictions without O(N²) peer review."
        changed={actionMsg || 'No correction action this session.'}
        next="Approved corrections emit ledger events and evidence under docs/audits/quantum_corrections/."
        context={[
          { label: 'Approvals', value: '#/approvals' },
          { label: 'Timeline', value: '#/timeline' },
          { label: 'Proofs', value: '#/proofs' },
        ]}
      />
      <div style={{ marginBottom: 12 }}>
        <button type="button" onClick={seedDemo}>Seed demo data</button>
        {' '}
        <button type="button" onClick={load}>Refresh</button>
      </div>
      {err && <StateNotice tone="danger" title="Syndrome error" detail={err} action={<button type="button" onClick={load}>Retry</button>} />}
      {loading ? <PageSkeleton label="Loading" /> : null}
      {!loading && dash && (
        <>
          <p data-testid="verification-status">
            Verification: <strong>{dash.verification_status}</strong>
            {' · '}
            Swarm run: <code>{dash.swarm_run_id}</code>
          </p>
          <section style={{ marginBottom: 24 }}>
            <h2 style={{ fontSize: 18 }}>Syndromes</h2>
            {(dash.syndromes || []).length === 0 ? (
              <StateNotice title="No syndromes" detail="Outputs are consistent across the verification graph." />
            ) : (
              <table className="table-basic" data-testid="syndrome-table">
                <thead>
                  <tr><th>Report</th><th>Locations</th><th>Confidence</th><th>Status</th><th>Diff</th></tr>
                </thead>
                <tbody>
                  {dash.syndromes.map((s) => (
                    <tr key={s.report_id}>
                      <td><code>{s.report_id}</code></td>
                      <td>{(s.syndrome_locations || []).join(', ')}</td>
                      <td>{(s.confidence || 0).toFixed(2)}</td>
                      <td>{s.status}</td>
                      <td>
                        <pre style={{ fontSize: 11, margin: 0 }}>{JSON.stringify(s.diff?.texts || {}, null, 0)}</pre>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
          <section>
            <h2 style={{ fontSize: 18 }}>Corrections</h2>
            {(dash.corrections || []).length === 0 ? (
              <StateNotice title="No corrections" detail="No correction actions proposed." />
            ) : (
              <table className="table-basic" data-testid="correction-table">
                <thead>
                  <tr><th>Action</th><th>Target</th><th>Weight</th><th>Status</th><th>Operator</th></tr>
                </thead>
                <tbody>
                  {dash.corrections.map((c) => (
                    <tr key={c.action_id}>
                      <td><code>{c.action_id}</code></td>
                      <td>{c.target_entity}</td>
                      <td>{(c.correction_weight || 0).toFixed(2)}</td>
                      <td>{c.status}</td>
                      <td>
                        {c.status === 'pending' && (
                          <>
                            <button type="button" onClick={() => approve(c.action_id)}>Approve</button>
                            {' '}
                            <button type="button" onClick={() => reject(c.action_id)}>Reject</button>
                            {' '}
                            <button type="button" onClick={() => escalate(c.action_id)}>Escalate</button>
                          </>
                        )}
                        {c.status !== 'pending' && (c.approved_by || c.rejected_by || '—')}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        </>
      )}
    </Layout>
  )
}
