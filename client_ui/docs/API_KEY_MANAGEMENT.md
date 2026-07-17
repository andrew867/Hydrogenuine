# API key management (internal UX)

This doc describes key classes, storage policy, rotation, and environment binding for the internal client_ui.

## Key classes

1. **Operator key** — Tenant-scoped access. Used for chats, messages, principals, approvals, and `GET /v1/tenants/me` / `GET /v1/tenants/me/usage`. Determines tenant identity. Header: `Authorization: Bearer <key>` or `X-API-Key`.

2. **Admin key** — Additive privilege only for `/v1/admin/*` and destructive endpoints (tenant export/delete). Never used for normal chat. Header: `X-Admin-Key`.

3. **Service key** — Optional; for restricted tool execution or background actions. Must be explicitly selected per action; no implicit fallback. Header: `X-Service-Key`.

Scoping: Operator key = tenant identity. Admin key does not change tenant. Service key = explicit per-action only.

## Storage policy

- **Default:** In-memory only. Keys are cleared on lock or tab close.
- **Optional:** sessionStorage with explicit warning and configurable "auto-clear on idle" timer.
- **Lock:** Clears all keys and tenant overrides immediately.

## Rotation

1. Add new key in Settings.
2. Use **Validate** to confirm (operator: `GET /v1/tenants/me`, admin: `GET /v1/admin/ping`, service: `GET /v1/service/ping`).
3. Switch active key (replace or add as new).
4. Keep previous key in memory until you confirm removal.

## Environment binding

Each key can be bound to an API base URL and label (e.g. prod, sandbox, local). Requests to a different base URL are blocked until the user confirms (cross-environment confirmation in Settings).

## Validate endpoints

| Key class | Endpoint |
|-----------|----------|
| Operator  | `GET /v1/tenants/me` |
| Admin     | `GET /v1/admin/tenants` or `GET /v1/admin/ping` |
| Service   | `GET /v1/service/ping` |

## Audit

The UI logs key events (added, validated, removed) as non-sensitive telemetry. Raw keys are never logged.

## Tenant-admin and principal keys (gateway config)

- **Tenant-admin:** Keys listed in `hg.json` under `gateway.auth.tenant_admin_keys` (or env **HG_GATEWAY_TENANT_ADMIN_KEYS**) are gateway credentials for API and automation flows. The browser UI should use Keycloak SSO with the matching `demo-tenant-admin` user in demo mode. The backend returns `role: "tenant_admin"` in `GET /v1/tenants/me`. Tenant-admins can manage principals (list/create/disable) and export their own tenant.
- **Principal keys:** Keys in `gateway.auth.principal_keys` (or **HG_GATEWAY_PRINCIPAL_KEYS** in format `key:tenant_id:principal_id,...`) are gateway credentials for API and automation flows. The browser UI should use Keycloak SSO with the matching demo client user in demo mode. The backend returns `role: "principal"` and `principal_id`; the client UI shows principal-scoped UX (Approvals assigned to them, My availability only).
