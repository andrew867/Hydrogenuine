import React, { useCallback, useEffect, useState } from 'react'
import { ConfirmDialog, RecognitionActiveBadge, useConsentIndicator } from 'hg_ui_kit'
import Layout from '../components/Layout.jsx'
import Breadcrumbs from '../components/Breadcrumbs.jsx'
import SharedEventSummary from '../components/SharedEventSummary.jsx'
import StateNotice from '../components/StateNotice.jsx'
import { PageSkeleton } from '../components/PageStates.jsx'
import { api } from '../lib/api.js'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8080/api/v1'
const DEFAULT_SUBJECT = 'demo-user'

export default function ConsentLedger() {
  const [subjectId, setSubjectId] = useState(DEFAULT_SUBJECT)
  const [status, setStatus] = useState(null)
  const [ledger, setLedger] = useState(null)
  const [err, setErr] = useState(null)
  const [loading, setLoading] = useState(true)
  const [revokeTarget, setRevokeTarget] = useState(null)

  const indicator = useConsentIndicator({
    statusUrl: `${API_BASE}/consent/status`,
    subjectId,
    headers: () => ({}),
    pollMs: 10000,
  })

  const load = useCallback(() => {
    setErr(null)
    setLoading(true)
    Promise.all([
      api.getConsentStatus(subjectId),
      api.getConsentLedger({ offset: 0, limit: 100 }),
    ])
      .then(([st, lg]) => {
        setStatus(st)
        setLedger(lg)
      })
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false))
  }, [subjectId])

  useEffect(() => { load() }, [load])

  const grants = (status?.active_grants || []).filter((g) => g.event === 'CONSENT_GRANTED')

  const confirmRevoke = () => {
    if (!revokeTarget) return
    api.revokeConsent({
      record_id: revokeTarget.record_id,
      subject_id: revokeTarget.subject_id,
      revoked_by: 'operator',
    })
      .then(() => {
        setRevokeTarget(null)
        load()
        indicator.refresh()
      })
      .catch((e) => setErr(e.message))
  }

  return (
    <Layout title="Consent ledger">
      <Breadcrumbs items={[{ label: 'Home', href: '#/home' }, { label: 'Consent ledger' }]} />
      <SharedEventSummary
        eyebrow="G15 / repr_interp"
        title="Cognitive recognition consent"
        intro="Append-only consent ledger, grant/revoke flows, and no-silent-activation indicator."
        status={status?.effective_class === 'none' ? 'idle' : 'active'}
        statusTone={status?.effective_class === 'none' ? 'neutral' : 'warn'}
        happened={`Effective class: ${status?.effective_class || 'none'}`}
        when={status?.generated_at || '—'}
        why="User-targeted recognition requires explicit consent before any capture or mediator probe."
        changed={`${grants.length} active grant(s) for ${subjectId}`}
        next="Revoke immediately on operator request; audit tail below."
        context={[{ label: 'Governance', value: '#/governance' }]}
      />
      <div style={{ marginBottom: 12, display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        <label>
          Subject ID
          <input value={subjectId} onChange={(e) => setSubjectId(e.target.value)} style={{ marginLeft: 8 }} />
        </label>
        <button type="button" onClick={load}>Refresh</button>
        <button type="button" onClick={() => api.seedConsentDemo().then(load).catch((e) => setErr(e.message))}>
          Seed demo grants
        </button>
        <RecognitionActiveBadge
          active={indicator.recognitionActive}
          effectiveClass={indicator.effectiveClass}
          href="#/consent"
        />
      </div>
      {err && <StateNotice tone="danger" title="Consent error" detail={err} />}
      {loading ? <PageSkeleton label="Loading consent ledger" /> : null}
      {!loading && (
        <>
          <section style={{ marginBottom: 24 }}>
            <h3>Active grants</h3>
            {grants.length === 0 ? <p>No active grants.</p> : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Record</th>
                    <th>Class</th>
                    <th>Purpose</th>
                    <th>Expires</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {grants.map((g) => (
                    <tr key={g.record_id}>
                      <td>{g.record_id}</td>
                      <td>{g.consent_class}</td>
                      <td>{g.purpose}</td>
                      <td>{g.expires_at || '—'}</td>
                      <td>
                        <button type="button" onClick={() => setRevokeTarget(g)}>Revoke</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
          <section>
            <h3>Ledger tail</h3>
            <pre style={{ maxHeight: 320, overflow: 'auto' }}>
              {JSON.stringify(ledger?.events || [], null, 2)}
            </pre>
          </section>
        </>
      )}
      <ConfirmDialog
        open={Boolean(revokeTarget)}
        title="Revoke consent grant"
        description={`Revoke ${revokeTarget?.record_id} for subject ${revokeTarget?.subject_id}? This appends CONSENT_REVOKED immediately.`}
        confirmLabel="Revoke"
        destructive
        onConfirm={confirmRevoke}
        onCancel={() => setRevokeTarget(null)}
      />
    </Layout>
  )
}
