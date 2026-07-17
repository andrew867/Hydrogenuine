/**
 * KeyRing state: keys per class, metadata, tenant override, read-only mode, lock.
 * Keys are stored in memory only by default; optional sessionStorage when E2E persist is on.
 */

import { create } from "zustand";
import type { KeyClass, KeyMeta } from "@/lib/keyTypes";

const E2E_OPERATOR_KEY = "e2e_operator_key";
const SESSION_OPERATOR_KEY = "hg_operator_key";
const SESSION_ADMIN_KEY = "hg_admin_key";
const SESSION_SERVICE_KEY = "hg_service_key";
const SESSION_STEPUP_TOKEN = "hg_stepup_token";
const SESSION_STEPUP_VERIFIED_AT = "hg_stepup_verified_at";
const SESSION_BROWSER_AUTH = "hg_browser_auth";

function e2ePersistOperatorKey(value: string | null): void {
  if (typeof window === "undefined") return;
  try {
    if (value) window.sessionStorage.setItem(E2E_OPERATOR_KEY, value);
    else window.sessionStorage.removeItem(E2E_OPERATOR_KEY);
  } catch {
    // ignore
  }
}

function persistSessionValue(key: string, value: string | null): void {
  if (typeof window === "undefined") return;
  try {
    if (value) window.sessionStorage.setItem(key, value);
    else window.sessionStorage.removeItem(key);
  } catch {
    // ignore
  }
}

export function restoreKeysFromSessionStorage(
  getState: () => { operatorKey: KeyEntry | null; adminKey: KeyEntry | null; serviceKey: KeyEntry | null; stepupToken: string | null; browserSession: BrowserSession | null },
  actions: { setOperatorKey: (v: string | null) => void; setAdminKey: (v: string | null) => void; setServiceKey: (v: string | null) => void; setStepupToken: (v: string | null, verifiedAt?: string | null) => void; setBrowserSession: (v: BrowserSession | null) => void }
): void {
  if (typeof window === "undefined") return;
  try {
    const operatorRaw =
      window.sessionStorage.getItem(SESSION_OPERATOR_KEY)
      || (process.env.NEXT_PUBLIC_E2E_PERSIST_KEYS === "true"
      ? window.sessionStorage.getItem(E2E_OPERATOR_KEY)
      : null);
    if (operatorRaw && !getState().operatorKey) actions.setOperatorKey(operatorRaw);
    const adminRaw = window.sessionStorage.getItem(SESSION_ADMIN_KEY);
    if (adminRaw && !getState().adminKey) actions.setAdminKey(adminRaw);
    const serviceRaw = window.sessionStorage.getItem(SESSION_SERVICE_KEY);
    if (serviceRaw && !getState().serviceKey) actions.setServiceKey(serviceRaw);
    const stepupRaw = window.sessionStorage.getItem(SESSION_STEPUP_TOKEN);
    const stepupVerifiedAt = window.sessionStorage.getItem(SESSION_STEPUP_VERIFIED_AT);
    if (stepupRaw && !getState().stepupToken) actions.setStepupToken(stepupRaw, stepupVerifiedAt);
    const browserRaw = window.sessionStorage.getItem(SESSION_BROWSER_AUTH);
    if (browserRaw && !getState().browserSession) actions.setBrowserSession(JSON.parse(browserRaw) as BrowserSession);
  } catch {
    // ignore
  }
}

export type BrowserSession = {
  tenant_id: string;
  principal_id: string;
  roles: string[];
  created_at?: string | null;
  expires_at?: string | null;
};

type KeyEntry = {
  value: string;
  meta: KeyMeta;
};

type KeyRingState = {
  restored: boolean;
  /** When true, all keys and overrides are cleared and no headers are provided. */
  locked: boolean;
  operatorKey: KeyEntry | null;
  adminKey: KeyEntry | null;
  serviceKey: KeyEntry | null;
  stepupToken: string | null;
  stepupVerifiedAt: string | null;
  browserSession: BrowserSession | null;
  /** Pack 13: Short-lived JWT for impersonation; when set, operator requests use Bearer this instead of API key. */
  impersonationToken: string | null;
  /** Tenant id being impersonated (for banner display). */
  impersonationTenantId: string | null;
  /** Dev only: override tenant id sent as X-Tenant-ID. */
  tenantOverride: string | null;
  readOnlyMode: boolean;
  /** Cross-environment: when request baseUrl !== key's baseUrl, block unless confirmed. */
  crossEnvConfirmedUntil: number; // timestamp
  /** Last X-Request-ID sent (for error display). */
  lastRequestId: string | null;
  // Actions
  setOperatorKey(value: string | null, meta?: Partial<KeyMeta>): void;
  setAdminKey(value: string | null, meta?: Partial<KeyMeta>): void;
  setServiceKey(value: string | null, meta?: Partial<KeyMeta>): void;
  setStepupToken(value: string | null, verifiedAt?: string | null): void;
  clearStepupToken(): void;
  setBrowserSession(value: BrowserSession | null): void;
  setImpersonationToken(token: string | null, tenantId?: string | null): void;
  setTenantOverride(value: string | null): void;
  setReadOnlyMode(value: boolean): void;
  lock(): void;
  unlock(): void;
  recordUse(keyClass: KeyClass): void;
  setLastRequestId(id: string | null): void;
  confirmCrossEnv(): void;
  clearCrossEnvConfirm(): void;
  markRestored(): void;
};

const defaultMeta = (baseUrl: string, label: string): KeyMeta => ({
  baseUrl,
  label,
  lastUsedAt: "",
});

function getDefaultBase(): string {
  const base = typeof process !== "undefined" && process.env?.NEXT_PUBLIC_HG_API_BASE
    ? process.env.NEXT_PUBLIC_HG_API_BASE
    : "http://localhost:8080";
  return String(base).replace(/\/$/, "");
}

export const useKeyRingStore = create<KeyRingState>((set) => ({
    restored: false,
    locked: false,
    operatorKey: null,
    adminKey: null,
    serviceKey: null,
    stepupToken: null,
    stepupVerifiedAt: null,
    browserSession: null,
    impersonationToken: null,
    impersonationTenantId: null,
    tenantOverride: null,
    readOnlyMode: false,
    crossEnvConfirmedUntil: 0,
    lastRequestId: null,

    setOperatorKey(value, meta) {
      persistSessionValue(SESSION_OPERATOR_KEY, value);
      if (typeof window !== "undefined" && process.env.NEXT_PUBLIC_E2E_PERSIST_KEYS === "true") {
        e2ePersistOperatorKey(value);
      }
      set((s) => {
        if (s.locked) return s;
        const base = getDefaultBase();
        return {
          operatorKey: value
            ? { value, meta: { ...defaultMeta(base, "default"), ...meta } }
            : null,
        };
      });
    },
    setAdminKey(value, meta) {
      persistSessionValue(SESSION_ADMIN_KEY, value);
      set((s) => {
        if (s.locked) return s;
        const base = getDefaultBase();
        return {
          adminKey: value
            ? { value, meta: { ...defaultMeta(base, "default"), ...meta } }
            : null,
        };
      });
    },
    setServiceKey(value, meta) {
      persistSessionValue(SESSION_SERVICE_KEY, value);
      set((s) => {
        if (s.locked) return s;
        const base = getDefaultBase();
        return {
          serviceKey: value
            ? { value, meta: { ...defaultMeta(base, "default"), ...meta } }
            : null,
        };
      });
    },
    setStepupToken(value, verifiedAt) {
      const resolvedVerifiedAt = value ? (verifiedAt ?? new Date().toISOString()) : null;
      persistSessionValue(SESSION_STEPUP_TOKEN, value);
      persistSessionValue(SESSION_STEPUP_VERIFIED_AT, resolvedVerifiedAt);
      set((s) => {
        if (s.locked) return s;
        return {
          stepupToken: value || null,
          stepupVerifiedAt: resolvedVerifiedAt,
        };
      });
    },
    clearStepupToken() {
      persistSessionValue(SESSION_STEPUP_TOKEN, null);
      persistSessionValue(SESSION_STEPUP_VERIFIED_AT, null);
      set({
        stepupToken: null,
        stepupVerifiedAt: null,
      });
    },
    setBrowserSession(value) {
      persistSessionValue(SESSION_BROWSER_AUTH, value ? JSON.stringify(value) : null);
      set((s) => {
        if (s.locked) return s;
        return { browserSession: value ?? null };
      });
    },
    setImpersonationToken(token, tenantId) {
      set((s) => (s.locked ? s : {
        impersonationToken: token || null,
        impersonationTenantId: (tenantId !== undefined ? tenantId : s.impersonationTenantId) ?? null,
      }));
    },
    setTenantOverride(value) {
      set((s) => (s.locked ? s : { tenantOverride: value || null }));
    },
    setReadOnlyMode(value) {
      set({ readOnlyMode: value });
    },
    lock() {
      persistSessionValue(SESSION_OPERATOR_KEY, null);
      persistSessionValue(SESSION_ADMIN_KEY, null);
      persistSessionValue(SESSION_SERVICE_KEY, null);
      persistSessionValue(SESSION_STEPUP_TOKEN, null);
      persistSessionValue(SESSION_STEPUP_VERIFIED_AT, null);
      persistSessionValue(SESSION_BROWSER_AUTH, null);
      if (typeof window !== "undefined" && process.env.NEXT_PUBLIC_E2E_PERSIST_KEYS === "true") {
        e2ePersistOperatorKey(null);
      }
      set({
        locked: true,
        operatorKey: null,
        adminKey: null,
        serviceKey: null,
        stepupToken: null,
        stepupVerifiedAt: null,
        browserSession: null,
        impersonationToken: null,
        impersonationTenantId: null,
        tenantOverride: null,
        crossEnvConfirmedUntil: 0,
      });
    },
    unlock() {
      set({ locked: false });
    },
    recordUse(keyClass) {
      const now = new Date().toISOString();
      set((s) => {
        if (s.locked) return s;
        const upd: Partial<KeyRingState> = {};
        if (keyClass === "operator" && s.operatorKey)
          upd.operatorKey = { ...s.operatorKey, meta: { ...s.operatorKey.meta, lastUsedAt: now, lastUsedEndpointClass: keyClass } };
        if (keyClass === "admin" && s.adminKey)
          upd.adminKey = { ...s.adminKey, meta: { ...s.adminKey.meta, lastUsedAt: now, lastUsedEndpointClass: keyClass } };
        if (keyClass === "service" && s.serviceKey)
          upd.serviceKey = { ...s.serviceKey, meta: { ...s.serviceKey.meta, lastUsedAt: now, lastUsedEndpointClass: keyClass } };
        return upd;
      });
    },
    setLastRequestId(id) {
      set({ lastRequestId: id });
    },
    confirmCrossEnv() {
      set({ crossEnvConfirmedUntil: Date.now() + 60_000 }); // 1 min
    },
    clearCrossEnvConfirm() {
      set({ crossEnvConfirmedUntil: 0 });
    },
    markRestored() {
      set({ restored: true });
    },
  }));
