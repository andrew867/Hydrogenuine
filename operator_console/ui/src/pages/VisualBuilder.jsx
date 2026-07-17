import React, { useEffect, useMemo, useState } from 'react'
import Layout from '../components/Layout.jsx'
import JsonBlock from '../components/JsonBlock.jsx'
import { api } from '../lib/api.js'
import { withReturnUrl } from '../lib/navigationContext.js'

const DEFAULT_NODE = {
  id: 'new_node',
  type: 'agent',
  assigned_entity: '',
  depends_on: [],
  inputs: {},
  policy: { timeout_s: 300, max_retries: 0 },
}

function parseJsonInput(text, fallback = {}) {
  if (!text || !text.trim()) return fallback
  return JSON.parse(text)
}

function computeLevelMap(nodes) {
  const byId = new Map(nodes.map((n) => [n.id, n]))
  const memo = new Map()
  const active = new Set()

  const level = (id) => {
    if (memo.has(id)) return memo.get(id)
    if (active.has(id)) return 0
    active.add(id)
    const node = byId.get(id)
    if (!node) {
      active.delete(id)
      memo.set(id, 0)
      return 0
    }
    const deps = Array.isArray(node.depends_on) ? node.depends_on.filter((d) => byId.has(d)) : []
    const v = deps.length ? Math.max(...deps.map((d) => level(d) + 1)) : 0
    active.delete(id)
    memo.set(id, v)
    return v
  }

  nodes.forEach((n) => level(n.id))
  return memo
}

function normalizeDag(dag) {
  if (!dag || typeof dag !== 'object') return null
  return {
    graph_id: dag.graph_id || '',
    version: dag.version || '1.0',
    run_policy: dag.run_policy || { max_concurrency: 1 },
    inputs: dag.inputs || {},
    nodes: Array.isArray(dag.nodes) ? dag.nodes : [],
  }
}

export default function VisualBuilder() {
  const [jobs, setJobs] = useState([])
  const [selectedJob, setSelectedJob] = useState('')
  const [dag, setDag] = useState(null)
  const [selectedNodeId, setSelectedNodeId] = useState('')
  const [nodeInputsText, setNodeInputsText] = useState('{}')
  const [graphInputsText, setGraphInputsText] = useState('{}')
  const [runPolicyText, setRunPolicyText] = useState('{}')
  const [edgeSource, setEdgeSource] = useState('')
  const [edgeTarget, setEdgeTarget] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const levelMap = useMemo(() => computeLevelMap(dag?.nodes || []), [dag])
  const columns = useMemo(() => {
    const grouped = new Map()
    for (const n of dag?.nodes || []) {
      const lv = levelMap.get(n.id) || 0
      if (!grouped.has(lv)) grouped.set(lv, [])
      grouped.get(lv).push(n)
    }
    return [...grouped.entries()].sort((a, b) => a[0] - b[0])
  }, [dag, levelMap])

  const selectedNode = useMemo(() => {
    if (!dag) return null
    return (dag.nodes || []).find((n) => n.id === selectedNodeId) || null
  }, [dag, selectedNodeId])

  const nodeIds = useMemo(() => (dag?.nodes || []).map((n) => n.id), [dag])

  useEffect(() => {
    let mounted = true
    api.listScheduledJobs()
      .then((res) => {
        if (!mounted) return
        const items = res.jobs || []
        setJobs(items)
        const preferred = localStorage.getItem('openclaw_builder_job_id') || ''
        if (preferred && items.some((j) => j.job_id === preferred)) {
          setSelectedJob(preferred)
          localStorage.removeItem('openclaw_builder_job_id')
          return
        }
        const first = items.find((j) => j.exists) || items[0]
        if (first) setSelectedJob(first.job_id)
      })
      .catch((e) => setError(e.message))
    return () => { mounted = false }
  }, [])

  useEffect(() => {
    if (!selectedJob) return
    setError(null)
    setResult(null)
    api.getScheduledJobDag(selectedJob)
      .then((res) => {
        const next = normalizeDag(res.dag)
        setDag(next)
        setGraphInputsText(JSON.stringify(next?.inputs || {}, null, 2))
        setRunPolicyText(JSON.stringify(next?.run_policy || {}, null, 2))
        const firstNode = (next?.nodes || [])[0]
        setSelectedNodeId(firstNode?.id || '')
        setNodeInputsText(JSON.stringify(firstNode?.inputs || {}, null, 2))
        setEdgeSource(firstNode?.id || '')
        setEdgeTarget(firstNode?.id || '')
      })
      .catch((e) => {
        setDag(null)
        setError(e.message)
      })
  }, [selectedJob])

  useEffect(() => {
    if (!selectedNode) {
      setNodeInputsText('{}')
      return
    }
    setNodeInputsText(JSON.stringify(selectedNode.inputs || {}, null, 2))
  }, [selectedNode])

  useEffect(() => {
    if (!nodeIds.length) {
      setEdgeSource('')
      setEdgeTarget('')
      return
    }
    if (!edgeSource || !nodeIds.includes(edgeSource)) setEdgeSource(nodeIds[0])
    if (!edgeTarget || !nodeIds.includes(edgeTarget)) setEdgeTarget(nodeIds[0])
  }, [nodeIds, edgeSource, edgeTarget])

  const updateDag = (fn) => {
    setDag((prev) => {
      if (!prev) return prev
      return fn(prev)
    })
  }

  const updateNode = (nodeId, patch) => {
    updateDag((prev) => ({
      ...prev,
      nodes: prev.nodes.map((n) => (n.id === nodeId ? { ...n, ...patch } : n)),
    }))
  }

  const renameNode = (oldId, newId) => {
    const target = newId.trim()
    if (!target) return
    if ((dag?.nodes || []).some((n) => n.id === target && n.id !== oldId)) {
      setError(`Node id already exists: ${target}`)
      return
    }
    updateDag((prev) => ({
      ...prev,
      nodes: prev.nodes.map((n) => {
        if (n.id === oldId) return { ...n, id: target }
        const deps = Array.isArray(n.depends_on) ? n.depends_on.map((d) => (d === oldId ? target : d)) : []
        return { ...n, depends_on: deps }
      }),
    }))
    setSelectedNodeId(target)
    if (edgeSource === oldId) setEdgeSource(target)
    if (edgeTarget === oldId) setEdgeTarget(target)
  }

  const addNode = () => {
    if (!dag) return
    const ids = new Set((dag.nodes || []).map((n) => n.id))
    let i = 1
    let next = `new_node_${i}`
    while (ids.has(next)) {
      i += 1
      next = `new_node_${i}`
    }
    const created = { ...DEFAULT_NODE, id: next }
    updateDag((prev) => ({ ...prev, nodes: [...prev.nodes, created] }))
    setSelectedNodeId(next)
    setNodeInputsText(JSON.stringify(created.inputs, null, 2))
    setEdgeSource(next)
    setEdgeTarget(next)
  }

  const deleteSelected = () => {
    if (!dag || !selectedNodeId) return
    updateDag((prev) => {
      const kept = prev.nodes.filter((n) => n.id !== selectedNodeId)
      return {
        ...prev,
        nodes: kept.map((n) => ({ ...n, depends_on: (n.depends_on || []).filter((d) => d !== selectedNodeId) })),
      }
    })
    const next = (dag.nodes || []).find((n) => n.id !== selectedNodeId)
    setSelectedNodeId(next?.id || '')
  }

  const addEdge = () => {
    if (!dag || !edgeSource || !edgeTarget) return
    if (edgeSource === edgeTarget) {
      setError('Cannot add self-dependency edge.')
      return
    }
    updateDag((prev) => ({
      ...prev,
      nodes: prev.nodes.map((n) => {
        if (n.id !== edgeTarget) return n
        const deps = Array.isArray(n.depends_on) ? [...n.depends_on] : []
        if (!deps.includes(edgeSource)) deps.push(edgeSource)
        return { ...n, depends_on: deps }
      }),
    }))
    setError(null)
  }

  const removeEdge = () => {
    if (!dag || !edgeSource || !edgeTarget) return
    updateDag((prev) => ({
      ...prev,
      nodes: prev.nodes.map((n) => {
        if (n.id !== edgeTarget) return n
        return { ...n, depends_on: (n.depends_on || []).filter((d) => d !== edgeSource) }
      }),
    }))
  }

  const doValidate = async () => {
    if (!dag) return
    setError(null)
    setResult(null)
    try {
      setResult(await api.validateGraph(dag))
    } catch (e) {
      setError(e.message)
    }
  }

  const doReview = async () => {
    if (!dag) return
    setError(null)
    setResult(null)
    try {
      setResult(await api.reviewGraph(dag))
    } catch (e) {
      setError(e.message)
    }
  }

  const doSave = async () => {
    if (!dag || !selectedJob) return
    setError(null)
    setResult(null)
    setBusy(true)
    try {
      const res = await api.saveScheduledJobDag(selectedJob, dag)
      setResult(res)
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  const applyNodeInputsText = () => {
    if (!selectedNode) return
    try {
      const parsed = parseJsonInput(nodeInputsText, {})
      updateNode(selectedNode.id, { inputs: parsed })
      setError(null)
    } catch (e) {
      setError(`Node inputs JSON error: ${e.message}`)
    }
  }

  const applyGraphInputs = () => {
    if (!dag) return
    try {
      const parsed = parseJsonInput(graphInputsText, {})
      updateDag((prev) => ({ ...prev, inputs: parsed }))
      setError(null)
    } catch (e) {
      setError(`Graph inputs JSON error: ${e.message}`)
    }
  }

  const applyRunPolicy = () => {
    if (!dag) return
    try {
      const parsed = parseJsonInput(runPolicyText, {})
      updateDag((prev) => ({ ...prev, run_policy: parsed }))
      setError(null)
    } catch (e) {
      setError(`Run policy JSON error: ${e.message}`)
    }
  }

  const exportJson = () => {
    if (!dag) return
    const blob = new Blob([JSON.stringify(dag, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${selectedJob || 'dag'}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const importJson = (event) => {
    const file = event.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => {
      try {
        const parsed = JSON.parse(String(reader.result || '{}'))
        const next = normalizeDag(parsed)
        setDag(next)
        setGraphInputsText(JSON.stringify(next?.inputs || {}, null, 2))
        setRunPolicyText(JSON.stringify(next?.run_policy || {}, null, 2))
        const first = (next?.nodes || [])[0]
        setSelectedNodeId(first?.id || '')
      } catch (e) {
        setError(`Import JSON failed: ${e.message}`)
      }
    }
    reader.readAsText(file)
  }

  const openInRunDag = () => {
    if (!dag) return
    localStorage.setItem('openclaw_dag_draft', JSON.stringify(dag, null, 2))
    window.location.hash = withReturnUrl('#/run')
  }

  return (
    <Layout title="Visual DAG Builder">
      {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}
      <section className="section-card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>Scheduled jobs</h3>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
          <label htmlFor="scheduled-job">Job</label>
          <select id="scheduled-job" value={selectedJob} onChange={(e) => setSelectedJob(e.target.value)}>
            {jobs.map((j) => (
              <option key={j.job_id} value={j.job_id}>
                {j.job_id} ({j.graph_id || 'missing'})
              </option>
            ))}
          </select>
          <button type="button" onClick={doValidate}>Validate</button>
          <button type="button" onClick={doReview}>Review</button>
          <button type="button" onClick={doSave} disabled={busy || !dag}>{busy ? 'Saving...' : 'Save DAG'}</button>
          <button type="button" onClick={openInRunDag} disabled={!dag}>Open in Run DAG</button>
          <button type="button" onClick={exportJson} disabled={!dag}>Export JSON</button>
          <label style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 12 }}>Import</span>
            <input type="file" accept="application/json" onChange={importJson} />
          </label>
        </div>
      </section>

      <section className="section-card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>Graph metadata</h3>
        {!dag && <p className="muted">Load a workflow DAG to edit graph metadata.</p>}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          <label>
            <div style={{ fontSize: 12, color: '#9aa3b2' }}>graph_id</div>
            <input
              value={dag?.graph_id || ''}
              onChange={(e) => updateDag((prev) => ({ ...prev, graph_id: e.target.value }))}
              style={{ width: '100%' }}
              disabled={!dag}
            />
          </label>
          <label>
            <div style={{ fontSize: 12, color: '#9aa3b2' }}>version</div>
            <input
              value={dag?.version || ''}
              onChange={(e) => updateDag((prev) => ({ ...prev, version: e.target.value }))}
              style={{ width: '100%' }}
              disabled={!dag}
            />
          </label>
        </div>
        <div style={{ marginTop: 10 }}>
          <div style={{ fontSize: 12, color: '#9aa3b2' }}>run_policy (JSON)</div>
          <textarea
            rows={4}
            value={runPolicyText}
            onChange={(e) => setRunPolicyText(e.target.value)}
            style={{ width: '100%', fontFamily: 'ui-monospace, monospace', fontSize: 12 }}
          />
          <button type="button" onClick={applyRunPolicy} disabled={!dag}>Apply run_policy JSON</button>
        </div>
        <div style={{ marginTop: 10 }}>
          <div style={{ fontSize: 12, color: '#9aa3b2' }}>inputs (JSON)</div>
          <textarea
            rows={4}
            value={graphInputsText}
            onChange={(e) => setGraphInputsText(e.target.value)}
            style={{ width: '100%', fontFamily: 'ui-monospace, monospace', fontSize: 12 }}
          />
          <button type="button" onClick={applyGraphInputs} disabled={!dag}>Apply inputs JSON</button>
        </div>
      </section>

      <section className="section-card" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ marginTop: 0, marginBottom: 8 }}>Visual nodes</h3>
          <button type="button" onClick={addNode} disabled={!dag}>Add node</button>
        </div>
        {!dag && <p className="muted">Load a workflow DAG to inspect nodes visually.</p>}
        {dag && (
          <div style={{ display: 'grid', gridTemplateColumns: `repeat(${Math.max(columns.length, 1)}, minmax(220px, 1fr))`, gap: 12 }}>
            {columns.map(([level, nodes]) => (
              <div key={level} style={{ border: '1px solid var(--border)', borderRadius: 8, padding: 10 }}>
                <div style={{ fontSize: 12, color: '#9aa3b2', marginBottom: 8 }}>Level {level}</div>
                {nodes.map((n) => (
                  <button
                    key={n.id}
                    type="button"
                    onClick={() => setSelectedNodeId(n.id)}
                    style={{
                      width: '100%',
                      textAlign: 'left',
                      marginBottom: 8,
                      borderRadius: 8,
                      border: n.id === selectedNodeId ? '1px solid var(--accent)' : '1px solid var(--border)',
                      background: n.id === selectedNodeId ? 'rgba(17, 156, 255, 0.12)' : 'transparent',
                      padding: 8,
                    }}
                  >
                    <div style={{ fontWeight: 600 }}>{n.id}</div>
                    <div style={{ fontSize: 12, color: '#9aa3b2' }}>{n.type} {n.assigned_entity ? `| ${n.assigned_entity}` : ''}</div>
                    <div style={{ fontSize: 12, color: '#9aa3b2' }}>depends_on: {(n.depends_on || []).join(', ') || 'none'}</div>
                  </button>
                ))}
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="section-card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>Edge management</h3>
        {!dag && <p className="muted">Load a DAG before editing dependency edges.</p>}
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
          <label>
            <div style={{ fontSize: 12, color: '#9aa3b2' }}>Source</div>
            <select value={edgeSource} onChange={(e) => setEdgeSource(e.target.value)} disabled={!dag || !nodeIds.length}>
              {nodeIds.map((id) => <option key={`src-${id}`} value={id}>{id}</option>)}
            </select>
          </label>
          <label>
            <div style={{ fontSize: 12, color: '#9aa3b2' }}>Target</div>
            <select value={edgeTarget} onChange={(e) => setEdgeTarget(e.target.value)} disabled={!dag || !nodeIds.length}>
              {nodeIds.map((id) => <option key={`dst-${id}`} value={id}>{id}</option>)}
            </select>
          </label>
          <button type="button" onClick={addEdge} disabled={!dag || !nodeIds.length}>Add edge</button>
          <button type="button" onClick={removeEdge} disabled={!dag || !nodeIds.length}>Remove edge</button>
        </div>
      </section>

      <section className="section-card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>Node editor</h3>
        {!selectedNode && <p className="muted">Select a node from the visual board.</p>}
        {selectedNode && (
          <>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
              <label>
                <div style={{ fontSize: 12, color: '#9aa3b2' }}>id</div>
                <input value={selectedNode.id} onChange={(e) => renameNode(selectedNode.id, e.target.value)} style={{ width: '100%' }} />
              </label>
              <label>
                <div style={{ fontSize: 12, color: '#9aa3b2' }}>type</div>
                <input value={selectedNode.type || ''} onChange={(e) => updateNode(selectedNode.id, { type: e.target.value })} style={{ width: '100%' }} />
              </label>
              <label>
                <div style={{ fontSize: 12, color: '#9aa3b2' }}>assigned_entity</div>
                <input value={selectedNode.assigned_entity || ''} onChange={(e) => updateNode(selectedNode.id, { assigned_entity: e.target.value })} style={{ width: '100%' }} />
              </label>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginTop: 10 }}>
              <label>
                <div style={{ fontSize: 12, color: '#9aa3b2' }}>depends_on (comma separated)</div>
                <input
                  value={(selectedNode.depends_on || []).join(',')}
                  onChange={(e) => updateNode(selectedNode.id, {
                    depends_on: e.target.value
                      .split(',')
                      .map((d) => d.trim())
                      .filter(Boolean),
                  })}
                  style={{ width: '100%' }}
                />
              </label>
              <label>
                <div style={{ fontSize: 12, color: '#9aa3b2' }}>timeout_s</div>
                <input
                  type="number"
                  value={selectedNode.policy?.timeout_s ?? 300}
                  onChange={(e) => updateNode(selectedNode.id, {
                    policy: { ...selectedNode.policy, timeout_s: Number(e.target.value || 0) },
                  })}
                  style={{ width: '100%' }}
                />
              </label>
              <label>
                <div style={{ fontSize: 12, color: '#9aa3b2' }}>max_retries</div>
                <input
                  type="number"
                  value={selectedNode.policy?.max_retries ?? 0}
                  onChange={(e) => updateNode(selectedNode.id, {
                    policy: { ...selectedNode.policy, max_retries: Number(e.target.value || 0) },
                  })}
                  style={{ width: '100%' }}
                />
              </label>
            </div>
            <div style={{ marginTop: 10 }}>
              <div style={{ fontSize: 12, color: '#9aa3b2' }}>inputs (JSON)</div>
              <textarea
                rows={6}
                value={nodeInputsText}
                onChange={(e) => setNodeInputsText(e.target.value)}
                style={{ width: '100%', fontFamily: 'ui-monospace, monospace', fontSize: 12 }}
              />
              <div style={{ display: 'flex', gap: 8 }}>
                <button type="button" onClick={applyNodeInputsText}>Apply node inputs JSON</button>
                <button type="button" onClick={deleteSelected}>Delete node</button>
              </div>
            </div>
          </>
        )}
      </section>

      {result && (
        <section className="section-card">
          <h3 style={{ marginTop: 0 }}>Result</h3>
          <JsonBlock value={result} />
        </section>
      )}
    </Layout>
  )
}
