# `client_ui`

`client_ui` is the primary tenant-facing Hydrogenuine workspace. It consumes the shared `hg_ui_kit` package (`ThemeProvider`, `EnvBadge`, tokens) from `ui/hg_ui_kit`.

It is a live Next.js application, not a mock scaffold. The app is wired to the current gateway and operator APIs for chat, personas, steering, approvals, principals, document workflows, and swarm orchestration.

## Implemented UI Areas

- Chat workspace with multi-chat sidebar, markdown rendering, citations, and tool cards.
- Persona-aware chat creation.
- SSE-backed response streaming.
- Per-chat steering controls.
- Approval queue with approve and deny actions.
- Tenant settings and approval policy controls.
- Principal management and availability.
- Document upload, parse, browse, attach, retrieve, and export flows.
- Swarm launch and swarm-aware chat grouping.

## Local Run

```bash
npm install
npm run dev
```

Default development URL: `http://localhost:3000` for `next dev`, while the Dockerized repo configuration exposes the client UI on `http://localhost:3001`.

## Environment

Set these in `.env.local` as needed:

- `NEXT_PUBLIC_HG_API_BASE`
- `NEXT_PUBLIC_HG_SSE_URL`
- `NEXT_PUBLIC_HG_WS_URL`
- `NEXT_PUBLIC_HG_DEMO_MODE`

In the full stack compose setup, the client UI is built against the operator API host on `http://localhost:8080`, which mounts the public gateway routes it needs for the browser workspace.

## Key Code Areas

- `src/app/`
  - Route entry points.
- `src/components/chat/`
  - Chat, composer, streaming, steering, and message rendering.
- `src/components/approvals/`
  - Approval queue UX.
- `src/components/documents/`
  - Document sidebar, viewer, citations, and parse interactions.
- `src/components/principals/`
  - Principal management and self-availability flows.
- `src/components/swarm/`
  - Swarm launch and run views.
- `src/lib/hgApi.ts`
  - Typed client for `/v1` and selected `/api/v1` routes.

## Verification

The app has both unit and Playwright coverage, including persona/steering and document decomposition flows:

- `npm run test`
- `npm run e2e`
