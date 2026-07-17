import React, { useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import { api } from '../lib/api.js'
import StateNotice from '../components/StateNotice.jsx'

export default function PersonasPage() {
  const [personas, setPersonas] = useState([])
  const [err, setErr] = useState(null)
  const [loading, setLoading] = useState(true)
  const [importJson, setImportJson] = useState('')
  const [importResult, setImportResult] = useState(null)
  const [importing, setImporting] = useState(false)
  const [query, setQuery] = useState('')

  const load = async () => {
    setErr(null)
    setLoading(true)
    try {
      const response = await api.listPersonas()
      setPersonas(response.personas || [])
    } catch (error) {
      setErr(error.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const filteredPersonas = personas.filter((persona) => {
    const needle = query.trim().toLowerCase()
    if (!needle) return true
    return [persona.name, persona.fingerprint_id, persona.type, persona.source].some((value) =>
      String(value || '').toLowerCase().includes(needle)
    )
  })

  const handleImport = async () => {
    let body
    try {
      body = JSON.parse(importJson)
    } catch (_) {
      setImportResult({ ok: false, error: 'Invalid JSON' })
      return
    }
    setImporting(true)
    setImportResult(null)
    try {
      const result = await api.importPersona(body)
      setImportResult(result)
      setImportJson('')
      await load()
    } catch (error) {
      setImportResult({ ok: false, error: error.message })
    } finally {
      setImporting(false)
    }
  }

  return (
    <Layout title="Personas">
      {err ? <StateNotice tone="danger" title="Could not load personas" detail={err} action={<button type="button" onClick={load}>Retry</button>} /> : null}
      <p style={{ marginBottom: 12, color: 'var(--muted)' }}>
        Built-in and imported personas for operator-facing catalog management, exports, and imports.
      </p>
      <StateNotice
        title="Naturalness operations moved"
        detail="Preview, evaluation, history, and swarm drill-down now live on their own page so the catalog stays focused."
        action={<a href="#/persona-naturalness">Open Persona Naturalness</a>}
      />

      <div style={{ display: 'flex', gap: 8, alignItems: 'center', margin: '16px 0', flexWrap: 'wrap' }}>
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search personas"
          style={{ flex: '1 1 240px' }}
        />
        <button type="button" onClick={load}>Refresh</button>
        <span style={{ color: 'var(--muted)', fontSize: 13 }}>{filteredPersonas.length} visible / {personas.length} total</span>
      </div>

      {loading ? (
        <StateNotice title="Loading personas" detail="Reading built-in and imported persona fingerprints from the operator catalog." />
      ) : null}

      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 18, marginBottom: 8 }}>Catalog ({filteredPersonas.length})</h2>
        {!loading && filteredPersonas.length === 0 ? (
          <StateNotice title="No personas matched" detail={query ? 'Adjust the search term or refresh the catalog.' : 'No persona fingerprints are currently available.'} />
        ) : null}
        {filteredPersonas.length > 0 ? (
          <div style={{ overflowX: 'auto', maxWidth: '100%' }}>
          <table cellPadding="8" style={{ borderCollapse: 'collapse', width: '100%', minWidth: 820 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                <th style={{ textAlign: 'left' }}>Name</th>
                <th style={{ textAlign: 'left' }}>ID</th>
                <th style={{ textAlign: 'left' }}>Type</th>
                <th style={{ textAlign: 'left' }}>Source</th>
                <th style={{ textAlign: 'left' }}>Skins</th>
                <th style={{ textAlign: 'left' }}>Export</th>
              </tr>
            </thead>
            <tbody>
              {filteredPersonas.map((persona) => (
                <tr key={persona.fingerprint_id} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td>{persona.name}</td>
                  <td><code>{persona.fingerprint_id}</code></td>
                  <td>{persona.type}</td>
                  <td>{persona.source}</td>
                  <td>{(persona.skins || []).map((skin) => skin.id).join(', ') || '—'}</td>
                  <td>
                    <a
                      href={api.exportPersonaUrl(persona.fingerprint_id)}
                      download={`persona-${persona.fingerprint_id}.json`}
                      style={{ marginRight: 8 }}
                    >
                      JSON
                    </a>
                    {(persona.skins || []).map((skin) => (
                      <a
                        key={skin.id}
                        href={api.exportPersonaUrl(persona.fingerprint_id, skin.id)}
                        download={`persona-${persona.fingerprint_id}-${skin.id}.json`}
                        style={{ marginRight: 8 }}
                      >
                        {skin.name}
                      </a>
                    ))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        ) : null}
      </section>

      <section>
        <h2 style={{ fontSize: 18, marginBottom: 8 }}>Import</h2>
        <p style={{ marginBottom: 8, fontSize: 14, color: 'var(--muted)' }}>
          Paste fingerprint or skin JSON below and click Import. Validates and stores under `persona_imports`.
        </p>
        <textarea
          value={importJson}
          onChange={(event) => setImportJson(event.target.value)}
          placeholder='{"entity": "...", "cognitive_fingerprint": {...}}'
          rows={6}
          style={{ width: '100%', maxWidth: 600, fontFamily: 'monospace', fontSize: 12, padding: 8, marginBottom: 8 }}
        />
        <div style={{ marginBottom: 8 }}>
          <button type="button" onClick={handleImport} disabled={importing || !importJson.trim()}>
            {importing ? 'Importing…' : 'Import'}
          </button>
        </div>
        {importResult ? (
          <div style={{ color: importResult.ok ? 'var(--success)' : 'var(--danger)' }}>
            {importResult.ok ? `Imported as id: ${importResult.id}` : importResult.error || importResult.detail}
          </div>
        ) : null}
      </section>
    </Layout>
  )
}
