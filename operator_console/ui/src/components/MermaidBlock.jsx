import React, { useEffect, useMemo, useState } from 'react'

export default function MermaidBlock({ dag }) {
  const diagram = useMemo(() => {
    if (!dag || !dag.nodes) return null
    const lines = ['flowchart TD']
    const edges = Array.isArray(dag.edges) ? dag.edges : []
    const labels = new Map()
    for (const n of dag.nodes) {
      const id = n.id
      const label = n.label || id
      labels.set(id, label)
      const deps = Array.isArray(n.depends_on) ? n.depends_on : []
      if (!deps.length && edges.length === 0) lines.push(`  ${id}[${label}]`)
      for (const d of deps) lines.push(`  ${d} --> ${id}`)
    }
    if (edges.length > 0) {
      for (const edge of edges) {
        if (!edge || !edge.from || !edge.to) continue
        const from = edge.from
        const to = edge.to
        const fromLabel = labels.get(from) || from
        const toLabel = labels.get(to) || to
        lines.push(`  ${from}[${fromLabel}] --> ${to}[${toLabel}]`)
      }
    }
    return lines.join('\n')
  }, [dag])

  const [svg, setSvg] = useState('')
  const [err, setErr] = useState('')

  useEffect(() => {
    let cancelled = false
    if (!diagram) {
      setSvg('')
      setErr('')
      return () => { cancelled = true }
    }
    const render = async () => {
      try {
        const { default: mermaid } = await import('mermaid')
        const themeAttr = document.documentElement.getAttribute('data-hg-theme')
        const isDark = document.documentElement.classList.contains('dark') || themeAttr === 'dark'
        mermaid.initialize({ startOnLoad: false, securityLevel: 'loose', theme: isDark ? 'dark' : 'default' })
        const id = `mermaid_${Date.now()}_${Math.random().toString(16).slice(2)}`
        const out = await mermaid.render(id, diagram)
        if (!cancelled) {
          setSvg(out.svg || '')
          setErr('')
        }
      } catch (e) {
        if (!cancelled) {
          setErr(e?.message || String(e))
          setSvg('')
        }
      }
    }
    render()
    return () => { cancelled = true }
  }, [diagram])

  if (!diagram) return null
  return (
    <div>
      <div style={{ fontWeight: 600, marginBottom: 6 }}>Graph</div>
      {svg ? (
        <div className="code-block" style={{ overflowX: 'auto' }} dangerouslySetInnerHTML={{ __html: svg }} />
      ) : (
        <pre className="code-block">{diagram}</pre>
      )}
      {err && <div style={{ color: 'var(--danger)', fontSize: 12 }}>Graph render failed: {err}</div>}
    </div>
  )
}


