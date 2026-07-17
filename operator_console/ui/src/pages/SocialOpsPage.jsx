import React, { useCallback, useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import StateNotice from '../components/StateNotice.jsx'
import { api } from '../lib/api.js'

function lastActivityLabel(summary) {
  if (!summary || !summary.last_seen_at) return 'No recent activity'
  return `${summary.last_seen_kind || 'activity'}${summary.stale ? ' · stale' : ''}`
}

export default function SocialOpsPage() {
  const [accounts, setAccounts] = useState([])
  const [selectedId, setSelectedId] = useState('')
  const [overview, setOverview] = useState(null)
  const [lastAction, setLastAction] = useState(null)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState(null)

  const loadAccounts = useCallback(() => {
    setErr(null)
    setLoading(true)
    api.listKeystoreAccounts()
      .then((r) => {
        const items = Array.isArray(r.items) ? r.items : []
        setAccounts(items)
        if (!selectedId && items[0]?.social_account_id) {
          setSelectedId(items[0].social_account_id)
        }
      })
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false))
  }, [selectedId])

  const loadOverview = useCallback((socialAccountId) => {
    if (!socialAccountId) {
      setOverview(null)
      return
    }
    setErr(null)
    api.getKeystoreAccountOverview(socialAccountId)
      .then((r) => setOverview(r))
      .catch((e) => setErr(e.message))
  }, [])

  useEffect(() => { loadAccounts() }, [loadAccounts])
  useEffect(() => { loadOverview(selectedId) }, [selectedId, loadOverview])

  const selectedAccount = accounts.find((item) => item.social_account_id === selectedId) || null
  const continuityHealth = overview?.latest_browser_session_health || null
  const continuityTone = continuityHealth?.status === 'degraded' ? 'danger' : continuityHealth?.status === 'closed' ? 'muted' : 'success'
  const readiness = overview?.readiness || null
  const continuityInjury = overview?.continuity_injury_summary || null
  const lastActivity = overview?.last_activity_summary || null
  const notificationSummary = overview?.notification_summary || null
  const replacedDegradedSession = lastAction?.replaced_degraded_session || null
  const proofCards = [
    { key: 'latest_registration_proof', title: 'Registration / Account Proof' },
    { key: 'latest_verification_proof', title: 'Verification Proof' },
    { key: 'latest_post_proof', title: 'Latest Post Proof' },
    { key: 'latest_reply_proof', title: 'Latest Reply Proof' },
    { key: 'latest_challenge_proof', title: 'Latest Challenge Proof' },
  ].filter((item) => overview?.[item.key])

  const runLogin = async () => {
    if (!selectedAccount?.entity_scope) return
    if (selectedAccount?.platform !== 'facebook') return
    setErr(null)
    try {
      const result = await api.facebookLogin({
        entity_id: selectedAccount.entity_scope,
        social_account_id: selectedAccount.social_account_id,
      })
      setLastAction(result)
      loadOverview(selectedAccount.social_account_id)
    } catch (e) {
      setErr(e.message)
    }
  }

  const runNotifications = async () => {
    if (!selectedAccount?.entity_scope) return
    if (selectedAccount?.platform !== 'facebook') return
    setErr(null)
    try {
      const result = await api.facebookReadNotifications({
        entity_id: selectedAccount.entity_scope,
        social_account_id: selectedAccount.social_account_id,
        limit: 10,
      })
      setLastAction(result)
      loadOverview(selectedAccount.social_account_id)
    } catch (e) {
      setErr(e.message)
    }
  }

  return (
    <Layout title="Social Ops">
      {err && (
        <StateNotice
          tone="danger"
          title="Social ops failed"
          detail={err}
          action={<button type="button" onClick={() => loadOverview(selectedId)}>Retry</button>}
        />
      )}
      <p>
        Inspect keystore-backed social accounts, proof state, continuity health, and recent human-facing runtime receipts.
        Facebook-specific browser actions stay available where that adapter exists; the page itself is no longer platform-locked.
      </p>
      {readiness && (
        <section className="section-card" style={{ marginBottom: 16 }}>
          <h3 style={{ marginTop: 0 }}>Readiness</h3>
          <StateNotice
            tone={readiness.ready ? 'success' : 'danger'}
            title={readiness.ready ? 'Ready' : 'Blocked'}
            detail={(readiness.blocking || []).length ? `Missing: ${(readiness.blocking || []).join(', ')}` : 'No blocking checks'}
          />
          <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', marginTop: 12 }}>
            <div className="section-card">
              <div className="muted" style={{ fontSize: 11 }}>State</div>
              <div>{readiness?.summary?.state || 'unknown'}</div>
            </div>
            <div className="section-card">
              <div className="muted" style={{ fontSize: 11 }}>Browser session</div>
              <div>{readiness?.summary?.browser_session_id || 'missing'}</div>
            </div>
            <div className="section-card">
              <div className="muted" style={{ fontSize: 11 }}>Continuity</div>
              <div>{readiness?.summary?.continuity_status || 'missing'}</div>
            </div>
            <div className="section-card">
              <div className="muted" style={{ fontSize: 11 }}>Continuity injury</div>
              <div>{continuityInjury?.status || 'none'}</div>
              <div className="muted" style={{ fontSize: 12 }}>
                {continuityInjury?.last_repair_at
                  ? `repaired ${continuityInjury.last_repair_at}`
                  : (continuityInjury?.last_injury_reason || 'no recorded injury')}
              </div>
            </div>
            <div className="section-card">
              <div className="muted" style={{ fontSize: 11 }}>Recent activity</div>
              <div>{lastActivityLabel(lastActivity)}</div>
              <div className="muted" style={{ fontSize: 12 }}>{lastActivity?.last_seen_at || '—'}</div>
            </div>
            <div className="section-card">
              <div className="muted" style={{ fontSize: 11 }}>Recent notifications</div>
              <div>{notificationSummary?.count || 0}</div>
              <div className="muted" style={{ fontSize: 12 }}>{notificationSummary?.latest?.message || 'none'}</div>
            </div>
          </div>
        </section>
      )}
      <section className="section-card" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          <select value={selectedId} onChange={(e) => setSelectedId(e.target.value)} style={{ minWidth: 260 }}>
            <option value="">Select social account</option>
            {accounts.map((account) => (
              <option key={account.social_account_id} value={account.social_account_id}>
                {account.platform} · {account.account_alias} ({account.state})
              </option>
            ))}
          </select>
          <button type="button" onClick={loadAccounts}>Refresh accounts</button>
          <button type="button" onClick={() => loadOverview(selectedId)} disabled={!selectedId}>Refresh overview</button>
          <button type="button" onClick={runLogin} disabled={!selectedAccount?.entity_scope || selectedAccount?.platform !== 'facebook'}>Run Facebook login</button>
          <button type="button" onClick={runNotifications} disabled={!selectedAccount?.entity_scope || selectedAccount?.platform !== 'facebook'}>Read Facebook notifications</button>
        </div>
        {loading && <div className="muted" style={{ marginTop: 8 }}>Loading accounts…</div>}
      </section>

      {overview?.item && (
        <section className="section-card" style={{ marginBottom: 16 }}>
          <h3 style={{ marginTop: 0 }}>Account</h3>
          <pre style={{ background: 'var(--panel-2)', padding: 12, overflow: 'auto' }}>
            {JSON.stringify(overview.item, null, 2)}
          </pre>
        </section>
      )}

      {overview?.latest_browser_session && (
        <section className="section-card" style={{ marginBottom: 16 }}>
          <h3 style={{ marginTop: 0 }}>Latest Browser Session</h3>
          {continuityHealth && (
            <div style={{ marginBottom: 12 }}>
              <StateNotice
                tone={continuityTone}
                title={`Continuity ${continuityHealth.status || 'unknown'}`}
                detail={
                  continuityHealth.status === 'degraded'
                    ? `Restart-critical browser artifacts are broken: ${(continuityHealth.issues || []).join(', ') || 'unknown issue'}.`
                    : continuityHealth.status === 'closed'
                      ? 'This browser session is closed and not expected to restore.'
                      : 'Restart-critical browser artifacts are present for this browser session.'
                }
              />
              <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', marginTop: 12 }}>
                <div className="section-card">
                  <div className="muted" style={{ fontSize: 11 }}>Profile dir</div>
                  <div>{continuityHealth.profile_dir_exists ? 'present' : 'missing'}</div>
                </div>
                <div className="section-card">
                  <div className="muted" style={{ fontSize: 11 }}>Latest screenshot</div>
                  <div>{continuityHealth.latest_screenshot_exists ? 'present' : 'missing / none'}</div>
                </div>
                <div className="section-card">
                  <div className="muted" style={{ fontSize: 11 }}>Latest snapshot</div>
                  <div>{continuityHealth.latest_snapshot_exists ? 'present' : 'missing / none'}</div>
                </div>
                <div className="section-card">
                  <div className="muted" style={{ fontSize: 11 }}>Trace</div>
                  <div>{continuityHealth.trace_exists ? 'present' : 'missing / none'}</div>
                </div>
              </div>
              {!!continuityHealth.issues?.length && (
                <div className="muted" style={{ marginTop: 10 }}>
                  Issues: {continuityHealth.issues.join(', ')}
                </div>
              )}
            </div>
          )}
          <pre style={{ background: 'var(--panel-2)', padding: 12, overflow: 'auto' }}>
            {JSON.stringify(overview.latest_browser_session, null, 2)}
          </pre>
        </section>
      )}

      {overview?.latest_notification_digest && (
        <section className="section-card" style={{ marginBottom: 16 }}>
          <h3 style={{ marginTop: 0 }}>Latest Notification Digest</h3>
          <pre style={{ background: 'var(--panel-2)', padding: 12, overflow: 'auto' }}>
            {JSON.stringify(overview.latest_notification_digest, null, 2)}
          </pre>
        </section>
      )}

      {proofCards.length > 0 && (
        <section className="section-card" style={{ marginBottom: 16 }}>
          <h3 style={{ marginTop: 0 }}>Latest Proof State</h3>
          <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))' }}>
            {proofCards.map((card) => (
              <div key={card.key} style={{ border: '1px solid var(--border)', background: 'var(--panel-2)', padding: 12 }}>
                <div style={{ fontWeight: 600, marginBottom: 8 }}>{card.title}</div>
                <pre style={{ margin: 0, overflow: 'auto', whiteSpace: 'pre-wrap' }}>
                  {JSON.stringify(overview[card.key], null, 2)}
                </pre>
              </div>
            ))}
          </div>
        </section>
      )}

      {Array.isArray(overview?.recent_human_notifications) && overview.recent_human_notifications.length > 0 && (
        <section className="section-card" style={{ marginBottom: 16 }}>
          <h3 style={{ marginTop: 0 }}>Recent Human Notifications</h3>
          <div style={{ display: 'grid', gap: 12 }}>
            {overview.recent_human_notifications.map((item, index) => (
              <div key={`${item.timestamp || 'notification'}-${index}`} style={{ border: '1px solid var(--border)', background: 'var(--panel-2)', padding: 12 }}>
                <div style={{ fontWeight: 600, marginBottom: 6 }}>{item.kind || 'run_update'}</div>
                <div className="muted" style={{ marginBottom: 8 }}>
                  {item.timestamp || 'unknown time'} · {item.task_name || 'unknown task'}
                </div>
                <pre style={{ margin: 0, overflow: 'auto', whiteSpace: 'pre-wrap' }}>
                  {JSON.stringify(item, null, 2)}
                </pre>
              </div>
            ))}
          </div>
        </section>
      )}

      {Array.isArray(overview?.latest_artifacts) && overview.latest_artifacts.length > 0 && (
        <section className="section-card" style={{ marginBottom: 16 }}>
          <h3 style={{ marginTop: 0 }}>Latest Artifacts</h3>
          <table className="table full-width">
            <thead>
              <tr>
                <th>Type</th>
                <th>Path</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {overview.latest_artifacts.map((artifact) => (
                <tr key={artifact.proof_id}>
                  <td>{artifact.artifact_type}</td>
                  <td>{artifact.path}</td>
                  <td>{artifact.created_at}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {lastAction && (
        <section className="section-card">
          <h3 style={{ marginTop: 0 }}>Last Action Result</h3>
          {replacedDegradedSession && (
            <div style={{ marginBottom: 12 }}>
              <StateNotice
                tone="danger"
                title="Degraded session rotated out"
                detail={`Replaced ${replacedDegradedSession.browser_session_id || 'unknown session'} because ${replacedDegradedSession.reason || 'continuity was degraded'}.`}
              />
              {!!replacedDegradedSession?.previous_health?.issues?.length && (
                <div className="muted" style={{ marginTop: 8 }}>
                  Previous issues: {replacedDegradedSession.previous_health.issues.join(', ')}
                </div>
              )}
            </div>
          )}
          <pre style={{ background: 'var(--panel-2)', padding: 12, overflow: 'auto' }}>
            {JSON.stringify(lastAction, null, 2)}
          </pre>
        </section>
      )}
    </Layout>
  )
}
