import React, { useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import { api } from '../lib/api.js'
import StateNotice from '../components/StateNotice.jsx'

const RESEARCH_JOB_ID = 'knowledge-research-auto-v2'

export default function Knowledge() {
  const [stats, setStats] = useState(null)
  const [control, setControl] = useState(null)
  const [readiness, setReadiness] = useState(null)
  const [deliverySummary, setDeliverySummary] = useState(null)
  const [sourceConfig, setSourceConfig] = useState(null)
  const [sourceForm, setSourceForm] = useState({
    brave: { enabled: true, news_count: 4, web_count: 5 },
    google_news: { enabled: false, news_count: 4, hl: 'en-US', gl: 'US', ceid: 'US:en' },
    local_news: { enabled: false, urlsText: '', timeout_s: 8 },
  })
  const [sourceBusy, setSourceBusy] = useState(false)
  const [sourceProbeBusy, setSourceProbeBusy] = useState(false)
  const [sourceProbeQuery, setSourceProbeQuery] = useState('AI agents infrastructure current events')
  const [sourceProbeResult, setSourceProbeResult] = useState(null)
  const [recentRuns, setRecentRuns] = useState([])
  const [err, setErr] = useState(null)
  const [loadingOverview, setLoadingOverview] = useState(true)
  const [runResult, setRunResult] = useState(null)
  const [runGoal, setRunGoal] = useState('')
  const [runningKnowledge, setRunningKnowledge] = useState(false)
  const [queueForm, setQueueForm] = useState({ topic: '', requested_by: '', priority: 'medium', context: '' })
  const [queueBusy, setQueueBusy] = useState(false)
  const [scheduleBusy, setScheduleBusy] = useState(false)
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [searching, setSearching] = useState(false)
  const [inspectChatId, setInspectChatId] = useState('')
  const [inspectWorkspace, setInspectWorkspace] = useState(null)
  const [inspecting, setInspecting] = useState(false)
  const [showWorkspaceJson, setShowWorkspaceJson] = useState(false)

  const loadOverview = () => {
    setLoadingOverview(true)
    setErr(null)
    return Promise.allSettled([
      api.getKnowledgeStats(),
      api.getKnowledgeControl(),
      api.getKnowledgeReadiness(),
      api.getKnowledgeDeliverySummary(),
      api.getKnowledgeSources(),
      api.getRecentKnowledgeWorkspaces(6),
    ])
      .then(([statsResult, controlResult, readinessResult, deliveryResult, sourcesResult, runsResult]) => {
        if (statsResult.status === 'fulfilled') setStats(statsResult.value?.ok ? statsResult.value : null)
        else setStats(null)

        if (controlResult.status === 'fulfilled') setControl(controlResult.value?.ok ? controlResult.value : null)
        else setControl(null)

        if (readinessResult.status === 'fulfilled') setReadiness(readinessResult.value?.ok ? readinessResult.value : null)
        else setReadiness(null)

        if (deliveryResult.status === 'fulfilled') setDeliverySummary(deliveryResult.value?.ok ? deliveryResult.value : null)
        else setDeliverySummary(null)

        if (sourcesResult.status === 'fulfilled') setSourceConfig(sourcesResult.value?.ok ? sourcesResult.value?.sources || null : null)
        else setSourceConfig(null)

        if (runsResult.status === 'fulfilled') setRecentRuns(runsResult.value?.items || [])
        else setRecentRuns([])

        const firstError = [statsResult, controlResult, readinessResult, deliveryResult, sourcesResult, runsResult].find((item) => item.status === 'rejected')
        if (firstError?.reason) setErr(firstError.reason.message || 'Could not load knowledge overview.')
      })
      .finally(() => setLoadingOverview(false))
  }

  useEffect(() => {
    loadOverview()
  }, [])

  useEffect(() => {
    if (!sourceConfig) return
    setSourceForm({
      brave: {
        enabled: !!sourceConfig?.brave?.enabled,
        news_count: sourceConfig?.brave?.news_count ?? 4,
        web_count: sourceConfig?.brave?.web_count ?? 5,
      },
      google_news: {
        enabled: !!sourceConfig?.google_news?.enabled,
        news_count: sourceConfig?.google_news?.news_count ?? 4,
        hl: sourceConfig?.google_news?.hl ?? 'en-US',
        gl: sourceConfig?.google_news?.gl ?? 'US',
        ceid: sourceConfig?.google_news?.ceid ?? 'US:en',
      },
      local_news: {
        enabled: !!sourceConfig?.local_news?.enabled,
        urlsText: (sourceConfig?.local_news?.urls || []).join('\n'),
        timeout_s: sourceConfig?.local_news?.timeout_s ?? 8,
      },
    })
  }, [sourceConfig])

  const runKnowledge = () => {
    setRunningKnowledge(true)
    setErr(null)
    setRunResult(null)
    api.triggerScheduledJob(RESEARCH_JOB_ID, { goal: runGoal.trim() })
      .then((response) => {
        setRunResult(response || { ok: true })
        loadOverview()
      })
      .catch((error) => {
        setErr(error.message || 'Could not run knowledge sync.')
      })
      .finally(() => setRunningKnowledge(false))
  }

  const addQueueTopic = () => {
    if (!queueForm.topic.trim()) return
    setQueueBusy(true)
    setErr(null)
    api.addKnowledgeQueueTopic({
      topic: queueForm.topic.trim(),
      requested_by: queueForm.requested_by.trim(),
      priority: queueForm.priority,
      context: queueForm.context.trim(),
    })
      .then(() => {
        setQueueForm({ topic: '', requested_by: '', priority: 'medium', context: '' })
        loadOverview()
      })
      .catch((error) => setErr(error.message || 'Could not add queue topic.'))
      .finally(() => setQueueBusy(false))
  }

  const removeQueueTopic = (topic) => {
    setQueueBusy(true)
    setErr(null)
    api.removeKnowledgeQueueTopic(topic)
      .then(() => loadOverview())
      .catch((error) => setErr(error.message || 'Could not remove queue topic.'))
      .finally(() => setQueueBusy(false))
  }

  const clearQueue = () => {
    setQueueBusy(true)
    setErr(null)
    api.clearKnowledgeQueue()
      .then(() => loadOverview())
      .catch((error) => setErr(error.message || 'Could not clear queue.'))
      .finally(() => setQueueBusy(false))
  }

  const setScheduleEnabled = (enabled) => {
    setScheduleBusy(true)
    setErr(null)
    api.setKnowledgeScheduleEnabled(enabled)
      .then(() => loadOverview())
      .catch((error) => setErr(error.message || 'Could not update schedule state.'))
      .finally(() => setScheduleBusy(false))
  }

  const doSearch = () => {
    if (!query.trim()) return
    setSearching(true)
    api.searchKnowledge(query.trim(), 20)
      .then((r) => setResults(r.results || []))
      .catch((e) => { setErr(e.message); setResults([]) })
      .finally(() => setSearching(false))
  }

  const inspectWorkspaceForChat = () => {
    if (!inspectChatId.trim()) return
    setInspecting(true)
    setShowWorkspaceJson(false)
    api.getKnowledgeWorkspace(inspectChatId.trim())
      .then((r) => setInspectWorkspace(r))
      .catch((e) => { setErr(e.message); setInspectWorkspace(null) })
      .finally(() => setInspecting(false))
  }

  const saveSourceConfig = () => {
    setSourceBusy(true)
    setErr(null)
    api.setKnowledgeSources({
      sources: {
        brave: {
          enabled: !!sourceForm.brave.enabled,
          news_count: Number(sourceForm.brave.news_count) || 4,
          web_count: Number(sourceForm.brave.web_count) || 5,
        },
        google_news: {
          enabled: !!sourceForm.google_news.enabled,
          news_count: Number(sourceForm.google_news.news_count) || 4,
          hl: String(sourceForm.google_news.hl || 'en-US').trim() || 'en-US',
          gl: String(sourceForm.google_news.gl || 'US').trim() || 'US',
          ceid: String(sourceForm.google_news.ceid || 'US:en').trim() || 'US:en',
        },
        local_news: {
          enabled: !!sourceForm.local_news.enabled,
          urls: String(sourceForm.local_news.urlsText || '')
            .split('\n')
            .map((item) => item.trim())
            .filter(Boolean),
          timeout_s: Number(sourceForm.local_news.timeout_s) || 8,
        },
      },
    })
      .then((response) => {
        setSourceConfig(response?.sources || null)
      })
      .catch((error) => setErr(error.message || 'Could not save knowledge source config.'))
      .finally(() => setSourceBusy(false))
  }

  const probeSources = () => {
    setSourceProbeBusy(true)
    setErr(null)
    api.probeKnowledgeSources({ query: sourceProbeQuery.trim() })
      .then((response) => setSourceProbeResult(response || null))
      .catch((error) => setErr(error.message || 'Could not probe knowledge sources.'))
      .finally(() => setSourceProbeBusy(false))
  }

  const queueItems = control?.queued_topics || []
  const schedule = control?.schedule || null
  const domains = control?.domain_specs || []

  return (
    <Layout title="Knowledge Machine">
      {err ? <StateNotice tone="danger" title="Could not load knowledge data" detail={err} action={<button type="button" onClick={loadOverview}>Retry</button>} /> : null}

      <section className="section-card" style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 18, marginBottom: 8 }}>Readiness</h2>
        <p className="muted" style={{ marginTop: 0 }}>
          Fast operator read on whether the Knowledge Machine is in shape to run without guessing across five separate panels.
        </p>
        <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
          <div className="section-card">
            <div className="muted" style={{ fontSize: 12 }}>Overall</div>
            <div style={{ fontSize: 28, fontWeight: 700 }}>{readiness?.ready ? 'Ready' : 'Blocked'}</div>
            <div className="muted">
              {(readiness?.blocking || []).length ? `Missing: ${(readiness.blocking || []).join(', ')}` : 'No blocking checks'}
            </div>
          </div>
          <div className="section-card">
            <div className="muted" style={{ fontSize: 12 }}>Enabled sources</div>
            <div style={{ fontSize: 22, fontWeight: 700 }}>{(readiness?.summary?.enabled_sources || []).length}</div>
            <div className="muted">{(readiness?.summary?.enabled_sources || []).join(', ') || 'none'}</div>
          </div>
          <div className="section-card">
            <div className="muted" style={{ fontSize: 12 }}>Latest brief</div>
            <div style={{ fontSize: 22, fontWeight: 700 }}>{readiness?.summary?.latest_brief_path ? 'Present' : 'Missing'}</div>
            <div className="muted">{readiness?.summary?.latest_brief_path || 'No current-events brief yet'}</div>
          </div>
        </div>
      </section>

      <section className="section-card" style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 18, marginBottom: 8 }}>Control plane</h2>
        <p className="muted" style={{ marginTop: 0 }}>
          Queue research work, toggle the recurring knowledge cycle, and launch a targeted run without editing runtime JSON by hand.
        </p>
        <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', marginBottom: 16 }}>
          <div className="section-card">
            <div className="muted" style={{ fontSize: 12 }}>Queue</div>
            <div style={{ fontSize: 28, fontWeight: 700 }}>{control?.queue_count ?? 0}</div>
            <div className="muted">pending topics</div>
          </div>
          <div className="section-card">
            <div className="muted" style={{ fontSize: 12 }}>Schedule</div>
            <div style={{ fontSize: 28, fontWeight: 700 }}>{schedule?.enabled ? 'On' : 'Off'}</div>
            <div className="muted">
              {schedule?.entry?.cron || (schedule?.entry?.interval_minutes ? `every ${schedule.entry.interval_minutes} min` : 'not scheduled')}
            </div>
          </div>
          <div className="section-card">
            <div className="muted" style={{ fontSize: 12 }}>Knowledge DB</div>
            <div style={{ fontSize: 28, fontWeight: 700 }}>{stats?.total_documents ?? 0}</div>
            <div className="muted">indexed documents</div>
          </div>
        </div>

        <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))' }}>
          <div className="section-card">
            <h3 style={{ marginTop: 0, fontSize: 16 }}>Manual run</h3>
            <label className="muted" htmlFor="knowledge-goal">Optional goal override</label>
            <textarea
              id="knowledge-goal"
              value={runGoal}
              onChange={(e) => setRunGoal(e.target.value)}
              placeholder="Leave blank to let the queue and domain rotation drive the run."
              style={{ width: '100%', minHeight: 96, marginTop: 8, padding: 8 }}
            />
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 12 }}>
              <button type="button" onClick={runKnowledge} disabled={runningKnowledge}>
                {runningKnowledge ? 'Running…' : 'Run knowledge now'}
              </button>
              <button type="button" onClick={loadOverview} disabled={loadingOverview}>
                {loadingOverview ? 'Refreshing…' : 'Refresh'}
              </button>
            </div>
            {runResult ? (
              <StateNotice
                tone="success"
                title="Knowledge run started"
                detail={runResult?.run_id ? `Run ${runResult.run_id} queued for ${RESEARCH_JOB_ID}.` : `${RESEARCH_JOB_ID} triggered.`}
              />
            ) : null}
          </div>

          <div className="section-card">
            <h3 style={{ marginTop: 0, fontSize: 16 }}>Recurring schedule</h3>
            <p className="muted" style={{ marginTop: 0 }}>
              Current cadence: {schedule?.entry?.cron || (schedule?.entry?.interval_minutes ? `every ${schedule.entry.interval_minutes} min` : 'disabled')}
            </p>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <button type="button" onClick={() => setScheduleEnabled(true)} disabled={scheduleBusy || schedule?.enabled}>
                Enable recurring run
              </button>
              <button type="button" onClick={() => setScheduleEnabled(false)} disabled={scheduleBusy || !schedule?.enabled}>
                Disable recurring run
              </button>
            </div>
            <p className="muted" style={{ marginBottom: 0, marginTop: 12 }}>
              Disabling removes the job from realtime scheduling without deleting the DAG or queue state.
            </p>
          </div>
        </div>
      </section>

      <section className="section-card" style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 18, marginBottom: 8 }}>Recent research delivery</h2>
        <p className="muted" style={{ marginTop: 0 }}>
          The same bounded research-delivery surface entities use for current-events and recent knowledge outputs.
        </p>
        <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))' }}>
          <div className="section-card">
            <div className="muted" style={{ fontSize: 12 }}>Latest brief</div>
            <div style={{ fontWeight: 700, marginTop: 6 }}>
              {deliverySummary?.latest_brief_path || 'No current-events brief yet'}
            </div>
            {deliverySummary?.latest_brief_source_mix && Object.keys(deliverySummary.latest_brief_source_mix).length ? (
              <div className="muted" style={{ marginTop: 8 }}>
                Sources: {Object.entries(deliverySummary.latest_brief_source_mix).map(([name, count]) => `${name} (${count})`).join(', ')}
              </div>
            ) : null}
            {deliverySummary?.latest_brief_preview ? (
              <pre style={{ whiteSpace: 'pre-wrap', marginTop: 12, maxHeight: 220, overflow: 'auto' }}>
                {deliverySummary.latest_brief_preview}
              </pre>
            ) : (
              <div className="muted" style={{ marginTop: 12 }}>No brief preview available.</div>
            )}
          </div>
          <div className="section-card">
            <div className="muted" style={{ fontSize: 12 }}>Recent topics</div>
            {(deliverySummary?.recent_topics || []).length ? (
              <ul style={{ marginTop: 12, paddingLeft: 18 }}>
                {(deliverySummary?.recent_topics || []).map((item, idx) => (
                  <li key={`${item.topic || 'topic'}-${idx}`} style={{ marginBottom: 8 }}>
                    <strong>{item.topic || 'Untitled topic'}</strong>
                    <div className="muted">{item.category || 'uncategorized'}{item.file_path ? ` · ${item.file_path}` : ''}</div>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="muted" style={{ marginTop: 12 }}>No recent research topics recorded yet.</div>
            )}
            {(deliverySummary?.queue || []).length ? (
              <div className="muted" style={{ marginTop: 12 }}>
                Queue next: {(deliverySummary.queue || []).map((item) => item.topic).filter(Boolean).join(', ')}
              </div>
            ) : null}
          </div>
        </div>
      </section>

      <section className="section-card" style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 18, marginBottom: 8 }}>Queue</h2>
        <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', marginBottom: 16 }}>
          <input
            type="text"
            value={queueForm.topic}
            onChange={(e) => setQueueForm((prev) => ({ ...prev, topic: e.target.value }))}
            placeholder="Topic"
            style={{ padding: 8 }}
          />
          <input
            type="text"
            value={queueForm.requested_by}
            onChange={(e) => setQueueForm((prev) => ({ ...prev, requested_by: e.target.value }))}
            placeholder="Requested by"
            style={{ padding: 8 }}
          />
          <select
            value={queueForm.priority}
            onChange={(e) => setQueueForm((prev) => ({ ...prev, priority: e.target.value }))}
            style={{ padding: 8 }}
          >
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
          <input
            type="text"
            value={queueForm.context}
            onChange={(e) => setQueueForm((prev) => ({ ...prev, context: e.target.value }))}
            placeholder="Context / why this matters"
            style={{ padding: 8 }}
          />
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16 }}>
          <button type="button" onClick={addQueueTopic} disabled={queueBusy || !queueForm.topic.trim()}>
            {queueBusy ? 'Saving…' : 'Add to queue'}
          </button>
          <button type="button" onClick={clearQueue} disabled={queueBusy || queueItems.length === 0}>
            Clear queue
          </button>
        </div>
        {queueItems.length > 0 ? (
          <div style={{ overflowX: 'auto', maxWidth: '100%' }}>
            <table cellPadding="8" style={{ borderCollapse: 'collapse', width: '100%', minWidth: 720 }}>
              <thead>
                <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
                  <th>Topic</th>
                  <th>Priority</th>
                  <th>Requested by</th>
                  <th>When</th>
                  <th>Context</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {queueItems.map((item) => (
                  <tr key={`${item.topic}-${item.date_requested || 'na'}`} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td>{item.topic}</td>
                    <td>{item.priority || 'medium'}</td>
                    <td>{item.requested_by || '—'}</td>
                    <td>{item.date_requested ? new Date(item.date_requested).toLocaleString() : '—'}</td>
                    <td>{item.context || '—'}</td>
                    <td>
                      <button type="button" onClick={() => removeQueueTopic(item.topic)} disabled={queueBusy}>
                        Remove
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <StateNotice title="Queue is empty" detail="Add operator topics here, or let the runtime feed queue itself when it holds low-confidence social actions." />
        )}
      </section>

      <section className="section-card" style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 18, marginBottom: 8 }}>Domain rotation</h2>
        <p className="muted" style={{ marginTop: 0 }}>
          Current built-in research sweep domains for the recurring cycle.
        </p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {domains.map((domain) => (
            <span key={domain.key} style={{ border: '1px solid var(--border)', borderRadius: 999, padding: '6px 10px', fontSize: 13 }}>
              {domain.title} <span className="muted">({domain.category})</span>
            </span>
          ))}
          {!domains.length ? <span className="muted">No domain specs loaded.</span> : null}
        </div>
      </section>

      <section className="section-card" style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 18, marginBottom: 8 }}>Research sources</h2>
        <p className="muted" style={{ marginTop: 0 }}>
          Active source adapters feeding the current-events and research cycle. Update them here instead of hand-editing runtime JSON.
        </p>
        <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))' }}>
          <div className="section-card">
            <div className="muted" style={{ fontSize: 12 }}>Brave</div>
            <div style={{ fontSize: 22, fontWeight: 700 }}>{sourceConfig?.brave?.enabled ? 'On' : 'Off'}</div>
            <div className="muted">news {sourceConfig?.brave?.news_count ?? '—'} · web {sourceConfig?.brave?.web_count ?? '—'}</div>
          </div>
          <div className="section-card">
            <div className="muted" style={{ fontSize: 12 }}>Google News RSS</div>
            <div style={{ fontSize: 22, fontWeight: 700 }}>{sourceConfig?.google_news?.enabled ? 'On' : 'Off'}</div>
            <div className="muted">news {sourceConfig?.google_news?.news_count ?? '—'} · {sourceConfig?.google_news?.hl ?? '—'} / {sourceConfig?.google_news?.gl ?? '—'}</div>
          </div>
          <div className="section-card">
            <div className="muted" style={{ fontSize: 12 }}>Local feeds</div>
            <div style={{ fontSize: 22, fontWeight: 700 }}>{sourceConfig?.local_news?.enabled ? 'On' : 'Off'}</div>
            <div className="muted">{sourceConfig?.local_news?.url_count ?? 0} configured feed{(sourceConfig?.local_news?.url_count ?? 0) === 1 ? '' : 's'}</div>
          </div>
        </div>
        <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', marginTop: 16 }}>
          <div className="section-card">
            <h3 style={{ marginTop: 0, fontSize: 16 }}>Brave</h3>
            <label style={{ display: 'block', marginBottom: 8 }}>
              <input
                type="checkbox"
                checked={!!sourceForm.brave.enabled}
                onChange={(e) => setSourceForm((prev) => ({ ...prev, brave: { ...prev.brave, enabled: e.target.checked } }))}
              /> Enable Brave search
            </label>
            <div style={{ display: 'grid', gap: 8, gridTemplateColumns: '1fr 1fr' }}>
              <input
                type="number"
                min="1"
                max="25"
                value={sourceForm.brave.news_count}
                onChange={(e) => setSourceForm((prev) => ({ ...prev, brave: { ...prev.brave, news_count: e.target.value } }))}
                placeholder="News count"
                style={{ padding: 8 }}
              />
              <input
                type="number"
                min="1"
                max="25"
                value={sourceForm.brave.web_count}
                onChange={(e) => setSourceForm((prev) => ({ ...prev, brave: { ...prev.brave, web_count: e.target.value } }))}
                placeholder="Web count"
                style={{ padding: 8 }}
              />
            </div>
          </div>
          <div className="section-card">
            <h3 style={{ marginTop: 0, fontSize: 16 }}>Google News RSS</h3>
            <label style={{ display: 'block', marginBottom: 8 }}>
              <input
                type="checkbox"
                checked={!!sourceForm.google_news.enabled}
                onChange={(e) => setSourceForm((prev) => ({ ...prev, google_news: { ...prev.google_news, enabled: e.target.checked } }))}
              /> Enable Google News RSS
            </label>
            <div style={{ display: 'grid', gap: 8, gridTemplateColumns: '1fr 1fr' }}>
              <input
                type="number"
                min="1"
                max="25"
                value={sourceForm.google_news.news_count}
                onChange={(e) => setSourceForm((prev) => ({ ...prev, google_news: { ...prev.google_news, news_count: e.target.value } }))}
                placeholder="News count"
                style={{ padding: 8 }}
              />
              <input
                type="text"
                value={sourceForm.google_news.hl}
                onChange={(e) => setSourceForm((prev) => ({ ...prev, google_news: { ...prev.google_news, hl: e.target.value } }))}
                placeholder="hl"
                style={{ padding: 8 }}
              />
              <input
                type="text"
                value={sourceForm.google_news.gl}
                onChange={(e) => setSourceForm((prev) => ({ ...prev, google_news: { ...prev.google_news, gl: e.target.value } }))}
                placeholder="gl"
                style={{ padding: 8 }}
              />
              <input
                type="text"
                value={sourceForm.google_news.ceid}
                onChange={(e) => setSourceForm((prev) => ({ ...prev, google_news: { ...prev.google_news, ceid: e.target.value } }))}
                placeholder="ceid"
                style={{ padding: 8 }}
              />
            </div>
          </div>
          <div className="section-card">
            <h3 style={{ marginTop: 0, fontSize: 16 }}>Local feeds</h3>
            <label style={{ display: 'block', marginBottom: 8 }}>
              <input
                type="checkbox"
                checked={!!sourceForm.local_news.enabled}
                onChange={(e) => setSourceForm((prev) => ({ ...prev, local_news: { ...prev.local_news, enabled: e.target.checked } }))}
              /> Enable local RSS/Atom feeds
            </label>
            <input
              type="number"
              min="2"
              max="60"
              value={sourceForm.local_news.timeout_s}
              onChange={(e) => setSourceForm((prev) => ({ ...prev, local_news: { ...prev.local_news, timeout_s: e.target.value } }))}
              placeholder="Timeout (s)"
              style={{ padding: 8, marginBottom: 8, width: '100%' }}
            />
            <textarea
              value={sourceForm.local_news.urlsText}
              onChange={(e) => setSourceForm((prev) => ({ ...prev, local_news: { ...prev.local_news, urlsText: e.target.value } }))}
              placeholder="One feed URL per line"
              style={{ width: '100%', minHeight: 100, padding: 8 }}
            />
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 16 }}>
          <input
            type="text"
            value={sourceProbeQuery}
            onChange={(e) => setSourceProbeQuery(e.target.value)}
            placeholder="Probe query"
            style={{ flex: 1, minWidth: 260, padding: 8 }}
          />
          <button type="button" onClick={probeSources} disabled={sourceProbeBusy}>
            {sourceProbeBusy ? 'Probing…' : 'Probe sources'}
          </button>
          <button type="button" onClick={saveSourceConfig} disabled={sourceBusy}>
            {sourceBusy ? 'Saving…' : 'Save source config'}
          </button>
        </div>
        {sourceProbeResult?.sources ? (
          <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', marginTop: 16 }}>
            {Object.entries(sourceProbeResult.sources).map(([name, item]) => (
              <div key={name} className="section-card">
                <div className="muted" style={{ fontSize: 12 }}>{name}</div>
                <div style={{ fontSize: 22, fontWeight: 700 }}>{item?.enabled ? 'Enabled' : 'Disabled'}</div>
                {'news_count' in (item || {}) ? <div className="muted">news {item.news_count ?? 0}</div> : null}
                {'web_count' in (item || {}) ? <div className="muted">web {item.web_count ?? 0}</div> : null}
                {(item?.sample_titles || []).length ? (
                  <ul style={{ paddingLeft: 18, marginBottom: 0, marginTop: 12 }}>
                    {(item.sample_titles || []).map((title) => <li key={title}>{title}</li>)}
                  </ul>
                ) : (
                  <div className="muted" style={{ marginTop: 12 }}>No sample results.</div>
                )}
              </div>
            ))}
          </div>
        ) : null}
        {sourceConfig?.local_news?.enabled && (sourceConfig?.local_news?.urls || []).length ? (
          <div style={{ marginTop: 12 }}>
            <strong>Configured local feeds</strong>
            <ul style={{ paddingLeft: 18, marginBottom: 0 }}>
              {(sourceConfig.local_news.urls || []).map((url) => (
                <li key={url}><code>{url}</code></li>
              ))}
            </ul>
          </div>
        ) : null}
      </section>

      <section className="section-card" style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 18, marginBottom: 8 }}>Knowledge workspaces</h2>
        <p className="muted" style={{ marginTop: 0 }}>
          Recent planner-backed research and document-review runs derived from live chat workspaces.
        </p>
        <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
          <input
            type="text"
            value={inspectChatId}
            onChange={(e) => setInspectChatId(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && inspectWorkspaceForChat()}
            placeholder="Inspect chat_id…"
            style={{ flex: 1, minWidth: 260, padding: 8 }}
          />
          <button type="button" onClick={inspectWorkspaceForChat} disabled={inspecting}>
            {inspecting ? 'Loading…' : 'Inspect chat workspace'}
          </button>
        </div>
        {recentRuns.length > 0 ? (
          <div style={{ overflowX: 'auto', maxWidth: '100%' }}>
            <table cellPadding="8" style={{ borderCollapse: 'collapse', width: '100%', minWidth: 760, marginBottom: 16 }}>
              <thead>
                <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
                  <th>When</th>
                  <th>Kind</th>
                  <th>Chat</th>
                  <th>Summary</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {recentRuns.map((run) => (
                  <tr key={`${run.chat_id}-${run.message_id}`} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td>{run.created_at ? new Date(run.created_at).toLocaleString() : '—'}</td>
                    <td>{run.kind === 'research_summary' ? 'Research' : 'Document review'}</td>
                    <td>
                      <div>{run.chat_title || run.chat_id}</div>
                      <div className="muted" style={{ fontSize: 12 }}>{run.chat_id}</div>
                    </td>
                    <td>{run.assistant_excerpt || run.query || run.title}</td>
                    <td>
                      <button type="button" onClick={() => { setInspectChatId(run.chat_id); setInspectWorkspace(null); api.getKnowledgeWorkspace(run.chat_id).then((r) => setInspectWorkspace(r)).catch((e) => setErr(e.message)) }}>
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
        {loadingOverview ? <StateNotice title="Loading knowledge workspace overview" detail="Fetching knowledge stats, control state, and recent planner-backed runs." /> : null}
        {!loadingOverview && !recentRuns.length ? <StateNotice title="No recent knowledge-work runs" detail="Planner-backed research and document review runs will appear here after they complete." /> : null}
        {inspectWorkspace ? (
          <div style={{ marginTop: 16 }}>
            <h3 style={{ fontSize: 16, marginBottom: 8 }}>Chat workspace</h3>
            <p className="muted" style={{ marginTop: 0 }}>{inspectWorkspace.chat?.title || inspectWorkspace.chat?.chat_id}</p>
            <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', marginBottom: 16 }}>
              <div className="section-card">
                <h4 style={{ marginTop: 0 }}>Documents</h4>
                <ul style={{ paddingLeft: 18, marginBottom: 0 }}>
                  {(inspectWorkspace.documents || []).map((doc) => (
                    <li key={doc.document_id}>
                      {doc.filename} · {doc.parse_status} · {(doc.segments || []).length} segments
                    </li>
                  ))}
                  {!inspectWorkspace.documents?.length && <li>No attached documents.</li>}
                </ul>
              </div>
              <div className="section-card">
                <h4 style={{ marginTop: 0 }}>Runs</h4>
                <ul style={{ paddingLeft: 18, marginBottom: 0 }}>
                  {(inspectWorkspace.runs || []).map((run) => (
                    <li key={run.message_id}>
                      {(run.kind === 'research_summary' ? 'Research' : 'Document review')} · {run.plan_template || '—'}
                    </li>
                  ))}
                  {!inspectWorkspace.runs?.length && <li>No structured runs.</li>}
                </ul>
              </div>
            </div>
            <button type="button" onClick={() => setShowWorkspaceJson((value) => !value)}>
              {showWorkspaceJson ? 'Hide raw workspace JSON' : 'Show raw workspace JSON'}
            </button>
            {showWorkspaceJson ? (
              <pre style={{ background: '#0b1118', padding: 12, overflow: 'auto', borderRadius: 8, border: '1px solid var(--border)', marginTop: 12, maxHeight: 420 }}>
                {JSON.stringify(inspectWorkspace, null, 2)}
              </pre>
            ) : null}
          </div>
        ) : null}
      </section>

      {stats ? (
        <section style={{ marginBottom: 24 }}>
          <h2 style={{ fontSize: 18, marginBottom: 8 }}>Stats</h2>
          <p><strong>Total documents:</strong> {stats.total_documents ?? 0}</p>
          {stats.by_category && stats.by_category.length > 0 ? (
            <div style={{ overflowX: 'auto', maxWidth: '100%' }}>
              <table cellPadding="8" style={{ borderCollapse: 'collapse', marginTop: 8, minWidth: 420 }}>
                <thead>
                  <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
                    <th>Category</th>
                    <th>Count</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.by_category.map((c) => (
                    <tr key={c.category} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td>{c.category}</td>
                      <td>{c.count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </section>
      ) : null}

      {stats && !stats.ok ? <StateNotice title="Knowledge DB unavailable" detail="The shared knowledge index is not responding yet." /> : null}

      <section>
        <h2 style={{ fontSize: 18, marginBottom: 8 }}>Search</h2>
        <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && doSearch()}
            placeholder="Search knowledge…"
            style={{ flex: 1, padding: 8 }}
          />
          <button type="button" onClick={doSearch} disabled={searching}>
            {searching ? 'Searching…' : 'Search'}
          </button>
        </div>
        {results.length > 0 ? (
          <ul style={{ listStyle: 'none', padding: 0 }}>
            {results.map((r, i) => (
              <li key={i} style={{ borderBottom: '1px solid var(--border)', padding: '8px 0' }}>
                <strong>{r.title || r.file_path}</strong>
                {r.category ? <span style={{ marginLeft: 8, color: 'var(--muted)' }}>{r.category}</span> : null}
                {r.snippet ? (
                  <div style={{ marginTop: 4, fontSize: 14, color: '#444' }} dangerouslySetInnerHTML={{ __html: r.snippet }} />
                ) : null}
              </li>
            ))}
          </ul>
        ) : null}
        {!searching && query.trim() && results.length === 0 ? (
          <StateNotice title="No search results" detail="Try a broader term or wait for the next knowledge sync." />
        ) : null}
      </section>
    </Layout>
  )
}
