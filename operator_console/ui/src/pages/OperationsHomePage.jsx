import React, { useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import SharedEventSummary from '../components/SharedEventSummary.jsx'
import StateNotice from '../components/StateNotice.jsx'
import { api } from '../lib/api.js'

function HubCard({ eyebrow, title, detail, href, metric }) {
  return (
    <a href={href} className="card" style={{ display: 'block', textDecoration: 'none', color: 'inherit' }}>
      <div style={{ color: 'var(--accent)', fontSize: 11, letterSpacing: 1, textTransform: 'uppercase', marginBottom: 8 }}>{eyebrow}</div>
      <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 6 }}>{title}</div>
      <div style={{ color: 'var(--muted)', fontSize: 13, minHeight: 36 }}>{detail}</div>
      {metric ? <div style={{ marginTop: 12, fontSize: 12, color: 'var(--text)' }}>{metric}</div> : null}
    </a>
  )
}

export default function OperationsHomePage() {
  const [summary, setSummary] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(() => {
    let cancelled = false
    Promise.allSettled([
      api.getStatusDashboard(24),
      api.getApprovalsQueue({ limit: 20 }),
      api.listKeystoreAccounts('facebook'),
      api.getPersonaNaturalnessSummary({ hours: 168 }),
      api.listRuns(25),
    ]).then((results) => {
      if (cancelled) return
      const [statusRes, approvalsRes, socialRes, personaRes, runsRes] = results
      setSummary({
        status: statusRes.status === 'fulfilled' ? statusRes.value : null,
        approvals: approvalsRes.status === 'fulfilled' ? approvalsRes.value : null,
        social: socialRes.status === 'fulfilled' ? socialRes.value : null,
        persona: personaRes.status === 'fulfilled' ? personaRes.value : null,
        runs: runsRes.status === 'fulfilled' ? runsRes.value : null,
      })
      const rejected = results.find((r) => r.status === 'rejected')
      if (rejected?.reason?.message) setErr(rejected.reason.message)
    }).catch((error) => {
      if (!cancelled) setErr(error.message)
    })
    return () => { cancelled = true }
  }, [])

  const pendingApprovals = Array.isArray(summary?.approvals?.items) ? summary.approvals.items.length : null
  const socialAccounts = Array.isArray(summary?.social?.items) ? summary.social.items.length : null
  const recentRuns = Array.isArray(summary?.runs) ? summary.runs.length : null
  const autonomyTurns = summary?.persona?.summary?.total_turns ?? summary?.persona?.total_turns ?? null
  const latestState = summary?.status?.summary?.latest_state?.mode || summary?.status?.latest_state?.mode || null

  return (
    <Layout title="Operations Home">
      {err ? (
        <StateNotice tone="danger" title="Some operations panels could not load" detail={err} />
      ) : null}
      <SharedEventSummary
        eyebrow="Operations home"
        title="Start here"
        intro="This is the control center for entity work, timeline review, proofs, governance, and recovery."
        status={latestState || 'ready'}
        statusTone={latestState === 'healthy' ? 'good' : latestState === 'degraded' ? 'danger' : 'neutral'}
        happened="The operator view is ready."
        when="Current session"
        why="Use this page to move from entity to work to lineage to review without changing the mental model."
        changed={`Approvals ${pendingApprovals ?? '—'} · runs ${recentRuns ?? '—'} · social ${socialAccounts ?? '—'}`}
        next="Open an entity, launch work, inspect what happened, then review or recover from the same story."
        context={[
          { label: 'Latest mode', value: latestState || '—' },
          { label: 'Approvals loaded', value: pendingApprovals ?? '—' },
          { label: 'Recent runs', value: recentRuns ?? '—' },
        ]}
      />
      <section className="section-card" style={{ marginBottom: 16 }}>
        <div style={{ color: 'var(--muted)', fontSize: 12, letterSpacing: 1, textTransform: 'uppercase', marginBottom: 8 }}>Canonical workspace map</div>
        <h2 style={{ marginTop: 0, marginBottom: 8 }}>Operate the system by job, not by page archaeology.</h2>
        <p style={{ margin: 0, color: 'var(--muted)', maxWidth: 780 }}>
          This home page is the start point for monitoring, approvals, proofs, persona inspection, social supervision, and run investigation.
          It is the first step in the canonical workspace information architecture.
        </p>
        <div className="card" style={{ marginTop: 16 }}>
          <div className="eyebrow">Demo path</div>
          <div style={{ marginTop: 8, color: 'var(--text)', fontWeight: 600 }}>
            Entity → work → lineage → review → recovery.
          </div>
          <p className="muted" style={{ margin: '8px 0 0', maxWidth: 760 }}>
            Open an entity, launch work, inspect the resulting lineage, review the proof, and return to recovery without switching product modes.
          </p>
          <ol style={{ margin: '12px 0 0 18px', padding: 0, color: 'var(--muted)', fontSize: 13, lineHeight: 1.6 }}>
            <li>Open an entity and read the current state.</li>
            <li>Launch work or inspect an existing run.</li>
            <li>Follow the timeline or provenance to see why it happened.</li>
            <li>Review proof or governance if the output needs attention.</li>
            <li>Return to recovery or the entity snapshot from the same thread.</li>
          </ol>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 12, fontSize: 13 }}>
            <a href="#/entities" className="nav-link">Entities</a>
            <a href="#/workflows" className="nav-link">Workflows</a>
            <a href="#/runs" className="nav-link">Runs</a>
            <a href="#/timeline" className="nav-link">Timeline</a>
            <a href="#/proofs" className="nav-link">Proofs</a>
            <a href="#/governance" className="nav-link">Governance</a>
          </div>
        </div>
      </section>

      <div className="card-grid" style={{ marginBottom: 16 }}>
        <HubCard
          eyebrow="Observe"
          title="Status"
          detail="System dashboard, budgets, autonomy controls, and report snapshots."
          href="#/status"
          metric={latestState ? `Latest mode: ${latestState}` : null}
        />
        <HubCard
          eyebrow="Govern"
          title="Approvals"
          detail="Review pending actions, risk decisions, and human gate checkpoints."
          href="#/approvals"
          metric={pendingApprovals != null ? `${pendingApprovals} approvals loaded` : null}
        />
        <HubCard
          eyebrow="Operate"
          title="Social Ops"
          detail="Supervise keystore-backed social accounts, browser sessions, and notification checks."
          href="#/social"
          metric={socialAccounts != null ? `${socialAccounts} social accounts visible` : null}
        />
        <HubCard
          eyebrow="Inspect"
          title="Personas"
          detail="Preview naturalness, autonomy, history, and evaluation traces."
          href="#/persona-naturalness"
          metric={autonomyTurns != null ? `${autonomyTurns} recent naturalness turns` : null}
        />
        <HubCard
          eyebrow="Steward"
          title="Governance"
          detail="Operate receipts, policy versions, constitutional roots, and release gate state."
          href="#/governance"
        />
        <HubCard
          eyebrow="Evidence"
          title="Proofs"
          detail="Move from recent evidence to replay, proof artifacts, and event history."
          href="#/timeline"
        />
        <HubCard
          eyebrow="Records"
          title="Content CMS"
          detail="Edit plans, runbooks, skills, and persona/meta docs in-browser."
          href="#/content"
        />
        <HubCard
          eyebrow="Records"
          title="Artifact Registry"
          detail="Browse generated logs, screenshots, backups, snapshots, and archive records."
          href="#/artifacts"
        />
        <HubCard
          eyebrow="Records"
          title="Source Registry"
          detail="Inspect Python source blobs, module paths, version history, and archive state."
          href="#/source-registry"
        />
        <HubCard
          eyebrow="Records"
          title="Executable Registry"
          detail="Inspect executable source metadata, module paths, versions, and archive history."
          href="#/executables"
        />
        <HubCard
          eyebrow="Records"
          title="Task Registry"
          detail="Inspect task launch metadata, ownership, and version history."
          href="#/task-registry"
        />
        <HubCard
          eyebrow="Explore"
          title="Run Explorer"
          detail="Inspect runs, DAGs, snapshots, delegation, and run-level artifacts."
          href="#/"
          metric={recentRuns != null ? `${recentRuns} recent runs loaded` : null}
        />
      </div>
    </Layout>
  )
}
