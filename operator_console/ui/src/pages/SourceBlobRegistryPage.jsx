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

function formatVersionLine(version) {
  if (!version) return ''
  const suffix = version.change_summary || version.created_at || 'no summary'
  return `v${version.version_number} · ${suffix}`
}

export default function SourceBlobRegistryPage() {
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [overview, setOverview] = useState({ summary: { total_documents: 0, total_versions: 0, by_class: [], classes: [] }, source_blobs: [] })
  const [selectedId, setSelectedId] = useState('')
  const [sourceBlob, setSourceBlob] = useState(null)
  const [versions, setVersions] = useState([])
  const [diffView, setDiffView] = useState(null)
  const [runResult, setRunResult] = useState(null)
  const [running, setRunning] = useState(false)
  const [editorTitle, setEditorTitle] = useState('')
  const [editorBody, setEditorBody] = useState('')
  const [editorChangeSummary, setEditorChangeSummary] = useState('edited via operator console')
  const [runEntrypoint, setRunEntrypoint] = useState('')
  const [runArgs, setRunArgs] = useState('')
  const [runTimeout, setRunTimeout] = useState('120')
  const [createFilePath, setCreateFilePath] = useState('hg_platforms/new_source.py')
  const [createTitle, setCreateTitle] = useState('')
  const [createBody, setCreateBody] = useState('def main():\n    return True\n')
  const [createChangeSummary, setCreateChangeSummary] = useState('created via operator console')

  const grouped = useMemo(() => groupByClass(overview.source_blobs), [overview.source_blobs])
  const latestVersion = versions?.[0] || null

  const hydrateRecord = async (detail) => {
    const record = detail?.source_blob || null
    setSourceBlob(record)
    setVersions(record?.versions || [])
    setRunResult(record?.runs?.[0] ? { ok: record.runs[0].status === 'completed', run: record.runs[0] } : null)
    setEditorTitle(record?.title || '')
    setEditorBody(record?.versions?.[0]?.source_text || '')
    setEditorChangeSummary(`edited ${record?.title || record?.file_path || 'source blob'} via operator console`)
    setRunEntrypoint(record?.module_path || '')
    if (record?.versions?.length > 1) {
      try {
        const diff = await api.getSourceRegistryDiff(record.source_blob_id)
        setDiffView(diff?.diff || null)
      } catch (err) {
        setDiffView(null)
      }
    } else {
      setDiffView(null)
    }
  }

  const loadOverview = async (preferredId = selectedId) => {
    setLoading(true)
    setError('')
    try {
      const overviewData = await api.getSourceRegistryOverview()
      setOverview(overviewData || { summary: { total_documents: 0, total_versions: 0, by_class: [], classes: [] }, source_blobs: [] })
      const blobs = overviewData?.source_blobs || []
      const nextId = preferredId || blobs[0]?.source_blob_id || ''
      setSelectedId(nextId)
      if (nextId) {
        const detail = await api.getSourceRegistryRecord(nextId)
        await hydrateRecord(detail)
      } else {
        setSourceBlob(null)
        setVersions([])
        setEditorTitle('')
        setEditorBody('')
        setDiffView(null)
        setRunResult(null)
      }
    } catch (err) {
      setError(err?.message || 'Could not load source registry')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadOverview()
  }, [])

  const loadSourceBlob = async (sourceBlobId) => {
    setSelectedId(sourceBlobId)
    setError('')
    try {
      const detail = await api.getSourceRegistryRecord(sourceBlobId)
      await hydrateRecord(detail)
    } catch (err) {
      setError(err?.message || 'Could not load source record')
    }
  }

  const loadVersionIntoEditor = async (version) => {
    if (!sourceBlob) return
    setEditorTitle(sourceBlob.title || '')
    setEditorBody(version?.source_text || '')
    setEditorChangeSummary(`loaded version ${version?.version_number || 'unknown'} into editor`)
    try {
      const diff = await api.getSourceRegistryDiff(sourceBlob.source_blob_id, version?.version_id || null, latestVersion?.version_id || null)
      setDiffView(diff?.diff || null)
    } catch (err) {
      setDiffView(null)
    }
  }

  const syncRegistry = async () => {
    setSyncing(true)
    setError('')
    try {
      await api.syncSourceRegistry({})
      await loadOverview(selectedId)
    } catch (err) {
      setError(err?.message || 'Could not sync source registry')
    } finally {
      setSyncing(false)
    }
  }

  const handleCreate = async () => {
    setSaving(true)
    setError('')
    try {
      const result = await api.createSourceRegistryRecord({
        class_key: 'python_source',
        file_path: createFilePath,
        source_text: createBody,
        title: createTitle || null,
        actor_id: 'operator_console',
        change_summary: createChangeSummary,
      })
      const nextId = result?.source_blob?.source_blob_id || ''
      setCreateBody('def main():\n    return True\n')
      setCreateTitle('')
      await loadOverview(nextId)
    } catch (err) {
      setError(err?.message || 'Could not create source blob')
    } finally {
      setSaving(false)
    }
  }

  const handleSave = async () => {
    if (!sourceBlob?.source_blob_id) return
    setSaving(true)
    setError('')
    try {
      await api.saveSourceRegistryRecord(sourceBlob.source_blob_id, {
        source_text: editorBody,
        title: editorTitle || null,
        actor_id: 'operator_console',
        change_summary: editorChangeSummary,
      })
      await loadOverview(sourceBlob.source_blob_id)
    } catch (err) {
      setError(err?.message || 'Could not save source blob')
    } finally {
      setSaving(false)
    }
  }

  const handleRun = async () => {
    if (!sourceBlob?.source_blob_id) return
    setRunning(true)
    setError('')
    try {
      const args = (runArgs || '').trim() ? runArgs.trim().split(/\s+/).filter(Boolean) : []
      const result = await api.runSourceRegistryRecord(sourceBlob.source_blob_id, {
        entrypoint: runEntrypoint || null,
        args,
        timeout_s: Number(runTimeout) > 0 ? Number(runTimeout) : 120,
        actor_id: 'operator_console',
        change_summary: 'sandboxed source run via operator console',
      })
      setRunResult(result)
      await loadOverview(sourceBlob.source_blob_id)
    } catch (err) {
      setError(err?.message || 'Could not run source blob')
    } finally {
      setRunning(false)
    }
  }

  const handleArchive = async () => {
    if (!sourceBlob?.source_blob_id) return
    setSaving(true)
    setError('')
    try {
      await api.archiveSourceRegistryRecord(sourceBlob.source_blob_id, {
        actor_id: 'operator_console',
        change_summary: 'archived via operator console',
      })
      await loadOverview(sourceBlob.source_blob_id)
    } catch (err) {
      setError(err?.message || 'Could not archive source blob')
    } finally {
      setSaving(false)
    }
  }

  const handleRestore = async () => {
    if (!sourceBlob?.source_blob_id) return
    setSaving(true)
    setError('')
    try {
      await api.restoreSourceRegistryRecord(sourceBlob.source_blob_id, {
        actor_id: 'operator_console',
        change_summary: 'restored via operator console',
      })
      await loadOverview(sourceBlob.source_blob_id)
    } catch (err) {
      setError(err?.message || 'Could not restore source blob')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Layout title="Source Registry">
      {error ? <StateNotice tone="danger" title="Could not load source registry" detail={error} action={<button type="button" onClick={loadOverview}>Retry</button>} /> : null}
      {loading ? <StateNotice title="Loading source registry" detail="Reading Python source blobs, module paths, and version history from Postgres." /> : null}
      <section className="section-card" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', alignItems: 'center' }}>
          <div>
            <div className="eyebrow">Source and runtime plane</div>
            <h2 style={{ margin: '6px 0 8px' }}>One pane for executable Python source inventory, editing, and history.</h2>
            <p className="muted" style={{ margin: 0, maxWidth: 840 }}>
              The registry tracks live Python source blobs under hg_platforms, their module paths, hashes, version
              history, and audit state as database records so operators can edit and compare source without leaving
              the browser.
            </p>
          </div>
          <button type="button" onClick={syncRegistry} disabled={syncing}>
            {syncing ? 'Syncing…' : 'Sync inventory'}
          </button>
        </div>
      </section>

      <div className="card-grid" style={{ marginBottom: 16 }}>
        <div className="card"><strong>{overview.summary?.total_documents ?? 0}</strong><div className="muted">Source blobs</div></div>
        <div className="card"><strong>{overview.summary?.total_versions ?? 0}</strong><div className="muted">Versions</div></div>
        <div className="card"><strong>{overview.summary?.classes?.length ?? 0}</strong><div className="muted">Classes</div></div>
      </div>

      <section className="section-card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>Create source blob</h3>
        <div className="card-grid">
          <label className="card">
            <div className="eyebrow">File path</div>
            <input value={createFilePath} onChange={(event) => setCreateFilePath(event.target.value)} style={{ width: '100%' }} />
          </label>
          <label className="card">
            <div className="eyebrow">Title</div>
            <input value={createTitle} onChange={(event) => setCreateTitle(event.target.value)} style={{ width: '100%' }} />
          </label>
        </div>
        <label>
          <div className="eyebrow">Source text</div>
          <textarea
            value={createBody}
            onChange={(event) => setCreateBody(event.target.value)}
            rows={10}
            style={{ width: '100%', fontFamily: 'monospace', fontSize: 13 }}
          />
        </label>
        <label style={{ display: 'block', marginTop: 10 }}>
          <div className="eyebrow">Change summary</div>
          <input value={createChangeSummary} onChange={(event) => setCreateChangeSummary(event.target.value)} style={{ width: '100%' }} />
        </label>
        <button type="button" onClick={handleCreate} disabled={saving || !createFilePath.trim() || !createBody.trim()} style={{ marginTop: 10 }}>
          {saving ? 'Saving…' : 'Create source blob'}
        </button>
      </section>

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
            {!Object.keys(grouped).length ? <div className="muted">No source blobs indexed yet.</div> : null}
          </div>
        </section>

        <section className="section-card">
          <h3 style={{ marginTop: 0 }}>Records</h3>
          <div style={{ display: 'grid', gap: 10 }}>
            {(overview.source_blobs || []).map((item) => (
              <button
                key={item.source_blob_id}
                type="button"
                onClick={() => loadSourceBlob(item.source_blob_id)}
                className={`card ${selectedId === item.source_blob_id ? 'card-selected' : ''}`}
                style={{ textAlign: 'left' }}
              >
                <div className="eyebrow">{item.class_key}</div>
                <div style={{ fontWeight: 700 }}>{item.title}</div>
                <div className="muted" style={{ fontSize: 12 }}>{item.file_path}</div>
              </button>
            ))}
          </div>
        </section>
      </div>

      {sourceBlob ? (
        <section className="section-card" style={{ marginTop: 16 }}>
          <h3 style={{ marginTop: 0 }}>{sourceBlob.title}</h3>
          <div className="muted" style={{ fontSize: 12, marginBottom: 12 }}>{sourceBlob.file_path}</div>
          <div className="card-grid">
            <div className="card"><div className="eyebrow">Module</div><div>{sourceBlob.module_path}</div></div>
            <div className="card"><div className="eyebrow">Hash</div><div style={{ wordBreak: 'break-all' }}>{sourceBlob.source_sha256}</div></div>
            <div className="card"><div className="eyebrow">Lines</div><div>{sourceBlob.line_count}</div></div>
            <div className="card"><div className="eyebrow">Words</div><div>{sourceBlob.word_count}</div></div>
            <div className="card"><div className="eyebrow">Status</div><div>{sourceBlob.latest_status || 'current'}</div></div>
            <div className="card"><div className="eyebrow">Active</div><div>{sourceBlob.active ? 'yes' : 'no'}</div></div>
            <div className="card"><div className="eyebrow">VS Code</div><div>{sourceBlob.vscode_uri ? <a href={sourceBlob.vscode_uri}>{sourceBlob.workspace_path || sourceBlob.vscode_uri}</a> : 'n/a'}</div></div>
          </div>

          <div style={{ marginTop: 16, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button type="button" onClick={handleSave} disabled={saving}>Save source</button>
            <button type="button" onClick={handleRun} disabled={running}>Run sandboxed</button>
            <button type="button" onClick={handleArchive} disabled={saving || sourceBlob.latest_status === 'archived'}>Archive</button>
            <button type="button" onClick={handleRestore} disabled={saving || sourceBlob.latest_status !== 'archived'}>Restore</button>
          </div>

          <div className="card-grid" style={{ marginTop: 16 }}>
            <label className="card">
              <div className="eyebrow">Entrypoint</div>
              <input value={runEntrypoint} onChange={(event) => setRunEntrypoint(event.target.value)} style={{ width: '100%' }} />
            </label>
            <label className="card">
              <div className="eyebrow">Args</div>
              <input value={runArgs} onChange={(event) => setRunArgs(event.target.value)} style={{ width: '100%' }} />
            </label>
            <label className="card">
              <div className="eyebrow">Timeout (s)</div>
              <input value={runTimeout} onChange={(event) => setRunTimeout(event.target.value)} style={{ width: '100%' }} />
            </label>
          </div>

          {runResult ? (
            <div className="section-card" style={{ marginTop: 16 }}>
              <h4 style={{ marginTop: 0 }}>Latest sandbox run</h4>
              <div className="card-grid">
                <div className="card"><div className="eyebrow">Status</div><div>{runResult.run?.status || (runResult.ok ? 'completed' : 'failed')}</div></div>
                <div className="card"><div className="eyebrow">Return code</div><div>{runResult.run?.returncode ?? 'n/a'}</div></div>
                <div className="card"><div className="eyebrow">Sandbox</div><div style={{ wordBreak: 'break-all' }}>{runResult.run?.sandbox_id || 'n/a'}</div></div>
              </div>
              <div style={{ display: 'grid', gap: 12, marginTop: 12 }}>
                <label>
                  <div className="eyebrow">Stdout</div>
                  <textarea readOnly value={runResult.run?.stdout || ''} rows={8} style={{ width: '100%', fontFamily: 'monospace', fontSize: 13 }} />
                </label>
                <label>
                  <div className="eyebrow">Stderr</div>
                  <textarea readOnly value={runResult.run?.stderr || ''} rows={8} style={{ width: '100%', fontFamily: 'monospace', fontSize: 13 }} />
                </label>
              </div>
            </div>
          ) : null}

          <div style={{ marginTop: 16 }}>
            <h4 style={{ marginBottom: 8 }}>Edit source</h4>
            <label>
              <div className="eyebrow">Title</div>
              <input value={editorTitle} onChange={(event) => setEditorTitle(event.target.value)} style={{ width: '100%' }} />
            </label>
            <label style={{ display: 'block', marginTop: 10 }}>
              <div className="eyebrow">Source text</div>
              <textarea
                value={editorBody}
                onChange={(event) => setEditorBody(event.target.value)}
                rows={18}
                style={{ width: '100%', fontFamily: 'monospace', fontSize: 13 }}
              />
            </label>
            <label style={{ display: 'block', marginTop: 10 }}>
              <div className="eyebrow">Change summary</div>
              <input value={editorChangeSummary} onChange={(event) => setEditorChangeSummary(event.target.value)} style={{ width: '100%' }} />
            </label>
          </div>

          <div style={{ marginTop: 16 }}>
            <h4 style={{ marginBottom: 8 }}>Version history</h4>
            <div style={{ display: 'grid', gap: 8 }}>
              {versions.map((version) => (
                <button
                  key={version.version_id}
                  type="button"
                  onClick={() => loadVersionIntoEditor(version)}
                  className="card"
                  style={{ textAlign: 'left' }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center' }}>
                    <strong>v{version.version_number}</strong>
                    <span className="muted">{version.state}</span>
                  </div>
                  <div className="muted" style={{ fontSize: 12, marginTop: 6 }}>{formatVersionLine(version)}</div>
                </button>
              ))}
              {!versions.length ? <div className="muted">No versions indexed yet.</div> : null}
            </div>
          </div>

          <div style={{ marginTop: 16 }}>
            <h4 style={{ marginBottom: 8 }}>Recent runs</h4>
            <div style={{ display: 'grid', gap: 8 }}>
              {(sourceBlob.runs || []).map((run) => (
                <div key={run.run_id} className="card">
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center' }}>
                    <strong>{run.status}</strong>
                    <span className="muted">{run.created_at}</span>
                  </div>
                  <div className="muted" style={{ fontSize: 12, marginTop: 6 }}>
                    {run.module_path} · rc={run.returncode ?? 'n/a'} · {run.change_summary || 'no summary'}
                  </div>
                </div>
              ))}
              {!sourceBlob.runs?.length ? <div className="muted">No sandbox runs recorded yet.</div> : null}
            </div>
          </div>

          <div style={{ marginTop: 16 }}>
            <h4 style={{ marginBottom: 8 }}>Diff view</h4>
            {diffView ? (
              <pre style={{ whiteSpace: 'pre-wrap', margin: 0, fontFamily: 'monospace', maxHeight: 520, overflow: 'auto' }}>
                {diffView.diff_text}
              </pre>
            ) : (
              <div className="muted">Select a version with a history delta to view the diff.</div>
            )}
          </div>
        </section>
      ) : null}
    </Layout>
  )
}
