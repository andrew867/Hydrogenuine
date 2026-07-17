import React, { useCallback, useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import { api } from '../lib/api.js'
import { AsyncPageBody } from '../components/PageStates.jsx'

export default function EvalsPage() {
  const [summary, setSummary] = useState(null)
  const [trends, setTrends] = useState(null)
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState(null)

  const load = useCallback(() => {
    setErr(null)
    setLoading(true)
    Promise.all([
      api.getEvalsSummary()
        .then((r) => {
          if (r.ok && r.report) setSummary(r.report)
          else setSummary(null)
        })
        .catch((e) => { setErr(e.message); setSummary(null) }),
      api.getEvalsTrends()
        .then((r) => setTrends(r.rows || []))
        .catch(() => setTrends([])),
    ]).finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load])

  const empty = !loading && !err && !summary

  return (
    <Layout title="Evals">
      <AsyncPageBody
        loading={loading}
        error={err}
        onRetry={load}
        empty={empty}
        emptyTitle="No eval report yet"
        emptyDescription="Run python scripts/evals/run.py to generate the first deterministic eval report."
        loadingLabel="Loading eval summary"
      >
        {summary?.deterministic && (
          <section>
            <h3>Latest deterministic</h3>
            <p>
              <strong>{summary.deterministic.passed}/{summary.deterministic.total}</strong> passed
              ({((summary.deterministic.pass_rate || 0) * 100).toFixed(0)}%) — {summary.timestamp}
            </p>
            <ul>
              {summary.deterministic.results?.map((r, i) => (
                <li key={i}>{r.passed ? '✓' : '✗'} {r.case_id}: {r.description}</li>
              ))}
            </ul>
          </section>
        )}
        {trends?.length > 0 && (
          <section style={{ marginTop: 24 }}>
            <h3>Trends</h3>
            <table style={{ borderCollapse: 'collapse', width: '100%' }}>
              <thead>
                <tr>
                  <th style={{ textAlign: 'left', padding: 6 }}>Timestamp</th>
                  <th style={{ textAlign: 'right', padding: 6 }}>Pass rate</th>
                  <th style={{ textAlign: 'right', padding: 6 }}>Passed</th>
                  <th style={{ textAlign: 'right', padding: 6 }}>Total</th>
                </tr>
              </thead>
              <tbody>
                {trends.slice(-20).reverse().map((row, i) => (
                  <tr key={i}>
                    <td style={{ padding: 6 }}>{row.timestamp}</td>
                    <td style={{ textAlign: 'right', padding: 6 }}>{(parseFloat(row.pass_rate) * 100).toFixed(0)}%</td>
                    <td style={{ textAlign: 'right', padding: 6 }}>{row.passed}</td>
                    <td style={{ textAlign: 'right', padding: 6 }}>{row.total}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}
      </AsyncPageBody>
    </Layout>
  )
}
