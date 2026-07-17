"use client";

import React from "react";
import QRCode from "qrcode";
import { hgApi } from "@/lib/hgApi";
import { useKeyRingStore } from "@/store/keyRingStore";

type ApiLikeError = Error & {
  status?: number;
  code?: string;
  detail?: unknown;
};

export type StepupMode = "idle" | "checking" | "needs_enrollment" | "ready" | "enrolling" | "verifying" | "verified";

export function useStepupFlow(userId?: string) {
  const browserSession = useKeyRingStore((s) => s.browserSession);
  const resolvedUserId = React.useMemo(() => {
    const explicit = (userId || "").trim();
    if (explicit) return explicit;
    const principal = String(browserSession?.principal_id || "").trim();
    if (principal) return principal;
    return "default";
  }, [browserSession?.principal_id, userId]);
  const setStepupToken = useKeyRingStore((s) => s.setStepupToken);
  const [mode, setMode] = React.useState<StepupMode>("idle");
  const [challengeId, setChallengeId] = React.useState<string | null>(null);
  const [secret, setSecret] = React.useState<string | null>(null);
  const [provisioningUri, setProvisioningUri] = React.useState<string | null>(null);
  const [qrDataUrl, setQrDataUrl] = React.useState<string | null>(null);
  const [code, setCode] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);

  const reset = React.useCallback(() => {
    setMode("idle");
    setChallengeId(null);
    setSecret(null);
    setProvisioningUri(null);
    setQrDataUrl(null);
    setCode("");
    setError(null);
  }, []);

  const issueChallenge = React.useCallback(async () => {
    setError(null);
    setMode("checking");
    try {
      const challenge = await hgApi.stepupChallenge(resolvedUserId);
      setChallengeId(challenge.challenge_id);
      setMode("ready");
      return challenge.challenge_id;
    } catch (err) {
      const typed = err as ApiLikeError;
      if (typed.status === 404) {
        setChallengeId(null);
        setMode("needs_enrollment");
        return null;
      }
      setMode("idle");
      setError(typed.message || "Failed to start step-up challenge.");
      return null;
    }
  }, [resolvedUserId]);

  const enroll = React.useCallback(async () => {
    setError(null);
    setMode("enrolling");
    try {
      const enrolled = await hgApi.stepupEnroll(resolvedUserId);
      setSecret(enrolled.secret);
      setProvisioningUri(enrolled.provisioning_uri);
      try {
        const qr = await QRCode.toDataURL(enrolled.provisioning_uri, {
          width: 220,
          margin: 1,
        });
        setQrDataUrl(qr);
      } catch {
        setQrDataUrl(null);
      }
      const freshChallengeId = await hgApi.stepupChallenge(resolvedUserId).then((challenge) => challenge.challenge_id);
      setChallengeId(freshChallengeId);
      setMode("ready");
      return freshChallengeId;
    } catch (err) {
      const typed = err as ApiLikeError;
      setMode("idle");
      setError(typed.message || "Failed to enroll step-up authentication.");
      return null;
    }
  }, [resolvedUserId]);

  const verify = React.useCallback(async () => {
    const normalized = code.trim();
    if (!challengeId) {
      setError("Start a step-up challenge first.");
      return null;
    }
    if (!/^\d{6}$/.test(normalized)) {
      setError("Enter the 6-digit code from Google Authenticator.");
      return null;
    }
    setError(null);
    setMode("verifying");
    try {
      const result = await hgApi.stepupVerify(challengeId, normalized);
      setStepupToken(result.stepup_token);
      setMode("verified");
      return result.stepup_token;
    } catch (err) {
      const typed = err as ApiLikeError;
      if (typed.status === 401) {
        try {
          const freshChallenge = await hgApi.stepupChallenge(resolvedUserId);
          setChallengeId(freshChallenge.challenge_id);
          setMode("ready");
          setError("That code was rejected or the challenge expired. A fresh challenge is ready; enter the current 6-digit code and try again.");
          return null;
        } catch {
          setChallengeId(null);
          setMode("idle");
          setError("That code was rejected and the challenge could not be refreshed. Start step-up again.");
          return null;
        }
      }
      setMode("ready");
      setError(typed.message || "Step-up verification failed.");
      return null;
    }
  }, [challengeId, code, resolvedUserId, setStepupToken]);

  return {
    mode,
    challengeId,
    secret,
    provisioningUri,
    qrDataUrl,
    code,
    setCode,
    error,
    reset,
    issueChallenge,
    enroll,
    verify,
  };
}
