import React, { useCallback, useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import Layout from '../components/Layout.jsx'
import Breadcrumbs from '../components/Breadcrumbs.jsx'
import SharedEventSummary from '../components/SharedEventSummary.jsx'
import StateNotice from '../components/StateNotice.jsx'
import { PageSkeleton } from '../components/PageStates.jsx'
import { api } from '../lib/api.js'

export default function SpectrumMonitor() {
  const [data, setData] = useState(null)
  const [emitters, setEmitters] = useState(null)
  const [err, setErr] = useState(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(() => {
    setErr(null)
    setLoading(true)
    Promise.all([api.getSpectrumSnapshot(), api.getSpectrumEmitters()])
      .then(([snap, em]) => {
        setData(snap)
        setEmitters(em)
      })
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load])

  const bands = data?.snapshot?.bands || []
  const chartData = bands.map((b) => ({
    band: b.label || b.band_id,
    energy: Math.round(b.energy || 0),
    fraction: ((b.fraction || 0) * 100).toFixed(1),
  }))

  return (
    <Layout title="Spectrum monitor">
      <Breadcrumbs items={[{ label: 'Home', href: '#/home' }, { label: 'Spectrum monitor' }]} />
      <SharedEventSummary
        eyebrow="S7 observability"
        title="Broadband mesh spectrum"
        intro="One wavelength-independent observer across all mesh channels with emitter localization (Rydberg analog)."
        status={data?.alerts?.length ? 'watch' : 'healthy'}
        statusTone={data?.alerts?.length ? 'warn' : 'good'}
        happened={`${data?.snapshot?.observation_count ?? 0} observations`}
        when={data?.generated_at || '—'}
        why="Unified observability localizes noisy coordination emitters before they flood verification."
        changed={`Peak band: ${data?.snapshot?.peak_band_id ?? '—'} · ${data?.snapshot?.emitter_count ?? 0} emitters`}
        next="Hot cognitive band → review entanglement graph; hot alert band → incident queue."
        context={[
          { label: 'Entanglement', value: '#/entanglement' },
          { label: 'Noise profiles', value: '#/noise-profiles' },
        ]}
      />
      <div style={{ marginBottom: 12, display: 'flex', gap: 8 }}>
        <button type="button" onClick={load}>Refresh</button>
        <button
          type="button"
          onClick={() => api.seedSpectrumDemo().then(() => load()).catch((e) => setErr(e.message))}
        >
          Seed spectrum demo
        </button>
      </div>
      {err && <StateNotice tone="danger" title="Spectrum error" detail={err} />}
      {loading ? <PageSkeleton label="Loading spectrum" /> : null}
      {!loading && data && (
        <>
          <section style={{ marginBottom: 24 }}>
            <h2>Band energy</h2>
            <div style={{ width: '100%', height: 280 }}>
              <ResponsiveContainer>
                <BarChart data={chartData}>
                  <XAxis dataKey="band" tick={{ fontSize: 11 }} />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="energy" fill="#6366f1" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </section>
          <section style={{ marginBottom: 24 }}>
            <h2>Localized emitters</h2>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  <th align="left">Emitter</th>
                  <th align="left">Band</th>
                  <th align="left">Energy</th>
                  <th align="left">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {(emitters?.emitters || []).map((row) => (
                  <tr key={`${row.emitter_id}-${row.band_id}`}>
                    <td>{row.emitter_id}</td>
                    <td>{row.band_id}</td>
                    <td>{row.energy?.toFixed(1)}</td>
                    <td>{(row.confidence * 100).toFixed(0)}%</td>
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
