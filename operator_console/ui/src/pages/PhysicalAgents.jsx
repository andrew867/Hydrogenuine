import React, { useCallback, useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import Breadcrumbs from '../components/Breadcrumbs.jsx'
import StateNotice from '../components/StateNotice.jsx'
import { PageSkeleton } from '../components/PageStates.jsx'
import { api } from '../lib/api.js'

function SensingIndicator({ active, modalities }) {
  return (
    <div className="physical-sensing-indicator" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <span
        aria-label={active ? 'Sensing active' : 'Sensing inactive'}
        style={{
          width: 12,
          height: 12,
          borderRadius: '50%',
          background: active ? '#22c55e' : '#94a3b8',
          boxShadow: active ? '0 0 8px #22c55e' : 'none',
        }}
      />
      <strong>Sensing:</strong>
      <span>{active ? 'ACTIVE' : 'OFF'}</span>
      {modalities?.length > 0 && (
        <span style={{ color: '#64748b' }}>({modalities.join(', ')})</span>
      )}
    </div>
  )
}

export default function PhysicalAgents() {
  const [agents, setAgents] = useState([])
  const [selected, setSelected] = useState(null)
  const [detail, setDetail] = useState(null)
  const [err, setErr] = useState(null)
  const [loading, setLoading] = useState(true)
  const [actionMsg, setActionMsg] = useState(null)

  const loadList = useCallback(() => {
    setErr(null)
    setLoading(true)
    api.getPhysicalAgents()
      .then((data) => {
        setAgents(data.agents || [])
        if (!selected && data.agents?.length) {
          setSelected(data.agents[0].robot_id)
        }
      })
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false))
  }, [selected])

  const loadDetail = useCallback((robotId) => {
    if (!robotId) return
    api.getPhysicalAgent(robotId)
      .then((data) => setDetail(data))
      .catch((e) => setErr(e.message))
  }, [])

  useEffect(() => {
    api.seedPhysicalDemo().finally(loadList)
  }, [loadList])

  useEffect(() => {
    if (selected) loadDetail(selected)
  }, [selected, loadDetail, actionMsg])

  const onHalt = () => {
    if (!selected) return
    api.haltPhysicalAgent(selected, { reason: 'operator_console_halt' })
      .then(() => setActionMsg(`Halted ${selected} at ${new Date().toISOString()}`))
      .catch((e) => setErr(e.message))
  }

  const onResume = () => {
    if (!selected) return
    api.resumePhysicalAgent(selected)
      .then(() => setActionMsg(`Resumed ${selected} at ${new Date().toISOString()}`))
      .catch((e) => setErr(e.message))
  }

  const safetyBadge = (state) => {
    const colors = { idle: '#22c55e', evaluating: '#eab308', halted: '#ef4444' }
    return (
      <span style={{ color: colors[state] || '#64748b', fontWeight: 600 }}>
        {String(state || 'unknown').toUpperCase()}
      </span>
    )
  }

  return (
    <Layout>
      <Breadcrumbs
        items={[
          { label: 'Operations', value: '#/home' },
          { label: 'Physical agents', value: '#/physical-agents' },
        ]}
      />
      <h1>Physical Agents</h1>
      <p>Robot state, sensor fusion, safety gate, and halt/resume controls.</p>
      {err && <StateNotice tone="danger" title="Physical agents error" detail={err} />}
      {actionMsg && <StateNotice tone="muted" title="Action" detail={actionMsg} />}
      {loading ? <PageSkeleton label="Loading" /> : null}
      {!loading && (
        <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: 24 }}>
          <aside>
            <h2>Robots</h2>
            <ul style={{ listStyle: 'none', padding: 0 }}>
              {agents.map((a) => (
                <li key={a.robot_id} style={{ marginBottom: 8 }}>
                  <button
                    type="button"
                    onClick={() => setSelected(a.robot_id)}
                    style={{
                      width: '100%',
                      textAlign: 'left',
                      padding: 8,
                      border: selected === a.robot_id ? '2px solid #3b82f6' : '1px solid #e2e8f0',
                      borderRadius: 6,
                      background: '#fff',
                      cursor: 'pointer',
                    }}
                  >
                    <div><strong>{a.robot_id}</strong></div>
                    <div style={{ fontSize: 12, color: '#64748b' }}>{a.fingerprint_id}</div>
                    <SensingIndicator active={a.sensing_active} modalities={a.modalities} />
                  </button>
                </li>
              ))}
            </ul>
          </aside>
          <section>
            {detail && (
              <>
                <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
                  <button type="button" onClick={onHalt}>Emergency halt</button>
                  <button type="button" onClick={onResume}>Resume (ack required)</button>
                  <button type="button" onClick={() => loadDetail(selected)}>Refresh</button>
                </div>
                <SensingIndicator
                  active={detail.sensors?.sensing_active}
                  modalities={detail.sensors?.modalities}
                />
                <dl style={{ display: 'grid', gridTemplateColumns: '180px 1fr', gap: '8px 16px', marginTop: 16 }}>
                  <dt>Lifecycle</dt><dd>{detail.lifecycle}</dd>
                  <dt>Safety state</dt><dd>{safetyBadge(detail.safety?.state)}</dd>
                  <dt>Watchdog</dt><dd>{detail.watchdog?.state}</dd>
                  <dt>Actuation allowed</dt><dd>{detail.watchdog?.actuation_allowed ? 'Yes' : 'No'}</dd>
                  <dt>Human near</dt><dd>{detail.sensors?.human_near ? 'YES' : 'No'}</dd>
                  <dt>Model stale</dt><dd>{detail.sensors?.model_stale ? 'Yes' : 'No'}</dd>
                  <dt>Battery</dt><dd>{Math.round((detail.battery_pct || 0) * 100)}%</dd>
                  <dt>Available energy</dt><dd>{detail.energy?.available_wh?.toFixed(1)} Wh</dd>
                  <dt>Pose</dt><dd>{JSON.stringify(detail.pose)}</dd>
                </dl>
                {detail.safety?.recent_decisions?.length > 0 && (
                  <>
                    <h3>Recent safety decisions</h3>
                    <ul>
                      {detail.safety.recent_decisions.map((d) => (
                        <li key={d.decision_id}>
                          {d.allowed ? 'APPROVED' : 'DENIED'} — level {d.level}: {d.reason}
                        </li>
                      ))}
                    </ul>
                  </>
                )}
              </>
            )}
          </section>
        </div>
      )}
    </Layout>
  )
}
