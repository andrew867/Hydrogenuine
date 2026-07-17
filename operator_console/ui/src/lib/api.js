function canonicalizeLoopbackBase(baseUrl, fallback) {
  const base = baseUrl || fallback
  try {
    const parsed = new URL(base)
    if (typeof window !== 'undefined') {
      const currentHost = window.location.hostname
      const loopbackHosts = new Set(['localhost', '127.0.0.1', '::1'])
      if (currentHost && loopbackHosts.has(parsed.hostname) && loopbackHosts.has(currentHost) && parsed.hostname !== currentHost) {
        parsed.hostname = currentHost
      }
    }
    return parsed.toString().replace(/\/$/, '')
  } catch {
    return base
  }
}

const API_BASE = canonicalizeLoopbackBase(import.meta.env.VITE_API_BASE, 'http://localhost:8080/api/v1')
// Gateway v1 (admin proofs) — same origin as API, path /v1
const GATEWAY_V1_BASE = (() => {
  try {
    return new URL(API_BASE).origin + '/v1'
  } catch {
    return 'http://localhost:8080/v1'
  }
})()

export const STORAGE_BROWSER_SESSION = 'oc_browser_session'

/** Legacy key paths removed (U1.1): browser cookie session is the auth source. */
export function getApiKey() {
  return ''
}

export function getAdminKey() {
  return ''
}

export function getBrowserSession() {
  try {
    const raw = sessionStorage.getItem(STORAGE_BROWSER_SESSION)
    return raw ? JSON.parse(raw) : null
  } catch (_) {}
  return null
}

export function setBrowserSession(session) {
  try {
    if (session) sessionStorage.setItem(STORAGE_BROWSER_SESSION, JSON.stringify(session))
    else sessionStorage.removeItem(STORAGE_BROWSER_SESSION)
  } catch (_) {}
}

export function clearBrowserSession() {
  setBrowserSession(null)
}

function browserSessionHasRole(roles) {
  const session = getBrowserSession()
  if (!session || !Array.isArray(session.roles)) return false
  return roles.some((role) => session.roles.includes(role))
}

function withAuthHeaders(headers = {}, { apiKey = getApiKey(), adminKey = getAdminKey() } = {}) {
  const next = { ...headers }
  if (apiKey) next.Authorization = `Bearer ${apiKey}`
  if (adminKey) next['X-Admin-Key'] = adminKey
  return next
}

async function req(path, { method='GET', body=null } = {}) {
  const headers = withAuthHeaders()
  if (body !== null) headers['Content-Type'] = 'application/json'
  const res = await fetch(`${API_BASE}${path}`, { method, headers, body: body ? JSON.stringify(body) : null, credentials: 'include' })
  const ct = res.headers.get('content-type') || ''
  if (!res.ok) {
    const txt = ct.includes('application/json') ? JSON.stringify(await res.json()) : await res.text()
    throw new Error(`HTTP ${res.status}: ${txt}`)
  }
  return ct.includes('application/json') ? await res.json() : await res.text()
}

export const api = {
  listRuns: (limit = 200) => req(`/runs?limit=${limit}`),
  getRun: (runId) => req(`/runs/${runId}`),
  getToolTrace: (runId, limit = 200) => req(`/runs/${runId}/tool-trace?limit=${limit}`),
  resumeRun: (runId) => req(`/runs/${runId}/resume`, { method: 'POST' }),
  approveRun: (runId) => req(`/runs/${runId}/approve`, { method: 'POST' }),
  denyRun: (runId, body = {}) => req(`/runs/${runId}/deny`, { method: 'POST', body }),
  replayRun: (runId) => req(`/runs/${runId}/replay`, { method: 'POST' }),
  cancelRun: (runId) => req(`/runs/${runId}/cancel`, { method: 'POST' }),
  cancelStaleRuns: (staleMinutes = 30) => req(`/runs/cancel-stale?stale_minutes=${staleMinutes}`, { method: 'POST' }),
  listArtifacts: (runId) => req(`/runs/${runId}/artifacts`),
  getArtifactUrl: (runId, path) =>
    `${API_BASE}/runs/${runId}/artifact?path=${encodeURIComponent(path)}`,
  validateGraph: (dag) => req('/graphs/validate', { method: 'POST', body: { dag } }),
  reviewGraph: (dag) => req('/graphs/review', { method: 'POST', body: { dag } }),
  runGraph: (dag) => req('/graphs/run', { method: 'POST', body: { dag } }),
  listSnapshots: (runId) => req(`/runs/${runId}/snapshots`),
  getSnapshot: (runId, seq) => req(`/runs/${runId}/snapshots/${seq}`),
  listCheckpoints: (runId) => req(`/runs/${runId}/checkpoints`),
  approveCheckpoint: (runId, checkpointId, body = {}) => req(`/runs/${runId}/checkpoints/${checkpointId}/approve`, { method: 'POST', body }),
  denyCheckpoint: (runId, checkpointId, body = {}) => req(`/runs/${runId}/checkpoints/${checkpointId}/deny`, { method: 'POST', body }),
  forkFromSnapshot: (runId, seq) => req(`/runs/${runId}/fork/${seq}`, { method: 'POST' }),
  getRunEventsStreamToken: (runId) => req(`/runs/${runId}/events/stream-token`),
  eventsStreamUrl: (runId, streamToken) =>
    `${API_BASE}/runs/${runId}/events/stream${streamToken ? `?stream_token=${encodeURIComponent(streamToken)}` : ''}`,
  runsStreamUrl: () => `${API_BASE}/runs/stream`,
  getRunState: (runId) => req(`/runs/${runId}/state`),
  getRunLineage: (runId) => req(`/runs/${runId}/lineage`),
  getRunSwarm: (runId) => req(`/runs/${runId}/swarm`),
  getJsonArtifact: (runId, name) => req(`/runs/${runId}/artifacts/json/${name}`),
  getOwnershipChain: (runId, taskId = null) => req(`/runs/${runId}/ownership/chain${taskId ? `?task_id=${encodeURIComponent(taskId)}` : ''}`),
  getOwnershipEdges: (runId, taskId = null) => req(`/runs/${runId}/ownership/edges${taskId ? `?task_id=${encodeURIComponent(taskId)}` : ''}`),
  getOwnershipEvents: (runId, taskId = null, limit = 100) => req(`/runs/${runId}/ownership/events?limit=${limit}${taskId ? `&task_id=${encodeURIComponent(taskId)}` : ''}`),
  searchOwnership: (runId, q, taskId = null, limit = 50) => req(`/runs/${runId}/ownership/search?q=${encodeURIComponent(q)}&limit=${limit}${taskId ? `&task_id=${encodeURIComponent(taskId)}` : ''}`),
  getOwnershipAvailability: (runId) => req(`/runs/${runId}/ownership/availability`),
  getAnalytics: (runId) => req(`/runs/${runId}/analytics`),
  listEntities: () => req('/entities'),
  getEntity: (entityId) => req(`/entities/${entityId}`),
  getEntityGraph: (entityId) => req(`/entities/${entityId}/entity-graph`),
  getEntityPersona: (entityId) => req(`/entities/${entityId}/persona`),
  getKnowledgeStats: () => req('/knowledge/stats'),
  getKnowledgeControl: () => req('/knowledge/control'),
  getKnowledgeReadiness: () => req('/knowledge/readiness'),
  getKnowledgeDeliverySummary: (limit = 5, maxChars = 3000) => req(`/knowledge/delivery-summary?limit=${limit}&max_chars=${maxChars}`),
  getKnowledgeSources: () => req('/knowledge/sources'),
  setKnowledgeSources: (body) => req('/knowledge/sources', { method: 'POST', body }),
  probeKnowledgeSources: (body) => req('/knowledge/sources/probe', { method: 'POST', body }),
  searchKnowledge: (q, limit = 10) => req(`/knowledge/search?q=${encodeURIComponent(q)}&limit=${limit}`),
  getContentRegistryOverview: () => req('/content/registry'),
  getContentRegistryClasses: () => req('/content/registry/classes'),
  getContentRegistryDocument: (contentId) => req(`/content/registry/${encodeURIComponent(contentId)}`),
  getContentRegistryVersions: (contentId) => req(`/content/registry/${encodeURIComponent(contentId)}/versions`),
  syncContentRegistry: (body = {}) => req('/content/registry/sync', { method: 'POST', body }),
  saveContentRegistryDocument: (contentId, body) => req(`/content/registry/${encodeURIComponent(contentId)}`, { method: 'PUT', body }),
  archiveContentRegistryDocument: (contentId, body = {}) => req(`/content/registry/${encodeURIComponent(contentId)}/archive`, { method: 'POST', body }),
  restoreContentRegistryDocument: (contentId, body = {}) => req(`/content/registry/${encodeURIComponent(contentId)}/restore`, { method: 'POST', body }),
  getArtifactRegistryOverview: () => req('/artifact-registry/registry'),
  getArtifactRegistryClasses: () => req('/artifact-registry/registry/classes'),
  getArtifactRegistryRecord: (artifactId) => req(`/artifact-registry/registry/${encodeURIComponent(artifactId)}`),
  getArtifactRegistryVersions: (artifactId) => req(`/artifact-registry/registry/${encodeURIComponent(artifactId)}/versions`),
  syncArtifactRegistry: (body = {}) => req('/artifact-registry/registry/sync', { method: 'POST', body }),
  getReflectionArtifacts: () => req('/reflections'),
  getReflectionArtifact: (artifactId) => req(`/reflections/${encodeURIComponent(artifactId)}`),
  createReflectionArtifact: (body) => req('/reflections', { method: 'POST', body }),
  getReflectionCycleStatus: () => req('/reflections/cycles'),
  runReflectionCycles: (body = {}) => req('/reflections/cycles/run', { method: 'POST', body }),
  promoteReflectionArtifact: (artifactId, body = {}) => req(`/reflections/${encodeURIComponent(artifactId)}/promote`, { method: 'POST', body }),
  discardReflectionArtifact: (artifactId, body = {}) => req(`/reflections/${encodeURIComponent(artifactId)}/discard`, { method: 'POST', body }),
  escalateReflectionArtifact: (artifactId, body = {}) => req(`/reflections/${encodeURIComponent(artifactId)}/escalate`, { method: 'POST', body }),
  getSourceRegistryOverview: () => req('/source-registry/registry'),
  getSourceRegistryRecord: (sourceBlobId) => req(`/source-registry/registry/${encodeURIComponent(sourceBlobId)}`),
  getSourceRegistryVersions: (sourceBlobId) => req(`/source-registry/registry/${encodeURIComponent(sourceBlobId)}/versions`),
  getSourceRegistryDiff: (sourceBlobId, leftVersionId = null, rightVersionId = null) => {
    const params = new URLSearchParams()
    if (leftVersionId) params.set('left_version_id', leftVersionId)
    if (rightVersionId) params.set('right_version_id', rightVersionId)
    const query = params.toString()
    return req(`/source-registry/registry/${encodeURIComponent(sourceBlobId)}/diff${query ? `?${query}` : ''}`)
  },
  syncSourceRegistry: (body = {}) => req('/source-registry/registry/sync', { method: 'POST', body }),
  createSourceRegistryRecord: (body) => req('/source-registry/registry', { method: 'POST', body }),
  saveSourceRegistryRecord: (sourceBlobId, body) => req(`/source-registry/registry/${encodeURIComponent(sourceBlobId)}`, { method: 'PUT', body }),
  archiveSourceRegistryRecord: (sourceBlobId, body = {}) => req(`/source-registry/registry/${encodeURIComponent(sourceBlobId)}/archive`, { method: 'POST', body }),
  restoreSourceRegistryRecord: (sourceBlobId, body = {}) => req(`/source-registry/registry/${encodeURIComponent(sourceBlobId)}/restore`, { method: 'POST', body }),
  runSourceRegistryRecord: (sourceBlobId, body = {}) => req(`/source-registry/registry/${encodeURIComponent(sourceBlobId)}/run`, { method: 'POST', body }),
  getExecutableRegistryOverview: () => req('/executable-registry/registry'),
  getExecutableRegistryRecord: (toolId) => req(`/executable-registry/registry/${encodeURIComponent(toolId)}`),
  getExecutableRegistryVersions: (toolId) => req(`/executable-registry/registry/${encodeURIComponent(toolId)}/versions`),
  syncExecutableRegistry: (body = {}) => req('/executable-registry/registry/sync', { method: 'POST', body }),
  getTaskRegistryOverview: () => req('/task-registry/registry'),
  getTaskRegistryRecord: (taskName) => req(`/task-registry/registry/${encodeURIComponent(taskName)}`),
  getTaskRegistryVersions: (taskName) => req(`/task-registry/registry/${encodeURIComponent(taskName)}/versions`),
  syncTaskRegistry: (body = {}) => req('/task-registry/registry/sync', { method: 'POST', body }),
  saveTaskRegistryRecord: (taskName, body = {}) => req(`/task-registry/registry/${encodeURIComponent(taskName)}`, { method: 'PUT', body }),
  getRecentKnowledgeWorkspaces: (limit = 20) => api.gatewayV1.req(`/knowledge-workspaces/recent?limit=${limit}`),
  getKnowledgeWorkspace: (chatId) => api.gatewayV1.req(`/chats/${encodeURIComponent(chatId)}/knowledge-workspace`),
  getKnowledgeCategories: () => req('/knowledge/categories'),
  getKnowledgeDomainSpecs: () => req('/knowledge/domain-specs'),
  listKnowledgeQueue: () => req('/knowledge/queue'),
  addKnowledgeQueueTopic: (body) => req('/knowledge/queue', { method: 'POST', body }),
  removeKnowledgeQueueTopic: (topic) => req(`/knowledge/queue?topic=${encodeURIComponent(topic)}`, { method: 'DELETE' }),
  clearKnowledgeQueue: () => req('/knowledge/queue/all', { method: 'DELETE' }),
  setKnowledgeScheduleEnabled: (enabled) => req('/knowledge/schedule', { method: 'POST', body: { enabled } }),
  getConfig: () => req('/config'),
  getWorkspaceConfig: () => req('/config/workspace'),
  getRecentActivity: (limitRuns = 10, limitDecisions = 20, view = 'compact') =>
    req(`/activity/recent?limit_runs=${limitRuns}&limit_decisions=${limitDecisions}&view=${encodeURIComponent(view)}`),
  getActivityProjection: (params = {}) => req(`/activity/projection?${new URLSearchParams(params)}`),
  getSteeringEvents: (limit = 100) => req(`/steering/events?limit=${limit}`),
  getAuthorityConfig: () => req('/steering/authority-config'),
  getSteeringProfiles: () => req('/steering/profiles'),
  getSteeringProfile: (agentId) => req(`/steering/profiles/${encodeURIComponent(agentId)}`),
  getStatusDashboard: (hours = 24) => req(`/status/dashboard?hours=${hours}`),
  getStatusReports: (limit = 20) => req(`/status/reports?limit=${limit}`),
  getStatusReportBlob: async (reportRef) => {
    const headers = withAuthHeaders()
    const res = await fetch(`${API_BASE}/status/reports/file/${encodeURIComponent(reportRef)}`, { headers, credentials: 'include' })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    return await res.blob()
  },
  getMonitoringInsight: (hours = 24, limitRuns = 200, dagOnly = false) =>
    req(`/status/insight?hours=${hours}&limit_runs=${limitRuns}&dag_only=${dagOnly ? 'true' : 'false'}`),
  getEvalsSummary: () => req('/evals/summary'),
  getEvalsTrends: () => req('/evals/trends'),
  getAutonomy: () => req('/status/autonomy'),
  patchAutonomy: (payload) => req('/status/autonomy', { method: 'PATCH', body: payload }),
  listWorkflows: () => req('/workflows'),
  getWorkflow: (workflowId) => req(`/workflows/${encodeURIComponent(workflowId)}`),
  runAcceptanceChecks: (workflowId, body = {}) => req(`/workflows/${encodeURIComponent(workflowId)}/acceptance-checks`, { method: 'POST', body }),
  listScheduledJobs: () => req('/workflows/scheduled-jobs'),
  getScheduledJobDag: (jobId) => req(`/workflows/scheduled-jobs/${encodeURIComponent(jobId)}/dag`),
  saveScheduledJobDag: (jobId, dag) => req(`/workflows/scheduled-jobs/${encodeURIComponent(jobId)}/dag`, { method: 'PUT', body: { dag } }),
  triggerScheduledJob: (jobId, body = {}) => req(`/workflows/scheduled-jobs/${encodeURIComponent(jobId)}/run`, { method: 'POST', body }),
  listTemplates: () => req('/templates'),
  getTemplate: (templateId, goal = null) => req(`/templates/${encodeURIComponent(templateId)}${goal ? `?goal=${encodeURIComponent(goal)}` : ''}`),
  instantiateTemplate: (templateId, payload = {}) => req(`/templates/${encodeURIComponent(templateId)}/instantiate`, { method: 'POST', body: payload }),
  getFaultScenarios: () => req('/fault/scenarios'),
  runFaultScenario: (body) => req('/fault/run', { method: 'POST', body }),
  redactPreview: (payload) => req('/retention/redact-preview', { method: 'POST', body: payload }),
  purgeByRunId: (runId) => req('/retention/purge', { method: 'POST', body: { run_id: runId } }),
  getRetentionAudit: (limit = 50) => req(`/retention/audit?limit=${limit}`),
  getTrustMetrics: () => req('/proofs/trust-metrics'),
  getRecoverySummary: (staleMinutes = 30) => req(`/recovery/summary?stale_minutes=${staleMinutes}`),
  recordRecoveryAction: (body) => req('/recovery/actions', { method: 'POST', body }),
  seedFingerprintBranchesDemo: (body) => req('/fingerprint-branches/seed-demo', { method: 'POST', body }),
  getFingerprintBranches: (fingerprintId) => req(`/fingerprint-branches/${encodeURIComponent(fingerprintId)}/branches`),
  compareFingerprintBranches: (fingerprintId, body) => req(`/fingerprint-branches/${encodeURIComponent(fingerprintId)}/compare`, { method: 'POST', body }),
  reconcileFingerprintBranches: (fingerprintId, body) => req(`/fingerprint-branches/${encodeURIComponent(fingerprintId)}/reconcile`, { method: 'POST', body }),
  seedQuantumDemo: (body = {}) => req('/quantum/seed-demo', { method: 'POST', body }),
  getEntanglementGraph: () => req('/quantum/entanglement/graph'),
  getEntanglementPair: (pairId) => req(`/quantum/entanglement/pairs/${encodeURIComponent(pairId)}`),
  getNoiseProfiles: () => req('/quantum/noise/profiles'),
  getNoiseProfile: (entityId) => req(`/quantum/noise/profiles/${encodeURIComponent(entityId)}`),
  getSyndromeDashboard: () => req('/quantum/syndrome/dashboard'),
  getSpectrumSnapshot: () => req('/quantum/spectrum/snapshot'),
  getSpectrumEmitters: (limit = 20) => req(`/quantum/spectrum/emitters?limit=${limit}`),
  getSpectrumEmitter: (emitterId) => req(`/quantum/spectrum/emitters/${encodeURIComponent(emitterId)}`),
  seedSpectrumDemo: () => req('/quantum/spectrum/seed-demo', { method: 'POST', body: {} }),
  approveQuantumCorrection: (correctionId) => req(`/quantum/syndrome/corrections/${encodeURIComponent(correctionId)}/approve`, { method: 'POST', body: {} }),
  escalateQuantumCorrection: (correctionId, body = {}) =>
    req(`/quantum/syndrome/corrections/${encodeURIComponent(correctionId)}/escalate`, { method: 'POST', body }),
  rejectQuantumCorrection: (correctionId, body = {}) => req(`/quantum/syndrome/corrections/${encodeURIComponent(correctionId)}/reject`, { method: 'POST', body }),
  getFleetSnapshot: () => req('/fleet/snapshot'),
  seedFleetDemo: () => req('/fleet/seed-demo', { method: 'POST', body: {} }),
  runFleetMeshProof: () => req('/fleet/mesh/cross-host-proof', { method: 'POST', body: {} }),
  haltFleetZone: (zoneId, body = {}) => req(`/fleet/zones/${encodeURIComponent(zoneId)}/halt`, { method: 'POST', body }),
  getConsentStatus: (subjectId) => req(`/consent/status?subject_id=${encodeURIComponent(subjectId)}`),
  grantConsent: (body) => req('/consent/grant', { method: 'POST', body }),
  revokeConsent: (body) => req('/consent/revoke', { method: 'POST', body }),
  getConsentLedger: ({ offset = 0, limit = 50 } = {}) => req(`/consent/ledger?offset=${offset}&limit=${limit}`),
  seedConsentDemo: () => req('/consent/seed-demo', { method: 'POST', body: {} }),
  getUserRecognitionStatus: (subjectId) => req(`/user-recognition/status?subject_id=${encodeURIComponent(subjectId)}`),
  analyzeUserRecognition: (body) => req('/user-recognition/analyze', { method: 'POST', body }),
  getUserRecognitionTemplates: () => req('/user-recognition/templates'),
  seedUserRecognitionDemo: () => req('/user-recognition/seed-demo', { method: 'POST', body: {} }),
  proofReconstruction: {
    seedDemo: () => req('/proof-reconstruction/seed-demo', { method: 'POST', body: {} }),
    getDashboard: () => req('/proof-reconstruction/dashboard'),
    reconstruct: (body) => req('/proof-reconstruction/reconstruct', { method: 'POST', body }),
  },
  seedPhysicalDemo: (body = {}) => req('/physical/seed-demo', { method: 'POST', body }),
  getPhysicalAgents: () => req('/physical/agents'),
  getPhysicalAgent: (robotId) => req(`/physical/agents/${encodeURIComponent(robotId)}`),
  haltPhysicalAgent: (robotId, body = {}) => req(`/physical/agents/${encodeURIComponent(robotId)}/halt`, { method: 'POST', body }),
  resumePhysicalAgent: (robotId) => req(`/physical/agents/${encodeURIComponent(robotId)}/resume`, { method: 'POST', body }),
  evaluatePhysicalCommand: (robotId, body = {}) => req(`/physical/agents/${encodeURIComponent(robotId)}/evaluate`, { method: 'POST', body }),
  seedAdvancedModelsDemo: (body = {}) => req('/advanced-models/seed-demo', { method: 'POST', body }),
  getAdvancedModelsDashboard: () => req('/advanced-models/dashboard'),
  getAdvancedModelDetail: (modelId) => req(`/advanced-models/models/${encodeURIComponent(modelId)}`),
  syncLearningCorpus: () => req('/learning/sync', { method: 'POST', body: {} }),
  getLearningTelemetry: () => req('/learning/telemetry'),
  getLearningRelabelQueue: () => req('/learning/relabel-queue'),
  postLearningRelabel: (signalId, body) => req(`/learning/relabel/${encodeURIComponent(signalId)}`, { method: 'POST', body }),
  getLearningTrackRecords: () => req('/learning/track-records'),
  getLearningTrackRecord: (entityId) => req(`/learning/track-records/${encodeURIComponent(entityId)}`),
  runLearningShadowFeedback: () => req('/learning/shadow/run', { method: 'POST', body: {} }),
  getLearningShadowLedger: (path) => req(`/learning/shadow/ledger${path ? `?path=${encodeURIComponent(path)}` : ''}`),
  getLearningActivity: () => req('/learning/activity'),
  getLearningLivePriors: () => req('/learning/live/priors'),
  unfreezeLearningPath: (pathName) => req(`/learning/live/unfreeze-path/${encodeURIComponent(pathName)}`, { method: 'POST', body: {} }),
  unfreezeLearningParameter: (parameter) => req(`/learning/live/unfreeze-parameter/${encodeURIComponent(parameter)}`, { method: 'POST', body: {} }),
  resolveLearningIncident: (incidentId) => req(`/learning/incidents/${encodeURIComponent(incidentId)}/resolve`, { method: 'POST', body: {} }),
  getMediatorCatalog: () => req('/mediators/catalog'),
  probeMediator: (body) => req('/mediators/probe', { method: 'POST', body }),
  getQuantum2ActivationState: () => req('/quantum2/activation/state'),
  getQuantum2ActivationHistory: () => req('/quantum2/activation/history'),
  getQuantum2Divergence: (component) => req(`/quantum2/activation/divergence/${encodeURIComponent(component)}`),
  enableQuantum2Shadow: (component, body = {}) => req(`/quantum2/activation/modules/${encodeURIComponent(component)}/enable-shadow`, { method: 'POST', body }),
  promoteQuantum2Live: (component, body = {}) => req(`/quantum2/activation/modules/${encodeURIComponent(component)}/promote-live`, { method: 'POST', body }),
  disableQuantum2Module: (component, body = {}) => req(`/quantum2/activation/modules/${encodeURIComponent(component)}/disable`, { method: 'POST', body }),
  runQuantum2ShadowWorkloads: () => req('/quantum2/activation/run-shadow-workloads', { method: 'POST', body: {} }),
  getQuantum2GoNoGo: () => req('/quantum2/activation/go-no-go'),
  flipQuantum2CodecLive: (body = {}) => req('/quantum2/activation/flip-codec-live', { method: 'POST', body }),
  flipQuantum2ShadowFirstLive: (body = {}) => req('/quantum2/activation/flip-shadow-first-live', { method: 'POST', body }),
  getQuantum2LiveSummary: () => req('/quantum2/activation/live-summary'),
  runQuantum2ProductionValidation: () => req('/quantum2/validation/run', { method: 'POST', body: {} }),
  getQuantum2ValidationStatus: () => req('/quantum2/validation/status'),
  getQuantum2DivergenceReport: () => req('/quantum2/validation/divergence-report'),
  getLearningControlGroupStats: () => req('/learning/control-group/stats'),
  getLearningLineage: (entityId) => req(`/learning/lineage/${encodeURIComponent(entityId)}`),
  getEvolutionProposals: (entityId) => req(`/learning/evolution/proposals${entityId ? `?entity_id=${encodeURIComponent(entityId)}` : ''}`),
  approveEvolutionProposal: (proposalId, body) => req(`/learning/evolution/proposals/${encodeURIComponent(proposalId)}/approve`, { method: 'POST', body }),
  rollbackEvolution: (entityId) => req(`/learning/evolution/rollback/${encodeURIComponent(entityId)}`, { method: 'POST', body: {} }),
  search: (q = '', limit = 30) => req(`/search?${new URLSearchParams({ q, limit: String(limit) })}`),
  explainBlock: (workItemId) => req(`/operator/explain-block?work_item_id=${encodeURIComponent(workItemId)}`),
  getOperatorStatusOverview: () => req('/operator/status-overview'),
  getOperatorRunDetail: (runId) => req(`/operator/run-detail/${encodeURIComponent(runId)}`),
  getIncidentQueue: () => req('/operator/incident-queue'),
  getApprovalsQueue: (params = {}) => req(`/operator/approvals?${new URLSearchParams(params)}`),
  getEntityApprovalRequest: (approvalId) => req(`/approvals-entity/${encodeURIComponent(approvalId)}`),
  approveEntityApprovalRequest: (approvalId, body = {}) => req(`/approvals-entity/${encodeURIComponent(approvalId)}/approve`, { method: 'POST', body }),
  rejectEntityApprovalRequest: (approvalId, body = {}) => req(`/approvals-entity/${encodeURIComponent(approvalId)}/reject`, { method: 'POST', body }),
  requestEditEntityApprovalRequest: (approvalId, body = {}) => req(`/approvals-entity/${encodeURIComponent(approvalId)}/request-edit`, { method: 'POST', body }),
  refreshEntityApprovalRequest: (approvalId, body = {}) => req(`/approvals-entity/${encodeURIComponent(approvalId)}/refresh`, { method: 'POST', body }),
  getWorkflowDedup: (workflowId, limit = 100) =>
    req(`/workflows/${encodeURIComponent(workflowId)}/dedup?limit=${limit}`),
  listKeystoreAccounts: (platform = null) =>
    req(`/keystore/accounts${platform ? `?platform=${encodeURIComponent(platform)}` : ''}`),
  getKeystoreAccountOverview: (socialAccountId) =>
    req(`/keystore/accounts/${encodeURIComponent(socialAccountId)}/overview`),
  facebookLogin: (body) => req('/social-entity/facebook/login', { method: 'POST', body }),
  facebookReadNotifications: (body) => req('/social-entity/facebook/read-notifications', { method: 'POST', body }),
  replayIncidentQueue: (incidentId, shadow = true) => req('/operator/replay-incident', { method: 'POST', body: { incident_id: incidentId, shadow } }),
  pauseWorkflow: (workflowId) => req('/operator/pause', { method: 'POST', body: { workflow_id: workflowId } }),
  resumeWorkflow: (workflowId) => req('/operator/resume', { method: 'POST', body: { workflow_id: workflowId } }),
  rollbackWorkflow: (workflowId) => req('/operator/rollback', { method: 'POST', body: { workflow_id: workflowId } }),
  exportWeeklyReport: () => req('/operator/export-weekly-report', { method: 'POST' }),
  evaluateApproval: (workflowId, actionSummary = {}) => req('/operator/approval/evaluate', { method: 'POST', body: { workflow_id: workflowId, action_summary: actionSummary } }),
  getSlaDaily: (traces) => req(`/sla/daily${traces != null ? `?traces=${encodeURIComponent(JSON.stringify(traces))}` : ''}`),
  getSlaWeekly: (traces) => req(`/sla/weekly${traces != null ? `?traces=${encodeURIComponent(JSON.stringify(traces))}` : ''}`),
  getFailureClasses: () => req('/reliability/failure-classes'),
  getRetryPolicy: (className = null) => req(`/reliability/retry-policy${className ? `?class_name=${encodeURIComponent(className)}` : ''}`),
  getBreakers: () => req('/reliability/breakers'),
  resetBreaker: (workflowId, destination = null) => req('/reliability/breakers/reset', { method: 'POST', body: { workflow_id: workflowId, destination } }),
  getReliabilityIncidentQueue: (taskId = null) => req(`/reliability/incident-queue${taskId ? `?task_id=${encodeURIComponent(taskId)}` : ''}`),
  getBudgetSummary: (recentRuns = 200) => req(`/reliability/budget-summary?recent_runs=${recentRuns}`),
  getConflicts: () => req('/ownership/conflicts'),
  getHandoffs: (limit = 100) => req(`/ownership/handoffs?limit=${limit}`),
  getDelegationSummary: (runId) => req(`/runs/${runId}/delegation/summary`),
  getDelegationGraph: (runId) => req(`/runs/${runId}/delegation/graph`),
  getDelegationAnomalies: (runId) => req(`/runs/${runId}/delegation/anomalies`),
  getIncidentReport: (runId) => req(`/runs/${runId}/incident-report`),
  getIncidentReportMdUrl: (runId) => `${API_BASE}/runs/${runId}/incident-report.md`,
  listPersonas: () => req('/personas'),
  getOperationalPersonas: () => req('/personas/operational'),
  getOperationalAgencyControl: (platform, operationalAgentId) =>
    req(`/personas/operational/${encodeURIComponent(platform)}/${encodeURIComponent(operationalAgentId)}/agency-control`),
  patchOperationalAgencyControl: (platform, operationalAgentId, body) =>
    req(`/personas/operational/${encodeURIComponent(platform)}/${encodeURIComponent(operationalAgentId)}/agency-control`, { method: 'PATCH', body }),
  acknowledgeOperationalContinuityRecovery: (platform, operationalAgentId, body = {}) =>
    req(`/personas/operational/${encodeURIComponent(platform)}/${encodeURIComponent(operationalAgentId)}/continuity-recovery/ack`, { method: 'POST', body }),
  recordOperationalPostRebuild: (platform, operationalAgentId, body = {}) =>
    req(`/personas/operational/${encodeURIComponent(platform)}/${encodeURIComponent(operationalAgentId)}/post-rebuild/record`, { method: 'POST', body }),
  verifyOperationalPostRebuild: (platform, operationalAgentId, body = {}) =>
    req(`/personas/operational/${encodeURIComponent(platform)}/${encodeURIComponent(operationalAgentId)}/post-rebuild/verify`, { method: 'POST', body }),
  approveOperationalResumeCheckpoint: (platform, operationalAgentId, body = {}) =>
    req(`/personas/operational/${encodeURIComponent(platform)}/${encodeURIComponent(operationalAgentId)}/resume-checkpoint`, { method: 'POST', body }),
  getPersona: (fingerprintId, skinId = null) =>
    req(`/personas/${encodeURIComponent(fingerprintId)}${skinId ? `?skin_id=${encodeURIComponent(skinId)}` : ''}`),
  exportPersonaUrl: (fingerprintId, skinId = null) => {
    const params = new URLSearchParams()
    if (skinId) params.set('skin_id', skinId)
    const suffix = params.toString()
    return `${API_BASE}/personas/export/${encodeURIComponent(fingerprintId)}${suffix ? `?${suffix}` : ''}`
  },
  importPersona: (body) => req('/personas/import', { method: 'POST', body }),
  previewPersonaNaturalness: (body) => req('/personas/naturalness/preview', { method: 'POST', body }),
  evaluatePersonaNaturalness: (body) => req('/personas/naturalness/evaluate', { method: 'POST', body }),
  getPersonaNaturalnessHistory: (params = {}) => req(`/personas/naturalness/history?${new URLSearchParams(params)}`),
  getPersonaNaturalnessSummary: (params = {}) => req(`/personas/naturalness/summary?${new URLSearchParams(params)}`),
  getPersonaNaturalnessSwarm: (swarmRunId, params = {}) =>
    req(`/personas/naturalness/swarms/${encodeURIComponent(swarmRunId)}?${new URLSearchParams(params)}`),
  getPersonaAutonomyHistory: (params = {}) => req(`/personas/autonomy/history?${new URLSearchParams(params)}`),
  getPersonaAutonomySummary: (params = {}) => req(`/personas/autonomy/summary?${new URLSearchParams(params)}`),
  getPersonaAutonomySwarm: (swarmRunId, params = {}) =>
    req(`/personas/autonomy/swarms/${encodeURIComponent(swarmRunId)}?${new URLSearchParams(params)}`),
  governance: {
    getDashboard: () => req('/governance/dashboard'),
    getContracts: () => req('/governance/contracts'),
    listReceipts: (params = {}) => req(`/governance/receipts?${new URLSearchParams(params)}`),
    getReceipt: (receiptId) => req(`/governance/receipts/${encodeURIComponent(receiptId)}`),
    verifyReceipt: (receiptId) => req(`/governance/receipts/${encodeURIComponent(receiptId)}/verify`, { method: 'POST' }),
    exportReceipt: (receiptId) => req(`/governance/receipts/${encodeURIComponent(receiptId)}/export`),
    listPolicies: () => req('/governance/policies'),
    createPolicyVersion: (body) => req('/governance/policies/versions', { method: 'POST', body }),
    getPolicyVersion: (versionId) => req(`/governance/policies/versions/${encodeURIComponent(versionId)}`),
    simulatePolicyVersion: (versionId, body) => req(`/governance/policies/versions/${encodeURIComponent(versionId)}/simulate`, { method: 'POST', body }),
    activatePolicyVersion: (versionId, actorId = null) => req(`/governance/policies/versions/${encodeURIComponent(versionId)}/activate${actorId ? `?actor_id=${encodeURIComponent(actorId)}` : ''}`, { method: 'POST' }),
    rollbackPolicy: (policyKey, actorId = null) => req(`/governance/policies/${encodeURIComponent(policyKey)}/rollback${actorId ? `?actor_id=${encodeURIComponent(actorId)}` : ''}`, { method: 'POST' }),
    addPolicyFeedback: (body) => req('/governance/policies/feedback', { method: 'POST', body }),
    listConstitutionalRoots: () => req('/governance/constitutional-roots'),
    upsertConstitutionalRoot: (body) => req('/governance/constitutional-roots', { method: 'POST', body }),
    getConstitutionalRoot: (rootId) => req(`/governance/constitutional-roots/${encodeURIComponent(rootId)}`),
    addCheckpoint: (rootId, body) => req(`/governance/constitutional-roots/${encodeURIComponent(rootId)}/checkpoints`, { method: 'POST', body }),
    addDrift: (rootId, body) => req(`/governance/constitutional-roots/${encodeURIComponent(rootId)}/drift`, { method: 'POST', body }),
    getDriftReview: (params = {}) => req(`/governance/drift?${new URLSearchParams(params)}`),
    listBenchmarkSets: () => req('/governance/gate/benchmark-sets'),
    createBenchmarkSet: (body) => req('/governance/gate/benchmark-sets', { method: 'POST', body }),
    createBenchmarkRun: (body) => req('/governance/gate/benchmark-runs', { method: 'POST', body }),
    evaluateBenchmarkRun: (body) => req('/governance/gate/evaluate', { method: 'POST', body }),
    listEvaluations: (params = {}) => req(`/governance/gate/evaluations?${new URLSearchParams(params)}`),
    createReleaseVerdict: (body) => req('/governance/gate/release-verdicts', { method: 'POST', body }),
    checkGate: (workflowFamily, params = {}) => req(`/governance/gate/check/${encodeURIComponent(workflowFamily)}?${new URLSearchParams(params)}`),
    getDemoPath: (workflowFamily) => req(`/governance/demo-path/${encodeURIComponent(workflowFamily)}`),
    syncResearchWorkspace: (chatId, body = {}) => req(`/governance/research/workspaces/${encodeURIComponent(chatId)}/sync`, { method: 'POST', body }),
    listResearchRuns: (params = {}) => req(`/governance/research/runs?${new URLSearchParams(params)}`),
    getResearchRun: (researchRunId) => req(`/governance/research/runs/${encodeURIComponent(researchRunId)}`),
  },
  proofs: {
    base: GATEWAY_V1_BASE,
    hasProofAccess: () => browserSessionHasRole(['superadmin']),
    hasAdminKey: () => browserSessionHasRole(['superadmin']),
    async req(path, { method = 'GET', body = null } = {}) {
      const headers = withAuthHeaders({}, { apiKey: '', adminKey: getAdminKey() })
      if (body !== null) headers['Content-Type'] = 'application/json'
      const res = await fetch(`${GATEWAY_V1_BASE}/admin/proofs${path}`, { method, headers, body: body ? JSON.stringify(body) : null, credentials: 'include' })
      const ct = res.headers.get('content-type') || ''
      if (!res.ok) {
        const txt = ct.includes('application/json') ? JSON.stringify(await res.json()) : await res.text()
        throw new Error(`HTTP ${res.status}: ${txt}`)
      }
      return ct.includes('application/json') ? await res.json() : await res.text()
    },
    getIndex: () => api.proofs.req('/index'),
    run: (body) => api.proofs.req('/run', { method: 'POST', body }),
    getRunStatus: (runId) => api.proofs.req(`/runs/${encodeURIComponent(runId)}`),
    getRunArtifacts: (runId) => api.proofs.req(`/runs/${encodeURIComponent(runId)}/artifacts`),
    getRunFileUrl: (runId, filePath) =>
      `${GATEWAY_V1_BASE}/admin/proofs/runs/${encodeURIComponent(runId)}/files/${encodeURIComponent(filePath)}`,
    getRunLogsUrl: (runId) => `${GATEWAY_V1_BASE}/admin/proofs/runs/${encodeURIComponent(runId)}/logs`,
    cancelRun: (runId) => api.proofs.req(`/runs/${encodeURIComponent(runId)}/cancel`, { method: 'POST' }),
  },
  // Pack 13: Gateway admin (superadmin) — Bearer admin key only
  gatewayAdmin: {
    async req(path, { method = 'GET', body = null } = {}) {
      const headers = withAuthHeaders({}, { apiKey: '', adminKey: getAdminKey() })
      if (body !== null) headers['Content-Type'] = 'application/json'
      const res = await fetch(`${GATEWAY_V1_BASE}${path}`, { method, headers, body: body ? JSON.stringify(body) : null, credentials: 'include' })
      const ct = res.headers.get('content-type') || ''
      if (!res.ok) {
        const txt = ct.includes('application/json') ? JSON.stringify(await res.json()) : await res.text()
        throw new Error(`HTTP ${res.status}: ${txt}`)
      }
      return ct.includes('application/json') ? await res.json() : await res.text()
    },
    listTenants: (search, limit, offset) =>
      api.gatewayAdmin.req(`/admin/tenants?${new URLSearchParams({ ...(search && { search }), ...(limit != null && { limit }), ...(offset != null && { offset }) })}`),
    createTenant: (body) => api.gatewayAdmin.req('/admin/tenants', { method: 'POST', body }),
    getTenant: (tenantId) => api.gatewayAdmin.req(`/admin/tenants/${encodeURIComponent(tenantId)}`),
    updateTenant: (tenantId, body) => api.gatewayAdmin.req(`/admin/tenants/${encodeURIComponent(tenantId)}`, { method: 'PATCH', body }),
    addDomain: (tenantId, body) => api.gatewayAdmin.req(`/admin/tenants/${encodeURIComponent(tenantId)}/domains`, { method: 'POST', body }),
    removeDomain: (tenantId, hostname) => api.gatewayAdmin.req(`/admin/tenants/${encodeURIComponent(tenantId)}/domains/${encodeURIComponent(hostname)}`, { method: 'DELETE' }),
    getUsage: (tenantId) => api.gatewayAdmin.req(`/admin/tenants/${encodeURIComponent(tenantId)}/usage`),
    createKey: (tenantId) => api.gatewayAdmin.req(`/admin/tenants/${encodeURIComponent(tenantId)}/keys`, { method: 'POST' }),
    exportTenant: (tenantId) => api.gatewayAdmin.req(`/admin/tenants/${encodeURIComponent(tenantId)}/export`, { method: 'POST' }),
    deleteTenant: (tenantId, confirmTenantId) => api.gatewayAdmin.req(`/admin/tenants/${encodeURIComponent(tenantId)}/delete`, { method: 'POST', body: { confirm_tenant_id: confirmTenantId } }),
    impersonate: (body) => api.gatewayAdmin.req('/admin/impersonate', { method: 'POST', body }),
  },
  // Pack 13: Gateway v1 tenant-scoped (operator/tenant_admin key for principals, tenant settings)
  gatewayV1: {
    async req(path, { method = 'GET', body = null } = {}) {
      const headers = withAuthHeaders()
      if (body !== null) headers['Content-Type'] = 'application/json'
      const res = await fetch(`${GATEWAY_V1_BASE}${path}`, { method, headers, body: body ? JSON.stringify(body) : null, credentials: 'include' })
      const ct = res.headers.get('content-type') || ''
      if (!res.ok) {
        const txt = ct.includes('application/json') ? JSON.stringify(await res.json()) : await res.text()
        throw new Error(`HTTP ${res.status}: ${txt}`)
      }
      return ct.includes('application/json') ? await res.json() : await res.text()
    },
    listPrincipals: (includeDisabled = false) =>
      api.gatewayV1.req(`/principals${includeDisabled ? '?include_disabled=true' : ''}`),
    getPrincipal: (id) => api.gatewayV1.req(`/principals/${encodeURIComponent(id)}`),
    createPrincipal: (body) => api.gatewayV1.req('/principals', { method: 'POST', body }),
    patchPrincipalAvailability: (id, body) =>
      api.gatewayV1.req(`/principals/${encodeURIComponent(id)}/availability`, { method: 'PATCH', body }),
    getTenantMe: () => api.gatewayV1.req('/tenants/me'),
    getTenantMeSettings: () => api.gatewayV1.req('/tenants/me/settings'),
    patchTenantMeSettings: (body) => api.gatewayV1.req('/tenants/me/settings', { method: 'PATCH', body }),
    // Pack 17: retention policy and export
    getTenantRetention: () => api.gatewayV1.req('/tenant/retention'),
    patchTenantRetention: (body) => api.gatewayV1.req('/tenant/retention', { method: 'PATCH', body }),
    async downloadTenantExport() {
      const headers = withAuthHeaders()
      const res = await fetch(`${GATEWAY_V1_BASE}/tenant/export`, { method: 'POST', headers, credentials: 'include' })
      if (!res.ok) throw new Error(`Export failed: ${res.status}`)
      const blob = await res.blob()
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = `tenant_export_${new Date().toISOString().slice(0, 10)}.zip`
      a.click()
      URL.revokeObjectURL(a.href)
    },
    // Pack 25: timeline and evidence
    getTimeline: (params = {}) => api.gatewayV1.req(`/analytics/timeline?${new URLSearchParams(params)}`),
    getEvidence: (params = {}) => api.gatewayV1.req(`/analytics/evidence?${new URLSearchParams(params)}`),
    getReplay: (runId) => api.gatewayV1.req(`/analytics/replay?run_id=${encodeURIComponent(runId)}`),
    getSystemStatus: () => api.gatewayV1.req('/system/status'),
    getSystemVersion: () => api.gatewayV1.req('/system/version'),
    getTenantAudit: (params = {}) => api.gatewayV1.req(`/tenant/audit?${new URLSearchParams(params)}`),
    getAdminAudit: (params = {}) => api.gatewayAdmin.req(`/admin/audit?${new URLSearchParams(params)}`),
    notificationsStreamUrl: () => `${GATEWAY_V1_BASE}/stream/notifications`,
  },
  agent0: {
    status: () => req('/agent0/status'),
    worldState: () => req('/agent0/world-state'),
    events: (params = {}) => req(`/agent0/events?${new URLSearchParams(params)}`),
    proposals: () => req('/agent0/proposals'),
    governance: () => req('/agent0/governance'),
    arousal: () => req('/agent0/arousal'),
    recovery: () => req('/agent0/recovery'),
    execution: () => req('/agent0/execution'),
    maintenance: () => req('/agent0/maintenance'),
    memory: () => req('/agent0/memory'),
    proofs: () => req('/agent0/proofs'),
    subsystems: () => req('/agent0/subsystems'),
    receipts: (params = {}) => req(`/agent0/receipts?${new URLSearchParams(params)}`),
    pause: (body) => req('/agent0/pause', { method: 'POST', body }),
    resume: (body) => req('/agent0/resume', { method: 'POST', body }),
    panic: (body) => req('/agent0/panic', { method: 'POST', body }),
    requestReplay: (body) => req('/agent0/request-replay', { method: 'POST', body }),
    requestRecovery: (body) => req('/agent0/request-recovery', { method: 'POST', body }),
  },
  auth: {
    getConfig: async () => {
      const res = await fetch(`${GATEWAY_V1_BASE}/auth/config`, { credentials: 'include' })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      return res.json()
    },
    getMe: async () => {
      const res = await fetch(`${GATEWAY_V1_BASE}/auth/me`, { credentials: 'include' })
      if (res.status === 401) return null
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setBrowserSession(data)
      return data
    },
    demoLogin: async () => {
      const res = await fetch(`${GATEWAY_V1_BASE}/auth/demo/login`, {
        method: 'POST',
        credentials: 'include',
      })
      const ct = res.headers.get('content-type') || ''
      if (!res.ok) {
        const txt = ct.includes('application/json') ? JSON.stringify(await res.json()) : await res.text()
        throw new Error(`HTTP ${res.status}: ${txt}`)
      }
      const data = ct.includes('application/json') ? await res.json() : null
      setBrowserSession(data)
      return data
    },
    logout: async () => {
      await fetch(`${GATEWAY_V1_BASE}/auth/logout`, { method: 'POST', credentials: 'include' })
      clearBrowserSession()
    },
    oidcLogout: (frontendRedirectUri) => {
      clearBrowserSession()
      window.location.assign(`${GATEWAY_V1_BASE}/auth/oidc/logout?frontend_redirect_uri=${encodeURIComponent(frontendRedirectUri)}`)
    },
  },
}
