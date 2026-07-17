import React, { useCallback, useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import { api } from '../lib/api.js'
import { AsyncPageBody, EmptyState } from '../components/PageStates.jsx'

export default function Config() {
  const [consoleConfig, setConsoleConfig] = useState(null)
  const [workspaceConfig, setWorkspaceConfig] = useState(null)
  const [categories, setCategories] = useState([])
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState(null)

  const load = useCallback(() => {
    setErr(null)
    setLoading(true)
    Promise.all([
      api.getConfig().then((r) => setConsoleConfig(r)).catch((e) => setErr(e.message)),
      api.getWorkspaceConfig().then((r) => setWorkspaceConfig(r)).catch(() => setWorkspaceConfig(null)),
      api.getKnowledgeCategories().then((r) => setCategories(r.categories || [])).catch(() => setCategories([])),
    ]).finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load])

  return (
    <Layout title="Config">
      <AsyncPageBody loading={loading} error={err} onRetry={load} loadingLabel="Loading console configuration">
        {consoleConfig && (
          <section style={{ marginBottom: 24 }}>
            <h2 style={{ fontSize: 18, marginBottom: 8 }}>Console</h2>
            <table cellPadding="8" style={{ borderCollapse: 'collapse' }}>
              <tbody>
                <tr><td><strong>runs_root</strong></td><td><code>{consoleConfig.runs_root}</code></td></tr>
                <tr><td><strong>sqlite_path</strong></td><td><code>{consoleConfig.sqlite_path}</code></td></tr>
                <tr><td><strong>cors_origins</strong></td><td><code>{consoleConfig.cors_origins}</code></td></tr>
                <tr><td><strong>api_key</strong></td><td>{consoleConfig.api_key}</td></tr>
              </tbody>
            </table>
          </section>
        )}
        {workspaceConfig && (
          <section style={{ marginBottom: 24 }}>
            <h2 style={{ fontSize: 18, marginBottom: 8 }}>Workspace paths</h2>
            <table cellPadding="8" style={{ borderCollapse: 'collapse' }}>
              <tbody>
                {workspaceConfig.workspace_root != null && (
                  <tr><td><strong>workspace_root</strong></td><td><code>{workspaceConfig.workspace_root}</code></td></tr>
                )}
                {workspaceConfig.job_registry_path != null && (
                  <tr><td><strong>job_registry</strong></td><td><code>{workspaceConfig.job_registry_path}</code></td></tr>
                )}
                {workspaceConfig.personas_base != null && (
                  <tr><td><strong>personas_base</strong></td><td><code>{workspaceConfig.personas_base}</code></td></tr>
                )}
                {workspaceConfig.knowledge_db_path != null && (
                  <tr><td><strong>knowledge_db</strong></td><td><code>{workspaceConfig.knowledge_db_path}</code></td></tr>
                )}
              </tbody>
            </table>
          </section>
        )}
        <section>
          <h2 style={{ fontSize: 18, marginBottom: 8 }}>Topics / Categories (knowledge DB)</h2>
          {categories.length === 0 ? (
            <EmptyState
              title="No categories"
              description="Knowledge DB is empty or unavailable for this environment."
            />
          ) : (
            <table cellPadding="8" style={{ borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  <th align="left">Category</th>
                  <th align="left">Topics</th>
                </tr>
              </thead>
              <tbody>
                {categories.map((c) => (
                  <tr key={c.category}>
                    <td>{c.category}</td>
                    <td>{(c.topics || []).join(', ') || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      </AsyncPageBody>
    </Layout>
  )
}
