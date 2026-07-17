"use client";

import { env } from "@/lib/env";
import { useKeyRingStore } from "@/store/keyRingStore";
import { maskKey } from "@/lib/keyTypes";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ApiErrorDisplay, type ApiErrorLike } from "@/components/ui/ApiErrorDisplay";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { hgApi } from "@/lib/hgApi";
import React, { useCallback, useState } from "react";
import { StepupSettingsCard } from "@/components/auth/StepupSettingsCard";
import { KeystoreAccounts } from "@/components/keystore/KeystoreAccounts";
import { PageSkeleton, ThemeToggle } from "hg_ui_kit";

function RetentionExportCard() {
  const { operatorKey, browserSession, locked } = useKeyRingStore();
  const enabled = !env.demoMode && !locked && (!!operatorKey || !!browserSession);
  const { data: retention, isLoading, error, refetch } = useQuery({
    queryKey: ["tenant-retention"],
    queryFn: () => hgApi.getTenantRetention(),
    enabled,
    retry: false,
  });
  const [draft, setDraft] = React.useState<typeof retention | null>(null);
  const [exporting, setExporting] = React.useState(false);
  const [saveError, setSaveError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (retention) setDraft(retention);
  }, [retention]);

  const save = useMutation({
    mutationFn: () => hgApi.patchTenantRetention(draft!),
    onSuccess: () => {
      setSaveError(null);
      void refetch();
    },
    onError: (e) => setSaveError(e instanceof Error ? e.message : "Failed to save retention policy"),
  });

  if (!enabled) return null;
  if (isLoading) return <Card className="mb-3"><PageSkeleton label="Loading retention policy" rows={2} /></Card>;
  if (error || !draft) return null;

  return (
    <Card className="mb-3">
      <div className="font-semibold mb-2">Data retention & export</div>
      <div className="text-sm text-muted mb-3">Tenant retention windows and full export archive (zip + manifest).</div>
      {draft.legal_hold_enabled ? (
        <div className="text-sm text-warning mb-3">Legal hold is ON — automated purge is blocked for this tenant.</div>
      ) : null}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 text-sm">
        {(["chats_days", "docs_days", "proofs_days", "logs_days"] as const).map((field) => (
          <label key={field}>
            {field.replace("_days", "").replace("_", " ")} (days)
            <input
              type="number"
              min={1}
              className="mt-1 block w-full rounded-xl border border-border/70 bg-bg/40 px-3 py-2"
              value={draft[field]}
              onChange={(e) => setDraft((prev) => (prev ? { ...prev, [field]: parseInt(e.target.value, 10) || prev[field] } : prev))}
            />
          </label>
        ))}
      </div>
      <label className="mt-3 flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={draft.legal_hold_enabled}
          onChange={(e) => setDraft((prev) => (prev ? { ...prev, legal_hold_enabled: e.target.checked } : prev))}
        />
        Legal hold
      </label>
      {saveError ? <div className="text-sm text-danger mt-2">{saveError}</div> : null}
      <div className="mt-4 flex flex-wrap gap-2">
        <Button onClick={() => save.mutate()} disabled={save.isPending}>
          {save.isPending ? "Saving…" : "Save retention"}
        </Button>
        <Button
          onClick={async () => {
            setExporting(true);
            try {
              await hgApi.downloadTenantExport();
            } catch (e) {
              setSaveError(e instanceof Error ? e.message : "Export failed");
            } finally {
              setExporting(false);
            }
          }}
          disabled={exporting}
        >
          {exporting ? "Preparing export…" : "Download full export"}
        </Button>
      </div>
    </Card>
  );
}

function ApprovalPolicyCard() {
  const { data: settings, isLoading, error } = useQuery({
    queryKey: ["tenant-me-settings"],
    queryFn: () => hgApi.getTenantMeSettings(),
    retry: false,
  });
  const qc = useQueryClient();
  const canEdit = settings?.can_edit === true;
  const patch = useMutation({
    mutationFn: (body: { first_turn_approval_required?: boolean; auto_approve_kinds?: string[] }) =>
      hgApi.patchTenantMeSettings(body),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["tenant-me-settings"] }),
  });
  if (error || isLoading || !settings) return null;
  const firstTurn = settings.first_turn_approval_required ?? false;
  const autoKinds = settings.auto_approve_kinds ?? [];
  const chatTurnAuto = autoKinds.includes("chat_turn");
  return (
    <Card className="mb-3">
      <div className="font-semibold mb-2">Approval &amp; policies</div>
      <div className="text-sm text-muted mb-3">
        {canEdit
          ? "Tenant-admin controls for first-reply approval and auto-approval by kind."
          : "Current tenant approval posture. Editing is limited to tenant-admin sessions."}
      </div>
      <div className="space-y-3">
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={firstTurn}
            onChange={(e) => patch.mutate({ first_turn_approval_required: e.target.checked })}
            disabled={patch.isPending || !canEdit}
          />
          <span>Require approval before first reply</span>
        </label>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={chatTurnAuto}
            onChange={(e) => {
              const next = e.target.checked
                ? [...new Set([...autoKinds, "chat_turn"])]
                : autoKinds.filter((k) => k !== "chat_turn");
              patch.mutate({ auto_approve_kinds: next });
            }}
            disabled={patch.isPending || !canEdit}
          />
          <span>Auto-approve chat turns</span>
        </label>
      </div>
    </Card>
  );
}

function TenantUsageDetail() {
  const { data: usage, isLoading } = useQuery({
    queryKey: ["tenant-usage"],
    queryFn: () => hgApi.getTenantUsage(),
    enabled: !env.demoMode,
  });
  const [open, setOpen] = useState(false);
  if (isLoading || !usage) return null;
  const u = usage.usage || {};
  const keys = Object.keys(u).sort();
  return (
    <Card className="mb-3">
      <button
        type="button"
        className="w-full flex items-center justify-between p-3 text-left"
        onClick={() => setOpen(!open)}
      >
        <span className="font-semibold">Tenant usage detail</span>
        <span className="text-muted text-sm">{open ? "Hide" : "Show"}</span>
      </button>
      {open && (
        <div className="px-3 pb-3 grid gap-2 text-sm">
          {keys.length === 0 ? (
            <div className="text-muted">No usage counters yet.</div>
          ) : (
            keys.map((k) => (
              <div key={k} className="flex justify-between gap-3">
                <span className="text-muted">{k}</span>
                <span className="font-mono">{String(u[k])}</span>
              </div>
            ))
          )}
        </div>
      )}
    </Card>
  );
}

function ArchivedChatsCard() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const { data: archivedChats = [], isLoading } = useQuery({
    queryKey: ["archived-chats"],
    queryFn: () => hgApi.listChats({ includeArchived: true, archivedOnly: true }),
    retry: false,
  });
  const { data: deletedChats = [] } = useQuery({
    queryKey: ["deleted-chats"],
    queryFn: () => hgApi.listChats({ includeDeleted: true, deletedOnly: true, includeArchived: true }),
    retry: false,
  });
  const groupedSwarms = new Map<string, typeof archivedChats>();
  const standalone = archivedChats.filter((chat) => !chat.swarmRunId);
  const deletedSwarms = new Map<string, typeof deletedChats>();
  const deletedStandalone = deletedChats.filter((chat) => !chat.swarmRunId);
  archivedChats.filter((chat) => !!chat.swarmRunId).forEach((chat) => {
    const runId = String(chat.swarmRunId);
    groupedSwarms.set(runId, [...(groupedSwarms.get(runId) ?? []), chat]);
  });
  deletedChats.filter((chat) => !!chat.swarmRunId).forEach((chat) => {
    const runId = String(chat.swarmRunId);
    deletedSwarms.set(runId, [...(deletedSwarms.get(runId) ?? []), chat]);
  });

  const restoreChat = async (chatId: string) => {
    await hgApi.restoreChat(chatId);
    await qc.invalidateQueries({ queryKey: ["chats"] });
    await qc.invalidateQueries({ queryKey: ["archived-chats"] });
    await qc.invalidateQueries({ queryKey: ["deleted-chats"] });
  };
  const restoreSwarm = async (swarmRunId: string) => {
    await hgApi.restoreSwarm(swarmRunId);
    await qc.invalidateQueries({ queryKey: ["chats"] });
    await qc.invalidateQueries({ queryKey: ["archived-chats"] });
    await qc.invalidateQueries({ queryKey: ["deleted-chats"] });
  };

  return (
    <Card className="mb-3">
      <div className="font-semibold mb-2">Archived chats &amp; swarms</div>
      <div className="text-sm text-muted mb-3">Older chats are auto-archived and hidden from the sidebar.</div>
      <div className="flex items-center justify-between gap-3">
        <div className="text-sm text-muted">
          {isLoading ? "Loading archived items…" : `${archivedChats.length} archived · ${deletedChats.length} deleted`}
        </div>
        <Button onClick={() => setOpen(true)}>Open archive</Button>
      </div>
      {open ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={() => setOpen(false)}>
          <div className="w-full max-w-3xl rounded-[28px] border border-border/80 bg-bg shadow-soft" onClick={(event) => event.stopPropagation()}>
            <div className="flex items-center justify-between border-b border-border/70 px-5 py-4">
              <div>
                <div className="font-semibold">Archived chats &amp; swarms</div>
                <div className="text-sm text-muted">Restore archived work without leaving settings.</div>
              </div>
              <Button onClick={() => setOpen(false)}>Close</Button>
            </div>
            <div className="max-h-[70vh] overflow-y-auto px-5 py-4 space-y-3">
              {isLoading ? <div className="text-sm text-muted">Loading archived items…</div> : null}
              {!isLoading && archivedChats.length === 0 ? <div className="text-sm text-muted">No archived chats right now.</div> : null}
              {Array.from(deletedSwarms.entries()).map(([runId, chats]) => (
                <div key={`deleted-${runId}`} className="rounded-2xl border border-rose-400/20 bg-rose-400/5 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="font-medium">{chats.find((chat) => chat.swarmRole === "orchestrator")?.title || "Deleted swarm"}</div>
                      <div className="text-xs text-muted">
                        {chats.length} deleted chat(s) · restore by {chats[0]?.restoreDeadlineAt ? new Date(chats[0].restoreDeadlineAt).toLocaleString() : "30 days"}
                      </div>
                    </div>
                    <Button onClick={() => void restoreSwarm(runId)}>Restore swarm</Button>
                  </div>
                </div>
              ))}
              {Array.from(groupedSwarms.entries()).map(([runId, chats]) => (
                <div key={runId} className="rounded-2xl border border-border/70 bg-bg/40 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="font-medium">{chats.find((chat) => chat.swarmRole === "orchestrator")?.title || "Archived swarm"}</div>
                      <div className="text-xs text-muted">{chats.length} archived chat(s)</div>
                    </div>
                    <Button onClick={() => void restoreSwarm(runId)}>Restore swarm</Button>
                  </div>
                </div>
              ))}
              {standalone.map((chat) => (
                <div key={chat.id} className="rounded-2xl border border-border/70 bg-bg/40 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="font-medium">{chat.title}</div>
                      <div className="text-xs text-muted">{chat.archiveReason || "manual"} · {chat.archivedAt ? new Date(chat.archivedAt).toLocaleString() : "archived"}</div>
                    </div>
                    <Button onClick={() => void restoreChat(chat.id)}>Restore</Button>
                  </div>
                </div>
              ))}
              {deletedStandalone.map((chat) => (
                <div key={`deleted-${chat.id}`} className="rounded-2xl border border-rose-400/20 bg-rose-400/5 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="font-medium">{chat.title}</div>
                      <div className="text-xs text-muted">
                        {chat.deleteReason || "manual"} · restore by {chat.restoreDeadlineAt ? new Date(chat.restoreDeadlineAt).toLocaleString() : "30 days"}
                      </div>
                    </div>
                    <Button onClick={() => void restoreChat(chat.id)}>Restore</Button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : null}
    </Card>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <div className="text-muted">{k}</div>
      <div className="font-mono text-xs bg-bg/40 border border-border/70 rounded-xl px-2 py-1 max-w-[70%] truncate">
        {v}
      </div>
    </div>
  );
}

/** Hold-to-reveal: show full key only while pointer is down. */
function RevealKey({ value, children }: { value: string; children: React.ReactNode }) {
  const [reveal, setReveal] = useState(false);
  return (
    <span
      className="select-none font-mono text-xs"
      onPointerDown={() => setReveal(true)}
      onPointerUp={() => setReveal(false)}
      onPointerLeave={() => setReveal(false)}
    >
      {reveal ? value : children}
    </span>
  );
}

function KeyRow({
  label,
  keyClass,
  value,
  meta,
  onSet,
  onCopyMasked,
  onValidate,
}: {
  label: string;
  keyClass: "operator" | "admin" | "service";
  value: string | null;
  meta: { baseUrl: string; label: string; lastUsedAt: string } | null;
  onSet: (v: string) => void;
  onCopyMasked: () => void;
  onValidate?: () => void;
}) {
  const [input, setInput] = useState("");
  const hasKey = !!value;
  return (
    <div className="space-y-2">
      <div className="font-medium text-sm">{label}</div>
      {hasKey ? (
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-muted text-xs">Key:</span>
          <RevealKey value={value!}>{maskKey(value!)}</RevealKey>
          <Button onClick={onCopyMasked}>Copy masked</Button>
          {onValidate ? <Button onClick={onValidate}>Validate</Button> : null}
          <Button tone="danger" onClick={() => onSet("")}>
            Remove
          </Button>
          {meta?.lastUsedAt ? (
            <span className="text-xs text-muted">Last used: {new Date(meta.lastUsedAt).toLocaleString()}</span>
          ) : null}
        </div>
      ) : (
        <div className="flex gap-2">
          <input
            type="password"
            placeholder={`Enter ${label} key`}
            className="flex-1 rounded-xl border border-border/70 bg-bg/40 px-3 py-2 text-sm"
            value={input}
            onChange={(e) => setInput(e.target.value)}
          />
          <Button onClick={() => { onSet(input); setInput(""); }} disabled={!input.trim()}>
            Add
          </Button>
        </div>
      )}
      {meta ? (
        <div className="text-xs text-muted">
          Environment: {meta.label} — {meta.baseUrl}
        </div>
      ) : null}
    </div>
  );
}

export function SettingsView() {
  const [demo, setDemo] = React.useState(env.demoMode);
  const {
    locked,
    operatorKey,
    adminKey,
    serviceKey,
    browserSession,
    tenantOverride,
    readOnlyMode,
    lock,
    setOperatorKey,
    setAdminKey,
    setServiceKey,
    setTenantOverride,
    setReadOnlyMode,
    confirmCrossEnv,
  } = useKeyRingStore();

  const { data: tenant, isLoading: tenantLoading } = useQuery({
    queryKey: ["tenant-me"],
    queryFn: () => hgApi.getTenantMe(),
    enabled: !env.demoMode && !locked && (!!operatorKey || !!browserSession),
    retry: false,
  });

  const handleCopyMasked = useCallback((key: string) => {
    navigator.clipboard?.writeText(maskKey(key));
  }, []);

  const [validateError, setValidateError] = useState<ApiErrorLike | null>(null);
  const validateOperator = useCallback(async () => {
    setValidateError(null);
    try {
      const t = await hgApi.getTenantMe();
      alert(t ? `OK — tenant: ${t.tenant_id}` : "Failed");
    } catch (e) {
      setValidateError((e instanceof Error ? e : new Error(String(e))) as ApiErrorLike);
    }
  }, []);
  const validateAdmin = useCallback(async () => {
    setValidateError(null);
    try {
      await hgApi.adminPing();
      alert("Admin key OK");
    } catch (e) {
      setValidateError((e instanceof Error ? e : new Error(String(e))) as ApiErrorLike);
    }
  }, []);

  return (
    <div className="p-4 max-w-[980px] mx-auto">
      <div className="mb-4">
        <div className="text-lg font-semibold">Settings</div>
        <div className="text-sm text-muted">API keys, tenant context, and backend integration</div>
      </div>

      <Card className="mb-3">
        <ThemeToggle />
      </Card>

      {locked ? (
        <Card>
          <div className="text-center py-4">
            <div className="text-muted mb-2">Session locked. Keys and overrides have been cleared.</div>
            <div className="text-sm text-muted">Close this tab or add keys again in Settings to continue.</div>
          </div>
        </Card>
      ) : (
        <>
          <Card className="mb-3">
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <div>
                <div className="font-semibold">Lock</div>
                <div className="text-sm text-muted">Clear all keys and tenant overrides immediately.</div>
              </div>
              <Button tone="danger" onClick={lock}>
                Lock
              </Button>
            </div>
          </Card>

          {validateError && (
            <ApiErrorDisplay error={validateError} endpoint="Validate key" className="mb-3" />
          )}
          <Card className="mb-3">
            <div className="font-semibold mb-3">API keys</div>
            <div className="space-y-4">
              <KeyRow
                label="Operator key (tenant-scoped)"
                keyClass="operator"
                value={operatorKey?.value ?? null}
                meta={operatorKey?.meta ?? null}
                onSet={(v) => setOperatorKey(v || null)}
                onCopyMasked={() => operatorKey && handleCopyMasked(operatorKey.value)}
                onValidate={operatorKey ? validateOperator : undefined}
              />
              <KeyRow
                label="Admin key (admin endpoints only)"
                keyClass="admin"
                value={adminKey?.value ?? null}
                meta={adminKey?.meta ?? null}
                onSet={(v) => setAdminKey(v || null)}
                onCopyMasked={() => adminKey && handleCopyMasked(adminKey.value)}
                onValidate={adminKey ? validateAdmin : undefined}
              />
              <KeyRow
                label="Service key (optional)"
                keyClass="service"
                value={serviceKey?.value ?? null}
                meta={serviceKey?.meta ?? null}
                onSet={(v) => setServiceKey(v || null)}
                onCopyMasked={() => serviceKey && handleCopyMasked(serviceKey.value)}
              />
            </div>
            <div className="mt-3 text-xs text-muted">
              Keys are stored in memory only. Lock clears them. Hold on masked key to reveal.
            </div>
            <div className="mt-2">
              <Button onClick={confirmCrossEnv}>Confirm cross-environment (allow 1 min)</Button>
              <span className="text-xs text-muted ml-2">Use if a request was blocked due to key bound to different base URL.</span>
            </div>
          </Card>

          {((!env.demoMode && (operatorKey || browserSession)) || env.demoMode) ? <StepupSettingsCard /> : null}

          {((!env.demoMode && (operatorKey || browserSession)) || env.demoMode) && (
            <>
              {!env.demoMode ? (
                <>
                  <Card className="mb-3">
                    <div className="font-semibold mb-2">Current tenant</div>
                    {tenantLoading ? (
                      <PageSkeleton label="Loading settings" rows={3} />
                    ) : tenant ? (
                      <div className="grid gap-2 text-sm">
                        <Row k="Tenant ID" v={tenant.tenant_id} />
                        <Row k="Environment" v={tenant.environment} />
                        {tenant.role ? <Row k="Role" v={tenant.role} /> : null}
                        {tenant.principal_id ? <Row k="Principal" v={tenant.principal_id} /> : null}
                        {Object.keys(tenant.usage || {}).length > 0 ? (
                          <div className="text-muted">Usage snapshot: {JSON.stringify(tenant.usage)}</div>
                        ) : null}
                        {tenant.principal_missing ? (
                          <div className="text-xs text-muted">
                            This principal session is valid, but no local principal profile has been provisioned yet.
                          </div>
                        ) : null}
                      </div>
                    ) : (
                      <div className="text-sm text-muted">Could not load tenant details for this session.</div>
                    )}
                  </Card>
                  <TenantUsageDetail />
                  <ApprovalPolicyCard />
                  <Card className="mb-3">
                    <KeystoreAccounts />
                  </Card>
                </>
              ) : null}
              <ArchivedChatsCard />
            </>
          )}

          {env.devTenantHeader && (
            <Card className="mb-3">
              <div className="font-semibold mb-2">Dev: Tenant override</div>
              <div className="text-sm text-muted mb-2">Override X-Tenant-ID (dev only). Leave empty to use key mapping.</div>
              <input
                type="text"
                placeholder="e.g. default or tenant_a"
                className="w-full rounded-xl border border-border/70 bg-bg/40 px-3 py-2 text-sm"
                value={tenantOverride ?? ""}
                onChange={(e) => setTenantOverride(e.target.value || null)}
              />
            </Card>
          )}

          <RetentionExportCard />

          <Card className="mb-3">
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <div>
                <div className="font-semibold">Read-only mode</div>
                <div className="text-sm text-muted">Disables admin and destructive actions (safety affordance only).</div>
              </div>
              <Badge tone={readOnlyMode ? "ok" : "neutral"}>{readOnlyMode ? "ON" : "OFF"}</Badge>
              <Button onClick={() => setReadOnlyMode(!readOnlyMode)}>{readOnlyMode ? "Turn off" : "Turn on"}</Button>
            </div>
          </Card>
        </>
      )}

      <Card className="mb-3">
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <div className="text-sm text-muted">
              When enabled, UI uses Next.js mock endpoints. Turn off when your HG backend is online.
            </div>
          </div>
          <Badge tone={demo ? "warning" : "ok"}>{demo ? "ON" : "OFF"}</Badge>
        </div>
        <div className="mt-4 flex gap-2">
          <Button onClick={() => setDemo((v) => !v)}>Toggle demo mode</Button>
        </div>
      </Card>

      <Card className="mb-3">
        <div className="font-semibold mb-2">Backend endpoints</div>
        <div className="text-sm text-muted">From environment variables.</div>
        <div className="mt-3 grid gap-2 text-sm">
          <Row k="API base" v={env.apiBase} />
          <Row k="SSE url" v={env.sseUrl} />
          <Row k="WS url" v={env.wsUrl} />
        </div>
      </Card>

      <Card className="mb-3">
        <div className="font-semibold mb-2">Security notes</div>
        <ul className="text-sm text-muted list-disc pl-5 space-y-1">
          <li>Keys are in-memory by default. Lock clears them.</li>
          <li>Use short-lived tokens when possible; rotate via validate then switch key.</li>
          <li>Sign approvals server-side; audit logs never include raw keys.</li>
        </ul>
      </Card>
    </div>
  );
}
