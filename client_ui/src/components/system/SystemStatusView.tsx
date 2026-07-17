"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { AsyncPageBody, Banner, KeyValueGrid } from "hg_ui_kit";
import { hgApi } from "@/lib/hgApi";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";

function statusTone(status?: string): "ok" | "warning" | "danger" | "neutral" {
  if (status === "green") return "ok";
  if (status === "yellow") return "warning";
  if (status === "red") return "danger";
  return "neutral";
}

export function SystemStatusView() {
  const versionQuery = useQuery({
    queryKey: ["system-version"],
    queryFn: () => hgApi.getSystemVersion(),
    retry: false,
  });
  const statusQuery = useQuery({
    queryKey: ["system-status"],
    queryFn: () => hgApi.getSystemStatus(),
    retry: false,
  });

  const loading = versionQuery.isLoading || statusQuery.isLoading;
  const error =
    (versionQuery.error instanceof Error ? versionQuery.error.message : null) ||
    (statusQuery.error instanceof Error ? statusQuery.error.message : null);

  const version = versionQuery.data;
  const status = statusQuery.data;
  const diagnostics = (status?.diagnostics ?? []) as Array<Record<string, unknown>>;

  return (
    <div className="p-4 max-w-[980px] mx-auto">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-lg font-semibold">System</div>
          <div className="text-sm text-muted">Gateway reachability, version, and runtime diagnostics</div>
        </div>
        <Button
          onClick={() => {
            void versionQuery.refetch();
            void statusQuery.refetch();
          }}
        >
          Refresh
        </Button>
      </div>

      <AsyncPageBody
        loading={loading}
        error={error}
        onRetry={() => {
          void versionQuery.refetch();
          void statusQuery.refetch();
        }}
      >
        {status?.status && status.status !== "green" ? (
          <Banner tone={status.status === "red" ? "danger" : "warning"}>
            System status is {status.status}. Review diagnostics below.
          </Banner>
        ) : null}

        <Card className="mb-3">
          <div className="flex items-center gap-3 mb-3">
            <div className="font-semibold">Overall status</div>
            <Badge tone={statusTone(status?.status)}>{status?.status ?? "unknown"}</Badge>
          </div>
          <KeyValueGrid
            entries={[
              { key: "Service", value: version?.service ?? "hg_gateway" },
              { key: "Version", value: version?.version ?? "—" },
              { key: "Build hash", value: version?.build_hash ?? "—" },
              { key: "Environment", value: version?.environment ?? "—" },
            ]}
          />
        </Card>

        <Card>
          <div className="font-semibold mb-3">Diagnostics</div>
          {diagnostics.length === 0 ? (
            <p className="text-sm text-muted">No diagnostics returned.</p>
          ) : (
            <div className="space-y-3">
              {diagnostics.map((row, index) => (
                <div key={`${row.component}-${index}`} className="rounded-xl border border-border/60 p-3">
                  <div className="font-medium">{String(row.component ?? "component")}</div>
                  {row.detail ? <div className="text-sm text-muted mt-1">{String(row.detail)}</div> : null}
                  {row.actionable ? (
                    <div className="text-sm text-warning mt-2">{String(row.actionable)}</div>
                  ) : null}
                  {row.error ? <div className="text-sm text-danger mt-2">{String(row.error)}</div> : null}
                </div>
              ))}
            </div>
          )}
        </Card>
      </AsyncPageBody>
    </div>
  );
}
