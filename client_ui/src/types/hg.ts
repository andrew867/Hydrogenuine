export type ChatSummary = {
  id: string;
  title: string;
  subtitle?: string;
  updatedAt: string;
  archivedAt?: string | null;
  archiveReason?: string | null;
  deletedAt?: string | null;
  deleteReason?: string | null;
  restoreDeadlineAt?: string | null;
  /** When set, chat has a persona and is steerable in Entity steering. */
  fingerprintId?: string | null;
  /** When set, chat belongs to this swarm run; use for sidebar grouping. */
  swarmRunId?: string | null;
  /** e.g. "entity" | "orchestrator". */
  swarmRole?: string | null;
  skinId?: string | null;
  traits?: Record<string, number>;
  traitOverrides?: Record<string, number>;
};

export type HgMessageRole = "user" | "assistant" | "tool" | "system";

export type ToolTimelineItem = { at: string; label: string };

export type ToolEvent = {
  name: string;
  status: "running" | "ok" | "error";
  timeline?: ToolTimelineItem[];
  detail?: string;
};

export type ChatDeliveryState = "pending" | "accepted" | "responding" | "completed" | "error";

export type HgMessage = {
  id: string;
  chatId: string;
  role: HgMessageRole;
  createdAt: string;
  content: string;
  deliveryState?: ChatDeliveryState;
  tool?: ToolEvent;
  provenance?: {
    prompt_id?: string | null;
    model_config_id?: string | null;
    sampling_params?: Record<string, unknown> | null;
    created_at?: string | null;
  };
  /** Document citations (Pack 12) or legacy { title, url?, note? }. */
  citations?: Citation[];
  sourceEvidence?: SourceEvidence[];
  /** True when this message required or requires human approval (e.g. tool use). */
  approvalsRequired?: boolean;
};

export type MessageProvenance = {
  message_id: string;
  chat_id: string;
  role: HgMessageRole;
  why: string;
  timeline_href?: string | null;
  turn_provenance?: {
    prompt_id?: string | null;
    model_config_id?: string | null;
    sampling_params?: Record<string, unknown> | null;
    created_at?: string | null;
  } | null;
  source_groups: {
    retrieval: SourceEvidence[];
    policy: Array<{ kind: string; label: string; value: unknown }>;
    evidence: Array<{ ledger_id?: string | null; timestamp?: string | null; evidence_type?: string | null; approval_id?: string | null; content_ref?: string | null }>;
    reflection: Array<{ kind: string; label: string; value: unknown }>;
    user_mirroring: Array<{ kind: string; label: string; value: unknown }>;
    inference: Array<{ kind: string; label: string; value: unknown }>;
  };
  message?: {
    message_id?: string | null;
    chat_id?: string | null;
    role?: string | null;
    created_at?: string | null;
    content?: string | null;
    approvals_required?: boolean | null;
  } | null;
  evidence_rows?: Array<{
    ledger_id?: string | null;
    timestamp?: string | null;
    evidence_type?: string | null;
    approval_id?: string | null;
    document_id?: string | null;
    content_ref?: string | null;
  }>;
};

export type HgAgent = {
  id: string;
  name: string;
  role: "primary" | "sub";
  status: "idle" | "working" | "blocked" | "error";
  children: string[];
  /** Shown when status is error (e.g. LLM call failed). */
  stateReason?: string | null;
};

export type ApprovalRisk = "low" | "medium" | "high";

export type ApprovalItem = {
  id: string;
  createdAt: string;
  resolvedAt?: string;
  status: "pending" | "approved" | "denied";
  kind: "external_request" | "data_write" | "tool_use" | "other";
  title: string;
  summary: string;
  risk: ApprovalRisk;
  requestedBy: string;
  payload: unknown;
  resolutionNote?: string;
  workflow?: string;
  run_id?: string;
  chat_id?: string;
  origin?: {
    type: "chat" | "run" | "workflow" | "unknown";
    chat_id?: string;
    run_id?: string;
    workflow_id?: string;
    route?: string | null;
    label?: string;
  };
};

/** Entity/social approval request (GET /api/v1/approvals-entity/pending). */
export type EntityApprovalItem = {
  approval_id: string;
  tenant_id?: string;
  entity_id: string;
  workflow_id?: string | null;
  step_id?: string | null;
  action_kind: string;
  target_platform?: string | null;
  target_account_alias?: string | null;
  preview_json: Record<string, unknown>;
  status: string;
  requested_at: string;
  decided_at?: string | null;
  decided_by?: string | null;
  decision_note?: string | null;
};

/** Keystore social account (GET /api/v1/keystore/accounts). */
export type KeystoreAccountItem = {
  social_account_id: string;
  tenant_id?: string;
  platform: string;
  account_alias: string;
  login_secret_alias_id?: string | null;
  mfa_secret_alias_id?: string | null;
  entity_scope?: string | null;
  persona_scope?: string | null;
  state: string;
  created_at: string;
};

/** Tenant identity and quota snapshot (GET /v1/tenants/me). */
export type TenantInfo = {
  tenant_id: string;
  environment: string;
  limits: Record<string, number>;
  usage: Record<string, number>;
  /** operator | tenant_admin | principal */
  role?: string;
  /** Set when role is principal. */
  principal_id?: string;
  principal_missing?: boolean;
  /** Pack 13: True when request was made with impersonation JWT. */
  impersonating?: boolean;
  /** Tenant id being impersonated (when impersonating is true). */
  impersonation_tenant_id?: string;
};

/** Detailed usage counters (GET /v1/tenants/me/usage). */
export type TenantUsage = {
  usage: Record<string, number>;
};

/** Pack 13 / U3: Host-derived branding (GET /v1/ui/brand). No auth. */
export type UiBrand = {
  tenant_id: string;
  display_name: string;
  logo_url: string | null;
  favicon_url?: string | null;
  theme: Record<string, unknown>;
  palettes?: {
    light?: Record<string, string>;
    dark?: Record<string, string>;
  };
  support_links: unknown[];
  brand_version?: number;
};

/** Request for POST /v1/swarm/run. Exactly one of task or tasks. */
export type SwarmRunRequest = {
  /** Single task broadcast to all N agents. */
  task?: string;
  /** N distinct tasks (one per agent). N = len(tasks). */
  tasks?: string[];
  /** Number of agents when using task (default 3). Ignored when tasks is set. */
  count?: number;
};

/** Response from POST /v1/swarm/run. 200 or 202. */
export type SwarmRunResponse = {
  chat_ids: string[];
  swarm_run_id?: string;
  parent_chat_id?: string;
  approval_ids?: string[];
  task?: string;
  tasks?: string[];
  message?: string;
};

export type SwarmWorkspaceChat = ChatSummary & {
  messageCount: number;
  latestRole?: string | null;
  latestText?: string;
  status: "completed" | "active" | "queued" | "error";
};

export type SwarmWorkspace = {
  swarm_run_id: string;
  orchestrator?: SwarmWorkspaceChat | null;
  members: SwarmWorkspaceChat[];
  counts: {
    completed: number;
    active: number;
    queued: number;
    error: number;
  };
  latest_activity?: string | null;
};

/** Document (Pack 12) — list/get from /v1/documents. */
export type Document = {
  document_id: string;
  tenant_id: string;
  chat_id?: string | null;
  filename: string;
  mime: string;
  size_bytes: number;
  sha256?: string | null;
  created_at: string;
  created_by?: string | null;
  parse_status: string;
  meta?: Record<string, unknown> | null;
};

/** Chunk (Pack 12) — from GET /v1/documents/:id/chunks or retrieve. */
export type DocumentChunk = {
  chunk_id: string;
  document_id: string;
  text: string;
  provenance?: { page_start?: number; page_end?: number };
  score?: number;
  citation?: Citation;
};

/** Citation (Pack 12) — document_id, filename, page range; optional title/url/note for legacy. */
export type Citation = {
  document_id?: string;
  filename?: string;
  page_start?: number;
  page_end?: number;
  chunk_id?: string;
  title?: string;
  url?: string;
  note?: string;
};

export type SourceEvidence = {
  title: string;
  url: string;
  snippet?: string;
  source?: string;
};

export type ActivityProjection = {
  view: "compact" | "expanded";
  compact: {
    mode: "compact";
    status: string | null;
    counts: Record<string, number>;
    latest?: Record<string, unknown> | null;
    since_last_wake: {
      anchor?: {
        event_id?: string | null;
        timestamp?: string | null;
        title?: string | null;
        detail?: string | null;
        event_type?: string | null;
      } | null;
      summary: string;
      counts: Record<string, number>;
      timeline: Array<Record<string, unknown>>;
    };
  };
  expanded: {
    mode: "expanded";
    status: string | null;
    counts: Record<string, number>;
    latest?: Record<string, unknown> | null;
    timeline: Array<Record<string, unknown>>;
    support_claims: Array<Record<string, unknown>>;
    continuity_events: Array<Record<string, unknown>>;
    approval_events: Array<Record<string, unknown>>;
    provenance_events: Array<Record<string, unknown>>;
    since_last_wake: ActivityProjection["compact"]["since_last_wake"];
  };
  active: ActivityProjection["compact"] | ActivityProjection["expanded"];
  since_last_wake: ActivityProjection["compact"]["since_last_wake"];
};

export type KnowledgeWorkspaceRun = {
  kind: "research_summary" | "document_decomposition";
  message_id: string;
  created_at: string;
  title: string;
  plan_template?: string | null;
  confidence?: number | null;
  node_count?: number | null;
  assistant_message_id?: string | null;
  assistant_excerpt?: string;
  sources?: SourceEvidence[];
  swarm_run_id?: string | null;
  query?: string;
  research_kind?: string;
  original_request?: string;
  query_variants?: string[];
  fetch_page_count?: number | null;
  result_window?: number | null;
  document_id?: string | null;
  segment_count?: number | null;
  segment_labels?: string[];
};

export type KnowledgeWorkspaceDocument = Document & {
  segments?: Array<{
    segment_id: string;
    label: string;
    page_start?: number;
    page_end?: number;
    chunk_ids?: string[];
  }>;
};

export type KnowledgeWorkspace = {
  chat: {
    chat_id: string;
    title: string;
    updated_at: string;
    swarm_run_id?: string | null;
    swarm_role?: string | null;
  };
  documents: KnowledgeWorkspaceDocument[];
  runs: KnowledgeWorkspaceRun[];
  research_runs: KnowledgeWorkspaceRun[];
  document_runs: KnowledgeWorkspaceRun[];
};

export type PlanPreview = {
  detected: boolean;
  request?: Record<string, unknown>;
  document?: Document;
  document_request?: Record<string, unknown>;
  plan?: {
    template?: string | null;
    confidence?: number | null;
    node_count?: number;
    inputs?: Record<string, unknown>;
    dag?: Record<string, unknown>;
  };
};

export type StepupChallenge = {
  challenge_id: string;
  method: string;
};

export type StepupVerifyResult = {
  stepup_token: string;
};

export type StepupEnrollResult = {
  user_id?: string;
  secret: string;
  provisioning_uri: string;
};

export type StepupStatus = {
  user_id: string;
  enrolled: boolean;
};

/** Export result (Pack 12) — POST /v1/exports/docx. */
export type ExportResult = {
  file_id: string;
  title: string;
};

/** Principal (user/agent) — GET/POST/PATCH /v1/principals. */
export type Principal = {
  id: string;
  type: "user" | "agent" | "service_account";
  label: string;
  timezone: string | null;
  on_call_hours: Record<string, unknown> | null;
  status: "online" | "offline" | "away";
  escalation_chain: string[] | null;
  disabled?: boolean;
  created_at: string;
  updated_at: string;
};
