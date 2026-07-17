import React, { useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import JsonBlock from '../components/JsonBlock.jsx'
import { api } from '../lib/api.js'

export default function ProductTemplates({ onLogout }) {
  const [templates, setTemplates] = useState([])
  const [selected, setSelected] = useState(null)
  const [goal, setGoal] = useState('')
  const [contextText, setContextText] = useState('')
  const [preview, setPreview] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(() => {
    api.product.listTemplates()
      .then((r) => setTemplates(r.items || []))
      .catch((e) => setErr(e.message))
  }, [])

  const selectTemplate = (tmpl) => {
    setSelected(tmpl)
    setPreview(null)
    setGoal('')
    setContextText('')
  }

  const instantiate = async () => {
    if (!selected) return
    setErr(null)
    try {
      const context = contextText.trim() ? JSON.parse(contextText) : {}
      const res = await api.product.instantiateTemplate(selected.template_id, { goal, context })
      if (!res.ok) throw new Error(res.error?.message || 'Failed to instantiate template')
      setPreview(res.dag)
    } catch (e) {
      setErr(e.message)
    }
  }

  const copyPreview = async () => {
    if (!preview) return
    await navigator.clipboard.writeText(JSON.stringify(preview, null, 2))
  }

  return (
    <Layout title="Templates" onLogout={onLogout}>
      {err && <div style={{ color: 'var(--danger)' }}>{err}</div>}
      <section className="section-card" style={{ marginBottom: 16 }}>
        <h2 style={{ marginTop: 0 }}>Template library</h2>
        <table>
          <thead>
            <tr>
              <th>template_id</th>
              <th>graph_id</th>
              <th>nodes</th>
              <th>description</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {templates.map((t) => (
              <tr key={t.template_id}>
                <td>{t.template_id}</td>
                <td>{t.graph_id || '—'}</td>
                <td>{t.node_count ?? '—'}</td>
                <td>{t.description || '—'}</td>
                <td><button onClick={() => selectTemplate(t)}>Select</button></td>
              </tr>
            ))}
            {!templates.length && (
              <tr><td colSpan={5} className="muted">No templates available.</td></tr>
            )}
          </tbody>
        </table>
      </section>

      <section className="section-card">
        <h2 style={{ marginTop: 0 }}>Template parameters</h2>
        {!selected && <div className="muted">Select a template to edit parameters.</div>}
        {selected && (
          <>
            <div className="muted" style={{ marginBottom: 8 }}>Selected: {selected.template_id}</div>
            <label style={{ display: 'block', marginBottom: 6 }}>Goal</label>
            <input
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              placeholder="Optional goal override"
              style={{ width: '100%', padding: 8, borderRadius: 8, border: '1px solid var(--border)', background: '#0b1118', color: 'var(--text)', marginBottom: 12 }}
            />
            <label style={{ display: 'block', marginBottom: 6 }}>Context (JSON)</label>
            <textarea
              value={contextText}
              onChange={(e) => setContextText(e.target.value)}
              placeholder='{"inputs": {"goal": "..."}}'
              rows={6}
              style={{ width: '100%', padding: 8, borderRadius: 8, border: '1px solid var(--border)', background: '#0b1118', color: 'var(--text)' }}
            />
            <div style={{ display: 'flex', gap: 10, marginTop: 10 }}>
              <button onClick={instantiate}>Instantiate</button>
              {preview && <button onClick={copyPreview}>Copy JSON</button>}
            </div>
          </>
        )}
      </section>

      {preview && (
        <section className="section-card" style={{ marginTop: 16 }}>
          <h2 style={{ marginTop: 0 }}>Preview DAG</h2>
          <JsonBlock value={preview} />
        </section>
      )}
    </Layout>
  )
}


