"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { hgApi } from "@/lib/hgApi";
import type { Principal } from "@/types/hg";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import Link from "next/link";
import React, { useEffect, useState } from "react";
import { PageSkeleton } from "hg_ui_kit";

/** Simple Next 24h coverage placeholder from on_call_hours + timezone. */
function AvailabilityPreview({ principal }: { principal: Principal }) {
  const tz = principal.timezone || "UTC";
  const hours = principal.on_call_hours;
  const status = principal.status;
  return (
    <Card className="p-3">
      <div className="font-semibold text-sm mb-2">Next 24h coverage</div>
      <div className="text-sm text-muted">
        Timezone: {tz}. Status: {status}.
        {hours && typeof hours === "object" ? (
          <div className="mt-1">On-call hours: {JSON.stringify(hours)}</div>
        ) : (
          <div className="mt-1">No on_call_hours set.</div>
        )}
        <div className="mt-2 text-xs">Gaps and primary/backup derived from on_call_hours when configured.</div>
      </div>
    </Card>
  );
}

export function PrincipalDetailView({ id }: { id: string }) {
  const qc = useQueryClient();
  const isNew = id === "new";

  const { data: principal, isLoading } = useQuery({
    queryKey: ["principal", id],
    queryFn: () => hgApi.getPrincipal(id),
    enabled: !isNew,
  });

  const { data: allPrincipals = [] } = useQuery({
    queryKey: ["principals"],
    queryFn: () => hgApi.listPrincipals(),
    enabled: true,
  });

  const [timezone, setTimezone] = useState("");
  const [status, setStatus] = useState<Principal["status"]>("offline");
  const [escalationChain, setEscalationChain] = useState<string[]>([]);
  const [escalationInput, setEscalationInput] = useState("");

  useEffect(() => {
    if (principal) {
      setTimezone(principal.timezone || "");
      setStatus(principal.status);
      setEscalationChain(principal.escalation_chain || []);
    }
  }, [principal]);

  const updateAvailability = useMutation({
    mutationFn: (body: { timezone?: string; status?: string; escalation_chain?: string[] }) =>
      hgApi.updatePrincipalAvailability(id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["principal", id] });
      qc.invalidateQueries({ queryKey: ["principals"] });
    },
  });

  const addToChain = () => {
    const trimmed = escalationInput.trim();
    if (!trimmed) return;
    const exists = allPrincipals.some((p) => p.id === trimmed);
    if (!exists) {
      alert(`Principal "${trimmed}" not found. Add it first or choose an existing id.`);
      return;
    }
    if (escalationChain.includes(trimmed)) return;
    setEscalationChain([...escalationChain, trimmed]);
    setEscalationInput("");
  };

  const removeFromChain = (idx: number) => {
    setEscalationChain(escalationChain.filter((_, i) => i !== idx));
  };

  if (isNew) {
    return (
      <div className="p-4 max-w-[980px] mx-auto">
        <div className="mb-4">
          <Link href="/principals" className="text-sm text-muted hover:text-accent">← Principals</Link>
        </div>
        <CreatePrincipalForm />
      </div>
    );
  }

  if (isLoading || !principal) {
    return (
      <div className="p-4 max-w-[980px] mx-auto">
        <PageSkeleton label="Loading principal" rows={4} />
      </div>
    );
  }

  return (
    <div className="p-4 max-w-[980px] mx-auto">
      <div className="mb-4">
        <Link href="/principals" className="text-sm text-muted hover:text-accent">← Principals</Link>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="p-4">
          <div className="font-semibold mb-3">{principal.label}</div>
          <div className="text-sm text-muted font-mono mb-4">{principal.id}</div>

          <div className="space-y-3">
            <div>
              <label className="text-xs text-muted block mb-1">Timezone</label>
              <input
                type="text"
                className="w-full rounded-xl border border-border/70 bg-bg/40 px-3 py-2 text-sm"
                value={timezone}
                onChange={(e) => setTimezone(e.target.value)}
                placeholder="e.g. America/New_York"
              />
            </div>
            <div>
              <label className="text-xs text-muted block mb-1">Status</label>
              <select
                className="w-full rounded-xl border border-border/70 bg-bg/40 px-3 py-2 text-sm"
                value={status}
                onChange={(e) => setStatus(e.target.value as Principal["status"])}
              >
                <option value="online">online</option>
                <option value="offline">offline</option>
                <option value="away">away</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-muted block mb-1">Escalation chain (principal ids, order matters)</label>
              <div className="flex gap-2 mb-2">
                <input
                  type="text"
                  className="flex-1 rounded-xl border border-border/70 bg-bg/40 px-3 py-2 text-sm"
                  value={escalationInput}
                  onChange={(e) => setEscalationInput(e.target.value)}
                  placeholder="Principal id"
                  list="principal-ids"
                />
                <Button onClick={addToChain}>Add</Button>
              </div>
              <datalist id="principal-ids">
                {allPrincipals.map((p) => (
                  <option key={p.id} value={p.id} />
                ))}
              </datalist>
              <ul className="space-y-1">
                {escalationChain.map((pid, idx) => (
                  <li key={idx} className="flex items-center gap-2 text-sm">
                    <span className="font-mono">{pid}</span>
                    <button type="button" className="text-danger text-xs" onClick={() => removeFromChain(idx)}>Remove</button>
                  </li>
                ))}
              </ul>
            </div>
            <Button
              onClick={() =>
                updateAvailability.mutate({
                  timezone: timezone || undefined,
                  status,
                  escalation_chain: escalationChain.length ? escalationChain : undefined,
                })
              }
              disabled={updateAvailability.isPending}
            >
              Save availability
            </Button>
          </div>
        </Card>

        <AvailabilityPreview principal={{ ...principal, timezone: timezone || null, status, escalation_chain: escalationChain.length ? escalationChain : null }} />
      </div>
    </div>
  );
}

function CreatePrincipalForm() {
  const qc = useQueryClient();
  const [id, setId] = useState("");
  const [type, setType] = useState<Principal["type"]>("user");
  const [label, setLabel] = useState("");
  const [timezone, setTimezone] = useState("");

  const create = useMutation({
    mutationFn: () => hgApi.createPrincipal({ id, type, label, timezone: timezone || undefined }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["principals"] });
      window.location.href = "/principals";
    },
  });

  return (
    <Card className="p-4">
      <div className="font-semibold mb-3">Create principal</div>
      <div className="space-y-3">
        <div>
          <label className="text-xs text-muted block mb-1">ID</label>
          <input
            type="text"
            className="w-full rounded-xl border border-border/70 bg-bg/40 px-3 py-2 text-sm"
            value={id}
            onChange={(e) => setId(e.target.value)}
            placeholder="unique id"
          />
        </div>
        <div>
          <label className="text-xs text-muted block mb-1">Type</label>
          <select
            className="w-full rounded-xl border border-border/70 bg-bg/40 px-3 py-2 text-sm"
            value={type}
            onChange={(e) => setType(e.target.value as Principal["type"])}
          >
            <option value="user">user</option>
            <option value="agent">agent</option>
            <option value="service_account">service_account</option>
          </select>
        </div>
        <div>
          <label className="text-xs text-muted block mb-1">Label</label>
          <input
            type="text"
            className="w-full rounded-xl border border-border/70 bg-bg/40 px-3 py-2 text-sm"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="Display name"
          />
        </div>
        <div>
          <label className="text-xs text-muted block mb-1">Timezone (optional)</label>
          <input
            type="text"
            className="w-full rounded-xl border border-border/70 bg-bg/40 px-3 py-2 text-sm"
            value={timezone}
            onChange={(e) => setTimezone(e.target.value)}
            placeholder="e.g. America/New_York"
          />
        </div>
        <Button onClick={() => create.mutate()} disabled={!id.trim() || !label.trim() || create.isPending}>
          Create
        </Button>
      </div>
    </Card>
  );
}
