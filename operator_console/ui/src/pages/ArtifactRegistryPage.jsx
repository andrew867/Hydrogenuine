import React, { useEffect, useMemo, useState } from 'react'
import Layout from '../components/Layout.jsx'
import StateNotice from '../components/StateNotice.jsx'
import { api } from '../lib/api.js'

function groupByClass(items) {
  const out = {}
  for (const item of items || []) {
    const key = item.class_key || 'other'
    if (!out[key]) out[key] = []
    out[key].push(item)
  }
  return out
}

function getArtifactState(item) {
  if (!item) return 'unknown'
  if (typeof item.latest_status === 'string' && item.latest_status.trim()) return item.latest_status.trim()
  return item.active === 0 ? 'archived' : 'current'
}

function isHistoricalArtifact(item) {
  return item?.active === 0 || getArtifactState(item) === 'archived'
}

export default function ArtifactRegistryPage() {
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [error, setError] = useState('')
  const [overview, setOverview] = useState({ summary: { total_artifacts: 0, total_versions: 0, by_class: [] }, artifacts: [] })
  const [classes, setClasses] = useState([])
  const [selectedId, setSelectedId] = useState('')
  const [artifact, setArtifact] = useState(null)
  const [versions, setVersions] = useState([])

  const grouped = useMemo(() => groupByClass(overview.artifacts), [overview.artifacts])
  const currentArtifacts = useMemo(
    () => (overview.artifacts || []).filter((item) => !isHistoricalArtifact(item)),
    [overview.artifacts],
  )
  const historicalArtifacts = useMemo(
    () => (overview.artifacts || []).filter((item) => isHistoricalArtifact(item)),
    [overview.artifacts],
  )

  const loadOverview = async (preferredId = selectedId) => {
    setLoading(true)
    setError('')
    try {
      const [overviewData, classData] = await Promise.all([
        api.getArtifactRegistryOverview(),
        api.getArtifactRegistryClasses(),
      ])
      setOverview(overviewData || { summary: { total_artifacts: 0, total_versions: 0, by_class: [] }, artifacts: [] })
      setClasses(classData?.classes || [])
      const docs = overviewData?.artifacts || []
      const nextId = preferredId || docs[0]?.artifact_id || ''
      setSelectedId(nextId)
      if (nextId) {
        const detail = await api.getArtifactRegistryRecord(nextId)
        setArtifact(detail?.artifact || null)
        setVersions(detail?.artifact?.versions || [])
      } else {
        setArtifact(null)
        setVersions([])
      }
    } catch (err) {
      setError(err?.message || 'Could not load artifact registry')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadOverview()
  }, [])

  const loadArtifact = async (artifactId) => {
    setSelectedId(artifactId)
    setError('')
    try {
      const detail = await api.getArtifactRegistryRecord(artifactId)
      setArtifact(detail?.artifact || null)
      setVersions(detail?.artifact?.versions || [])
    } catch (err) {
      setError(err?.message || 'Could not load artifact record')
    }
  }

  const syncRegistry = async () => {
    setSyncing(true)
    setError('')
    try {
      await api.syncArtifactRegistry({})
      await loadOverview(selectedId)
    } catch (err) {
      setError(err?.message || 'Could not sync artifact registry')
    } finally {
      setSyncing(false)
    }
  }

  return (
    <Layout title="Artifact Registry">
      {error ? <StateNotice tone="danger" title="Could not load artifact registry" detail={error} action={<button type="button" onClick={loadOverview}>Retry</button>} /> : null}
      {loading ? <StateNotice title="Loading artifact registry" detail="Reading generated artifacts, logs, screenshots, backups, snapshots, and reflection artifacts." /> : null}
      <section className="section-card" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', alignItems: 'center' }}>
          <div>
            <div className="eyebrow">Archive and recovery plane</div>
            <h2 style={{ margin: '6px 0 8px' }}>One pane for generated artifacts, recoverable snapshots, and typed reflections.</h2>
            <p className="muted" style={{ margin: 0, maxWidth: 800 }}>
              The registry tracks generated files, screenshots, backups, logs, archive snapshots, and reflection artifacts
              as database records so the operator can inspect and recover them without digging through disk trees.
            </p>
          </div>
          <button type="button" onClick={syncRegistry} disabled={syncing}>
            {syncing ? 'Syncing…' : 'Sync registry'}
          </button>
        </div>
      </section>

      <div className="card-grid" style={{ marginBottom: 16 }}>
        <div className="card"><strong>{overview.summary?.total_artifacts ?? 0}</strong><div className="muted">Artifacts</div></div>
        <div className="card"><strong>{overview.summary?.total_versions ?? 0}</strong><div className="muted">Versions</div></div>
        <div className="card"><strong>{classes.length}</strong><div className="muted">Artifact classes</div></div>
        <div className="card"><strong>{currentArtifacts.length}</strong><div className="muted">Current records</div></div>
        <div className="card"><strong>{historicalArtifacts.length}</strong><div className="muted">Historical records</div></div>
      </div>

      <div className="split-grid">
        <section className="section-card">
          <h3 style={{ marginTop: 0 }}>By class</h3>
          <div style={{ display: 'grid', gap: 12 }}>
            {Object.entries(grouped).map(([classKey, items]) => (
              <div key={classKey} className="card">
                <div className="eyebrow">{classKey}</div>
                <div style={{ marginTop: 4 }}>{items.length} records</div>
                <div className="muted" style={{ fontSize: 12, marginTop: 6 }}>
                  {items.slice(0, 3).map((item) => item.title).join(' · ')}
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="section-card">
          <h3 style={{ marginTop: 0 }}>Current records</h3>
          <div style={{ display: 'grid', gap: 10 }}>
            {currentArtifacts.map((item) => (
              <button
                key={item.artifact_id}
                type="button"
                onClick={() => loadArtifact(item.artifact_id)}
                className={`card ${selectedId === item.artifact_id ? 'card-selected' : ''}`}
                style={{ textAlign: 'left' }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center' }}>
                  <div className="eyebrow">{item.class_key}</div>
                  <span className="muted" style={{ fontSize: 12 }}>{getArtifactState(item)}</span>
                </div>
                <div style={{ fontWeight: 700 }}>{item.title}</div>
                <div className="muted" style={{ fontSize: 12 }}>{item.file_path}</div>
              </button>
            ))}
          </div>
        </section>
      </div>

      <section className="section-card" style={{ marginTop: 16 }}>
        <h3 style={{ marginTop: 0 }}>Historical records</h3>
        {historicalArtifacts.length ? (
          <div style={{ display: 'grid', gap: 10 }}>
            {historicalArtifacts.map((item) => (
              <button
                key={item.artifact_id}
                type="button"
                onClick={() => loadArtifact(item.artifact_id)}
                className={`card ${selectedId === item.artifact_id ? 'card-selected' : ''}`}
                style={{ textAlign: 'left' }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center' }}>
                  <div className="eyebrow">{item.class_key}</div>
                  <span className="muted" style={{ fontSize: 12 }}>{getArtifactState(item)}</span>
                </div>
                <div style={{ fontWeight: 700 }}>{item.title}</div>
                <div className="muted" style={{ fontSize: 12 }}>{item.file_path}</div>
              </button>
            ))}
          </div>
        ) : (
          <div className="muted">No historical records in the registry.</div>
        )}
      </section>

      {artifact ? (
        <section className="section-card" style={{ marginTop: 16 }}>
          <h3 style={{ marginTop: 0 }}>{artifact.title}</h3>
          <div className="muted" style={{ fontSize: 12, marginBottom: 12 }}>{artifact.file_path}</div>
          <div className="card-grid">
            <div className="card"><div className="eyebrow">Kind</div><div>{artifact.content_kind}</div></div>
            <div className="card"><div className="eyebrow">Mime</div><div>{artifact.mime_type}</div></div>
            <div className="card"><div className="eyebrow">Size</div><div>{artifact.source_size_bytes} bytes</div></div>
            <div className="card"><div className="eyebrow">Versions</div><div>{versions.length}</div></div>
            <div className="card"><div className="eyebrow">State</div><div>{getArtifactState(artifact)}</div></div>
            <div className="card"><div className="eyebrow">Active</div><div>{artifact.active ? 'yes' : 'no'}</div></div>
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
