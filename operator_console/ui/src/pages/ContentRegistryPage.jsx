import React, { useEffect, useMemo, useState } from 'react'
import Layout from '../components/Layout.jsx'
import { api } from '../lib/api.js'

function classLabelMap(classes) {
  return Object.fromEntries((classes || []).map((cls) => [cls.class_key, cls]))
}

export default function ContentRegistryPage() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [error, setError] = useState('')
  const [overview, setOverview] = useState({ summary: { total_documents: 0, total_versions: 0, by_class: [] }, documents: [] })
  const [classes, setClasses] = useState([])
  const [selectedId, setSelectedId] = useState('')
  const [document, setDocument] = useState(null)
  const [editorTitle, setEditorTitle] = useState('')
  const [editorBody, setEditorBody] = useState('')
  const [editorChangeSummary, setEditorChangeSummary] = useState('edited via operator console')
  const [createClassKey, setCreateClassKey] = useState('task')
  const [createFilePath, setCreateFilePath] = useState('skills/automation/tasks/new-content.md')
  const [createTitle, setCreateTitle] = useState('')
  const [createBody, setCreateBody] = useState('# New content\n')
  const [createChangeSummary, setCreateChangeSummary] = useState('created via operator console')
  const [versionView, setVersionView] = useState(null)

  const selectedClass = useMemo(() => classLabelMap(classes)[document?.class_key || createClassKey], [classes, document?.class_key, createClassKey])

  const loadOverview = async (preferredId = selectedId) => {
    setLoading(true)
    setError('')
    try {
      const data = await api.getContentRegistryOverview()
      const cls = await api.getContentRegistryClasses()
      setOverview(data || { summary: { total_documents: 0, total_versions: 0, by_class: [] }, documents: [] })
      setClasses(cls?.classes || [])
      const docs = data?.documents || []
      const nextId = preferredId || docs[0]?.content_id || ''
      setSelectedId(nextId)
      if (nextId) {
        const detail = await api.getContentRegistryDocument(nextId)
        setDocument(detail?.document || null)
        setEditorTitle(detail?.document?.title || '')
        setEditorBody(detail?.document?.versions?.[0]?.content_markdown || '')
        setVersionView(detail?.document?.versions?.[0] || null)
      } else {
        setDocument(null)
        setEditorTitle('')
        setEditorBody('')
        setVersionView(null)
      }
    } catch (err) {
      setError(err?.message || 'Could not load content registry')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadOverview()
  }, [])

  const loadDocument = async (contentId) => {
    setSelectedId(contentId)
    setError('')
    try {
      const detail = await api.getContentRegistryDocument(contentId)
      setDocument(detail?.document || null)
      setEditorTitle(detail?.document?.title || '')
      setEditorBody(detail?.document?.versions?.[0]?.content_markdown || '')
      setVersionView(detail?.document?.versions?.[0] || null)
    } catch (err) {
      setError(err?.message || 'Could not load document')
    }
  }

  const loadVersionIntoEditor = (version) => {
    setVersionView(version)
    setEditorTitle(document?.title || '')
    setEditorBody(version?.content_markdown || '')
    setEditorChangeSummary(`loaded version ${version?.version_number || 'unknown'} into editor`)
  }

  const refreshDocument = async (contentId = selectedId) => {
    if (!contentId) return
    const detail = await api.getContentRegistryDocument(contentId)
    setDocument(detail?.document || null)
    setEditorTitle(detail?.document?.title || '')
    setEditorBody(detail?.document?.versions?.[0]?.content_markdown || '')
    setVersionView(detail?.document?.versions?.[0] || null)
  }

  const handleCreate = async () => {
    setSaving(true)
    setError('')
    try {
      const result = await api.createContentRegistryDocument({
        class_key: createClassKey,
        file_path: createFilePath,
        title: createTitle || null,
        content_markdown: createBody,
        actor_id: 'operator_console',
        change_summary: createChangeSummary,
      })
      await loadOverview(result?.document?.content_id || '')
      setCreateBody('# New content\n')
      setCreateTitle('')
    } catch (err) {
      setError(err?.message || 'Could not create content document')
    } finally {
      setSaving(false)
    }
  }

  const handleSave = async () => {
    if (!document?.content_id) return
    setSaving(true)
    setError('')
    try {
      await api.saveContentRegistryDocument(document.content_id, {
        content_markdown: editorBody,
        title: editorTitle || null,
        actor_id: 'operator_console',
        change_summary: editorChangeSummary,
      })
      await refreshDocument(document.content_id)
      await loadOverview(document.content_id)
    } catch (err) {
      setError(err?.message || 'Could not save content document')
    } finally {
      setSaving(false)
    }
  }

  const handleArchive = async () => {
    if (!document?.content_id) return
    setSaving(true)
    setError('')
    try {
      await api.archiveContentRegistryDocument(document.content_id, {
        actor_id: 'operator_console',
        change_summary: 'archived via operator console',
      })
      await refreshDocument(document.content_id)
      await loadOverview(document.content_id)
    } catch (err) {
      setError(err?.message || 'Could not archive content document')
    } finally {
      setSaving(false)
    }
  }

  const handleRestore = async () => {
    if (!document?.content_id) return
    setSaving(true)
    setError('')
    try {
      await api.restoreContentRegistryDocument(document.content_id, {
        actor_id: 'operator_console',
        change_summary: 'restored via operator console',
      })
      await refreshDocument(document.content_id)
      await loadOverview(document.content_id)
    } catch (err) {
      setError(err?.message || 'Could not restore content document')
    } finally {
      setSaving(false)
    }
  }

  const handleSync = async () => {
    setSyncing(true)
    setError('')
    try {
      await api.syncContentRegistry({})
      await loadOverview(selectedId)
    } catch (err) {
      setError(err?.message || 'Could not sync content registry')
    } finally {
      setSyncing(false)
    }
  }

  return (
    <Layout title="Content CMS">
      <main style={{ padding: 24, display: 'grid', gap: 20 }}>
        <section style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: 12 }}>
          <article className="card"><div className="muted">Documents</div><div style={{ fontSize: 28, fontWeight: 700 }}>{overview.summary?.total_documents ?? 0}</div></article>
          <article className="card"><div className="muted">Versions</div><div style={{ fontSize: 28, fontWeight: 700 }}>{overview.summary?.total_versions ?? 0}</div></article>
          <article className="card"><div className="muted">Classes</div><div style={{ fontSize: 28, fontWeight: 700 }}>{classes.length}</div></article>
          <article className="card"><div className="muted">Current class</div><div style={{ fontSize: 20, fontWeight: 700 }}>{selectedClass?.title || '—'}</div></article>
        </section>

        {error ? <div className="card" style={{ borderColor: '#a33', background: 'rgba(160,60,60,0.08)' }}>{error}</div> : null}

        <section style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <button type="button" className="btn-secondary" onClick={handleSync} disabled={syncing}>
            {syncing ? 'Syncing…' : 'Sync from disk'}
          </button>
          <button type="button" className="btn-secondary" onClick={() => loadOverview(selectedId)} disabled={loading}>
            {loading ? 'Refreshing…' : 'Refresh'}
          </button>
        </section>

        <section className="card" style={{ display: 'grid', gap: 16 }}>
          <h2 style={{ margin: 0 }}>Create Document</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 12 }}>
            <label>
              <div className="muted">Class</div>
              <select value={createClassKey} onChange={(e) => setCreateClassKey(e.target.value)} style={{ width: '100%' }}>
                {classes.map((cls) => <option key={cls.class_key} value={cls.class_key}>{cls.title}</option>)}
              </select>
            </label>
            <label>
              <div className="muted">File path</div>
              <input value={createFilePath} onChange={(e) => setCreateFilePath(e.target.value)} style={{ width: '100%' }} />
            </label>
            <label>
              <div className="muted">Title</div>
              <input value={createTitle} onChange={(e) => setCreateTitle(e.target.value)} style={{ width: '100%' }} />
            </label>
            <label>
              <div className="muted">Change summary</div>
              <input value={createChangeSummary} onChange={(e) => setCreateChangeSummary(e.target.value)} style={{ width: '100%' }} />
            </label>
          </div>
          <label>
            <div className="muted">Markdown</div>
            <textarea value={createBody} onChange={(e) => setCreateBody(e.target.value)} rows={10} style={{ width: '100%', fontFamily: 'monospace' }} />
          </label>
          <button type="button" className="btn-primary" onClick={handleCreate} disabled={saving || !createFilePath.trim() || !createBody.trim()}>
            {saving ? 'Saving…' : 'Create document'}
          </button>
        </section>

        <section style={{ display: 'grid', gridTemplateColumns: '360px minmax(0, 1fr)', gap: 16, alignItems: 'start' }}>
          <aside className="card" style={{ display: 'grid', gap: 12 }}>
            <h2 style={{ margin: 0 }}>Documents</h2>
            <div style={{ display: 'grid', gap: 8, maxHeight: 720, overflow: 'auto' }}>
              {(overview.documents || []).map((doc) => (
                <button
                  key={doc.content_id}
                  type="button"
                  onClick={() => loadDocument(doc.content_id)}
                  className={`nav-link ${selectedId === doc.content_id ? 'active' : ''}`}
                  style={{ textAlign: 'left', width: '100%', display: 'grid', gap: 4 }}
                >
                  <div style={{ fontWeight: 700 }}>{doc.title}</div>
                  <div className="muted" style={{ fontSize: 12 }}>{doc.file_path}</div>
                  <div className="muted" style={{ fontSize: 12 }}>{doc.class_key} · {doc.latest_status} · v{doc.current_version_id ? doc.current_version_id.split(':v').pop() : '1'}</div>
                </button>
              ))}
              {!overview.documents?.length ? <div className="muted">No documents indexed yet.</div> : null}
            </div>
          </aside>

          <section className="card" style={{ display: 'grid', gap: 14 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
              <div>
                <h2 style={{ margin: 0 }}>{document?.title || 'Select a document'}</h2>
                <div className="muted">{document?.file_path || 'No document selected'}</div>
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button type="button" className="btn-primary" onClick={handleSave} disabled={saving || !document}>
                  {saving ? 'Saving…' : 'Save'}
                </button>
                <button type="button" className="btn-secondary" onClick={handleArchive} disabled={saving || !document || document.archived}>
                  Archive
                </button>
                <button type="button" className="btn-secondary" onClick={handleRestore} disabled={saving || !document || !document.archived}>
                  Restore
                </button>
              </div>
            </div>

            {document ? (
              <>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: 12 }}>
                  <article><div className="muted">Class</div><div>{document.class_key}</div></article>
                  <article><div className="muted">Archived</div><div>{document.archived ? 'yes' : 'no'}</div></article>
                  <article><div className="muted">Current version</div><div>{document.current_version_id || '—'}</div></article>
                  <article><div className="muted">Source hash</div><div style={{ wordBreak: 'break-all' }}>{document.source_sha256}</div></article>
                </div>

                <label>
                  <div className="muted">Title</div>
                  <input value={editorTitle} onChange={(e) => setEditorTitle(e.target.value)} style={{ width: '100%' }} />
                </label>

                <label>
                  <div className="muted">Markdown</div>
                  <textarea value={editorBody} onChange={(e) => setEditorBody(e.target.value)} rows={18} style={{ width: '100%', fontFamily: 'monospace' }} />
                </label>

                <label>
                  <div className="muted">Change summary</div>
                  <input value={editorChangeSummary} onChange={(e) => setEditorChangeSummary(e.target.value)} style={{ width: '100%' }} />
                </label>

                <section style={{ display: 'grid', gap: 8 }}>
                  <h3 style={{ margin: 0 }}>Versions</h3>
                  <div style={{ display: 'grid', gap: 8, maxHeight: 260, overflow: 'auto' }}>
                    {(document.versions || []).map((version) => (
                      <button
                        key={version.version_id}
                        type="button"
                        onClick={() => loadVersionIntoEditor(version)}
                        className={`nav-link ${versionView?.version_id === version.version_id ? 'active' : ''}`}
                        style={{ textAlign: 'left', width: '100%', display: 'grid', gap: 4 }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                          <strong>v{version.version_number}</strong>
                          <span className="muted">{version.state}</span>
                        </div>
                        <div className="muted" style={{ fontSize: 12 }}>{version.created_at}</div>
                        <div className="muted" style={{ fontSize: 12 }}>{version.change_summary || '—'}</div>
                      </button>
                    ))}
                  </div>
                </section>

                {versionView ? (
                  <section className="card" style={{ background: 'rgba(255,255,255,0.02)' }}>
                    <h3 style={{ marginTop: 0 }}>Selected version preview</h3>
                    <pre style={{ whiteSpace: 'pre-wrap', margin: 0, fontFamily: 'monospace' }}>{versionView.content_markdown}</pre>
                  </section>
                ) : null}
              </>
            ) : (
              <div className="muted">Select a document from the left or create a new one above.</div>
            )}
          </section>
        </section>
      </main>
    </Layout>
  )
}
