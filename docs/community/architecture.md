# Architecture

Hydrogenuine Community uses a local FastAPI gateway plus a static UI.

- Chat, planning, workflows, research, documents, memory, leases, receipts and exports are exposed under `/v1`.
- Persistent community state is a local JSON store selected by `HG_COMMUNITY_DATA_DIR`.
- Memory records are knowledge only and never grant tool authority.
- Tools are denied by default and require an active capability lease.
- Receipts form a local hash chain so actions can be reviewed after a run.

Commercial-only managed tenancy, SSO, fleet operations, private policy packs and proprietary connectors are outside this public edition.
