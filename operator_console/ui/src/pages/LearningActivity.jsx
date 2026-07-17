import React, { useCallback, useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import Breadcrumbs from '../components/Breadcrumbs.jsx'
import StateNotice from '../components/StateNotice.jsx'
import { PageSkeleton } from '../components/PageStates.jsx'
import { api } from '../lib/api.js'

export default function LearningActivity() {
  const [activity, setActivity] = useState(null)
  const [err, setErr] = useState(null)
  const [loading, setLoading] = useState(true)
  const [runMsg, setRunMsg] = useState(null)

  const load = useCallback(() => {
    setErr(null)
    setLoading(true)
    api.getLearningActivity()
      .then((data) => setActivity(data))
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    api.syncLearningCorpus().finally(load)
  }, [load])

  const onRunShadow = () => {
    setRunMsg(null)
    api.runLearningShadowFeedback()
      .then((data) => {
        const applied = data.live_applied ?? data.shadow_run?.live_applied ?? 0
        const written = data.shadow_run?.proposals_written ?? 0
        setRunMsg(`Run complete: ${written} proposals, ${applied} applied live`)
        load()
      })
      .catch((e) => setErr(e.message))
  }

  const onUnfreezePath = (pathName) => {
    api.unfreezeLearningPath(pathName)
      .then(() => load())
      .catch((e) => setErr(e.message))
  }

  const onResolveIncident = (incidentId) => {
    api.resolveLearningIncident(incidentId)
      .then(() => load())
      .catch((e) => setErr(e.message))
  }

  const tel = activity?.telemetry
  const liveEnabled = tel?.hg_learning_live_feedback_enabled
  const cgEnabled = tel?.hg_learning_control_group_enabled

  return (
    <Layout>
      <Breadcrumbs
        items={[
          { label: 'Operations', value: '#/home' },
          { label: 'Learning activity', value: '#/learning-activity' },
        ]}
      />
      <h1>Learning Activity</h1>
      <p>
        Shadow and live feedback paths. Live adjustments apply only when
        {' '}
        <code>HG_LEARNING_LIVE_FEEDBACK_ENABLED=1</code>
        {' '}
        or per-path flags are set (L3).
      </p>
      <button type="button" onClick={onRunShadow} style={{ marginBottom: 16 }}>
        Run feedback cycle
      </button>
      {runMsg && <StateNotice tone="muted" title="Feedback run" detail={runMsg} />}
      {tel && (
        <p style={{ color: '#64748b' }}>
          Ledger: {activity.ledger_count} · Live priors: {tel.hg_learning_live_prior_count ?? 0} ·
          Frozen paths: {tel.hg_learning_frozen_paths ?? 0} ·
          Open incidents: {tel.hg_learning_open_incidents ?? 0} ·
          Live feedback: {liveEnabled ? 'ON' : 'off'} ·
          Control group: {cgEnabled ? 'ON' : 'off'}
        </p>
      )}
      {activity?.control_group && (
        <section style={{ marginBottom: 24 }}>
          <h2>Control group (10% held-out)</h2>
          <p style={{ color: '#64748b' }}>
            Treatment: {activity.control_group.treatment_total ?? 0} runs ·
            Control: {activity.control_group.control_total ?? 0} runs
          </p>
        </section>
      )}
      {(activity?.open_incidents || []).length > 0 && (
        <section style={{ marginBottom: 24 }}>
          <h2>Open incidents</h2>
          <table className="data-table" style={{ width: '100%' }}>
            <thead>
              <tr>
                <th>Type</th>
                <th>Path</th>
                <th>When</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {activity.open_incidents.map((inc) => (
                <tr key={inc.incident_id}>
                  <td>{inc.incident_type}</td>
                  <td>{inc.path_name || '—'}</td>
                  <td>{inc.created_at}</td>
                  <td>
                    <button type="button" onClick={() => onResolveIncident(inc.incident_id)}>
                      Resolve
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
      {err && <StateNotice tone="danger" title="Learning activity error" detail={err} />}
      {loading ? <PageSkeleton label="Loading" /> : null}
      {!loading && activity?.paths?.map((path) => (
        <section key={path.path_name} style={{ marginBottom: 24, borderTop: '1px solid #e2e8f0', paddingTop: 12 }}>
          <h2>
            {path.path_name}
            {' '}
            <span style={{ fontSize: 14, color: path.frozen ? '#ef4444' : path.mode === 'live' ? '#2563eb' : '#64748b' }}>
              [{path.frozen ? 'FROZEN' : path.mode.toUpperCase()}]
            </span>
          </h2>
          {path.deferred_reason && (
            <p style={{ color: '#94a3b8' }}>Deferred: {path.deferred_reason}</p>
          )}
          {path.frozen && (
            <button type="button" onClick={() => onUnfreezePath(path.path_name)} style={{ marginBottom: 8 }}>
              Unfreeze path
            </button>
          )}
          {(path.recent_adjustments || []).length === 0 ? (
            <p style={{ color: '#94a3b8' }}>No adjustments yet.</p>
          ) : (
            <table className="data-table" style={{ width: '100%' }}>
              <thead>
                <tr>
                  <th>Parameter</th>
                  <th>Current</th>
                  <th>Proposed</th>
                  <th>Status</th>
                  <th>Evidence</th>
                  <th>When</th>
                </tr>
              </thead>
              <tbody>
                {path.recent_adjustments.map((adj) => (
                  <tr key={adj.adjustment_id}>
                    <td><code>{adj.parameter}</code></td>
                    <td>{adj.current_value ?? '—'}</td>
                    <td>{adj.proposed_value}</td>
                    <td>{adj.status}</td>
                    <td>{(adj.evidence_signal_ids || []).length} signals</td>
                    <td>{adj.created_at}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      ))}
    </Layout>
  )
}
