"use client";

import React, { useEffect, useMemo, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useUiStore } from "@/store/uiStore";
import { useKeyRingStore } from "@/store/keyRingStore";
import { useBrandStore } from "@/store/brandStore";
import { useQuery } from "@tanstack/react-query";
import { hgApi } from "@/lib/hgApi";
import { env } from "@/lib/env";
import { CommandPalette, EnvBadge, NotificationBell, useNotificationStream } from "hg_ui_kit";
import { getHeaders } from "@/lib/keyRing";
import { Icon } from "@/components/ui/Icon";
import { HardNavLink } from "@/components/navigation/HardNavLink";
import { cn } from "@/lib/cn";
import { logoutBrowserSession, startOidcLogout } from "@/lib/browserAuth";
import { getRouteLabel } from "@/lib/routeTaxonomy";
import { operatorHashUrl } from "@/lib/operatorLinks";

export function TopBar() {
  const path = usePathname();
  const router = useRouter();
  const [paletteOpen, setPaletteOpen] = useState(false);
  const { sidebarOpen, rightPanelOpen, setSidebarOpen, setRightPanelOpen } = useUiStore();
  const { operatorKey, adminKey, impersonationToken, tenantOverride, locked, lock, browserSession } = useKeyRingStore();
  const brand = useBrandStore((s) => s.brand);
  const isLogin = path === "/login";
  const hasWorkspaceAuth = env.demoMode || (!!operatorKey && !locked) || !!adminKey || !!impersonationToken || !!browserSession;
  const canToggleSidebar = hasWorkspaceAuth && !isLogin;
  const canToggleRightPanel = hasWorkspaceAuth && !!path?.startsWith("/chat/");

  const handleLogout = async () => {
    const hadBrowserSession = !!browserSession;
    lock();
    setSidebarOpen(false);
    setRightPanelOpen(false);
    if (hadBrowserSession) {
      useKeyRingStore.getState().setBrowserSession(null);
      const returnUrl = `${window.location.origin}/login?logged_out=1`;
      startOidcLogout(returnUrl);
      return;
    }
    await logoutBrowserSession().catch(() => undefined);
    if (typeof window !== "undefined") {
      window.location.assign("/login");
      return;
    }
    router.replace("/login");
  };

  const { data: tenant } = useQuery({
    queryKey: ["tenant-me"],
    queryFn: () => hgApi.getTenantMe(),
    enabled: !env.demoMode && !locked && (!!operatorKey || !!browserSession),
    retry: false,
  });

  const devOverrideActive = env.devTenantHeader && !!tenantOverride;
  const routeLabel = getRouteLabel(path);
  const isSuperadmin = tenant?.role === "superadmin" || !!adminKey;
  const notificationsEnabled = !env.demoMode && hasWorkspaceAuth;
  const { items: notifications } = useNotificationStream({
    streamUrl: hgApi.notificationsStreamUrl(),
    enabled: notificationsEnabled,
    headers: () => {
      const auth = getHeaders("operator", { baseUrl: env.apiBase || undefined, skipEnvCheck: false });
      return auth.ok ? auth.headers : {};
    },
  });

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPaletteOpen(true);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const paletteActions = useMemo(
    () => [
      { id: "home", label: "Go home", run: () => router.push("/") },
      { id: "approvals", label: "Open approvals", run: () => router.push("/approvals") },
      { id: "settings", label: "Open settings", run: () => router.push("/settings") },
      {
        id: "operator-runs",
        label: "Operator console: Runs",
        keywords: ["operator", "runs"],
        run: () => {
          window.location.assign(operatorHashUrl("/"));
        },
      },
      {
        id: "operator-proofs",
        label: "Operator console: Proofs",
        keywords: ["operator", "proofs"],
        run: () => {
          window.location.assign(operatorHashUrl("/proofs"));
        },
      },
    ],
    [router],
  );

  const active = (href: string) =>
    cn(
      "px-3 py-2 rounded-xl text-sm text-muted hover:bg-card/70 transition",
      (href === "/" ? path === "/" : path?.startsWith(href)) ? "bg-card/90 text-text" : ""
    );

  return (
    <>
      {devOverrideActive && (
        <div className="bg-danger/20 border-b border-danger/50 text-danger px-3 py-1.5 text-sm font-medium flex items-center gap-2">
          <span>DEV OVERRIDE</span>
          <span className="font-mono">{tenantOverride}</span>
        </div>
      )}
      <header className="h-14 flex items-center justify-between px-3 border-b border-border/80 bg-bg/80 backdrop-blur">
        <div className="flex items-center gap-2">
          <button
            aria-label="Toggle chats"
            className="p-2 rounded-xl hover:bg-card/70 disabled:opacity-40 disabled:cursor-not-allowed"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            disabled={!canToggleSidebar}
          >
            <Icon name="panelLeft" />
          </button>
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-2xl bg-accent/15 border border-accent/30 flex items-center justify-center shadow-soft overflow-hidden">
              {brand?.logo_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={brand.logo_url} alt="" className="h-full w-full object-cover" />
              ) : (
                <span className="text-accent font-semibold">hg</span>
              )}
            </div>
            <div className="leading-tight">
              <div className="font-semibold">{brand?.display_name ?? "Hydrogenuine"}</div>
              <div className="text-xs text-muted">
                {tenant
                  ? `${tenant.tenant_id}${tenant.role === "tenant_admin" ? " · Tenant admin" : tenant.role === "principal" && tenant.principal_id ? ` · Principal: ${tenant.principal_id}` : tenant.role === "operator" ? " · Operator" : ""}`
                  : env.demoMode
                    ? "demo"
                    : "client UI"}
                <span className="ml-2">· {routeLabel}</span>
              </div>
            </div>
          </div>
        </div>

        <nav className="flex items-center gap-1">
          <EnvBadge env={env.demoMode ? "demo" : "client"} mode={env.demoMode ? "demo" : "live"} systemHref="/system" />
          {notificationsEnabled ? (
            <NotificationBell
              items={notifications}
              onOpenItem={(item) => {
                if (item.href) router.push(item.href);
              }}
            />
          ) : null}
          <HardNavLink href="/" className={active("/")}>
            Home
          </HardNavLink>
          {adminKey ? (
            <HardNavLink href="/admin" className={active("/admin")}>
              Admin
            </HardNavLink>
          ) : null}
          <HardNavLink href="/approvals" className={active("/approvals")}>
            Approvals
          </HardNavLink>
          <HardNavLink href="/settings" className={active("/settings")}>
            Settings
          </HardNavLink>
          {!env.demoMode && (operatorKey || adminKey || browserSession) && (
            <button
              type="button"
              onClick={handleLogout}
              className="px-3 py-2 rounded-xl text-sm text-muted hover:bg-card/70 transition"
            >
              Log out
            </button>
          )}
          <button
            aria-label="Toggle details"
            className="p-2 rounded-xl hover:bg-card/70 disabled:opacity-40 disabled:cursor-not-allowed"
            onClick={() => setRightPanelOpen(!rightPanelOpen)}
            disabled={!canToggleRightPanel}
          >
            <Icon name="panelRight" />
          </button>
        </nav>
      </header>
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} actions={paletteActions} />
    </>
  );
}
