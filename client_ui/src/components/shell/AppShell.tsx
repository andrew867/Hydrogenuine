"use client";

import React, { useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Sidebar } from "@/components/shell/Sidebar";
import { TopBar } from "@/components/shell/TopBar";
import { RouteBreadcrumbs } from "@/components/shell/RouteBreadcrumbs";
import { RightPanel } from "@/components/shell/RightPanel";
import { ImpersonationBanner } from "@/components/shell/ImpersonationBanner";
import { useUiStore } from "@/store/uiStore";
import { useKeyRingStore } from "@/store/keyRingStore";
import { useBrandStore } from "@/store/brandStore";
import { hgApi } from "@/lib/hgApi";
import { env } from "@/lib/env";
import { refreshBrowserSession } from "@/lib/browserAuth";
import { SkipToContent } from "hg_ui_kit";
import { cn } from "@/lib/cn";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { sidebarOpen, rightPanelOpen, setSidebarOpen } = useUiStore();
  const [isMobile, setIsMobile] = React.useState(false);
  const { restored, operatorKey, impersonationToken, browserSession, locked } = useKeyRingStore();
  const setBrand = useBrandStore((s) => s.setBrand);
  const [browserSessionProbeDone, setBrowserSessionProbeDone] = React.useState(false);

  const hasOperatorAuth = operatorKey || impersonationToken || browserSession;
  const needsOperatorKey = restored && browserSessionProbeDone && !env.demoMode && !locked && !hasOperatorAuth;
  const isLogin = pathname === "/login";

  useEffect(() => {
    if (env.demoMode) return;
    hgApi.getUiBrand().then(setBrand);
  }, [setBrand]);

  useEffect(() => {
    if (env.demoMode) return;
    refreshBrowserSession()
      .catch(() => undefined)
      .finally(() => setBrowserSessionProbeDone(true));
  }, []);
  const isSettings = pathname === "/settings";
  const showKeyRequired = needsOperatorKey && !isSettings && !isLogin;
  const workspaceChromeAllowed = !isLogin && !showKeyRequired;
  const showSidebar = workspaceChromeAllowed && sidebarOpen;
  const showRightPanel = workspaceChromeAllowed && rightPanelOpen && !!pathname?.startsWith("/chat/");

  useEffect(() => {
    if (needsOperatorKey && !isLogin && !isSettings) {
      const returnUrl = pathname && pathname !== "/" ? pathname : undefined;
      router.replace(returnUrl ? `/login?returnUrl=${encodeURIComponent(returnUrl)}` : "/login");
    }
  }, [needsOperatorKey, isLogin, isSettings, pathname, router]);

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 767px)");
    const sync = () => {
      setIsMobile(mq.matches);
      if (mq.matches) setSidebarOpen(false);
    };
    sync();
    mq.addEventListener("change", sync);
    return () => mq.removeEventListener("change", sync);
  }, [setSidebarOpen]);

  useEffect(() => {
    if (isMobile) setSidebarOpen(false);
  }, [pathname, isMobile, setSidebarOpen]);

  return (
    <div className="h-dvh w-full overflow-hidden flex flex-col relative">
      <SkipToContent />
      <div className="shrink-0 relative z-30">
        <TopBar />
        <ImpersonationBanner />
        <RouteBreadcrumbs />
      </div>
      {!env.demoMode && (!restored || !browserSessionProbeDone) ? (
        <div className="flex min-h-[calc(100dvh-56px)] items-center justify-center p-8 text-muted">
          Restoring session…
        </div>
      ) : showKeyRequired ? (
        <div className="flex flex-col items-center justify-center gap-4 p-8 text-center min-h-[calc(100dvh-56px)]">
          <p className="text-muted">Operator key required to use the app.</p>
          <Link href="/login" className="px-4 py-2 rounded-xl bg-accent/20 border border-accent/50 text-accent font-medium hover:bg-accent/30">
            Log in
          </Link>
          <Link href="/settings" className="text-sm text-muted hover:underline">Settings</Link>
        </div>
      ) : (
        <div className="flex flex-1 min-h-0">
          {showSidebar && isMobile ? (
            <button
              type="button"
              className="fixed inset-0 z-40 bg-black/50"
              aria-label="Close navigation drawer"
              onClick={() => setSidebarOpen(false)}
            />
          ) : null}
          {showSidebar ? (
            <div
              className={cn(
                isMobile
                  ? "fixed inset-y-0 left-0 z-50 w-[320px] max-w-[84vw] shadow-2xl"
                  : "relative shrink-0",
              )}
            >
              <Sidebar />
            </div>
          ) : null}
          <main id="main-content" tabIndex={-1} className="flex-1 min-w-0 min-h-0 relative z-0 outline-none">
            <div className="h-full overflow-y-auto">{children}</div>
          </main>
          {showRightPanel ? (
            <div className={cn(isMobile ? "fixed inset-y-0 right-0 z-50 max-w-[88vw] shadow-2xl" : "relative shrink-0")}>
              <RightPanel />
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}
