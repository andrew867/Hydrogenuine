# Troubleshooting (internal UX)

## Auth failures

- **401 Unauthorized:** Missing or invalid API key. Add or correct the operator key in Settings. Ensure `Authorization: Bearer <key>` or `X-API-Key` is sent (KeyRing does this when operator key is set).
- **403 Forbidden:** Invalid admin key, or cross-tenant access, or policy denial. For admin actions, set the admin key in Settings and use **Validate** to confirm.

## 403 vs 401

- **401** — Authentication failed (wrong or missing key).
- **403** — Authenticated but not allowed (e.g. admin key required, or resource belongs to another tenant).

## Tenant mismatch

- If you see "Not authorized for this tenant" on principals or other resources, your operator key is scoped to a different tenant. Check current tenant in Settings (from `GET /v1/tenants/me`). In dev, you can use the tenant override (red banner) to switch context; in production, use an operator key mapped to the correct tenant.

## Missing principals

- Principals are tenant-scoped. If the list is empty, ensure your operator key resolves to the tenant that owns those principals. Validate the operator key and check the tenant id in Settings.

## Request blocked: cross-environment

- Keys are bound to an API base URL. If you see "Request blocked: key is bound to a different environment", the request base URL does not match the key's bound base. Use **Confirm cross-environment** in Settings to allow for a short period, or add a key bound to the current base URL.
