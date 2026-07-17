"use client";

import React, { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AsyncPageBody, TimeAgo } from "hg_ui_kit";
import { hgApi } from "@/lib/hgApi";
import { useKeyRingStore } from "@/store/keyRingStore";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";

type AuditRow = {
  event_id?: number;
  tenant_id?: string;
  event_type?: string;
  payload?: Record<string, unknown>;
  created_at?: string;
};

export function AuditLogView({ adminScope = false }: { adminScope?: boolean }) {
  const { adminKey } = useKeyRingStore();
  const [eventType, setEventType] = useState("");
  const [tenantFilter, setTenantFilter] = useState("");
  const useAdmin = adminScope && !!adminKey;

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ["audit-log", useAdmin ? "admin" : "tenant", eventType, tenantFilter],
    queryFn: () =>
      useAdmin
        ? hgApi.getAdminAudit({
            event_type: eventType || undefined,
            tenant_id: tenantFilter || undefined,
            limit: 100,
          })
        : hgApi.getTenantAudit({ event_type: eventType || undefined, limit: 100 }),
    enabled: useAdmin || !adminScope,
    retry: false,
  });

  const rows = (data?.items ?? []) as AuditRow[];
  const exportCsv = () => {
    const header = ["event_id", "tenant_id", "event_type", "created_at", "payload"];
    const lines = rows.map((row) =>
      [
        row.event_id ?? "",
        row.tenant_id ?? "",
        row.event_type ?? "",
        row.created_at ?? "",
        JSON.stringify(row.payload ?? {}),
      ]
        .map((cell) => `"${String(cell).replace(/"/g, '""')}"`)
        .join(","),
    );
    const blob = new Blob([[header.join(","), ...lines].join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `audit_${useAdmin ? "admin" : "tenant"}_${new Date().toISOString().slice(0, 10)}.csv`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const empty = !isLoading && !error && rows.length === 0;
  const errorMessage = error instanceof Error ? error.message : error ? String(error) : null;

  const subtitle = useMemo(
    () => (useAdmin ? "Cross-tenant audit events (admin key)" : "Tenant-scoped audit events"),
    [useAdmin],
  );

  return (
    <div className="p-4 max-w-[1100px] mx-auto">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="text-lg font-semibold">Audit log</div>
          <div className="text-sm text-muted">{subtitle}</div>
        </div>
        <Button onClick={() => refetch()} disabled={isFetching}>
          {isFetching ? "Refreshing…" : "Refresh"}
        </Button>
      </div>

      <Card className="mb-3">
        <div className="flex flex-wrap gap-3 items-end">
          <label className="text-sm">
            Event type
            <input
              className="mt-1 block w-48 rounded-xl border border-border/70 bg-bg/40 px-3 py-2 text-sm"
              value={eventType}
              onChange={(e) => setEventType(e.target.value)}
              placeholder="tenant.export"
            />
          </label>
          {useAdmin ? (
            <label className="text-sm">
              Tenant ID
              <input
                className="mt-1 block w-48 rounded-xl border border-border/70 bg-bg/40 px-3 py-2 text-sm"
                value={tenantFilter}
                onChange={(e) => setTenantFilter(e.target.value)}
                placeholder="default"
              />
            </label>
          ) : null}
          <Button onClick={exportCsv} disabled={rows.length === 0}>
            Export CSV
          </Button>
        </div>
      </Card>

      <AsyncPageBody loading={isLoading} error={errorMessage} onRetry={() => refetch()} empty={empty}>
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-muted border-b border-border/60">
                  <th className="py-2 pr-3">When</th>
                  <th className="py-2 pr-3">Tenant</th>
                  <th className="py-2 pr-3">Event</th>
                  <th className="py-2">Payload</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={`${row.event_id}-${row.created_at}`} className="border-b border-border/40 align-top">
                    <td className="py-2 pr-3 whitespace-nowrap">
                      {row.created_at ? <TimeAgo value={row.created_at} /> : "—"}
                    </td>
                    <td className="py-2 pr-3 font-mono text-xs">{row.tenant_id ?? "—"}</td>
                    <td className="py-2 pr-3">{row.event_type ?? "—"}</td>
                    <td className="py-2">
                      <pre className="text-xs whitespace-pre-wrap break-all text-muted">
                        {JSON.stringify(row.payload ?? {}, null, 2)}
                      </pre>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="text-xs text-muted mt-3">Total: {data?.total ?? rows.length}</div>
        </Card>
      </AsyncPageBody>
    </div>
  );
}
