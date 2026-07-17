"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useKeyRingStore } from "@/store/keyRingStore";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { env } from "@/lib/env";
import { fetchBrowserAuthConfig, startOidcLogin } from "@/lib/browserAuth";
import { refreshBrowserSession } from "@/lib/browserAuth";
import Link from "next/link";
import { PageSkeleton } from "hg_ui_kit";

function LoginFallback() {
  return (
    <div className="min-h-dvh flex items-center justify-center p-4">
      <PageSkeleton label="Loading login" rows={2} />
    </div>
  );
}

function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const returnUrl = searchParams.get("returnUrl") || "/";
  const loggedOut = searchParams.get("logged_out") === "1";
  const impersonation = searchParams.get("impersonation");
  const tenantId = searchParams.get("tenant_id");
  const { operatorKey, impersonationToken, browserSession, locked, setImpersonationToken } = useKeyRingStore();
  const [oidcEnabled, setOidcEnabled] = useState(false);
  const [oidcChecked, setOidcChecked] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Pack 13: When opened with ?impersonation=TOKEN&tenant_id=X (e.g. from Superadmin "Impersonate"), set token and redirect
  useEffect(() => {
    if (impersonation && tenantId) {
      setImpersonationToken(impersonation, tenantId);
      router.replace(returnUrl);
    }
  }, [impersonation, tenantId, returnUrl, router, setImpersonationToken]);

  useEffect(() => {
    if (env.demoMode) return;
    if (locked) return;
    if (operatorKey || impersonationToken || browserSession) {
      window.location.replace(returnUrl);
    }
  }, [browserSession, impersonationToken, locked, operatorKey, returnUrl]);

  useEffect(() => {
    if (env.demoMode) return;
    fetchBrowserAuthConfig()
      .then((cfg) => setOidcEnabled(Boolean(cfg?.oidc_enabled)))
      .catch(() => setOidcEnabled(false))
      .finally(() => setOidcChecked(true));
  }, []);

  useEffect(() => {
    if (env.demoMode) return;
    refreshBrowserSession().catch(() => undefined);
  }, []);

  useEffect(() => {
    if (env.demoMode) return;
    if (!oidcChecked || !oidcEnabled || loggedOut) return;
    if (locked || operatorKey || impersonationToken || browserSession) return;
    startOidcLogin(`${window.location.origin}${returnUrl}`);
  }, [browserSession, impersonationToken, locked, loggedOut, oidcChecked, oidcEnabled, operatorKey, returnUrl]);

  if (impersonation && tenantId) {
    return (
      <div className="min-h-dvh flex items-center justify-center p-4">
        <p className="text-muted">Redirecting as tenant…</p>
      </div>
    );
  }

  if (env.demoMode) {
    return (
      <div className="min-h-dvh flex items-center justify-center p-4">
        <Card className="p-6 max-w-md w-full">
          <div className="text-lg font-semibold mb-2">Login</div>
          <p className="text-muted text-sm mb-4">Demo mode is on; you can still continue with SSO.</p>
          <div className="space-y-3">
            <Button
              type="button"
              onClick={() => startOidcLogin(`${window.location.origin}${returnUrl}`)}
            >
              Continue with SSO
            </Button>
            <Link href="/" className="text-accent hover:underline block">Go to app</Link>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-dvh flex items-center justify-center p-4">
      <Card className="p-6 max-w-md w-full">
        <div className="text-lg font-semibold mb-2">Log in</div>
        <p className="text-muted text-sm mb-4">
          {oidcEnabled
            ? "Sending you through SSO by default."
            : "Sign in with your configured SSO provider."}
        </p>
        {loggedOut ? (
          <p className="text-xs text-muted mb-4">
            You are signed out. Choose SSO when you are ready to continue or switch accounts.
          </p>
        ) : null}
        {oidcEnabled ? (
          <div className="space-y-3">
            <Button
              type="button"
              onClick={() => startOidcLogin(`${window.location.origin}${returnUrl}`)}
            >
              Continue with SSO
            </Button>
          </div>
        ) : null}
        {!oidcEnabled ? (
          <p className="text-xs text-muted mt-4">If this page sits here, the IdP didn’t redirect. Check the gateway and Keycloak.</p>
        ) : null}
        {error ? <p className="text-xs text-danger mt-3">{error}</p> : null}
        <p className="text-xs text-muted mt-4">
          Browser sessions are now used when available.
        </p>
      </Card>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<LoginFallback />}>
      <LoginContent />
    </Suspense>
  );
}
