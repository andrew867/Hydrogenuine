import React, { useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import Breadcrumbs from '../components/Breadcrumbs.jsx'
import SharedEventSummary from '../components/SharedEventSummary.jsx'
import JsonBlock from '../components/JsonBlock.jsx'
import { api } from '../lib/api.js'
import { getHashQueryParam, normalizeHashHref } from '../lib/navigationContext.js'

const MAX_DIFFS = 200

function diffObjects(a, b, path = '') {
  const diffs = []
  const keys = new Set([...(a ? Object.keys(a) : []), ...(b ? Object.keys(b) : [])])
  for (const key of keys) {
    const nextPath = path ? `${path}.${key}` : key
    const va = a ? a[key] : undefined
    const vb = b ? b[key] : undefined
    const aObj = va && typeof va === 'object'
    const bObj = vb && typeof vb === 'object'
    if (aObj && bObj && !Array.isArray(va) && !Array.isArray(vb)) {
      diffs.push(...diffObjects(va, vb, nextPath))
    } else if (JSON.stringify(va) !== JSON.stringify(vb)) {
      diffs.push({ path: nextPath, left: va, right: vb })
    }
    if (diffs.length >= MAX_DIFFS) break
  }
  return diffs
}

export default function RunCompare() {
  const [leftId, setLeftId] = useState('')
  const [rightId, setRightId] = useState('')
  const [left, setLeft] = useState(null)
  const [right, setRight] = useState(null)
  const [diffs, setDiffs] = useState([])
  const [err, setErr] = useState(null)
  const [returnUrl, setReturnUrl] = useState('#/')

  useEffect(() => {
    const sync = () => {
      setLeftId(getHashQueryParam('left', ''))
      setRightId(getHashQueryParam('right', ''))
      setReturnUrl(normalizeHashHref(getHashQueryParam('returnUrl', '#/')))
    }
    sync()
    window.addEventListener('hashchange', sync)
    return () => window.removeEventListener('hashchange', sync)
  }, [])

  useEffect(() => {
    if (leftId && rightId) {
      void load()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [leftId, rightId])

  const load = async () => {
    setErr(null)
    try {
      const [lRun, rRun, lState, rState] = await Promise.all([
        api.getRun(leftId.trim()),
        api.getRun(rightId.trim()),
        api.getRunState(leftId.trim()),
        api.getRunState(rightId.trim()),
      ])
      if (!lRun.ok || !rRun.ok) throw new Error('Run not found')
      const leftData = { run: lRun, state: lState }
      const rightData = { run: rRun, state: rState }
      setLeft(leftData)
      setRight(rightData)
      setDiffs(diffObjects(leftData, rightData))
    } catch (e) {
      setErr(e.message)
    }
  }

  return (
    <Layout title="Run comparison">
      <Breadcrumbs items={[{ label: 'Home', href: '#/' }, { label: 'Runs', href: '#/' }, { label: 'Compare' }]} />
      <SharedEventSummary
        eyebrow="Run drilldown"
        title="Run comparison"
        intro="Compare two runs from the same origin and keep the comparison anchored to that story."
        status={!left || !right ? 'waiting' : (diffs.length === 0 ? 'match' : `${diffs.length} differences`)}
        statusTone={!left || !right ? 'neutral' : diffs.length === 0 ? 'good' : 'warn'}
        happened={`${leftId || 'left'} vs ${rightId || 'right'}`}
        when={left?.run?.started_at || right?.run?.started_at || 'Current session'}
        why="This page explains the delta before you jump back to another shell."
        changed={`Differences ${diffs.length} · left ${left ? 'loaded' : 'empty'} · right ${right ? 'loaded' : 'empty'}`}
        next="Open the source run detail, inspect lineage, or return to origin after reading the delta."
        context={[
          { label: 'Origin', value: returnUrl !== '#/' ? returnUrl : 'current' },
          { label: 'Left run', value: leftId || '—' },
          { label: 'Right run', value: rightId || '—' },
        ]}
      />
      {err && <div style={{ color: 'var(--danger)' }}>{err}</div>}
      {returnUrl !== '#/' && (
        <p style={{ marginBottom: 12 }}>
          <a href={returnUrl} className="nav-link">Back to origin</a>
        </p>
      )}
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 12 }}>
        <input
          placeholder="Left run_id"
          value={leftId}
          onChange={(e) => setLeftId(e.target.value)}
          style={{ flex: '1 1 260px', padding: 8, borderRadius: 8, border: '1px solid var(--border)', background: '#0b1118', color: 'var(--text)' }}
        />
        <input
          placeholder="Right run_id"
          value={rightId}
          onChange={(e) => setRightId(e.target.value)}
          style={{ flex: '1 1 260px', padding: 8, borderRadius: 8, border: '1px solid var(--border)', background: '#0b1118', color: 'var(--text)' }}
        />
        <button onClick={load} style={{ padding: '8px 12px', borderRadius: 8 }}>Compare</button>
      </div>

      {diffs.length > 0 && (
        <section className="section-card" style={{ marginBottom: 16 }}>
          <h3 style={{ marginTop: 0 }}>Differences ({diffs.length})</h3>
          <table>
            <thead>
              <tr>
                <th>Path</th>
                <th>Left</th>
                <th>Right</th>
              </tr>
            </thead>
            <tbody>
              {diffs.map((d, i) => (
                <tr key={i}>
                  <td>{d.path}</td>
                  <td><code>{JSON.stringify(d.left)}</code></td>
                  <td><code>{JSON.stringify(d.right)}</code></td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {(left || right) && (
        <section className="section-card">
          <h3 style={{ marginTop: 0 }}>Snapshots</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16 }}>
            <div>
              <h4>Left run</h4>
              {left ? <JsonBlock value={left.run} /> : <div className="muted">No data</div>}
            </div>
            <div>
              <h4>Right run</h4>
              {right ? <JsonBlock value={right.run} /> : <div className="muted">No data</div>}
            </div>
          </div>
        </section>
      )}
    </Layout>
  )
}


