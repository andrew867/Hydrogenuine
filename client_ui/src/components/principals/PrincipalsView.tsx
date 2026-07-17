"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { hgApi } from "@/lib/hgApi";
import type { Principal } from "@/types/hg";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { ApiErrorDisplay, type ApiErrorLike } from "@/components/ui/ApiErrorDisplay";
import Link from "next/link";
import React, { useMemo, useState, useEffect } from "react";
import { env } from "@/lib/env";
import { useKeyRingStore } from "@/store/keyRingStore";

export function PrincipalsView() {
  const router = useRouter();
  const qc = useQueryClient();
  const { operatorKey, browserSession, locked } = useKeyRingStore();
  const [typeFilter, setTypeFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [timezoneFilter, setTimezoneFilter] = useState<string>("");
  const [search, setSearch] = useState("");
  const [includeDisabled, setIncludeDisabled] = useState(false);

  const { data: tenant } = useQuery({
    queryKey: ["tenant-me"],
    queryFn: () => hgApi.getTenantMe(),
    enabled: !env.demoMode && !locked && (!!operatorKey || !!browserSession),
    retry: false,
  });
  const isPrincipal = tenant?.role === "principal" && !!tenant?.principal_id;
  useEffect(() => {
    if (isPrincipal && tenant?.principal_id)
      router.replace(`/principals/${encodeURIComponent(tenant.principal_id)}`);
  }, [isPrincipal, tenant?.principal_id, router]);

  const { data: principals = [], isError, error } = useQuery({
    queryKey: ["principals", includeDisabled],
    queryFn: () => hgApi.listPrincipals(includeDisabled),
    enabled: !!tenant && !isPrincipal,
  });

  const setDisabled = useMutation({
    mutationFn: ({ id, disabled }: { id: string; disabled: boolean }) =>
      hgApi.updatePrincipalAvailability(id, { disabled }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["principals"] });
    },
  });

  const filtered = useMemo(() => {
    let list = principals;
    if (typeFilter) list = list.filter((p) => p.type === typeFilter);
    if (statusFilter) list = list.filter((p) => p.status === statusFilter);
    if (timezoneFilter) list = list.filter((p) => (p.timezone || "").toLowerCase().includes(timezoneFilter.toLowerCase()));
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      list = list.filter(
        (p) =>
          p.id.toLowerCase().includes(q) ||
          p.label.toLowerCase().includes(q) ||
          (p.timezone || "").toLowerCase().includes(q)
      );
    }
    return list;
  }, [principals, typeFilter, statusFilter, timezoneFilter, search]);

  const types = useMemo(() => [...new Set(principals.map((p) => p.type))], [principals]);
  const statuses = useMemo(() => [...new Set(principals.map((p) => p.status))], [principals]);
  const timezones = useMemo(() => [...new Set(principals.map((p) => p.timezone).filter(Boolean))], [principals]);

  if (isPrincipal) return <div className="p-4 text-muted">Redirecting to My availability…</div>;

  const displayError = isError && error
    ? (error instanceof Error ? error : new Error(String(error))) as ApiErrorLike
    : null;
  const friendly403 = displayError?.status === 403
    ? { ...displayError, message: "Not authorized for this tenant." }
    : displayError;

  return (
    <div className="p-4 max-w-[980px] mx-auto">
      {friendly403 && (
        <ApiErrorDisplay error={friendly403} endpoint="GET /v1/principals" className="mb-4" />
      )}
      <div className="mb-4 flex items-center justify-between flex-wrap gap-2">
        <div>
          <div className="text-lg font-semibold">Principals</div>
          <div className="text-sm text-muted">Users and agents; manage availability and escalation.</div>
        </div>
        <Link href="/principals/new">
          <Button>Add principal</Button>
        </Link>
      </div>

      <Card className="mb-4 p-3">
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <label className="text-xs text-muted block mb-1">Search</label>
            <input
              type="text"
              placeholder="id, label, timezone"
              className="w-full rounded-xl border border-border/70 bg-bg/40 px-3 py-2 text-sm"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <div>
            <label className="text-xs text-muted block mb-1">Type</label>
            <select
              className="w-full rounded-xl border border-border/70 bg-bg/40 px-3 py-2 text-sm"
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
            >
              <option value="">All</option>
              {types.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-muted block mb-1">Status</label>
            <select
              className="w-full rounded-xl border border-border/70 bg-bg/40 px-3 py-2 text-sm"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="">All</option>
              {statuses.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-muted block mb-1">Timezone</label>
            <input
              type="text"
              placeholder="Filter by timezone"
              className="w-full rounded-xl border border-border/70 bg-bg/40 px-3 py-2 text-sm"
              value={timezoneFilter}
              onChange={(e) => setTimezoneFilter(e.target.value)}
            />
          </div>
          <div className="flex items-end">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={includeDisabled}
                onChange={(e) => setIncludeDisabled(e.target.checked)}
              />
              <span className="text-sm text-muted">Show disabled</span>
            </label>
          </div>
        </div>
      </Card>

      <div className="space-y-2">
        {filtered.length === 0 ? (
          <Card>
            <div className="text-sm text-muted py-4 text-center">
              {principals.length === 0 ? "No principals. Add one to get started." : "No principals match the filters."}
            </div>
          </Card>
        ) : (
          filtered.map((p) => (
            <Card key={p.id} className="p-3 flex items-center justify-between gap-2 flex-wrap">
              <Link href={`/principals/${encodeURIComponent(p.id)}`} className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <div>
                    <span className="font-semibold">{p.label}</span>
                    <span className="text-muted text-sm ml-2 font-mono">({p.id})</span>
                    {p.disabled ? <span className="ml-2 text-xs text-danger">Disabled</span> : null}
                  </div>
                  <div className="flex items-center gap-2 text-sm text-muted">
                    <span>{p.type}</span>
                    <span>{p.status}</span>
                    {p.timezone ? <span>{p.timezone}</span> : null}
                  </div>
                </div>
              </Link>
              <Button
                tone={p.disabled ? "neutral" : "danger"}
                onClick={(e) => { e.preventDefault(); setDisabled.mutate({ id: p.id, disabled: !p.disabled }); }}
                disabled={setDisabled.isPending}
              >
                {p.disabled ? "Enable" : "Disable"}
              </Button>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
