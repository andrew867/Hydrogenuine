import React, { useCallback, useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import Breadcrumbs from '../components/Breadcrumbs.jsx'
import SharedEventSummary from '../components/SharedEventSummary.jsx'
import StateNotice from '../components/StateNotice.jsx'
import { PageSkeleton } from '../components/PageStates.jsx'
import { api } from '../lib/api.js'

export default function FleetCoordination() {
  const [data, setData] = useState(null)
  const [proof, setProof] = useState(null)
  const [err, setErr] = useState(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(() => {
    setErr(null)
    setLoading(true)
    api.getFleetSnapshot()
      .then(setData)
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load])

  const snap = data?.snapshot || {}
  const halted = snap.halted_robots ?? 0

  return (
    <Layout title="Fleet coordination">
      <Breadcrumbs items={[{ label: 'Home', href: '#/home' }, { label: 'Fleet coordination' }]} />
      <SharedEventSummary
        eyebrow="Phase 10 / G11"
        title="Multi-robot fleet mesh"
        intro="Spatial zones, cross-host flood-fill, fleet-wide halt, and battery-driven task handoff."
        status={halted > 0 ? 'halted' : 'healthy'}
        statusTone={halted > 0 ? 'warn' : 'good'}
        happened={`${snap.robot_count ?? 0} robots · ${snap.zone_count ?? 0} zones`}
        when={data?.generated_at || '—'}
        why="Fleet coordination deconflicts shared workspaces and propagates emergency halt across zones."
        changed={`Halted: ${halted} · Pending handoffs: ${snap.pending_handoffs ?? 0}`}
        next="Proximity conflict → review environmental models; zone halt → incident runbook."
        context={[
          { label: 'Physical agents', value: '#/physical-agents' },
          { label: 'Spectrum monitor', value: '#/spectrum' },
        ]}
      />
      <div style={{ marginBottom: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <button type="button" onClick={load}>Refresh</button>
        <button
          type="button"
          onClick={() => api.seedFleetDemo().then(() => load()).catch((e) => setErr(e.message))}
        >
          Seed fleet demo
        </button>
        <button
          type="button"
          onClick={() => api.runFleetMeshProof().then(setProof).catch((e) => setErr(e.message))}
        >
          Run cross-host mesh proof
        </button>
        <button
          type="button"
          onClick={() => api.haltFleetZone('zone_warehouse').then(() => load()).catch((e) => setErr(e.message))}
        >
          Halt warehouse zone
        </button>
      </div>
      {err && <StateNotice tone="danger" title="Fleet error" detail={err} />}
      {proof && (
        <StateNotice
          tone={proof.ok ? 'good' : 'danger'}
          title="Cross-host flood-fill proof"
          detail={JSON.stringify(proof.per_host_deliveries || proof)}
        />
      )}
      {loading ? <PageSkeleton label="Loading fleet" /> : null}
      {!loading && snap.robots && (
        <>
          <section style={{ marginBottom: 24 }}>
            <h2>Zones</h2>
            <ul>
              {(snap.zones || []).map((z) => (
                <li key={z.zone_id}>
                  <strong>{z.label}</strong> ({z.zone_id}) — robots: {(z.robot_ids || []).join(', ')}
                </li>
              ))}
            </ul>
          </section>
          <section>
            <h2>Robots</h2>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  <th align="left">Robot</th>
                  <th align="left">Zone</th>
                  <th align="right">Battery</th>
                  <th align="right">Noise</th>
                  <th align="left">Job</th>
                  <th align="left">Halted</th>
                </tr>
              </thead>
              <tbody>
                {snap.robots.map((r) => (
                  <tr key={r.robot_id}>
                    <td>{r.robot_id}</td>
                    <td>{r.zone_id}</td>
                    <td align="right">{r.battery_wh}</td>
                    <td align="right">{r.noise_score}</td>
                    <td>{r.active_job_id || '—'}</td>
                    <td>{r.halted ? 'yes' : 'no'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </>
      )}
    </Layout>
  )
}
