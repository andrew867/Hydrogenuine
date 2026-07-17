import React, { useEffect, useMemo, useState } from 'react'
import Layout from '../components/Layout.jsx'
import StateNotice from '../components/StateNotice.jsx'
import { api } from '../lib/api.js'

function groupByKind(items) {
  const out = {}
  for (const item of items || []) {
    const key = item.tool_kind || 'other'
    if (!out[key]) out[key] = []
    out[key].push(item)
  }
  return out
}

export default function ExecutableRegistryPage() {
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [error, setError] = useState('')
  const [overview, setOverview] = useState({ summary: { total_tools: 0, total_versions: 0, by_kind: [] }, executables: [] })
  const [selectedId, setSelectedId] = useState('')
  const [tool, setTool] = useState(null)
  const [versions, setVersions] = useState([])

  const grouped = useMemo(() => groupByKind(overview.executables), [overview.executables])

  const loadOverview = async (preferredId = selectedId) => {
    setLoading(true)
    setError('')
    try {
      const overviewData = await api.getExecutableRegistryOverview()
      setOverview(overviewData || { summary: { total_tools: 0, total_versions: 0, by_kind: [] }, executables: [] })
      const tools = overviewData?.executables || []
      const nextId = preferredId || tools[0]?.tool_id || ''
      setSelectedId(nextId)
      if (nextId) {
        const detail = await api.getExecutableRegistryRecord(nextId)
        setTool(detail?.executable || null)
        setVersions(detail?.executable?.versions || [])
      } else {
        setTool(null)
        setVersions([])
      }
    } catch (err) {
      setError(err?.message || 'Could not load executable registry')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadOverview()
  }, [])

  const loadTool = async (toolId) => {
    setSelectedId(toolId)
    setError('')
    try {
      const detail = await api.getExecutableRegistryRecord(toolId)
      setTool(detail?.executable || null)
      setVersions(detail?.executable?.versions || [])
    } catch (err) {
      setError(err?.message || 'Could not load executable record')
    }
  }

  const syncRegistry = async () => {
    setSyncing(true)
    setError('')
    try {
      await api.syncExecutableRegistry({})
      await loadOverview(selectedId)
    } catch (err) {
      setError(err?.message || 'Could not sync executable registry')
    } finally {
      setSyncing(false)
    }
  }

  return (
    <Layout title="Executable Registry">
      {error ? <StateNotice tone="danger" title="Could not load executable registry" detail={error} action={<button type="button" onClick={loadOverview}>Retry</button>} /> : null}
      {loading ? <StateNotice title="Loading executable registry" detail="Reading executable metadata and version history from Postgres." /> : null}
      <section className="section-card" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', alignItems: 'center' }}>
          <div>
            <div className="eyebrow">Source and executable plane</div>
            <h2 style={{ margin: '6px 0 8px' }}>One pane for executable metadata and archive history.</h2>
            <p className="muted" style={{ margin: 0, maxWidth: 800 }}>
              The registry tracks executable source metadata, module paths, versions, and archive state in Postgres so
              the operator can inspect how the runtime is wired without treating Git as a black box.
            </p>
          </div>
          <button type="button" onClick={syncRegistry} disabled={syncing}>
            {syncing ? 'Syncing…' : 'Sync registry'}
          </button>
        </div>
      </section>

      <div className="card-grid" style={{ marginBottom: 16 }}>
        <div className="card"><strong>{overview.summary?.total_tools ?? 0}</strong><div className="muted">Executables</div></div>
        <div className="card"><strong>{overview.summary?.total_versions ?? 0}</strong><div className="muted">Versions</div></div>
        <div className="card"><strong>{Object.keys(grouped).length}</strong><div className="muted">Kinds</div></div>
      </div>

      <div className="split-grid">
        <section className="section-card">
          <h3 style={{ marginTop: 0 }}>By kind</h3>
          <div style={{ display: 'grid', gap: 12 }}>
            {Object.entries(grouped).map(([kind, items]) => (
              <div key={kind} className="card">
                <div className="eyebrow">{kind}</div>
                <div style={{ marginTop: 4 }}>{items.length} records</div>
                <div className="muted" style={{ fontSize: 12, marginTop: 6 }}>
                  {items.slice(0, 3).map((item) => item.title).join(' · ')}
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="section-card">
          <h3 style={{ marginTop: 0 }}>Records</h3>
          <div style={{ display: 'grid', gap: 10 }}>
            {(overview.executables || []).map((item) => (
              <button
                key={item.tool_id}
                type="button"
                onClick={() => loadTool(item.tool_id)}
                className={`card ${selectedId === item.tool_id ? 'card-selected' : ''}`}
                style={{ textAlign: 'left' }}
              >
                <div className="eyebrow">{item.tool_kind}{item.platform_id ? ` · ${item.platform_id}` : ''}</div>
                <div style={{ fontWeight: 700 }}>{item.title}</div>
                <div className="muted" style={{ fontSize: 12 }}>{item.file_path}</div>
              </button>
            ))}
          </div>
        </section>
      </div>

      {tool ? (
        <section className="section-card" style={{ marginTop: 16 }}>
          <h3 style={{ marginTop: 0 }}>{tool.title}</h3>
          <div className="muted" style={{ fontSize: 12, marginBottom: 12 }}>{tool.file_path}</div>
          <div className="card-grid">
            <div className="card"><div className="eyebrow">Module</div><div>{tool.module_path}</div></div>
            <div className="card"><div className="eyebrow">Kind</div><div>{tool.tool_kind}</div></div>
            <div className="card"><div className="eyebrow">Platform</div><div>{tool.platform_id || 'global'}</div></div>
            <div className="card"><div className="eyebrow">Versions</div><div>{versions.length}</div></div>
          </div>
          <div style={{ marginTop: 16 }}>
            <h4>Versions</h4>
            <div style={{ display: 'grid', gap: 8 }}>
              {versions.map((version) => (
                <div key={version.version_id} className="card">
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
                    <strong>v{version.version_number}</strong>
                    <span className="muted">{version.state}</span>
                  </div>
                  <div className="muted" style={{ fontSize: 12 }}>{version.change_summary || version.created_at}</div>
                </div>
              ))}
            </div>
          </div>
        </section>
      ) : null}
    </Layout>
  )
}
