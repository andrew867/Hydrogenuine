"use client";

import React from "react";
import Image from "next/image";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { useStepupFlow } from "@/components/auth/useStepupFlow";
import { useKeyRingStore } from "@/store/keyRingStore";

export function StepupSettingsCard() {
  const flow = useStepupFlow();
  const stepupToken = useKeyRingStore((s) => s.stepupToken);
  const stepupVerifiedAt = useKeyRingStore((s) => s.stepupVerifiedAt);
  const clearStepupToken = useKeyRingStore((s) => s.clearStepupToken);
  const canSubmitCode = flow.mode === "ready" || flow.mode === "verifying" || flow.mode === "verified";

  const verifyCurrentCode = async () => {
    const challengeId = await flow.issueChallenge();
    if (!challengeId) return;
  };

  const submit = async () => {
    await flow.verify();
  };

  return (
    <Card className="mb-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-semibold">Step-up authentication</div>
          <div className="mt-1 text-sm text-muted">
            Enroll Google Authenticator for high-risk approvals. The shared secret is stored server-side in the gateway store; this page only holds the short-lived verified token for your current session.
          </div>
        </div>
        <div className="flex flex-col items-end gap-2">
          <Badge tone={stepupToken ? "ok" : "neutral"}>{stepupToken ? "Session verified" : "Not verified"}</Badge>
          {stepupVerifiedAt ? <div className="text-xs text-muted">Verified {new Date(stepupVerifiedAt).toLocaleString()}</div> : null}
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <Button onClick={() => void verifyCurrentCode()} disabled={flow.mode === "checking" || flow.mode === "verifying" || flow.mode === "enrolling"}>
          Verify current code
        </Button>
        <Button tone="neutral" onClick={() => void flow.enroll()} disabled={flow.mode === "checking" || flow.mode === "verifying" || flow.mode === "enrolling"}>
          {flow.mode === "enrolling" ? "Preparing enrollment…" : "Enroll / rotate secret"}
        </Button>
        <Button tone="neutral" onClick={clearStepupToken} disabled={!stepupToken}>
          Clear session token
        </Button>
      </div>

      {flow.error ? <div className="mt-4 rounded-2xl border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-200">{flow.error}</div> : null}
      {flow.mode === "checking" ? <div className="mt-4 text-sm text-muted">Starting secure verification…</div> : null}
      {flow.mode === "needs_enrollment" ? (
        <div className="mt-4 rounded-2xl border border-amber-400/30 bg-amber-400/10 px-3 py-3 text-sm">
          No step-up enrollment exists yet. Click `Enroll / rotate secret` to create one for Google Authenticator.
        </div>
      ) : null}

      {flow.provisioningUri ? (
        <div className="mt-4 rounded-2xl border border-border/70 bg-card/40 p-4">
          <div className="font-medium">Google Authenticator enrollment</div>
          <div className="mt-1 text-sm text-muted">
            Scan the QR code in Google Authenticator, or use the manual secret if scanning is annoying.
          </div>
          <div className="mt-4 flex flex-col gap-4 lg:flex-row lg:items-start">
            <div className="shrink-0 rounded-2xl border border-border/70 bg-white p-3">
              {flow.qrDataUrl ? (
                <Image src={flow.qrDataUrl} alt="Step-up QR code" width={220} height={220} className="h-[220px] w-[220px]" unoptimized />
              ) : (
                <div className="flex h-[220px] w-[220px] items-center justify-center text-sm text-slate-500">QR unavailable</div>
              )}
            </div>
            <div className="min-w-0 flex-1 space-y-3">
              <div>
                <div className="text-xs uppercase tracking-wide text-muted">Manual secret</div>
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
        <div className="mt-4 rounded-2xl border border-border/70 bg-card/40 p-4">
          <div className="font-medium">Verify current code</div>
          <div className="mt-1 text-sm text-muted">
            Enter the live 6-digit code from Google Authenticator to mint a short-lived step-up token for this browser session.
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
                {flow.mode === "verifying" ? "Verifying…" : "Verify step-up"}
              </Button>
              <Button tone="neutral" onClick={() => void flow.issueChallenge()} disabled={flow.mode === "verifying"}>
                Refresh challenge
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </Card>
  );
}
