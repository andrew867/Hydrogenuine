"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { hgApi } from "@/lib/hgApi";
import type { ApprovalItem } from "@/types/hg";

function _approvalSnippet(a: ApprovalItem): string | null {
  const p = a.payload as Record<string, unknown> | undefined;
  if (!p || typeof p !== "object") return null;
  const title = p.title ?? p.draft_title ?? p.subject;
  const text = p.content ?? p.draft_content ?? p.body ?? p.text ?? p.message;
  if (typeof title === "string" && title.trim()) return title.trim().slice(0, 120);
  if (typeof text === "string" && text.trim()) return text.trim().slice(0, 120);
  return null;
}
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { StepupApprovalModal, type StepupApprovalRequest } from "@/components/auth/StepupApprovalModal";
import { useKeyRingStore } from "@/store/keyRingStore";
import React from "react";
import { EmptyState, ErrorState, PageSkeleton, useToast, visibilityAwareRefetchInterval } from "hg_ui_kit";

const PAGE_SIZE = 20;

export function ApprovalsView() {
  const qc = useQueryClient();
  const { push: pushToast } = useToast();
  const stepupToken = useKeyRingStore((s) => s.stepupToken);
  const clearStepupToken = useKeyRingStore((s) => s.clearStepupToken);
  const [statusFilter, setStatusFilter] = React.useState<"pending" | "all" | "approved">("pending");
  const [page, setPage] = React.useState(1);
  const { data, isLoading, isFetching, error } = useQuery({
    queryKey: ["approvals", statusFilter, page, PAGE_SIZE],
    queryFn: () =>
      hgApi.listApprovals({
        status: statusFilter,
        limit: PAGE_SIZE,
        offset: (page - 1) * PAGE_SIZE,
      }),
    refetchInterval: statusFilter === "pending" ? visibilityAwareRefetchInterval(5_000) : visibilityAwareRefetchInterval(30_000),
  });
  const [note, setNote] = React.useState<Record<string, string>>({});
  const [actionError, setActionError] = React.useState<string | null>(null);
  const [stepupRequest, setStepupRequest] = React.useState<StepupApprovalRequest | null>(null);

  React.useEffect(() => {
    setPage(1);
  }, [statusFilter]);

  const removePendingApprovalFromCache = (approvalId: string) => {
    qc.setQueryData(
      ["approvals", statusFilter, page, PAGE_SIZE],
      (current: Awaited<ReturnType<typeof hgApi.listApprovals>> | undefined) => {
        if (!current) return current;
        const approvals = (current.approvals ?? []).filter((item) => item.id !== approvalId);
        const total = current.total != null ? Math.max(0, current.total - 1) : undefined;
        return { approvals, total };
      }
    );
  };

  const refreshApprovalRelatedState = async () => {
    await Promise.allSettled([
      qc.invalidateQueries({ queryKey: ["approvals"] }),
      qc.invalidateQueries({ queryKey: ["chats"] }),
      qc.invalidateQueries({ queryKey: ["chat"] }),
      qc.invalidateQueries({ queryKey: ["messages"] }),
      qc.invalidateQueries({ queryKey: ["tenant-me-settings"] }),
    ]);
  };

  const clearNoteForApproval = (approvalId: string) => {
    setNote((current) => {
      const next = { ...current };
      delete next[approvalId];
      return next;
    });
  };

  const handleActionSuccess = (approvalId: string) => {
    removePendingApprovalFromCache(approvalId);
    clearNoteForApproval(approvalId);
    setStepupRequest(null);
    const actionId = useKeyRingStore.getState().lastRequestId;
    if (actionId) {
      pushToast({ message: `Approval ${approvalId} updated.`, tone: "success", actionId });
    }
    void refreshApprovalRelatedState();
  };

  const handleApprovalError = (
    error: unknown,
    pendingAction: { id: string; decision?: "approve" | "deny"; kind?: string }
  ) => {
    const typed = error as Error & { code?: string };
    if (typed.code === "stepup_required") {
      if (stepupToken) clearStepupToken();
      setActionError(null);
      setStepupRequest({
        approvalId: pendingAction.id,
        decision: pendingAction.decision ?? "approve",
        note:
          pendingAction.kind != null
            ? (note[pendingAction.id] || "Auto-approved this type via policy.")
            : (note[pendingAction.id] || ""),
        ...(pendingAction.kind != null ? { kind: pendingAction.kind } : {}),
      });
      return;
    }
    setActionError(typed instanceof Error ? typed.message : "Approval action failed.");
  };

  const resolve = useMutation({
    mutationFn: async (args: { id: string; decision: "approve" | "deny"; stepupToken?: string | null }) => {
      setActionError(null);
      await hgApi.resolveApproval(args.id, args.decision, note[args.id] || "", { stepupToken: args.stepupToken ?? stepupToken });
      return args;
    },
    onMutate: async (args) => {
      await qc.cancelQueries({ queryKey: ["approvals"] });
      const previous = qc.getQueryData(["approvals", statusFilter, page, PAGE_SIZE]);
      removePendingApprovalFromCache(args.id);
      return { previous };
    },
    onSuccess: ({ id }) => {
      handleActionSuccess(id);
    },
    onError: (error, variables, context) => {
      if (context?.previous) {
        qc.setQueryData(["approvals", statusFilter, page, PAGE_SIZE], context.previous);
      }
      const typed = error as Error & { requestId?: string };
      pushToast({
        message: typed.message || "Approval action failed.",
        tone: "danger",
        actionId: typed.requestId,
      });
      handleApprovalError(error, { id: variables.id, decision: variables.decision });
    }
  });

  const autoApproveTypeAndResolve = useMutation({
    mutationFn: async (a: { id: string; kind: string; stepupToken?: string | null }) => {
      setActionError(null);
      const settings = await hgApi.getTenantMeSettings();
      const current = settings?.auto_approve_kinds ?? [];
      const next = current.includes(a.kind) ? current : [...current, a.kind];
      await hgApi.patchTenantMeSettings({ auto_approve_kinds: next });
      await hgApi.resolveApproval(a.id, "approve", note[a.id] || "Auto-approved this type via policy.", { stepupToken: a.stepupToken ?? stepupToken });
      return a;
    },
    onSuccess: ({ id }) => {
      handleActionSuccess(id);
    },
    onError: (error, variables) => {
      handleApprovalError(error, { id: variables.id, kind: variables.kind });
    }
  });

  const items = data?.approvals ?? [];
  const total = data?.total;
  const totalPages = total != null ? Math.max(1, Math.ceil(total / PAGE_SIZE)) : 1;
  const displayList = items;

  return (
    <div className="p-4 max-w-[980px] mx-auto">
      <div className="mb-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="text-lg font-semibold">Approvals</div>
          <select
            className="rounded-xl bg-bg/40 border border-border/70 px-3 py-1.5 text-sm outline-none focus:border-accent/60"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as "pending" | "all" | "approved")}
            aria-label="Filter by status"
          >
            <option value="pending">Pending (not approved)</option>
            <option value="all">All</option>
            <option value="approved">Approved</option>
          </select>
          {(isLoading || isFetching) && (
            <span className="inline-flex items-center gap-1.5 text-sm text-muted">
              <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-border border-t-accent" aria-hidden />
              {isLoading ? "Loading…" : "Refreshing…"}
            </span>
          )}
        </div>
        <div className="text-sm text-muted mt-1">Human-in-the-loop control. Default: pending only; switch to All or Approved to see history.</div>
        {error instanceof Error ? <div className="mt-2"><ErrorState message={error.message} /></div> : null}
        {isLoading ? <div className="mt-3"><PageSkeleton label="Loading approvals" rows={4} /></div> : null}
        {actionError ? <div className="mt-2 text-sm text-danger">{actionError}</div> : null}
      </div>

      <div className="grid gap-3">
        {!isLoading && !error && !displayList.length ? (
          <EmptyState
            title={statusFilter === "pending" ? "No pending approvals" : `No ${statusFilter} approvals`}
            description="New approval requests will appear here when governance blocks an action."
          />
        ) : null}

        {!isLoading && displayList.map(a => (
          <Card key={a.id}>
            <div className="flex min-w-0 items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <div className="font-semibold">{a.title}</div>
                  <Badge tone={a.risk === "high" ? "danger" : a.risk === "medium" ? "warning" : "ok"}>
                    {a.risk.toUpperCase()}
                  </Badge>
                  <Badge tone="neutral">{a.kind}</Badge>
                  <Badge tone="neutral">by {a.requestedBy}</Badge>
                </div>
                <div className="text-sm text-muted mt-1">{a.summary}</div>
                {_approvalSnippet(a) ? (
                  <div className="text-sm mt-1 text-text/90">{_approvalSnippet(a)}</div>
                ) : null}
                {a.origin ? (
                  <div className="text-xs text-muted mt-2">
                    Origin: {a.origin.type}
                    {a.origin.label ? ` • ${a.origin.label}` : ""}
                    {a.origin.chat_id ? ` • chat ${a.origin.chat_id}` : ""}
                    {a.origin.run_id ? ` • run ${a.origin.run_id}` : ""}
                  </div>
                ) : null}

                <details className="mt-3">
                  <summary className="text-xs text-muted cursor-pointer">Show payload</summary>
                  <div className="mt-2 w-full max-w-full min-w-0 overflow-hidden rounded-2xl border border-border/70 bg-bg/60">
                    <pre className="max-w-full p-3 text-xs whitespace-pre-wrap break-words">
                      {JSON.stringify(a.payload, null, 2)}
                    </pre>
                  </div>
                </details>

                <div className="mt-3">
                  <div className="text-xs text-muted mb-1">Note</div>
                  <input
                    className="w-full rounded-2xl bg-bg/40 border border-border/70 px-3 py-2 outline-none focus:border-accent/60"
                    placeholder="Optional note for audit trail"
                    value={note[a.id] || ""}
                    onChange={e => setNote(n => ({ ...n, [a.id]: e.target.value }))}
                  />
                </div>
              </div>

              {a.status === "pending" ? (
                <div className="shrink-0 flex flex-col gap-2">
                  <Button
                    tone="ok"
                    onClick={() => resolve.mutate({ id: a.id, decision: "approve" })}
                    disabled={resolve.isPending || autoApproveTypeAndResolve.isPending}
                  >
                    {resolve.isPending ? "Submitting…" : "Approve"}
                  </Button>
                  <Button
                    tone="danger"
                    onClick={() => resolve.mutate({ id: a.id, decision: "deny" })}
                    disabled={resolve.isPending || autoApproveTypeAndResolve.isPending}
                  >
                    {resolve.isPending ? "Submitting…" : "Deny"}
                  </Button>
                  <Button
                    tone="neutral"
                    onClick={() => autoApproveTypeAndResolve.mutate(a)}
                    disabled={resolve.isPending || autoApproveTypeAndResolve.isPending}
                  >
                    {autoApproveTypeAndResolve.isPending ? "Submitting…" : "Auto approve this type"}
                  </Button>
                </div>
              ) : (
                <div className="text-sm text-muted">
                  {a.status === "approved" ? "Approved" : a.status === "denied" ? "Denied" : a.status}
                  {a.resolvedAt ? ` · ${new Date(a.resolvedAt).toLocaleString()}` : ""}
                </div>
              )}
            </div>
          </Card>
        ))}
      </div>

      {!isLoading && !error && (total == null || total > PAGE_SIZE) ? (
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <Button
            tone="neutral"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
          >
            Previous
          </Button>
          <span className="text-sm text-muted">
            {total != null
              ? `Page ${page} of ${totalPages} (${total} total)`
              : `Page ${page}`}
          </span>
          <Button
            tone="neutral"
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
          >
            Next
          </Button>
        </div>
      ) : null}

      <StepupApprovalModal
        request={stepupRequest}
        actionLabel={
          stepupRequest?.decision === "deny"
            ? "Deny"
            : stepupRequest?.kind
              ? "Auto approve"
              : "Approve"
        }
        onClose={() => setStepupRequest(null)}
        onCompleted={(approvalId) => {
          handleActionSuccess(approvalId);
        }}
      />

      <div className="mt-6 text-xs text-muted">
        Tip: In production, approvals should include immutable payload hashing and a signed operator decision.
      </div>
    </div>
  );
}
