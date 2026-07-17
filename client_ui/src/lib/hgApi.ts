/**
 * HG API client — uses /v1 contract paths.
 * Each method uses a key class: operator (tenant-scoped), admin (admin endpoints), service (explicit).
 * Configure NEXT_PUBLIC_HG_API_BASE; optional NEXT_PUBLIC_HG_SSE_URL, NEXT_PUBLIC_HG_WS_URL.
 */

import { hgFetch, hgFetchBlob } from "@/lib/http";
import { env } from "@/lib/env";
import type { ActivityProjection, ApprovalItem, ChatSummary, Citation, Document, DocumentChunk, EntityApprovalItem, ExportResult, HgAgent, HgMessage, KeystoreAccountItem, KnowledgeWorkspace, MessageProvenance, PlanPreview, Principal, SourceEvidence, StepupChallenge, StepupEnrollResult, StepupStatus, StepupVerifyResult, SwarmRunRequest, SwarmRunResponse, SwarmWorkspace, SwarmWorkspaceChat, TenantInfo, TenantUsage, UiBrand } from "@/types/hg";

function mapChat(c: {
  chat_id: string;
  title: string;
  updated_at: string;
  archived_at?: string | null;
  archive_reason?: string | null;
  deleted_at?: string | null;
  delete_reason?: string | null;
  restore_deadline_at?: string | null;
  fingerprint_id?: string | null;
  swarm_run_id?: string | null;
  swarm_role?: string | null;
  skin_id?: string | null;
}): ChatSummary {
  return {
    id: c.chat_id,
    title: c.title,
    updatedAt: c.updated_at,
    ...(c.archived_at != null && c.archived_at !== "" && { archivedAt: c.archived_at }),
    ...(c.archive_reason != null && c.archive_reason !== "" && { archiveReason: c.archive_reason }),
    ...(c.deleted_at != null && c.deleted_at !== "" && { deletedAt: c.deleted_at }),
    ...(c.delete_reason != null && c.delete_reason !== "" && { deleteReason: c.delete_reason }),
    ...(c.restore_deadline_at != null && c.restore_deadline_at !== "" && { restoreDeadlineAt: c.restore_deadline_at }),
    ...(c.fingerprint_id != null && c.fingerprint_id !== "" && { fingerprintId: c.fingerprint_id }),
    ...(c.swarm_run_id != null && c.swarm_run_id !== "" && { swarmRunId: c.swarm_run_id }),
    ...(c.swarm_role != null && c.swarm_role !== "" && { swarmRole: c.swarm_role }),
    ...(c.skin_id != null && c.skin_id !== "" && { skinId: c.skin_id }),
  };
}

function mapSwarmWorkspaceChat(c: {
  chat_id: string;
  title: string;
  updated_at: string;
  fingerprint_id?: string | null;
  skin_id?: string | null;
  swarm_run_id?: string | null;
  swarm_role?: string | null;
  message_count?: number;
  latest_role?: string | null;
  latest_text?: string | null;
  status: "completed" | "active" | "queued" | "error";
}): SwarmWorkspaceChat {
  return {
    ...mapChat(c),
    messageCount: Number(c.message_count ?? 0),
    latestRole: c.latest_role ?? null,
    latestText: c.latest_text ?? "",
    status: c.status,
  };
}

function mapMessage(m: {
  message_id: string;
  chat_id: string;
  role: string;
  created_at: string;
  content: string;
  agent_id?: string;
  tool_name?: string;
  tool_payload?: unknown;
  tool_result?: unknown;
  approvals_required?: boolean;
  provenance?: HgMessage["provenance"];
  citations?: Citation[];
  sources?: SourceEvidence[];
  sourceEvidence?: SourceEvidence[];
}): HgMessage {
  const msg: HgMessage = {
    id: m.message_id,
    chatId: m.chat_id,
    role: m.role as HgMessage["role"],
    createdAt: m.created_at,
    content: m.content,
  };
  if (m.tool_name) {
    msg.tool = {
      name: m.tool_name,
      status: "ok",
      ...(m.content ? { detail: m.content } : {}),
    };
  }
  if (Array.isArray(m.citations) && m.citations.length) msg.citations = m.citations;
  const directSources = Array.isArray(m.sources) ? m.sources : Array.isArray(m.sourceEvidence) ? m.sourceEvidence : [];
  if (directSources.length) msg.sourceEvidence = mergeUniqueByUrl(directSources);
  if (m.approvals_required !== undefined) msg.approvalsRequired = Boolean(m.approvals_required);
  if (m.provenance) msg.provenance = m.provenance;
  return msg;
}

function hostnameFor(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return "";
  }
}

function sourcesFromToolMessage(message: Record<string, unknown>): SourceEvidence[] {
  const toolName = String(message.tool_name || "");
  const toolResult = (message.tool_result as Record<string, unknown> | undefined) || {};
  const outputs = (toolResult.outputs as Record<string, unknown> | undefined) || toolResult;
  const data = (outputs.data as Record<string, unknown> | undefined) || outputs;
  if (toolName === "brave.news.search" || toolName === "brave.web.search" || toolName === "web.search_brave" || toolName === "search.query") {
    const results = Array.isArray(data.results) ? (data.results as Array<Record<string, unknown>>) : [];
    const sources = results.slice(0, 5).map((item) => ({
      title: String(item.title || item.url || "Source"),
      url: String(item.url || ""),
      snippet: String(item.description || ""),
      source: String(item.hostname || hostnameFor(String(item.url || "")) || "web"),
    })).filter((item) => item.url);
    return sources;
  }
  if (toolName === "search.fetch_url") {
    const url = String(data.url || data.final_url || "");
    if (!url) return [];
    const snippet = String(data.content_preview || "").replace(/\s+/g, " ").trim().slice(0, 240);
    const title = hostnameFor(url) || "Fetched source";
    return [{ title, url, snippet, source: hostnameFor(url) || "web" }];
  }
  return [];
}

function mergeUniqueByUrl(items: SourceEvidence[]): SourceEvidence[] {
  const seen = new Set<string>();
  const out: SourceEvidence[] = [];
  for (const item of items) {
    if (!item.url || seen.has(item.url)) continue;
    seen.add(item.url);
    out.push(item);
  }
  return out;
}

function attachDerivedEvidence(messages: Array<Record<string, unknown>>): HgMessage[] {
  const mapped = messages.map((message) => mapMessage(message as Parameters<typeof mapMessage>[0]));
  for (let index = 0; index < mapped.length; index += 1) {
    const message = mapped[index];
    if (message.role !== "assistant" || message.sourceEvidence?.length) continue;
    const sources: SourceEvidence[] = [];
    for (let lookback = index - 1; lookback >= 0; lookback -= 1) {
      const raw = messages[lookback];
      const role = String(raw.role || "");
      if (role === "assistant" || role === "user") break;
      if (role !== "tool") continue;
      sources.push(...sourcesFromToolMessage(raw));
    }
    if (sources.length) {
      message.sourceEvidence = mergeUniqueByUrl(sources).slice(0, 6);
    }
  }
  return mapped;
}

function mapAgent(a: {
  agent_id: string;
  label: string;
  status: string;
  parent_agent_id?: string;
  children?: string[];
  state_reason?: string | null;
}): HgAgent {
  return {
    id: a.agent_id,
    name: a.label,
    role: a.parent_agent_id ? "sub" : "primary",
    status: a.status as HgAgent["status"],
    children: a.children ?? [],
    stateReason: a.state_reason ?? null,
  };
}

/** Endpoint key class: operator (tenant), admin (admin only), service (explicit). */
export const hgApiKeyClass = {
  listChats: "operator" as const,
  getChat: "operator" as const,
  createChat: "operator" as const,
  getChatTraits: "operator" as const,
  putChatTraits: "operator" as const,
  listPersonas: "operator" as const,
  listMessages: "operator" as const,
  listAgents: "operator" as const,
  sendMessage: "operator" as const,
  listApprovals: "operator" as const,
  resolveApproval: "operator" as const,
  stepupChallenge: "operator" as const,
  stepupVerify: "operator" as const,
  stepupEnroll: "operator" as const,
  stepupStatus: "operator" as const,
  runSwarm: "operator" as const,
  getTenantMe: "operator" as const,
  getTenantUsage: "operator" as const,
  listPrincipals: "operator" as const,
  getPrincipal: "operator" as const,
  createPrincipal: "operator" as const,
  updatePrincipalAvailability: "operator" as const,
  listTenantsAdmin: "admin" as const,
  patchTenantQuotas: "admin" as const,
  exportTenant: "admin" as const,
  deleteTenant: "admin" as const,
  adminPing: "admin" as const,
  uploadFile: "operator" as const,
  listDocuments: "operator" as const,
  getDocument: "operator" as const,
  getChunks: "operator" as const,
  parseDocument: "operator" as const,
  retrieveDocuments: "operator" as const,
  getKnowledgeWorkspace: "operator" as const,
  previewResearchPlan: "operator" as const,
  previewDocumentPlan: "operator" as const,
  getChatAttachments: "operator" as const,
  setChatAttachments: "operator" as const,
  createExportDocx: "operator" as const,
  fetchFileBlob: "operator" as const,
};

export const hgApi = {
  /** GET /v1/chats — key: operator. Includes fingerprint_id when chat has a persona (steerable). */
  async listChats(options?: { includeArchived?: boolean; archivedOnly?: boolean; includeDeleted?: boolean; deletedOnly?: boolean }): Promise<ChatSummary[]> {
    const params = new URLSearchParams();
    if (options?.includeArchived) params.set("include_archived", "true");
    if (options?.archivedOnly) params.set("archived_only", "true");
    if (options?.includeDeleted) params.set("include_deleted", "true");
    if (options?.deletedOnly) params.set("deleted_only", "true");
    const suffix = params.size ? `?${params.toString()}` : "";
    const res = await hgFetch<{
      chats: Array<{ chat_id: string; title: string; updated_at: string; archived_at?: string | null; archive_reason?: string | null; deleted_at?: string | null; delete_reason?: string | null; restore_deadline_at?: string | null; fingerprint_id?: string | null; skin_id?: string | null; swarm_run_id?: string | null; swarm_role?: string | null }>;
    }>(`/v1/chats${suffix}`, { keyClass: "operator" });
    return (res?.chats ?? []).map(mapChat);
  },

  /** GET /v1/chats/:id — key: operator. Returns chat with persona (fingerprint_id, skin_id) and traits when present. */
  async getChat(chatId: string): Promise<(ChatSummary & { fingerprint_id?: string; skin_id?: string; temporary_fingerprint_id?: string | null; temporary_skin_id?: string | null; temporary_turns_remaining?: number | null; traits?: Record<string, number>; trait_overrides?: Record<string, number> }) | null> {
    try {
      const res = await hgFetch<{
        chat_id: string;
        title: string;
        updated_at: string;
        archived_at?: string | null;
        archive_reason?: string | null;
        deleted_at?: string | null;
        delete_reason?: string | null;
        restore_deadline_at?: string | null;
        fingerprint_id?: string;
        skin_id?: string;
        swarm_run_id?: string | null;
        swarm_role?: string | null;
        temporary_fingerprint_id?: string | null;
        temporary_skin_id?: string | null;
        temporary_turns_remaining?: number | null;
        traits?: Record<string, number>;
        trait_overrides?: Record<string, number>;
      }>(`/v1/chats/${encodeURIComponent(chatId)}`, { keyClass: "operator" });
      if (!res) return null;
      return {
        id: res.chat_id,
        title: res.title,
        updatedAt: res.updated_at,
        ...(res.archived_at != null && { archivedAt: res.archived_at }),
        ...(res.archive_reason != null && { archiveReason: res.archive_reason }),
        ...(res.deleted_at != null && { deletedAt: res.deleted_at }),
        ...(res.delete_reason != null && { deleteReason: res.delete_reason }),
        ...(res.restore_deadline_at != null && { restoreDeadlineAt: res.restore_deadline_at }),
        ...(res.fingerprint_id != null && { fingerprint_id: res.fingerprint_id }),
        ...(res.skin_id != null && { skin_id: res.skin_id }),
        ...(res.fingerprint_id != null && { fingerprintId: res.fingerprint_id }),
        ...(res.skin_id != null && { skinId: res.skin_id }),
        ...(res.swarm_run_id != null && { swarmRunId: res.swarm_run_id }),
        ...(res.swarm_role != null && { swarmRole: res.swarm_role }),
        ...(res.temporary_fingerprint_id != null && { temporary_fingerprint_id: res.temporary_fingerprint_id }),
        ...(res.temporary_skin_id != null && { temporary_skin_id: res.temporary_skin_id }),
        ...(res.temporary_turns_remaining != null && { temporary_turns_remaining: res.temporary_turns_remaining }),
        ...(res.traits && Object.keys(res.traits).length > 0 && { traits: res.traits }),
        ...(res.trait_overrides && Object.keys(res.trait_overrides).length > 0 && { traitOverrides: res.trait_overrides, trait_overrides: res.trait_overrides }),
      };
    } catch {
      const list = await hgApi.listChats();
      const c = list.find((x) => x.id === chatId);
      return c ?? null;
    }
  },

  /** POST /v1/chats — key: operator. Optional persona (fingerprint_id, skin_id). */
  async createChat(
    title: string,
    options?: { fingerprint_id?: string; skin_id?: string }
  ): Promise<{ chat_id: string; fingerprint_id?: string; skin_id?: string }> {
    const res = await hgFetch<{ chat_id: string; fingerprint_id?: string; skin_id?: string }>("/v1/chats", {
      method: "POST",
      body: JSON.stringify({ title, ...options }),
      keyClass: "operator",
    });
    return res;
  },

  /** DELETE /v1/chats/:id — key: operator. Permanently deletes a chat. */
  async deleteChat(chatId: string): Promise<void> {
    await hgFetch(`/v1/chats/${encodeURIComponent(chatId)}`, {
      method: "DELETE",
      keyClass: "operator",
    });
  },

  /** POST /v1/chats/:id/trash — key: operator. Tombstone a chat with restore window. */
  async trashChat(chatId: string, reason = "manual"): Promise<void> {
    await hgFetch(`/v1/chats/${encodeURIComponent(chatId)}/trash`, {
      method: "POST",
      body: JSON.stringify({ reason }),
      keyClass: "operator",
    });
  },

  /** POST /v1/chats/:id/archive — key: operator. Soft archive a chat. */
  async archiveChat(chatId: string, reason = "manual"): Promise<void> {
    await hgFetch(`/v1/chats/${encodeURIComponent(chatId)}/archive`, {
      method: "POST",
      body: JSON.stringify({ reason }),
      keyClass: "operator",
    });
  },

  /** POST /v1/chats/:id/restore — key: operator. Restore archived chat. */
  async restoreChat(chatId: string): Promise<void> {
    await hgFetch(`/v1/chats/${encodeURIComponent(chatId)}/restore`, {
      method: "POST",
      keyClass: "operator",
    });
  },

  /** DELETE /v1/swarms/:id — key: operator. Permanently deletes orchestrator + member chats for a swarm run. */
  async deleteSwarm(swarmRunId: string): Promise<{ deleted_count: number; deleted_chat_ids: string[] }> {
    const res = await hgFetch<{ deleted_count: number; deleted_chat_ids: string[] }>(`/v1/swarms/${encodeURIComponent(swarmRunId)}`, {
      method: "DELETE",
      keyClass: "operator",
    });
    return res ?? { deleted_count: 0, deleted_chat_ids: [] };
  },

  /** POST /v1/swarms/:id/archive — key: operator. Soft archive swarm orchestrator + member chats. */
  async archiveSwarm(swarmRunId: string, reason = "manual"): Promise<{ updated_count: number; updated_chat_ids: string[] }> {
    const res = await hgFetch<{ updated_count: number; updated_chat_ids: string[] }>(`/v1/swarms/${encodeURIComponent(swarmRunId)}/archive`, {
      method: "POST",
      body: JSON.stringify({ reason }),
      keyClass: "operator",
    });
    return res ?? { updated_count: 0, updated_chat_ids: [] };
  },

  /** POST /v1/swarms/:id/trash — key: operator. Tombstone swarm chats with restore window. */
  async trashSwarm(swarmRunId: string, reason = "manual"): Promise<{ updated_count: number; updated_chat_ids: string[] }> {
    const res = await hgFetch<{ updated_count: number; updated_chat_ids: string[] }>(`/v1/swarms/${encodeURIComponent(swarmRunId)}/trash`, {
      method: "POST",
      body: JSON.stringify({ reason }),
      keyClass: "operator",
    });
    return res ?? { updated_count: 0, updated_chat_ids: [] };
  },

  /** POST /v1/swarms/:id/restore — key: operator. Restore archived swarm chats. */
  async restoreSwarm(swarmRunId: string): Promise<{ updated_count: number; updated_chat_ids: string[] }> {
    const res = await hgFetch<{ updated_count: number; updated_chat_ids: string[] }>(`/v1/swarms/${encodeURIComponent(swarmRunId)}/restore`, {
      method: "POST",
      keyClass: "operator",
    });
    return res ?? { updated_count: 0, updated_chat_ids: [] };
  },

  /** GET /v1/chats/:id/traits — key: operator. Effective trait vector for steering. */
  async getChatTraits(chatId: string): Promise<{ traits: Record<string, number>; traitOverrides: Record<string, number> }> {
    const res = await hgFetch<{ ok: boolean; traits: Record<string, number>; trait_overrides?: Record<string, number> }>(
      `/v1/chats/${encodeURIComponent(chatId)}/traits`,
      { keyClass: "operator" }
    );
    return {
      traits: res?.traits ?? {},
      traitOverrides: res?.trait_overrides ?? {},
    };
  },

  /** PUT /v1/chats/:id/traits — key: operator. Set effective trait vector (steering). */
  async putChatTraits(chatId: string, traits: Record<string, number>): Promise<{ traits: Record<string, number>; traitOverrides: Record<string, number> }> {
    const res = await hgFetch<{ ok: boolean; traits: Record<string, number>; trait_overrides?: Record<string, number> }>(`/v1/chats/${encodeURIComponent(chatId)}/traits`, {
      method: "PUT",
      body: JSON.stringify({ traits }),
      keyClass: "operator",
    });
    return {
      traits: res?.traits ?? {},
      traitOverrides: res?.trait_overrides ?? {},
    };
  },

  /** PATCH /v1/chats/:id — key: operator. Update chat title/persona/skin. */
  async patchChat(chatId: string, body: { title?: string; fingerprint_id?: string | null; skin_id?: string | null; temporary_fingerprint_id?: string | null; temporary_skin_id?: string | null; temporary_turns_remaining?: number | null }): Promise<void> {
    await hgFetch(`/v1/chats/${encodeURIComponent(chatId)}`, {
      method: "PATCH",
      body: JSON.stringify(body),
      keyClass: "operator",
    });
  },

  /** GET /api/v1/personas — key: operator. List personas for dropdown. */
  async listPersonas(): Promise<Array<{ fingerprint_id: string; name: string; type: string; source: string; skins: Array<{ id: string; name: string }> }>> {
    const res = await hgFetch<{ ok: boolean; personas: Array<{ fingerprint_id: string; name: string; path: string; type: string; source: string; skins: Array<{ id: string; name: string }> }> }>(
      "/api/v1/personas",
      { keyClass: "operator" }
    );
    return (res?.personas ?? []).map((p) => ({
      fingerprint_id: p.fingerprint_id,
      name: p.name,
      type: p.type,
      source: p.source,
      skins: p.skins ?? [],
    }));
  },

  /** GET /v1/chats/:id/messages — key: operator */
  async listMessages(chatId: string): Promise<HgMessage[]> {
    const res = await hgFetch<{ messages: Array<Record<string, unknown>> }>(`/v1/chats/${encodeURIComponent(chatId)}/messages`, { keyClass: "operator" });
    return attachDerivedEvidence(res?.messages ?? []);
  },

  /** GET /api/v1/activity/projection — key: operator. Shared compact/expanded projection for operator and client surfaces. */
  async getActivityProjection(params: { limit_runs?: number; limit_decisions?: number; entity_id?: string | null; chat_id?: string | null; run_id?: string | null; workflow_id?: string | null; view?: "compact" | "expanded" } = {}): Promise<ActivityProjection | null> {
    const qs = new URLSearchParams();
    if (params.limit_runs != null) qs.set("limit_runs", String(params.limit_runs));
    if (params.limit_decisions != null) qs.set("limit_decisions", String(params.limit_decisions));
    if (params.entity_id) qs.set("entity_id", params.entity_id);
    if (params.chat_id) qs.set("chat_id", params.chat_id);
    if (params.run_id) qs.set("run_id", params.run_id);
    if (params.workflow_id) qs.set("workflow_id", params.workflow_id);
    if (params.view) qs.set("view", params.view);
    const res = await hgFetch<{ ok: boolean; activity_projection?: ActivityProjection }>(`/activity/projection?${qs.toString()}`, { keyClass: "operator" });
    return res?.activity_projection ?? null;
  },

  /** GET /v1/chats/:id/messages/:messageId/provenance — key: operator */
  async getMessageProvenance(chatId: string, messageId: string): Promise<MessageProvenance | null> {
    const res = await hgFetch<{ ok: boolean; message?: Record<string, unknown>; provenance?: Record<string, unknown> }>(
      `/v1/chats/${encodeURIComponent(chatId)}/messages/${encodeURIComponent(messageId)}/provenance`,
      { keyClass: "operator" }
    );
    if (!res?.ok || !res.provenance) return null;
    return res.provenance as MessageProvenance;
  },

  /** GET /v1/chats/:id/agents — key: operator */
  async listAgents(chatId: string): Promise<HgAgent[]> {
    const res = await hgFetch<{ agents: Array<Record<string, unknown>> }>(`/v1/chats/${encodeURIComponent(chatId)}/agents`, { keyClass: "operator" });
    return (res?.agents ?? []).map((a) => mapAgent(a as Parameters<typeof mapAgent>[0]));
  },

  /** POST /v1/chats/:id/messages — key: operator */
  async sendMessage(chatId: string, content: string): Promise<{ message?: HgMessage }> {
    const res = await hgFetch<{ message?: Record<string, unknown> }>(`/v1/chats/${encodeURIComponent(chatId)}/messages`, {
      method: "POST",
      body: JSON.stringify({ content }),
      keyClass: "operator",
    });
    if (res?.message) return { message: mapMessage(res.message as Parameters<typeof mapMessage>[0]) };
    return {};
  },

  /** GET /v1/approvals — key: operator. status: pending (default), all, approved, denied. Optional limit/offset for pagination; when used, response includes total. */
  async listApprovals(options?: {
    status?: "pending" | "all" | "approved" | "denied";
    limit?: number;
    offset?: number;
  }): Promise<{ approvals: ApprovalItem[]; total?: number }> {
    const params = new URLSearchParams();
    if (options?.status && options.status !== "pending") params.set("status", options.status);
    if (options?.limit != null) params.set("limit", String(options.limit));
    if (options?.offset != null) params.set("offset", String(options.offset));
    const qs = params.toString();
    const res = await hgFetch<{ approvals: ApprovalItem[]; total?: number }>(
      `/v1/approvals${qs ? `?${qs}` : ""}`,
      { keyClass: "operator" }
    );
    return { approvals: res?.approvals ?? [], total: res?.total };
  },

  /** POST /v1/approvals/:id/approve | deny — key: operator */
  async resolveApproval(approvalId: string, decision: "approve" | "deny", note: string, options?: { stepupToken?: string | null }): Promise<void> {
    const path = decision === "approve"
      ? `/v1/approvals/${encodeURIComponent(approvalId)}/approve`
      : `/v1/approvals/${encodeURIComponent(approvalId)}/deny`;
    await hgFetch(path, {
      method: "POST",
      body: JSON.stringify({ note }),
      headers: options?.stepupToken ? { "X-HG-Stepup": options.stepupToken } : undefined,
      keyClass: "operator",
    });
  },

  /** GET /api/v1/approvals-entity/pending — key: operator. Entity/social approval queue. */
  async listEntityApprovals(): Promise<EntityApprovalItem[]> {
    const res = await hgFetch<{ items: EntityApprovalItem[] }>("/api/v1/approvals-entity/pending", { keyClass: "operator" });
    return res?.items ?? [];
  },

  /** POST /api/v1/approvals-entity/:id/approve — key: operator */
  async approveEntityApproval(approvalId: string, note?: string): Promise<void> {
    await hgFetch(`/api/v1/approvals-entity/${encodeURIComponent(approvalId)}/approve`, {
      method: "POST",
      body: JSON.stringify({ note: note ?? "" }),
      keyClass: "operator",
    });
  },

  /** POST /api/v1/approvals-entity/:id/reject — key: operator */
  async rejectEntityApproval(approvalId: string, note?: string): Promise<void> {
    await hgFetch(`/api/v1/approvals-entity/${encodeURIComponent(approvalId)}/reject`, {
      method: "POST",
      body: JSON.stringify({ note: note ?? "" }),
      keyClass: "operator",
    });
  },

  /** GET /api/v1/keystore/accounts — key: operator. List social accounts. */
  async listKeystoreAccounts(platform?: string): Promise<KeystoreAccountItem[]> {
    const params = platform ? `?platform=${encodeURIComponent(platform)}` : "";
    const res = await hgFetch<{ items: KeystoreAccountItem[] }>(`/api/v1/keystore/accounts${params}`, { keyClass: "operator" });
    return res?.items ?? [];
  },

  async stepupChallenge(userId = "default"): Promise<StepupChallenge> {
    return hgFetch<StepupChallenge>("/v1/auth/stepup/challenge", {
      method: "POST",
      body: JSON.stringify({ user_id: userId }),
      keyClass: "operator",
    });
  },

  async stepupVerify(challengeId: string, code: string): Promise<StepupVerifyResult> {
    return hgFetch<StepupVerifyResult>("/v1/auth/stepup/verify", {
      method: "POST",
      body: JSON.stringify({ challenge_id: challengeId, code }),
      keyClass: "operator",
    });
  },

  async stepupEnroll(userId = "default"): Promise<StepupEnrollResult> {
    return hgFetch<StepupEnrollResult>("/v1/auth/stepup/enroll", {
      method: "POST",
      body: JSON.stringify({ user_id: userId }),
      keyClass: "operator",
    });
  },

  async stepupStatus(userId = "default"): Promise<StepupStatus> {
    const query = userId ? `?user_id=${encodeURIComponent(userId)}` : "";
    return hgFetch<StepupStatus>(`/v1/auth/stepup/status${query}`, {
      method: "GET",
      keyClass: "operator",
    });
  },

  /** POST /v1/swarm/run — key: operator. Run N agents in parallel. Body: task (broadcast) or tasks (array). Returns chat_ids; 202 with approval_ids if first-turn approval required. */
  async runSwarm(req: SwarmRunRequest): Promise<SwarmRunResponse> {
    const res = await hgFetch<SwarmRunResponse>("/v1/swarm/run", {
      method: "POST",
      body: JSON.stringify(req),
      keyClass: "operator",
    });
    return res;
  },

  /** GET /v1/swarms/:id — key: operator. */
  async getSwarmWorkspace(swarmRunId: string): Promise<SwarmWorkspace> {
    const res = await hgFetch<{
      swarm_run_id: string;
      orchestrator?: Record<string, unknown> | null;
      members: Array<Record<string, unknown>>;
      counts: SwarmWorkspace["counts"];
      latest_activity?: string | null;
    }>(`/v1/swarms/${encodeURIComponent(swarmRunId)}`, { keyClass: "operator" });
    return {
      swarm_run_id: res?.swarm_run_id ?? swarmRunId,
      orchestrator: res?.orchestrator ? mapSwarmWorkspaceChat(res.orchestrator as Parameters<typeof mapSwarmWorkspaceChat>[0]) : null,
      members: (res?.members ?? []).map((item) => mapSwarmWorkspaceChat(item as Parameters<typeof mapSwarmWorkspaceChat>[0])),
      counts: res?.counts ?? { completed: 0, active: 0, queued: 0, error: 0 },
      latest_activity: res?.latest_activity ?? null,
    };
  },

  /** GET /v1/system/version — key: operator. */
  async getSystemVersion(): Promise<Record<string, string>> {
    const res = await hgFetch<Record<string, string>>("/v1/system/version", { keyClass: "operator" });
    return res ?? {};
  },

  /** GET /v1/system/status — key: operator. */
  async getSystemStatus(): Promise<{ status?: string; diagnostics?: Array<Record<string, unknown>> }> {
    const res = await hgFetch<{ status?: string; diagnostics?: Array<Record<string, unknown>> }>("/v1/system/status", {
      keyClass: "operator",
    });
    return res ?? {};
  },

  /** GET /v1/tenant/audit — key: operator. */
  async getTenantAudit(params: { event_type?: string; limit?: number; offset?: number } = {}): Promise<{
    items: Array<Record<string, unknown>>;
    total: number;
  }> {
    const q = new URLSearchParams();
    if (params.event_type) q.set("event_type", params.event_type);
    if (params.limit != null) q.set("limit", String(params.limit));
    if (params.offset != null) q.set("offset", String(params.offset));
    const res = await hgFetch<{ items: Array<Record<string, unknown>>; total: number }>(
      `/v1/tenant/audit?${q.toString()}`,
      { keyClass: "operator" },
    );
    return res ?? { items: [], total: 0 };
  },

  /** GET /v1/admin/audit — key: admin. */
  async getAdminAudit(params: { tenant_id?: string; event_type?: string; limit?: number; offset?: number } = {}): Promise<{
    items: Array<Record<string, unknown>>;
    total: number;
  }> {
    const q = new URLSearchParams();
    if (params.tenant_id) q.set("tenant_id", params.tenant_id);
    if (params.event_type) q.set("event_type", params.event_type);
    if (params.limit != null) q.set("limit", String(params.limit));
    if (params.offset != null) q.set("offset", String(params.offset));
    const res = await hgFetch<{ items: Array<Record<string, unknown>>; total: number }>(
      `/v1/admin/audit?${q.toString()}`,
      { keyClass: "admin" },
    );
    return res ?? { items: [], total: 0 };
  },

  /** GET /v1/tenant/retention — key: operator. */
  async getTenantRetention(): Promise<{
    chats_days: number;
    docs_days: number;
    proofs_days: number;
    logs_days: number;
    legal_hold_enabled: boolean;
  }> {
    const res = await hgFetch<{
      chats_days: number;
      docs_days: number;
      proofs_days: number;
      logs_days: number;
      legal_hold_enabled: boolean;
    }>("/v1/tenant/retention", { keyClass: "operator" });
    return res!;
  },

  /** PATCH /v1/tenant/retention — key: operator. */
  async patchTenantRetention(body: {
    chats_days: number;
    docs_days: number;
    proofs_days: number;
    logs_days: number;
    legal_hold_enabled: boolean;
  }): Promise<void> {
    await hgFetch("/v1/tenant/retention", { method: "PATCH", body: JSON.stringify(body), keyClass: "operator" });
  },

  /** POST /v1/tenant/export — key: operator. Downloads zip archive. */
  async downloadTenantExport(): Promise<void> {
    const blob = await hgFetchBlob("/v1/tenant/export", { method: "POST", keyClass: "operator" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `tenant_export_${new Date().toISOString().slice(0, 10)}.zip`;
    anchor.click();
    URL.revokeObjectURL(url);
  },

  notificationsStreamUrl(): string {
    return `${env.apiBase}/v1/stream/notifications`;
  },

  swarmStreamUrl(swarmRunId: string): string {
    return `${env.apiBase}/v1/swarms/${encodeURIComponent(swarmRunId)}/stream`;
  },

  /** GET /v1/ui/brand — no auth. Host-derived tenant branding for white-label. */
  async getUiBrand(): Promise<UiBrand | null> {
    if (env.demoMode) return null;
    try {
      const url = `${env.apiBase}/v1/ui/brand`;
      const res = await fetch(url, { cache: "no-store" });
      if (!res.ok) return null;
      const data = await res.json();
      return data as UiBrand;
    } catch {
      return null;
    }
  },

  /** GET /v1/tenants/me — key: operator. Tenant identity, limits, usage snapshot. */
  async getTenantMe(): Promise<TenantInfo | null> {
    const res = await hgFetch<TenantInfo>("/v1/tenants/me", { keyClass: "operator" });
    return res ?? null;
  },

  /** GET /v1/tenants/me/usage — key: operator. Detailed usage counters. */
  async getTenantUsage(): Promise<TenantUsage | null> {
    const res = await hgFetch<TenantUsage>("/v1/tenants/me/usage", { keyClass: "operator" });
    return res ?? null;
  },

  /** GET /v1/tenants/me/settings — key: operator (tenant_admin). Includes approval policy. */
  async getTenantMeSettings(): Promise<{
    tenant_id: string;
    display_name?: string;
    theme?: Record<string, unknown>;
    support_links?: unknown[];
    first_turn_approval_required?: boolean;
    auto_approve_kinds?: string[];
    can_edit?: boolean;
  } | null> {
    const res = await hgFetch<{
      tenant_id: string;
      display_name?: string;
      theme?: Record<string, unknown>;
      support_links?: unknown[];
      first_turn_approval_required?: boolean;
      auto_approve_kinds?: string[];
      can_edit?: boolean;
    }>("/v1/tenants/me/settings", { keyClass: "operator" });
    return res ?? null;
  },

  /** PATCH /v1/tenants/me/settings — key: operator (tenant_admin). Update approval policy etc. */
  async patchTenantMeSettings(body: {
    display_name?: string;
    theme?: Record<string, unknown>;
    support_links?: unknown[];
    first_turn_approval_required?: boolean;
    auto_approve_kinds?: string[];
  }): Promise<void> {
    await hgFetch("/v1/tenants/me/settings", { method: "PATCH", body: JSON.stringify(body), keyClass: "operator" });
  },

  /** GET /v1/principals — key: operator. include_disabled to list disabled principals (tenant-admin/operator). */
  async listPrincipals(includeDisabled?: boolean): Promise<Principal[]> {
    const q = includeDisabled ? "?include_disabled=true" : "";
    const res = await hgFetch<{ principals: Principal[] }>(`/v1/principals${q}`, { keyClass: "operator" });
    return res?.principals ?? [];
  },

  /** GET /v1/principals/:id — key: operator. */
  async getPrincipal(id: string): Promise<Principal | null> {
    const res = await hgFetch<Principal | null>(`/v1/principals/${encodeURIComponent(id)}`, { keyClass: "operator" });
    return res ?? null;
  },

  /** POST /v1/principals — key: operator. */
  async createPrincipal(body: { id: string; type: string; label: string; timezone?: string; on_call_hours?: Record<string, unknown>; status?: string; escalation_chain?: string[] }): Promise<Principal> {
    const res = await hgFetch<Principal>("/v1/principals", {
      method: "POST",
      body: JSON.stringify(body),
      keyClass: "operator",
    });
    return res!;
  },

  /** PATCH /v1/principals/:id/availability — key: operator. disabled for tenant-admin/operator user management. */
  async updatePrincipalAvailability(
    id: string,
    body: { timezone?: string; on_call_hours?: Record<string, unknown>; status?: string; escalation_chain?: string[]; disabled?: boolean }
  ): Promise<void> {
    await hgFetch(`/v1/principals/${encodeURIComponent(id)}/availability`, {
      method: "PATCH",
      body: JSON.stringify(body),
      keyClass: "operator",
    });
  },

  /** GET /v1/admin/tenants — key: admin. */
  async listTenantsAdmin(): Promise<string[]> {
    const res = await hgFetch<{ tenant_ids: string[] }>("/v1/admin/tenants", { keyClass: "admin" });
    return res?.tenant_ids ?? [];
  },

  /** PATCH /v1/admin/tenants/:id/quotas — key: admin. */
  async patchTenantQuotas(tenantId: string, limits: Record<string, number>): Promise<void> {
    await hgFetch(`/v1/admin/tenants/${encodeURIComponent(tenantId)}/quotas`, {
      method: "PATCH",
      body: JSON.stringify({ limits }),
      keyClass: "admin",
    });
  },

  /** POST /v1/tenants/:id/export — key: admin or operator (own tenant). */
  async exportTenant(tenantId: string): Promise<Record<string, unknown>> {
    const res = await hgFetch<Record<string, unknown>>(`/v1/tenants/${encodeURIComponent(tenantId)}/export`, {
      method: "POST",
      keyClass: "admin",
    });
    return res ?? {};
  },

  /** POST /v1/tenants/:id/delete — key: admin. */
  async deleteTenant(tenantId: string): Promise<Record<string, unknown>> {
    const res = await hgFetch<Record<string, unknown>>(`/v1/tenants/${encodeURIComponent(tenantId)}/delete`, {
      method: "POST",
      keyClass: "admin",
    });
    return res ?? {};
  },

  /** GET /v1/admin/ping — key: admin. Validate admin key. */
  async adminPing(): Promise<{ status: string }> {
    return hgFetch<{ status: string }>("/v1/admin/ping", { keyClass: "admin" });
  },

  /** POST /v1/files/upload — key: operator. Multipart file; returns document_id. */
  async uploadFile(file: File, keyClass: "operator" = "operator"): Promise<{ document_id: string; filename: string; mime: string; size_bytes: number }> {
    const form = new FormData();
    form.append("file", file);
    return hgFetch<{ document_id: string; filename: string; mime: string; size_bytes: number }>("/v1/files/upload", {
      method: "POST",
      body: form,
      keyClass,
    });
  },

  /** GET /v1/documents?chat_id= — key: operator. */
  async listDocuments(chatId?: string): Promise<Document[]> {
    const q = chatId ? `?chat_id=${encodeURIComponent(chatId)}` : "";
    const res = await hgFetch<{ documents: Record<string, unknown>[] }>(`/v1/documents${q}`, { keyClass: "operator" });
    return (res?.documents ?? []).map((d) => d as unknown as Document);
  },

  /** GET /v1/documents/:id — key: operator. */
  async getDocument(documentId: string): Promise<Document | null> {
    try {
      const res = await hgFetch<Record<string, unknown>>(`/v1/documents/${encodeURIComponent(documentId)}`, { keyClass: "operator" });
      return res as unknown as Document;
    } catch {
      return null;
    }
  },

  /** GET /v1/documents/:id/chunks — key: operator. */
  async getChunks(documentId: string, page = 1, pageSize = 50): Promise<{ chunks: DocumentChunk[] }> {
    const res = await hgFetch<{ chunks: DocumentChunk[] }>(
      `/v1/documents/${encodeURIComponent(documentId)}/chunks?page=${page}&page_size=${pageSize}`,
      { keyClass: "operator" }
    );
    return { chunks: res?.chunks ?? [] };
  },

  /** POST /v1/documents/:id/parse — key: operator. */
  async parseDocument(documentId: string): Promise<{ job_id: string }> {
    const res = await hgFetch<{ job_id: string }>(`/v1/documents/${encodeURIComponent(documentId)}/parse`, {
      method: "POST",
      keyClass: "operator",
    });
    return res ?? { job_id: "" };
  },

  /** POST /v1/documents/retrieve — key: operator. */
  async retrieveDocuments(body: { query: string; chat_id?: string; top_k?: number }): Promise<{ chunks: Array<DocumentChunk & { citation?: Citation }> }> {
    const res = await hgFetch<{ chunks: Array<DocumentChunk & { citation?: Citation }> }>("/v1/documents/retrieve", {
      method: "POST",
      body: JSON.stringify(body),
      keyClass: "operator",
    });
    return res ?? { chunks: [] };
  },

  /** GET /v1/chats/:id/knowledge-workspace — key: operator. */
  async getKnowledgeWorkspace(chatId: string): Promise<KnowledgeWorkspace | null> {
    const res = await hgFetch<KnowledgeWorkspace>(`/v1/chats/${encodeURIComponent(chatId)}/knowledge-workspace`, {
      keyClass: "operator",
    });
    return res ?? null;
  },

  /** POST /v1/chats/:id/knowledge-workspace/research-plan-preview — key: operator. */
  async previewResearchPlan(chatId: string, content: string): Promise<PlanPreview> {
    const res = await hgFetch<PlanPreview>(`/v1/chats/${encodeURIComponent(chatId)}/knowledge-workspace/research-plan-preview`, {
      method: "POST",
      body: JSON.stringify({ content }),
      keyClass: "operator",
    });
    return res ?? { detected: false };
  },

  /** POST /v1/chats/:id/knowledge-workspace/document-plan-preview — key: operator. */
  async previewDocumentPlan(chatId: string, body: { content: string; document_id?: string; requested_count?: number }): Promise<PlanPreview> {
    const res = await hgFetch<PlanPreview>(`/v1/chats/${encodeURIComponent(chatId)}/knowledge-workspace/document-plan-preview`, {
      method: "POST",
      body: JSON.stringify(body),
      keyClass: "operator",
    });
    return res ?? { detected: false };
  },

  /** GET /v1/chats/:id/attachments — key: operator. */
  async getChatAttachments(chatId: string): Promise<string[]> {
    const res = await hgFetch<{ document_ids: string[] }>(`/v1/chats/${encodeURIComponent(chatId)}/attachments`, { keyClass: "operator" });
    return res?.document_ids ?? [];
  },

  /** POST /v1/chats/:id/attachments — key: operator. */
  async setChatAttachments(chatId: string, documentIds: string[]): Promise<void> {
    await hgFetch(`/v1/chats/${encodeURIComponent(chatId)}/attachments`, {
      method: "POST",
      body: JSON.stringify({ document_ids: documentIds }),
      keyClass: "operator",
    });
  },

  /** POST /v1/exports/docx — key: operator. */
  async createExportDocx(body: { title?: string; sections?: Array<{ heading?: string; text?: string; level?: number } | string>; citations?: Citation[] }): Promise<ExportResult> {
    const res = await hgFetch<ExportResult>("/v1/exports/docx", {
      method: "POST",
      body: JSON.stringify(body),
      keyClass: "operator",
    });
    return res!;
  },

  /** GET /v1/files/:id/download as blob — key: operator. */
  async fetchFileBlob(fileId: string): Promise<Blob> {
    return hgFetchBlob(`/v1/files/${encodeURIComponent(fileId)}/download`, { keyClass: "operator" });
  },

  /** URL for file download (use with fetchFileBlob for auth, or open in new tab if backend supports token-in-query). */
  getFileDownloadPath(fileId: string): string {
    const base = env.demoMode ? "" : env.apiBase;
    return `${base}/v1/files/${encodeURIComponent(fileId)}/download`;
  },
};

export type HgAuth = { bearer?: string };
