# OSS first-run UX fix plan

## Goal

Make the Hydrogenuine Community core usable after a clean install without cloud keys, private services, or unexplained transport-token failures.

## Planned changes

1. Replace the public `hg-setup` entry point with a unified `hg init` wizard.
2. Support demo, local OpenAI-compatible, cloud, and private-boundary modes.
3. Store only public configuration and key environment-variable names.
4. Add `hg doctor`, `hg config show --redacted`, and `hg demo`.
5. Add `hg chat new`, `hg chat list`, and `hg chat resume`.
6. Add explicit loopback-only no-key authentication for native demo and local modes.
7. Keep explicit gateway key mode for deployments that need a transport credential.
8. Preserve chats with SQLite in native and Docker launch paths.
9. Wire selected provider, model, and base URL into Community UI chat turns.
10. Distinguish optional-provider unavailability from a broken Community core.
11. Replace first-run docs and add configuration, troubleshooting, and multi-chat guides.
12. Add focused tests and a fail-closed readiness gate.

## Safety boundaries

- No push, tag, release, package upload, or public deployment.
- No public remote modification.
- No provider secret values in configuration or reports.
- No private endpoints, private proof bundles, customer data, or private policy packs.
- Public wording remains early public pre-alpha and Artificial Governed Intelligence.
- Test success is scoped to first-run behavior and does not promote broader readiness claims.
