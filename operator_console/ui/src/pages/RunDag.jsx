import React, { useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import Breadcrumbs from '../components/Breadcrumbs.jsx'
import SharedEventSummary from '../components/SharedEventSummary.jsx'
import JsonBlock from '../components/JsonBlock.jsx'
import MermaidBlock from '../components/MermaidBlock.jsx'
import { api } from '../lib/api.js'
import { getHashQueryParam, normalizeHashHref } from '../lib/navigationContext.js'

export default function RunDag() {
  const [dagText, setDagText] = useState('')
  const [result, setResult] = useState(null)
  const [err, setErr] = useState(null)
  const [draftLoaded, setDraftLoaded] = useState(false)
  const [lineageRunId, setLineageRunId] = useState('')
  const [lineageResult, setLineageResult] = useState(null)
  const [lineageError, setLineageError] = useState(null)
  const [returnUrl, setReturnUrl] = useState('#/')
  const currentRunId = getHashQueryParam('run_id', '')

  useEffect(() => {
    if (draftLoaded) return
    const draft = localStorage.getItem('openclaw_dag_draft')
    if (draft) {
      setDagText(draft)
    }
    setDraftLoaded(true)
  }, [draftLoaded])

  useEffect(() => {
    const sync = () => {
      setLineageRunId(getHashQueryParam('run_id', ''))
      setReturnUrl(normalizeHashHref(getHashQueryParam('returnUrl', '#/')))
    }
    sync()
    window.addEventListener('hashchange', sync)
    return () => window.removeEventListener('hashchange', sync)
  }, [])

  const parse = () => JSON.parse(dagText)

  const doValidate = async () => {
    setErr(null); setResult(null)
    try { setResult(await api.validateGraph(parse())) } catch (e) { setErr(e.message) }
  }
  const doReview = async () => {
    setErr(null); setResult(null)
    try { setResult(await api.reviewGraph(parse())) } catch (e) { setErr(e.message) }
  }
  const doRun = async () => {
    setErr(null); setResult(null)
    try {
      const r = await api.runGraph(parse())
      setResult(r)
      if (r.run_id) window.location.hash = `#/runs/${r.run_id}`
    } catch (e) { setErr(e.message) }
  }

  const saveDraft = () => {
    localStorage.setItem('openclaw_dag_draft', dagText)
  }

  const clearDraft = () => {
    localStorage.removeItem('openclaw_dag_draft')
    setDagText('')
  }

  const loadLineage = async () => {
    if (!lineageRunId.trim()) return
    setLineageError(null)
    try {
      const res = await api.getRunLineage(lineageRunId.trim())
      setLineageResult(res.ok === false ? null : res)
    } catch (e) {
      setLineageResult(null)
      setLineageError(e.message)
    }
  }

  const exportDag = () => {
    try {
      const blob = new Blob([JSON.stringify(parse(), null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'dag.json'
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      setErr(`Export failed: ${e.message}`)
    }
  }

  const importDag = (evt) => {
    const file = evt.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => {
      setDagText(String(reader.result || ''))
    }
    reader.readAsText(file)
  }

  return (
    <Layout title="Run DAG">
      <Breadcrumbs items={[{ label: 'Home', href: '#/' }, { label: 'Runs', href: '#/' }, { label: 'DAG' }]} />
      <SharedEventSummary
        eyebrow="Run drilldown"
        title="Run DAG"
        intro="Inspect the graph for a run or replay a draft without losing the origin context."
        status={lineageResult?.status || (result?.status || 'ready')}
        statusTone={lineageResult?.status === 'completed' ? 'good' : lineageResult?.status === 'blocked' ? 'danger' : 'neutral'}
        happened={lineageResult?.run_id || currentRunId || (result?.run_id || 'Draft DAG')}
        when={lineageResult?.run_id ? `Run ${lineageResult.run_id}` : 'Current session'}
        why="This page explains the graph and keeps the drilldown tied to the source run or draft."
        changed={`Draft ${dagText ? 'present' : 'empty'} · result ${result ? 'ready' : 'not run'} · lineage ${lineageResult ? 'loaded' : 'not loaded'}`}
        next="Validate, review, or run the DAG, then return to the source story."
        context={[
          { label: 'Origin', value: returnUrl !== '#/' ? returnUrl : 'current' },
          { label: 'Run', value: currentRunId || lineageRunId || '—' },
          { label: 'Draft', value: dagText ? 'loaded' : 'empty' },
        ]}
      />
      {err && <div style={{ color:'var(--danger)' }}>{err}</div>}
      {returnUrl !== '#/' && (
        <p style={{ marginBottom: 12 }}>
          <a href={returnUrl} className="nav-link">Back to origin</a>
        </p>
      )}
      <textarea
        value={dagText}
        onChange={e => setDagText(e.target.value)}
        placeholder="Paste DAG JSON here"
        rows={18}
        style={{ width:'100%', fontFamily:'ui-monospace, monospace', fontSize: 12, padding: 10, borderRadius: 8, background: '#0b1118', color: 'var(--text)', border: '1px solid var(--border)' }}
      />
      <div style={{ display:'flex', flexWrap: 'wrap', gap: 10, marginTop: 10 }}>
        <button onClick={doValidate} style={{ padding:'8px 12px', borderRadius:8 }}>Validate</button>
        <button onClick={doReview} style={{ padding:'8px 12px', borderRadius:8 }}>Review</button>
        <button onClick={doRun} style={{ padding:'8px 12px', borderRadius:8 }}>Run</button>
        <button onClick={saveDraft} style={{ padding:'8px 12px', borderRadius:8 }}>Save draft</button>
        <button onClick={exportDag} style={{ padding:'8px 12px', borderRadius:8 }}>Export JSON</button>
        <label style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 12, color: '#9aa3b2' }}>Import</span>
          <input type="file" accept="application/json" onChange={importDag} />
        </label>
        <button onClick={clearDraft} style={{ padding:'8px 12px', borderRadius:8 }}>Clear</button>
      </div>
      <div style={{ marginTop: 18 }}>
        <div style={{ fontWeight: 600, marginBottom: 6 }}>Run lineage lookup</div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          <input
            value={lineageRunId}
            onChange={(e) => setLineageRunId(e.target.value)}
            placeholder="Enter run_id"
            style={{ padding: '8px 10px', borderRadius: 8, minWidth: 280 }}
          />
          <button onClick={loadLineage} style={{ padding:'8px 12px', borderRadius:8 }}>Load lineage</button>
        </div>
        {lineageError && <div style={{ color: 'var(--danger)', marginTop: 6 }}>{lineageError}</div>}
        {lineageResult && (
          <div style={{ marginTop: 10 }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 10 }}>
              <div style={{ background: 'var(--panel-2)', padding: 12, borderRadius: 8 }}>
                <div><strong>Run</strong> <code>{lineageResult.run_id}</code></div>
                <div>Status: {lineageResult.status || '—'}</div>
                <div>Workflow: {lineageResult.workflow_href ? <a href={lineageResult.workflow_href}>{lineageResult.workflow_id || lineageResult.graph_id || '—'}</a> : (lineageResult.workflow_id || lineageResult.graph_id || '—')}</div>
                <div>Activity: {lineageResult.activity_href ? <a href={lineageResult.activity_href}>open activity</a> : '—'}</div>
              </div>
              <div style={{ background: 'var(--panel-2)', padding: 12, borderRadius: 8 }}>
                <div><strong>Swarm links</strong></div>
                <div>Parent: {lineageResult.parent_run_id ? <a href={`#/runs/${lineageResult.parent_run_id}`}>{lineageResult.parent_run_id}</a> : '—'}</div>
                <div>Children: {(lineageResult.child_run_ids || []).length > 0 ? lineageResult.child_run_ids.map((childId, i) => (
                  <span key={childId}>
                    {i > 0 ? ', ' : ''}
                    <a href={`#/runs/${childId}`}>{childId}</a>
                  </span>
                )) : '—'}</div>
              </div>
            </div>
            <MermaidBlock dag={lineageResult.lineage_graph} />
          </div>
        )}
      </div>
      {result && (
        <div style={{ marginTop: 12 }}>
          <JsonBlock value={result} />
        </div>
      )}
    </Layout>
  )
}


