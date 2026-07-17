"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { hgApi } from "@/lib/hgApi";
import { useKeyRingStore } from "@/store/keyRingStore";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { ApiErrorDisplay, type ApiErrorLike } from "@/components/ui/ApiErrorDisplay";
import Link from "next/link";
import React, { useState } from "react";

function ConfirmDeleteRow({
  tenantId,
  onConfirm,
  onCancel,
  isPending,
}: {
  tenantId: string;
  onConfirm: () => void;
  onCancel: () => void;
  isPending: boolean;
}) {
  const [typed, setTyped] = useState("");
  const match = typed === tenantId;
  return (
    <>
      <span className="text-sm text-muted">Type tenant id to confirm:</span>
      <input
        type="text"
        className="rounded border border-border/70 px-2 py-1 text-sm w-40"
        placeholder={tenantId}
        value={typed}
        onChange={(e) => setTyped(e.target.value)}
        data-testid="confirm-tenant-input"
      />
      <Button tone="danger" onClick={onConfirm} disabled={!match || isPending}>
        Confirm delete
      </Button>
      <Button tone="neutral" onClick={onCancel}>Cancel</Button>
    </>
  );
}

export function AdminView() {
  const { adminKey } = useKeyRingStore();
  const qc = useQueryClient();
  const [confirmDeleteId, setConfirmDeleteId] = useState("");
  const [quotaEdits, setQuotaEdits] = useState<Record<string, Record<string, number>>>({});

  const { data: tenantIds = [], isLoading, isError, error } = useQuery({
    queryKey: ["admin-tenants"],
    queryFn: () => hgApi.listTenantsAdmin(),
    enabled: !!adminKey,
    retry: false,
  });

  const patchQuotas = useMutation({
    mutationFn: ({ tenantId, limits }: { tenantId: string; limits: Record<string, number> }) =>
      hgApi.patchTenantQuotas(tenantId, limits),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-tenants"] });
      setQuotaEdits({});
    },
  });

  const deleteTenant = useMutation({
    mutationFn: (tenantId: string) => hgApi.deleteTenant(tenantId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-tenants"] });
      setConfirmDeleteId("");
    },
  });

  if (!adminKey) {
    return (
      <div className="p-4 max-w-[980px] mx-auto">
        <div className="text-lg font-semibold mb-2">Admin</div>
        <Card className="p-4">
          <p className="text-muted mb-2">Admin key required to view and manage tenants.</p>
          <Link href="/settings" className="text-accent hover:underline">Open Settings to add an admin key.</Link>
        </Card>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="p-4 max-w-[980px] mx-auto">
        <div className="text-muted">Loading tenants…</div>
      </div>
    );
  }

  return (
    <div className="p-4 max-w-[980px] mx-auto">
      {isError && error && (
        <ApiErrorDisplay
          error={(error instanceof Error ? error : new Error(String(error))) as ApiErrorLike}
          endpoint="GET /v1/admin/tenants"
          className="mb-4"
        />
      )}
      <div className="mb-4">
        <div className="text-lg font-semibold">Admin — Tenants</div>
        <div className="text-sm text-muted">List tenants, set quotas, export or delete (with confirmation).</div>
      </div>

      <Card className="mb-4 p-4">
        <div className="font-semibold mb-2">Tenant IDs</div>
        {tenantIds.length === 0 ? (
          <div className="text-sm text-muted">No tenants returned (backend may not support tenant_list).</div>
        ) : (
          <ul className="space-y-2">
            {tenantIds.map((tid) => (
              <li key={tid} className="flex items-center gap-3 flex-wrap">
                <span className="font-mono">{tid}</span>
                <QuotaForm
                  tenantId={tid}
                  limits={quotaEdits[tid]}
                  onLimitsChange={(limits) => setQuotaEdits((e) => ({ ...e, [tid]: limits }))}
                  onSave={(limits) => patchQuotas.mutate({ tenantId: tid, limits })}
                  isPending={patchQuotas.isPending}
                />
                <Button
                  tone="neutral"
                  onClick={() => window.open(`#export-${tid}`, "_self")}
                >
                  Export
                </Button>
                {confirmDeleteId === tid ? (
                  <ConfirmDeleteRow
                    tenantId={tid}
                    onConfirm={() => deleteTenant.mutate(tid)}
                    onCancel={() => setConfirmDeleteId("")}
                    isPending={deleteTenant.isPending}
                  />
                ) : (
                  <Button
                    tone="danger"
                    onClick={() => setConfirmDeleteId(tid)}
                  >
                    Delete
                  </Button>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

function QuotaForm({
  tenantId,
  limits,
  onLimitsChange,
  onSave,
  isPending,
}: {
  tenantId: string;
  limits?: Record<string, number>;
  onLimitsChange: (l: Record<string, number>) => void;
  onSave: (l: Record<string, number>) => void;
  isPending: boolean;
}) {
  const [show, setShow] = useState(false);
  const [requestPerMinute, setRequestPerMinute] = useState("");
  const [maxChats, setMaxChats] = useState("");
  const apply = () => {
    const l: Record<string, number> = {};
    if (requestPerMinute) l.request_per_minute = parseInt(requestPerMinute, 10);
    if (maxChats) l.max_chats = parseInt(maxChats, 10);
    if (Object.keys(l).length) {
      onLimitsChange(l);
      onSave(l);
    }
    setShow(false);
  };
  return (
    <>
      <Button tone="neutral" onClick={() => setShow(!show)}>Quotas</Button>
      {show && (
        <div className="flex gap-2 items-center flex-wrap">
          <input
            type="number"
            placeholder="req/min"
            className="w-20 rounded border border-border/70 px-2 py-1 text-sm"
            value={requestPerMinute}
            onChange={(e) => setRequestPerMinute(e.target.value)}
          />
          <input
            type="number"
            placeholder="max_chats"
            className="w-24 rounded border border-border/70 px-2 py-1 text-sm"
            value={maxChats}
            onChange={(e) => setMaxChats(e.target.value)}
          />
          <Button onClick={apply} disabled={isPending}>Apply</Button>
        </div>
      )}
    </>
  );
}
