import React, { useEffect, useMemo, useState } from 'react'
import Layout from '../components/Layout.jsx'
import StateNotice from '../components/StateNotice.jsx'
import { api } from '../lib/api.js'

function parseJson(text, fallback = {}) {
  try {
    return JSON.parse(text || '{}')
  } catch {
    return fallback
  }
}

function groupByPlatform(items) {
  const out = {}
  for (const item of items || []) {
    const key = item.platform_id || 'global'
    if (!out[key]) out[key] = []
    out[key].push(item)
  }
  return out
}

export default function TaskRegistryPage() {
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [overview, setOverview] = useState({ summary: { total_tools: 0, total_versions: 0, by_platform: [] }, tasks: [] })
  const [selectedId, setSelectedId] = useState('')
  const [task, setTask] = useState(null)
  const [versions, setVersions] = useState([])
  const [metadataText, setMetadataText] = useState('{\n  \n}')
  const [sandboxMode, setSandboxMode] = useState('')
  const [sandboxAllowlistText, setSandboxAllowlistText] = useState('')

  const grouped = useMemo(() => groupByPlatform(overview.tasks), [overview.tasks])

  const hydrateTask = (detail) => {
    const record = detail?.task || null
    setTask(record)
    setVersions(record?.versions || [])
    const payload = parseJson(record?.payload_json || '{}', {})
    setMetadataText(JSON.stringify(payload, null, 2))
    setSandboxMode(String(record?.sandbox_mode || payload?.sandbox_mode || ''))
    const allowlist = record?.sandbox_allowlist ?? payload?.sandbox_allowlist ?? []
    setSandboxAllowlistText(Array.isArray(allowlist) ? allowlist.join(', ') : String(allowlist || ''))
  }

  const loadOverview = async (preferredId = selectedId) => {
    setLoading(true)
    setError('')
    try {
      const overviewData = await api.getTaskRegistryOverview()
      setOverview(overviewData || { summary: { total_tools: 0, total_versions: 0, by_platform: [] }, tasks: [] })
      const tasks = overviewData?.tasks || []
      const nextId = preferredId || tasks[0]?.task_name || ''
      setSelectedId(nextId)
      if (nextId) {
        const detail = await api.getTaskRegistryRecord(nextId)
        hydrateTask(detail)
      } else {
        setTask(null)
        setVersions([])
        setMetadataText('{\n  \n}')
        setSandboxMode('')
        setSandboxAllowlistText('')
      }
    } catch (err) {
      setError(err?.message || 'Could not load task registry')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadOverview()
  }, [])

  const loadTask = async (taskName) => {
    setSelectedId(taskName)
    setError('')
    try {
      const detail = await api.getTaskRegistryRecord(taskName)
      hydrateTask(detail)
    } catch (err) {
      setError(err?.message || 'Could not load task record')
    }
  }

  const syncRegistry = async () => {
    setSyncing(true)
    setError('')
    try {
      await api.syncTaskRegistry({})
      await loadOverview(selectedId)
    } catch (err) {
      setError(err?.message || 'Could not sync task registry')
    } finally {
      setSyncing(false)
    }
  }

  const saveMetadata = async (patch = {}) => {
    if (!selectedId) {
      return
    }
    setSaving(true)
    setError('')
    try {
      const metadata = parseJson(metadataText || '{}', {})
      const sandboxAllowlist = sandboxAllowlistText
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean)
      const resp = await api.saveTaskRegistryRecord(selectedId, {
        metadata,
        sandbox_mode: sandboxMode || null,
        sandbox_allowlist: sandboxAllowlist.length ? sandboxAllowlist : null,
        ...patch,
      })
      hydrateTask(resp)
      await loadOverview(selectedId)
    } catch (err) {
      setError(err?.message || 'Could not save task record')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Layout title="Task Registry">
      {error ? <StateNotice tone="danger" title="Could not load task registry" detail={error} action={<button type="button" onClick={loadOverview}>Retry</button>} /> : null}
      {loading ? <StateNotice title="Loading task registry" detail="Reading task manifests and launch metadata from Postgres." /> : null}
      <section className="section-card" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', alignItems: 'center' }}>
          <div>
            <div className="eyebrow">Task manifest plane</div>
            <h2 style={{ margin: '6px 0 8px' }}>One pane for task launch metadata and ownership.</h2>
            <p className="muted" style={{ margin: 0, maxWidth: 800 }}>
              The registry tracks active task jobs, their session targets, modes, and executable hints in Postgres so
              launch policy can move away from ad hoc file lookups.
            </p>
          </div>
          <button type="button" onClick={syncRegistry} disabled={syncing}>
            {syncing ? 'Syncing…' : 'Sync registry'}
          </button>
        </div>
      </section>

      <div className="card-grid" style={{ marginBottom: 16 }}>
        <div className="card"><strong>{overview.summary?.total_tools ?? 0}</strong><div className="muted">Tasks</div></div>
        <div className="card"><strong>{overview.summary?.total_versions ?? 0}</strong><div className="muted">Versions</div></div>
        <div className="card"><strong>{Object.keys(grouped).length}</strong><div className="muted">Platforms</div></div>
      </div>

      <div className="split-grid">
        <section className="section-card">
          <h3 style={{ marginTop: 0 }}>By platform</h3>
          <div style={{ display: 'grid', gap: 12 }}>
            {Object.entries(grouped).map(([platformId, items]) => (
              <div key={platformId} className="card">
                <div className="eyebrow">{platformId}</div>
                <div style={{ marginTop: 4 }}>{items.length} records</div>
                <div className="muted" style={{ fontSize: 12, marginTop: 6 }}>
                  {items.slice(0, 3).map((item) => item.task_name).join(' · ')}
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="section-card">
          <h3 style={{ marginTop: 0 }}>Records</h3>
          <div style={{ display: 'grid', gap: 10 }}>
            {(overview.tasks || []).map((item) => (
              <button
                key={item.task_name}
                type="button"
                onClick={() => loadTask(item.task_name)}
                className={`card ${selectedId === item.task_name ? 'card-selected' : ''}`}
                style={{ textAlign: 'left' }}
              >
                <div className="eyebrow">{item.platform_id || 'global'} - {item.mode}</div>
                <div style={{ fontWeight: 700 }}>{item.task_name}</div>
                <div className="muted" style={{ fontSize: 12 }}>{item.job_id}</div>
              </button>
            ))}
          </div>
        </section>
      </div>

      {task ? (
        <section className="section-card" style={{ marginTop: 16 }}>
          <h3 style={{ marginTop: 0 }}>{task.task_name}</h3>
          <div className="muted" style={{ fontSize: 12, marginBottom: 12 }}>{task.source_path}</div>
          <div className="card-grid">
            <div className="card"><div className="eyebrow">Job ID</div><div>{task.job_id}</div></div>
            <div className="card"><div className="eyebrow">Session target</div><div>{task.session_target}</div></div>
            <div className="card"><div className="eyebrow">Mode</div><div>{task.mode}</div></div>
            <div className="card"><div className="eyebrow">Sandbox</div><div>{task.sandbox_mode || 'default'}</div></div>
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
          <div style={{ marginTop: 16 }}>
            <h4>Sandbox policy</h4>
            <div className="card-grid">
              <label className="card">
                <div className="eyebrow">Sandbox mode</div>
                <select value={sandboxMode} onChange={(event) => setSandboxMode(event.target.value)}>
                  <option value="">default</option>
                  <option value="sandbox">sandbox</option>
                  <option value="direct">direct</option>
                </select>
              </label>
              <label className="card">
                <div className="eyebrow">Sandbox allowlist</div>
                <textarea
                  value={sandboxAllowlistText}
                  onChange={(event) => setSandboxAllowlistText(event.target.value)}
                  rows={3}
                  placeholder="comma-separated tool names"
                  style={{ width: '100%', fontFamily: 'monospace', fontSize: 13 }}
                />
              </label>
            </div>
          </div>
          <div style={{ marginTop: 16 }}>
            <h4>Manifest metadata</h4>
            <textarea
              value={metadataText}
              onChange={(event) => setMetadataText(event.target.value)}
              rows={10}
              style={{ width: '100%', fontFamily: 'monospace', fontSize: 13 }}
            />
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 10 }}>
              <button type="button" onClick={() => saveMetadata()} disabled={saving}>Save metadata</button>
              <button type="button" onClick={() => saveMetadata({ disabled: true, archived: false })} disabled={saving}>Disable</button>
              <button type="button" onClick={() => saveMetadata({ disabled: false, archived: false })} disabled={saving}>Enable</button>
              <button type="button" onClick={() => saveMetadata({ archived: true })} disabled={saving}>Archive</button>
              <button type="button" onClick={() => saveMetadata({ archived: false })} disabled={saving}>Restore</button>
            </div>
          </div>
        </section>
      ) : null}
    </Layout>
  )
}
