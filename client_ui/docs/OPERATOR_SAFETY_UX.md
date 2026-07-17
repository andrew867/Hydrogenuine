# Operator Safety UX

Internal client_ui safeguards for destructive actions and key handling.

## Destructive action safeguards

- **Confirm tenant:** Export and delete tenant require typing the exact `tenant_id` to enable submit. This prevents accidental deletion of the wrong tenant.
- **Usage snapshot:** Before destructive actions, the UI can show current usage (from `GET /v1/tenants/me` or `/tenants/me/usage`).

## Dev override policy

- **Tenant banner:** When `X-Tenant-ID` override is active (dev only, when `NEXT_PUBLIC_HG_DEV_TENANT_HEADER=true`), a red banner shows "DEV OVERRIDE" and the override value.
- Do not rely on tenant override in production; tenant identity is derived from the API key only.

## Read-only mode

- Toggle in Settings or TopBar. When on, admin and destructive actions are disabled **client-side**.
- This is a safety affordance only, not access control. The backend still enforces authorization.

## Key handling rules

- **Key classes:** Operator (tenant), admin (admin endpoints only), service (explicit per-action). See [API_KEY_MANAGEMENT.md](API_KEY_MANAGEMENT.md).
- **Lock:** Clears all keys and overrides immediately. Use before stepping away.
- **No raw key logging:** Audit and telemetry never include raw keys; only events (added/validated/removed).
- **Guardrails:** Missing operator key blocks most of the app (link to Settings). Missing admin key hides admin routes and shows how to enable.

## Audit expectations

- Approval lifecycle and cross-tenant access are audited server-side.
- Key events (added/validated/removed) are logged client-side as non-sensitive telemetry.
