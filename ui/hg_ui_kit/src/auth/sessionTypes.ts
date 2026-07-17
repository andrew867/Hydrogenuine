export type HgSession = {
  tenant_id: string;
  principal_id: string;
  roles: string[];
  created_at?: string | null;
  expires_at?: string | null;
  impersonating?: boolean;
  impersonation_tenant_id?: string | null;
  scopes?: string[];
};

export function parseSessionPayload(data: unknown): HgSession | null {
  if (!data || typeof data !== "object") return null;
  const row = data as Record<string, unknown>;
  const roles = Array.isArray(row.roles) ? row.roles.map(String) : [];
  if (!row.tenant_id || !row.principal_id || roles.length === 0) return null;
  return {
    tenant_id: String(row.tenant_id),
    principal_id: String(row.principal_id),
    roles,
    created_at: row.created_at == null ? null : String(row.created_at),
    expires_at: row.expires_at == null ? null : String(row.expires_at),
    impersonating: Boolean(row.impersonating),
    impersonation_tenant_id:
      row.impersonation_tenant_id == null ? null : String(row.impersonation_tenant_id),
    scopes: Array.isArray(row.scopes) ? row.scopes.map(String) : undefined,
  };
}

export function sessionHasRole(session: HgSession | null, roles: string[]): boolean {
  if (!session) return false;
  return roles.some((role) => session.roles.includes(role));
}

export function primaryRoleLabel(session: HgSession | null): string {
  if (!session) return "Signed out";
  if (session.roles.includes("superadmin")) return "Superadmin";
  if (session.roles.includes("tenant_admin")) return "Tenant admin";
  if (session.roles.includes("operator")) return "Operator";
  if (session.roles.includes("principal")) return "Principal";
  return session.roles[0] ?? "User";
}
