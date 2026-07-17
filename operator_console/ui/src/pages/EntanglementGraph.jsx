import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Layout from '../components/Layout.jsx'
import Breadcrumbs from '../components/Breadcrumbs.jsx'
import SharedEventSummary from '../components/SharedEventSummary.jsx'
import StateNotice from '../components/StateNotice.jsx'
import { PageSkeleton } from '../components/PageStates.jsx'
import { api } from '../lib/api.js'

const WIDTH = 720
const HEIGHT = 420

function layoutForce(nodes, edges, iterations = 120) {
  const simNodes = nodes.map((n, i) => ({
    ...n,
    x: WIDTH / 2 + (i - nodes.length / 2) * 80,
    y: HEIGHT / 2 + (Math.random() - 0.5) * 60,
    vx: 0,
    vy: 0,
  }))
  const index = Object.fromEntries(simNodes.map((n) => [n.id, n]))
  for (let t = 0; t < iterations; t += 1) {
    for (let i = 0; i < simNodes.length; i += 1) {
      for (let j = i + 1; j < simNodes.length; j += 1) {
        const a = simNodes[i]
        const b = simNodes[j]
        let dx = a.x - b.x
        let dy = a.y - b.y
        const dist = Math.max(1, Math.hypot(dx, dy))
        const repulse = 4200 / (dist * dist)
        dx = (dx / dist) * repulse
        dy = (dy / dist) * repulse
        a.vx += dx
        a.vy += dy
        b.vx -= dx
        b.vy -= dy
      }
    }
    for (const edge of edges) {
      const a = index[edge.source]
      const b = index[edge.target]
      if (!a || !b) continue
      let dx = b.x - a.x
      let dy = b.y - a.y
      const dist = Math.max(1, Math.hypot(dx, dy))
      const attract = (dist - 140) * 0.04
      dx = (dx / dist) * attract
      dy = (dy / dist) * attract
      a.vx += dx
      a.vy += dy
      b.vx -= dx
      b.vy -= dy
    }
    for (const n of simNodes) {
      n.vx += (WIDTH / 2 - n.x) * 0.002
      n.vy += (HEIGHT / 2 - n.y) * 0.002
      n.vx *= 0.85
      n.vy *= 0.85
      n.x += n.vx
      n.y += n.vy
      n.x = Math.max(40, Math.min(WIDTH - 40, n.x))
      n.y = Math.max(40, Math.min(HEIGHT - 40, n.y))
    }
  }
  return simNodes
}

export default function EntanglementGraph() {
  const [graph, setGraph] = useState(null)
  const [selectedPair, setSelectedPair] = useState(null)
  const [decomposition, setDecomposition] = useState(null)
  const [err, setErr] = useState(null)
  const [loading, setLoading] = useState(true)
  const svgRef = useRef(null)

  const load = useCallback(() => {
    setErr(null)
    setLoading(true)
    api.getEntanglementGraph()
      .then((data) => setGraph(data))
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load])

  const positioned = useMemo(() => {
    if (!graph?.nodes?.length) return []
    return layoutForce(graph.nodes, graph.edges || [])
  }, [graph])

  const onEdgeClick = (edge) => {
    if (!edge.pair_id) return
    setSelectedPair(edge.pair_id)
    api.getEntanglementPair(edge.pair_id)
      .then((res) => setDecomposition(res.decomposition || {}))
      .catch((e) => setErr(e.message))
  }

  const seedDemo = () => {
    setErr(null)
    api.seedQuantumDemo()
      .then(() => load())
      .catch((e) => setErr(e.message))
  }

  return (
    <Layout title="Entanglement graph">
      <Breadcrumbs items={[{ label: 'Home', href: '#/home' }, { label: 'Entanglement' }]} />
      <SharedEventSummary
        eyebrow="Quantum visibility"
        title="Entanglement graph"
        intro="Force-directed view of correlated entity pairs from StateCorrelator. Click an edge for dimensional decomposition."
        status={graph?.anomaly_count ? 'watch' : 'healthy'}
        statusTone={graph?.anomaly_count ? 'warn' : 'good'}
        happened={`${graph?.nodes?.length || 0} entities · ${graph?.edges?.length || 0} pairs · ${graph?.anomaly_count || 0} anomalies`}
        when={graph?.generated_at || '—'}
        why="Operators need to see implicit coupling before approving swarm or evolution work."
        changed={selectedPair ? `Inspecting pair ${selectedPair}` : 'Select an edge to inspect correlation dimensions.'}
        next="Low correlation pairs may need meditation or fingerprint reconcile."
        context={[
          { label: 'Noise profiles', value: '#/noise-profiles' },
          { label: 'Syndrome dashboard', value: '#/syndrome' },
          { label: 'Entities', value: '#/entities' },
        ]}
      />
      <div style={{ marginBottom: 12 }}>
        <button type="button" onClick={seedDemo}>Seed demo data</button>
        {' '}
        <button type="button" onClick={load}>Refresh</button>
      </div>
      {err && <StateNotice tone="danger" title="Graph error" detail={err} action={<button type="button" onClick={load}>Retry</button>} />}
      {loading ? <PageSkeleton label="Loading" /> : null}
      {!loading && graph && (
        <>
          <svg ref={svgRef} width={WIDTH} height={HEIGHT} style={{ border: '1px solid var(--border)', borderRadius: 8, background: 'var(--panel)' }} data-testid="entanglement-graph-svg">
            {(graph.edges || []).map((edge) => {
              const a = positioned.find((n) => n.id === edge.source)
              const b = positioned.find((n) => n.id === edge.target)
              if (!a || !b) return null
              return (
                <g key={`${edge.source}-${edge.target}`} onClick={() => onEdgeClick(edge)} style={{ cursor: 'pointer' }}>
                  <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="var(--accent)" strokeWidth={2 + (edge.coefficient || 0) * 2} opacity={0.85} />
                  <title>{`${edge.source} ↔ ${edge.target} (${(edge.coefficient || 0).toFixed(2)})`}</title>
                </g>
              )
            })}
            {positioned.map((node) => (
              <g key={node.id}>
                <circle cx={node.x} cy={node.y} r={node.anomaly ? 14 : 10} fill={node.anomaly ? '#f85149' : '#3fb950'} stroke="#fff" strokeWidth={1} />
                <text x={node.x} y={node.y + 24} textAnchor="middle" fill="#c9d1d9" fontSize={11}>{node.label}</text>
              </g>
            ))}
          </svg>
          {decomposition && (
            <section style={{ marginTop: 16 }} data-testid="pair-decomposition">
              <h2 style={{ fontSize: 16 }}>Pair decomposition — {selectedPair}</h2>
              <table className="table-basic">
                <thead><tr><th>Dimension</th><th>Weight</th></tr></thead>
                <tbody>
                  {Object.entries(decomposition).map(([k, v]) => (
                    <tr key={k}><td>{k}</td><td>{Number(v).toFixed(3)}</td></tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}
        </>
      )}
    </Layout>
  )
}
