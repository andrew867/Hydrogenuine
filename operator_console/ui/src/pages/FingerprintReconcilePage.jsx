import React, { useState } from 'react'
import Layout from '../components/Layout.jsx'
import Breadcrumbs from '../components/Breadcrumbs.jsx'
import StateNotice from '../components/StateNotice.jsx'
import { api } from '../lib/api.js'

const DEMO_PROFILE = {
  cognitive_fingerprint: {
    reasoning_style: 'analytical',
    risk_tolerance: 0.4,
    communication_register: 'direct',
  },
}

export default function FingerprintReconcilePage() {
  const [fingerprintId, setFingerprintId] = useState('')
  const [parentId, setParentId] = useState('')
  const [childId, setChildId] = useState('')
  const [comparison, setComparison] = useState(null)
  const [audit, setAudit] = useState(null)
  const [err, setErr] = useState(null)

  const seedDemo = () => {
    setErr(null)
    api.seedFingerprintBranchesDemo({
      profile_json: DEMO_PROFILE,
      branch_overlays: {
        parent: { task_state: 'idle', notes: 'parent branch' },
        child: { task_state: 'active', notes: 'child branch' },
      },
    })
      .then((data) => {
        setFingerprintId(data.fingerprint_id)
        setParentId(data.parent_persona_id)
        setChildId(data.child_persona_id)
      })
      .catch((e) => setErr(e.message))
  }

  const compare = () => {
    setErr(null)
    api.compareFingerprintBranches(fingerprintId, { source_persona_id: parentId, target_persona_id: childId })
      .then((data) => setComparison(data.comparison))
      .catch((e) => setErr(e.message))
  }

  const reconcile = () => {
    setErr(null)
    api.reconcileFingerprintBranches(fingerprintId, {
      source_persona_id: parentId,
      target_persona_id: childId,
      strategy: 'prefer_newer',
      actor_id: 'operator',
    })
      .then((data) => {
        setComparison(data.comparison)
        setAudit(data.audit)
      })
      .catch((e) => setErr(e.message))
  }

  return (
    <Layout title="Fingerprint branch reconcile">
      <Breadcrumbs items={[{ label: 'Home', href: '#/home' }, { label: 'Fingerprint reconcile' }]} />
      <p className="muted" style={{ maxWidth: 720 }}>
        Same-fingerprint branches share an immutable hash core. Compare overlay conflicts and reconcile with audit trail.
      </p>
      {err && <StateNotice tone="danger" title="Error" detail={err} />}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16 }}>
        <button type="button" onClick={seedDemo}>Seed demo branches</button>
        <button type="button" disabled={!fingerprintId} onClick={compare}>Compare</button>
        <button type="button" disabled={!fingerprintId} onClick={reconcile}>Reconcile (prefer newer)</button>
      </div>
      <div style={{ display: 'grid', gap: 8, maxWidth: 720, marginBottom: 16 }}>
        <label>fingerprint_id <input value={fingerprintId} onChange={(e) => setFingerprintId(e.target.value)} style={{ width: '100%' }} /></label>
        <label>source persona <input value={parentId} onChange={(e) => setParentId(e.target.value)} style={{ width: '100%' }} /></label>
        <label>target persona <input value={childId} onChange={(e) => setChildId(e.target.value)} style={{ width: '100%' }} /></label>
      </div>
      {comparison && (
        <section className="card" style={{ marginBottom: 16 }}>
          <h2 style={{ fontSize: 16 }}>Comparison</h2>
          <pre style={{ whiteSpace: 'pre-wrap', fontSize: 12 }}>{JSON.stringify(comparison, null, 2)}</pre>
        </section>
      )}
      {audit && (
        <section className="card">
          <h2 style={{ fontSize: 16 }}>Audit</h2>
          <pre style={{ whiteSpace: 'pre-wrap', fontSize: 12 }}>{JSON.stringify(audit, null, 2)}</pre>
        </section>
      )}
    </Layout>
  )
}
