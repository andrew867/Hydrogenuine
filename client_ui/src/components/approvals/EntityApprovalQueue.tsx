"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { hgApi } from "@/lib/hgApi";
import type { EntityApprovalItem } from "@/types/hg";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import React from "react";

export function EntityApprovalQueue() {
  const qc = useQueryClient();
  const { data: items = [], isLoading, error } = useQuery({
    queryKey: ["entity-approvals"],
    queryFn: () => hgApi.listEntityApprovals(),
    refetchInterval: 5000,
  });
  const [note, setNote] = React.useState<Record<string, string>>({});
  const approve = useMutation({
    mutationFn: async (id: string) => {
      await hgApi.approveEntityApproval(id, note[id]);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["entity-approvals"] });
    },
  });
  const reject = useMutation({
    mutationFn: async (id: string) => {
      await hgApi.rejectEntityApproval(id, note[id]);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["entity-approvals"] });
    },
  });

  if (isLoading) return <p className="text-sm text-muted-foreground">Loading entity approvals…</p>;
  if (error) return <p className="text-sm text-destructive">Failed to load entity approvals.</p>;
  if (items.length === 0) return <p className="text-sm text-muted-foreground">No pending entity approvals.</p>;

  return (
    <div className="grid gap-3">
      <h3 className="text-sm font-semibold">Entity / Social approvals</h3>
      {items.map((item: EntityApprovalItem) => (
        <Card key={item.approval_id} className="p-4">
          <div className="text-sm font-medium">{item.entity_id}</div>
          <div className="text-xs text-muted-foreground">
            {item.target_platform ?? item.action_kind} · {item.action_kind}
          </div>
          <div className="mt-2 text-sm whitespace-pre-wrap">
            {typeof item.preview_json?.draft_text === "string"
              ? item.preview_json.draft_text.slice(0, 300)
              : JSON.stringify(item.preview_json).slice(0, 300)}
          </div>
          <div className="mt-3 flex flex-wrap gap-2 items-center">
            <input
              type="text"
              placeholder="Note (optional)"
              className="rounded border px-2 py-1 text-sm w-48"
              value={note[item.approval_id] ?? ""}
              onChange={(e) => setNote((prev) => ({ ...prev, [item.approval_id]: e.target.value }))}
            />
            <Button
              onClick={() => approve.mutate(item.approval_id)}
              disabled={approve.isPending || reject.isPending}
              className="px-2 py-1 text-xs"
            >
              Approve
            </Button>
            <Button
              onClick={() => reject.mutate(item.approval_id)}
              disabled={approve.isPending || reject.isPending}
              tone="danger"
              className="px-2 py-1 text-xs"
            >
              Reject
            </Button>
          </div>
        </Card>
      ))}
    </div>
  );
}
