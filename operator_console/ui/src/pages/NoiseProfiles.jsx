import React, { useCallback, useEffect, useState } from 'react'
import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, Tooltip, Legend,
} from 'recharts'
import Layout from '../components/Layout.jsx'
import Breadcrumbs from '../components/Breadcrumbs.jsx'
import SharedEventSummary from '../components/SharedEventSummary.jsx'
import StateNotice from '../components/StateNotice.jsx'
import { PageSkeleton } from '../components/PageStates.jsx'
import { api } from '../lib/api.js'

export default function NoiseProfiles() {
  const [data, setData] = useState(null)
  const [selected, setSelected] = useState(null)
  const [err, setErr] = useState(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(() => {
    setErr(null)
    setLoading(true)
    api.getNoiseProfiles()
      .then((res) => {
        setData(res)
        if (res.profiles?.length && !selected) setSelected(res.profiles[0].entity_id)
      })
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load])

  const profile = (data?.profiles || []).find((p) => p.entity_id === selected)

  const seedDemo = () => {
    api.seedQuantumDemo().then(() => load()).catch((e) => setErr(e.message))
  }

  const budgetRows = profile?.budget?.allocated
    ? Object.entries(profile.budget.allocated).map(([stage, value]) => ({ stage, budget: value }))
    : []

  return (
    <Layout title="Noise profiles">
      <Breadcrumbs items={[{ label: 'Home', href: '#/home' }, { label: 'Noise profiles' }]} />
      <SharedEventSummary
        eyebrow="Quantum visibility"
        title="Noise profiles"
        intro="Per-entity noise characterization from NoiseCharacterizer: sources, SNR, budget allocation, and mitigations."
        status={profile?.noise_magnitude > 0.5 ? 'watch' : 'healthy'}
        statusTone={profile?.noise_magnitude > 0.5 ? 'warn' : 'good'}
        happened={`${data?.profiles?.length || 0} entities profiled`}
        when={data?.generated_at || '—'}
        why="Targeted mitigation beats uniform retry when noise sources differ."
        changed={profile ? `SNR ${profile.overall_snr?.toFixed(2)} · magnitude ${profile.noise_magnitude?.toFixed(2)}` : 'Select an entity.'}
        next="High context_overflow → trim history; emotional_drift → meditation."
        context={[
          { label: 'Entanglement', value: '#/entanglement' },
          { label: 'Timeline', value: '#/timeline' },
        ]}
      />
      <div style={{ marginBottom: 12 }}>
        <button type="button" onClick={seedDemo}>Seed demo data</button>
        {' '}
        <button type="button" onClick={load}>Refresh</button>
      </div>
      {err && <StateNotice tone="danger" title="Noise profiles error" detail={err} />}
      {loading ? <PageSkeleton label="Loading" /> : null}
      {!loading && data && (
        <>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16 }}>
            {(data.profiles || []).map((p) => (
              <button
                key={p.entity_id}
                type="button"
                className={selected === p.entity_id ? 'nav-link active' : 'nav-link'}
                onClick={() => setSelected(p.entity_id)}
              >
                {p.entity_id}
              </button>
            ))}
          </div>
          {profile && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }} data-testid="noise-profile-detail">
              <div style={{ height: 280 }}>
                <h3 style={{ fontSize: 14 }}>Noise source radar</h3>
                <ResponsiveContainer width="100%" height="90%">
                  <RadarChart data={profile.radar || []}>
                    <PolarGrid />
                    <PolarAngleAxis dataKey="axis" />
                    <PolarRadiusAxis domain={[0, 1]} />
                    <Radar dataKey="value" stroke="#58a6ff" fill="#58a6ff" fillOpacity={0.45} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
              <div style={{ height: 280 }}>
                <h3 style={{ fontSize: 14 }}>Stage noise budget</h3>
                <ResponsiveContainer width="100%" height="90%">
                  <BarChart data={budgetRows}>
                    <XAxis dataKey="stage" />
                    <YAxis domain={[0, 1]} />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="budget" fill="#3fb950" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <section>
                <h3 style={{ fontSize: 14 }}>Mitigations</h3>
                <ul>
                  {(profile.mitigations || []).map((m) => <li key={m}>{m}</li>)}
                </ul>
              </section>
              <section>
                <h3 style={{ fontSize: 14 }}>Active alerts</h3>
                {(profile.alerts || []).length === 0 ? (
                  <p>No alert rules fired.</p>
                ) : (
                  <ul>
                    {profile.alerts.map((a) => (
                      <li key={a.id}>{a.description} (value {a.value})</li>
                    ))}
                  </ul>
                )}
              </section>
            </div>
          )}
        </>
      )}
    </Layout>
  )
}
