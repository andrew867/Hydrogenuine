import React, { useCallback, useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import Breadcrumbs from '../components/Breadcrumbs.jsx'
import StateNotice from '../components/StateNotice.jsx'
import { PageSkeleton } from '../components/PageStates.jsx'
import { api } from '../lib/api.js'

export default function LineageTree() {
  const [entityId, setEntityId] = useState('')
  const [tree, setTree] = useState(null)
  const [proposals, setProposals] = useState([])
  const [err, setErr] = useState(null)
  const [loading, setLoading] = useState(false)
  const [actionMsg, setActionMsg] = useState(null)

  const load = useCallback((id) => {
    if (!id.trim()) return
    setErr(null)
    setLoading(true)
    Promise.all([
      api.getLearningLineage(id.trim()),
      api.getEvolutionProposals(id.trim()),
    ])
      .then(([lineageData, proposalData]) => {
        setTree(lineageData)
        setProposals(proposalData.proposals || [])
      })
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    const params = new URLSearchParams(window.location.hash.split('?')[1] || '')
    const preset = params.get('entity_id') || ''
    if (preset) {
      setEntityId(preset)
      load(preset)
    }
  }, [load])

  const onSearch = (e) => {
    e.preventDefault()
    load(entityId)
  }

  const onApprove = (proposalId) => {
    setActionMsg(null)
    api.approveEvolutionProposal(proposalId, { operator_id: 'operator' })
      .then((data) => {
        setActionMsg(`Approved → ${data.child_fingerprint_id}`)
        load(entityId)
      })
      .catch((e) => setErr(e.message))
  }

  const onRollback = () => {
    setActionMsg(null)
    api.rollbackEvolution(entityId)
      .then((data) => {
        setActionMsg(`Rolled back to ${data.active_fingerprint_id}`)
        load(entityId)
      })
      .catch((e) => setErr(e.message))
  }

  return (
    <Layout>
      <Breadcrumbs
        items={[
          { label: 'Operations', value: '#/home' },
          { label: 'Fingerprint lineage', value: '#/learning-lineage' },
        ]}
      />
      <h1>Fingerprint Lineage</h1>
      <p>Governed identity evolution — every generation requires operator approval (Level 3).</p>
      <form onSubmit={onSearch} style={{ marginBottom: 16 }}>
        <input
          value={entityId}
          onChange={(e) => setEntityId(e.target.value)}
          placeholder="Entity ID"
          style={{ marginRight: 8, padding: 8 }}
        />
        <button type="submit">Load lineage</button>
        {tree?.active_fingerprint_id && (
          <button type="button" onClick={onRollback} style={{ marginLeft: 8 }}>
            Rollback to parent
          </button>
        )}
      </form>
      {actionMsg && <StateNotice tone="muted" title="Evolution action" detail={actionMsg} />}
      {err && <StateNotice tone="danger" title="Lineage error" detail={err} />}
      {loading ? <PageSkeleton label="Loading" /> : null}
      {proposals.length > 0 && (
        <section style={{ marginBottom: 24 }}>
          <h2>Pending evolution proposals</h2>
          <table className="data-table" style={{ width: '100%' }}>
            <thead>
              <tr>
                <th>Proposal</th>
                <th>Deltas</th>
                <th>Confidence</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {proposals.map((p) => (
                <tr key={p.proposal_id}>
                  <td><code>{p.proposal_id.slice(0, 8)}…</code></td>
                  <td>{JSON.stringify(p.trait_deltas)}</td>
                  <td>{p.confidence}</td>
                  <td>
                    <button type="button" onClick={() => onApprove(p.proposal_id)}>Approve</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
      {tree?.nodes?.length > 0 && (
        <section>
          <h2>
            Ancestry for {tree.entity_id}
            {' '}
            <span style={{ fontSize: 14, color: '#64748b' }}>
              active: <code>{tree.active_fingerprint_id}</code>
            </span>
          </h2>
          <table className="data-table" style={{ width: '100%' }}>
            <thead>
              <tr>
                <th>Gen</th>
                <th>Fingerprint</th>
                <th>Parent</th>
                <th>Diff</th>
                <th>Approved by</th>
                <th>Active</th>
              </tr>
            </thead>
            <tbody>
              {tree.nodes.map((n) => (
                <tr key={n.fingerprint_id}>
                  <td>{n.generation}</td>
                  <td><code>{n.fingerprint_id.slice(0, 16)}…</code></td>
                  <td>{n.parent_fingerprint_id ? <code>{n.parent_fingerprint_id.slice(0, 12)}…</code> : '—'}</td>
                  <td>{Object.keys(n.trait_diff || {}).length ? JSON.stringify(n.trait_diff) : '—'}</td>
                  <td>{n.approved_by || '—'}</td>
                  <td>{n.active ? 'yes' : ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
      {!loading && tree && tree.nodes?.length === 0 && (
        <p style={{ color: '#94a3b8' }}>No lineage nodes registered for this entity yet.</p>
      )}
    </Layout>
  )
}
