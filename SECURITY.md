# Security Policy

Report security issues privately to the repository owner through GitHub security advisories.

Do not include real secrets, customer data or private environment details in public issues.

Supported scope for the community release:

- Local FastAPI gateway.
- Static community UI.
- Local data store, receipts, memory, plans, workflows and leases.
- Public extension examples.

Out of scope for this repository:

- Managed cloud services.
- Enterprise tenancy, SSO and fleet administration.
- Proprietary connectors and policy packs.

Security defaults:

- Telemetry off.
- Deterministic offline model available without credentials.
- Tool execution denied until an explicit capability lease is approved.
- Memory records grant no authority.
