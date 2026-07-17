"use client";

import React from "react";
import Image from "next/image";
import { Button } from "@/components/ui/Button";
import { useStepupFlow } from "@/components/auth/useStepupFlow";
import { hgApi } from "@/lib/hgApi";

export type StepupApprovalRequest = {
  approvalId: string;
  decision: "approve" | "deny";
  note: string;
  kind?: string;
};

type StepupApprovalModalProps = {
  request: StepupApprovalRequest | null;
  actionLabel: string;
  onClose: () => void;
  onCompleted: (approvalId: string) => void;
};

export function StepupApprovalModal({ request, actionLabel, onClose, onCompleted }: StepupApprovalModalProps) {
  const open = !!request;
  const flow = useStepupFlow();
  const canSubmitCode = flow.mode === "ready" || flow.mode === "verifying" || flow.mode === "verified";
  const { reset, issueChallenge } = flow;
  const [actionError, setActionError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!open) {
      reset();
      setActionError(null);
      return;
    }
    reset();
    setActionError(null);
    void issueChallenge();
  }, [issueChallenge, open, reset]);

  if (!open) return null;

  const submit = async () => {
    if (!request) return;
    const pendingRequest = request;
    const token = await flow.verify();
    if (!token) return;
    try {
      setActionError(null);
      if (pendingRequest.kind) {
        const settings = await hgApi.getTenantMeSettings();
        const current = settings?.auto_approve_kinds ?? [];
        const next = current.includes(pendingRequest.kind) ? current : [...current, pendingRequest.kind];
        await hgApi.patchTenantMeSettings({ auto_approve_kinds: next });
      }
      await hgApi.resolveApproval(pendingRequest.approvalId, pendingRequest.decision, pendingRequest.note, { stepupToken: token });
      onCompleted(pendingRequest.approvalId);
      onClose();
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "Approval action failed after step-up verification.");
    }
  };

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/60 p-4" onClick={onClose}>
      <div
        className="w-full max-w-xl rounded-[28px] border border-border/80 bg-bg shadow-soft"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4 border-b border-border/70 px-5 py-4">
          <div>
            <div className="font-semibold">Step-up authentication required</div>
            <div className="mt-1 text-sm text-muted">
              High-risk approvals need a fresh Google Authenticator code before we can {actionLabel.toLowerCase()} this item.
            </div>
          </div>
          <Button tone="neutral" onClick={onClose}>Close</Button>
        </div>
        <div className="space-y-4 px-5 py-4">
          {actionError ? <div className="rounded-2xl border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-200">{actionError}</div> : null}
          {flow.error ? <div className="rounded-2xl border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-200">{flow.error}</div> : null}
          {flow.mode === "checking" ? <div className="text-sm text-muted">Starting secure verification…</div> : null}
          {flow.mode === "needs_enrollment" ? (
            <div className="rounded-2xl border border-amber-400/30 bg-amber-400/10 p-4">
              <div className="font-medium">No step-up authenticator is enrolled yet.</div>
              <div className="mt-1 text-sm text-muted">
                Enroll Google Authenticator now, or set it up later from `Settings`.
              </div>
              <div className="mt-3">
                <Button onClick={() => void flow.enroll()}>
                  Enroll with Google Authenticator
                </Button>
              </div>
            </div>
          ) : null}
          {flow.provisioningUri ? (
            <div className="rounded-2xl border border-border/70 bg-card/40 p-4">
              <div className="font-medium">Google Authenticator setup</div>
              <div className="mt-1 text-sm text-muted">
                Scan this QR code in Google Authenticator, or enter the secret manually if you prefer.
              </div>
              <div className="mt-4 flex flex-col gap-4 md:flex-row md:items-start">
                <div className="shrink-0 rounded-2xl border border-border/70 bg-white p-3">
                  {flow.qrDataUrl ? (
                    <Image src={flow.qrDataUrl} alt="Step-up QR code" width={220} height={220} className="h-[220px] w-[220px]" unoptimized />
                  ) : (
                    <div className="flex h-[220px] w-[220px] items-center justify-center text-sm text-slate-500">QR unavailable</div>
                  )}
                </div>
                <div className="min-w-0 space-y-3">
                  <div>
                    <div className="text-xs uppercase tracking-wide text-muted">Secret</div>
                    <div className="mt-1 break-all rounded-xl border border-border/70 bg-bg/50 px-3 py-2 font-mono text-xs">
                      {flow.secret}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-wide text-muted">Provisioning URI</div>
                    <div className="mt-1 break-all rounded-xl border border-border/70 bg-bg/50 px-3 py-2 font-mono text-[11px]">
                      {flow.provisioningUri}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ) : null}
          {canSubmitCode ? (
            <div className="rounded-2xl border border-border/70 bg-card/40 p-4">
              <div className="font-medium">Enter current code</div>
              <div className="mt-1 text-sm text-muted">
                Use the current 6-digit code from Google Authenticator.
              </div>
              <div className="mt-3 flex flex-col gap-3 sm:flex-row">
                <input
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  maxLength={6}
                  value={flow.code}
                  onChange={(event) => flow.setCode(event.target.value.replace(/\D/g, "").slice(0, 6))}
                  placeholder="123456"
                  className="w-full rounded-xl border border-border/70 bg-bg/40 px-3 py-2 text-lg tracking-[0.35em] outline-none focus:border-accent/60 sm:max-w-[180px]"
                />
                <div className="flex gap-2">
                  <Button onClick={() => void submit()} disabled={flow.mode === "verifying"}>
                    {flow.mode === "verifying" ? "Verifying…" : `${actionLabel} with step-up`}
                  </Button>
                  <Button tone="neutral" onClick={() => void flow.issueChallenge()} disabled={flow.mode === "verifying"}>
                    Refresh challenge
                  </Button>
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
