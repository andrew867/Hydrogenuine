import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  WorkbenchPage as WorkbenchView,
  createWorkbenchApi,
  timelineToViews,
  hashFile,
  SettingHeldError,
} from 'hg_ui_kit'
import { api } from '../lib/api.js'

// Operator-console host for the Agent Zero Workbench. Uses the new UX kit only
// (no legacy chat components) and the gateway cookie session (credentials via the
// kit API client). Governed run spine: create -> progress poll -> steering ->
// governed setting change (held when step-up missing). No external effects.
const GOVERNED_SETTINGS = [
  { key: 'model_route', label: 'Model route', actionClass: 'model_route_change', value: 'default' },
  { key: 'persona', label: 'Persona', actionClass: 'draft', value: 'researcher' },
  { key: 'temperature', label: 'Temperature', actionClass: 'configuration', value: '0.7' },
]

// The Workbench governed endpoints (/v1/workbench/*) are served by the GATEWAY,
// which the SPA reaches cross-origin (no vite proxy). Point the kit client at the
// gateway origin derived from VITE_API_BASE so browser calls hit :8080, not :5173.
const GATEWAY_ORIGIN = (() => {
  try {
    return new URL(import.meta.env.VITE_API_BASE || 'http://localhost:8080/api/v1').origin
  } catch {
    return 'http://localhost:8080'
  }
})()

export default function WorkbenchPageRoute() {
  const wbApi = useMemo(() => createWorkbenchApi({ baseUrl: GATEWAY_ORIGIN }), [])
  const [authState, setAuthState] = useState({ status: 'unauthenticated' })
  const [requestText, setRequestText] = useState('')
  const [steeringText, setSteeringText] = useState('')
  const [run, setRun] = useState(null)
  const [timeline, setTimeline] = useState(null)
  const [holdReason, setHoldReason] = useState(null)
  const [uploadState, setUploadState] = useState({ status: 'idle' })
  const [transport, setTransport] = useState('polling')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    let active = true
    api.auth.getMe().then((session) => {
      if (!active) return
      if (session && Array.isArray(session.roles) && session.roles.length) {
        setAuthState({
          status: 'authenticated',
          identity: {
            provider: 'keycloak',
            subject: session.principal_id || '',
            display_name: session.principal_id || '',
            roles: session.roles,
            assurance_level: 'password',
            step_up_required: false,
            step_up_satisfied: false,
            production_operator_auth: true,
            demo_local_signing: false,
          },
        })
      } else {
        setAuthState({ status: 'unauthenticated' })
      }
    }).catch(() => active && setAuthState({ status: 'unauthenticated' }))
    return () => { active = false }
  }, [])

  const refreshTimeline = useCallback(async (runId) => {
    const tl = await wbApi.getTimeline(runId)
    setTimeline(tl)
  }, [wbApi])

  const onCreateRun = useCallback(async (text) => {
    setSubmitting(true)
    try {
      const created = await wbApi.createRun(text)
      setRun(created)
      await refreshTimeline(created.run_id)
    } finally {
      setSubmitting(false)
    }
  }, [wbApi, refreshTimeline])

  // Live progress: consume the real SSE catch-up stream (observation only), then
  // reconcile from the authoritative timeline. If the stream is unavailable, fall
  // back to polling. Either way the timeline endpoint — never a stream frame — is
  // the source of truth; SSE frames can authorize nothing.
  useEffect(() => {
    if (!run || ['completed', 'failed'].includes(run.status)) return
    let cancelled = false
    const tick = async () => {
      try {
        await wbApi.openStream(run.run_id, { onEvent: () => {} })
        if (!cancelled) setTransport('stream')
      } catch {
        if (!cancelled) setTransport('polling')
      }
      if (!cancelled) await refreshTimeline(run.run_id).catch(() => {})
    }
    tick()
    const id = setInterval(tick, 3000)
    return () => { cancelled = true; clearInterval(id) }
  }, [run, wbApi, refreshTimeline])

  // Upload real file BYTES: hash locally (expectation), POST multipart to the
  // bounded local store; the server computes the authoritative sha256.
  const onSelectFile = useCallback(async (file) => {
    if (!run) return
    try {
      setUploadState({ status: 'hashing' })
      const expectedHash = await hashFile(file)
      setUploadState({ status: 'uploading' })
      const res = await wbApi.uploadArtifact(run.run_id, file, {
        expectedHash, label: file.name,
      })
      setUploadState({
        status: 'uploaded',
        last: { filename: res.filename, size_bytes: res.size_bytes, content_hash: res.content_hash },
      })
      const updated = await wbApi.getRun(run.run_id)
      setRun(updated)
      await refreshTimeline(run.run_id)
    } catch (e) {
      setUploadState({ status: 'error', error: e?.code || e?.message || 'upload_failed' })
    }
  }, [wbApi, run, refreshTimeline])

  const onSendSteering = useCallback(async (text) => {
    if (!run) return
    await wbApi.addSteering(run.run_id, text)
    setSteeringText('')
    await refreshTimeline(run.run_id)
  }, [wbApi, run, refreshTimeline])

  const onRequestSettingChange = useCallback(async (key) => {
    if (!run) return
    const setting = GOVERNED_SETTINGS.find((s) => s.key === key)
    if (!setting) return
    try {
      await wbApi.changeSetting(run.run_id, {
        setting: setting.key, action_class: setting.actionClass,
        old_value: setting.value, new_value: `${setting.value}-updated`,
      })
      setHoldReason(null)
    } catch (e) {
      if (e instanceof SettingHeldError) setHoldReason(e.reason)
      else throw e
    }
    await refreshTimeline(run.run_id)
  }, [wbApi, run, refreshTimeline])

  return (
    <div className="app-shell" style={{ padding: 24 }}>
      <WorkbenchView
        authState={authState}
        run={run}
        timeline={timeline}
        requestText={requestText}
        onRequestChange={setRequestText}
        onCreateRun={onCreateRun}
        steeringText={steeringText}
        onSteeringChange={setSteeringText}
        onSendSteering={onSendSteering}
        settings={GOVERNED_SETTINGS}
        onRequestSettingChange={onRequestSettingChange}
        holdReason={holdReason}
        uploadState={uploadState}
        onSelectFile={onSelectFile}
        transport={transport}
        submitting={submitting}
      />
    </div>
  )
}
