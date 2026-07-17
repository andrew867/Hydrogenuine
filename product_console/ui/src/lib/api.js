import { getProductApiKey } from './auth.js'

const PRODUCT_API_BASE = import.meta.env.VITE_PRODUCT_API_BASE || 'http://localhost:8080/api/product/v1'

async function productReq(path, { method = 'GET', body = null } = {}) {
  const headers = {}
  const devKey = getProductApiKey()
  if (devKey) headers.Authorization = `Bearer ${devKey}`
  if (body !== null) headers['Content-Type'] = 'application/json'
  const res = await fetch(`${PRODUCT_API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : null,
    credentials: 'include',
  })
  const ct = res.headers.get('content-type') || ''
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}: ${ct.includes('application/json') ? JSON.stringify(await res.json()) : await res.text()}`)
  }
  return ct.includes('application/json') ? await res.json() : await res.text()
}

export const api = {
  product: {
    req: productReq,
    getHealth: () => productReq('/health'),
    getDemoConfig: () => productReq('/config/demo'),
    listWorkflows: (params = {}) => productReq(`/workflows?${new URLSearchParams(params)}`),
    getWorkflow: (id) => productReq(`/workflows/${encodeURIComponent(id)}`),
    listWorkflowRuns: (id, params = {}) => productReq(`/workflows/${encodeURIComponent(id)}/runs?${new URLSearchParams(params)}`),
    listRuns: (params = {}) => productReq(`/runs?${new URLSearchParams(params)}`),
    getRun: (runId) => productReq(`/runs/${encodeURIComponent(runId)}`),
    listRunArtifacts: (runId) => productReq(`/runs/${encodeURIComponent(runId)}/artifacts`),
    getAuditReport: (runId) => productReq(`/runs/${encodeURIComponent(runId)}/audit-report`),
    listApprovals: (params = {}) => productReq(`/approvals?${new URLSearchParams(params)}`),
    getApproval: (id) => productReq(`/approvals/${encodeURIComponent(id)}`),
    listDeadletters: (params = {}) => productReq(`/incidents?${new URLSearchParams(params)}`),
    getDeadletter: (id) => productReq(`/incidents/${encodeURIComponent(id)}`),
    getPoliciesBlacklist: () => productReq('/policies/blacklist'),
    getMetricsSummary: (period = 'daily') => productReq(`/metrics/summary?period=${encodeURIComponent(period)}`),
    getMetricsReports: (limit = 20) => productReq(`/metrics/reports?limit=${limit}`),
    getMetricsReportBlob: async (reportRef) => {
      const headers = {}
      const devKey = getProductApiKey()
      if (devKey) headers.Authorization = `Bearer ${devKey}`
      const res = await fetch(`${PRODUCT_API_BASE}/metrics/reports/file/${encodeURIComponent(reportRef)}`, { headers, credentials: 'include' })
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`)
      return await res.blob()
    },
    triggerWorkflowRun: (wfId, body) => productReq(`/workflows/${encodeURIComponent(wfId)}/run`, { method: 'POST', body }),
    replayRun: (runId, body = {}) => productReq(`/runs/${encodeURIComponent(runId)}/replay`, { method: 'POST', body }),
    rollbackRun: (runId, body = {}) => productReq(`/runs/${encodeURIComponent(runId)}/rollback`, { method: 'POST', body }),
    pauseWorkflow: (wfId) => productReq(`/workflows/${encodeURIComponent(wfId)}/pause`, { method: 'POST' }),
    resumeWorkflow: (wfId) => productReq(`/workflows/${encodeURIComponent(wfId)}/resume`, { method: 'POST' }),
    overrideApproval: (id, body) => productReq(`/approvals/${encodeURIComponent(id)}/override`, { method: 'POST', body }),
    replayIncident: (id, body = { shadow: true }) =>
      productReq(`/incidents/${encodeURIComponent(id)}/replay`, { method: 'POST', body }),
    downloadRunArtifact: async (runId, name) => {
      const headers = {}
      const devKey = getProductApiKey()
      if (devKey) headers.Authorization = `Bearer ${devKey}`
      const res = await fetch(
        `${PRODUCT_API_BASE}/runs/${encodeURIComponent(runId)}/artifacts/download?${new URLSearchParams({ name })}`,
        { headers, credentials: 'include' },
      )
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`)
      return await res.blob()
    },
    listTemplates: () => productReq('/templates'),
    instantiateTemplate: (templateId, payload = {}) =>
      productReq(`/templates/${encodeURIComponent(templateId)}/instantiate`, { method: 'POST', body: payload }),
  },
}
