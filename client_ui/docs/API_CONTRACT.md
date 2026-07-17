# HG Client UI API Contract (Integration Only)

This UI build does **not** ship any mock API routes.

## Base URL
Configure:

- `NEXT_PUBLIC_HG_API_BASE` (example: `https://hg.yourdomain.com`)

Optional streaming:

- `NEXT_PUBLIC_HG_SSE_URL` (example: `https://hg.yourdomain.com/v1/stream`)
- `NEXT_PUBLIC_HG_WS_URL` (example: `wss://hg.yourdomain.com/v1/ws`)

The UI currently uses `src/lib/hgApi.ts` for all HTTP calls.

## Required Endpoints (REST)

### Chats
- `GET /v1/chats`
  - Response: `{ chats: Array<{ chat_id, title, updated_at, unread_count? }> }`

- `POST /v1/chats`
  - Body: `{ title?: string }`
  - Response: `{ chat_id: string }`

- `PATCH /v1/chats/{chat_id}`
  - Body: `{ title: string }`
  - Response: `204 No Content`

- `DELETE /v1/chats/{chat_id}`
  - Response: `204 No Content`

### Messages
- `GET /v1/chats/{chat_id}/messages`
  - Response: `{ messages: Array<ChatMessage> }`

- `POST /v1/chats/{chat_id}/messages`
  - Body: `{ content: string }`
  - Response: `{ message: ChatMessage }`

`ChatMessage` fields used by the UI:
- `message_id`, `chat_id`, `role`, `created_at`, `content`
- optional: `agent_id`
- optional tool message fields: `tool_name`, `tool_payload`, `tool_result`
- optional: `approvals_required`

### Agents (Per chat)
- `GET /v1/chats/{chat_id}/agents`
  - Response: `{ agents: Array<{ agent_id, label, status, parent_agent_id? }> }`

### Approvals
- `GET /v1/approvals`
  - Response: `{ approvals: Array<ApprovalItem> }`

- `POST /v1/approvals/{approval_id}/approve`
  - Body: `{ note?: string }`
  - Response: `204 No Content`

- `POST /v1/approvals/{approval_id}/deny`
  - Body: `{ note?: string }`
  - Response: `204 No Content`

## Streaming (Recommended)
If your backend supports streaming tokens, implement SSE on your gateway and feed events like:

- `message.delta` (append tokens to the active assistant message)
- `message.final` (mark message complete)
- `tool.start` / `tool.result` (populate tool timeline cards)
- `agent.status` (update agent tree)
- `approval.created` (add to approvals queue)

Wire-up point:
- `src/lib/streaming.ts` (if present) or add a small module to open an `EventSource` to `NEXT_PUBLIC_HG_SSE_URL`.

## Auth
If you require auth, the UI is ready for `Authorization: Bearer <token>` injection.
Add token handling in `src/lib/auth.ts` and pass `{ bearer }` to `hgApi.*`.
