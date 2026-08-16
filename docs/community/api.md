# Community API

All application routes are served below `/v1`. Native demo and local-model launchers use loopback-only no-key mode. Requests from a non-loopback client are refused in that mode.

Explicit `api-key` gateway mode requires a local transport header:

```text
x-api-key: oss-demo-key
```

This local transport credential is not a model-provider key. Provider credentials, when selected, remain in named environment variables.

`GET /healthz` is public and reports the selected gateway access mode without revealing credentials.

## Diagnostics and Models

- `GET /v1/diagnostics`: local health, data directory, telemetry and store counts.
- `GET /v1/models`: deterministic stub plus OpenAI-compatible, Ollama, LM Studio and vLLM-compatible provider capability records. Provider records have no authority effect.

## Chat

- `GET /v1/chats`: list chats.
- `POST /v1/chats`: create a chat with `title`.
- `GET /v1/chats/{chat_id}`: read chat metadata.
- `PATCH /v1/chats/{chat_id}`: rename a chat with `title`.
- `POST /v1/chats/{chat_id}/archive`: mark chat archived when the backing store supports it.
- `DELETE /v1/chats/{chat_id}`: delete a chat.
- `GET /v1/chats/{chat_id}/messages`: list messages.
- `POST /v1/chats/{chat_id}/messages`: add a user message and receive the final assistant response.
- `POST /v1/chats/{chat_id}/messages/stream`: Server-Sent Events stream with `message.created`, `agent.status`, `message.delta`, `message.final` and `done`.
- `POST /v1/chats/{chat_id}/stop`: record an operator stop marker.
- `POST /v1/chats/{chat_id}/retry`: retry from the last user message.
- `POST /v1/chats/{chat_id}/branch`: copy chat messages into a new branch chat.
- `POST /v1/chats/{chat_id}/attachments`: register a local attachment record.

Model selection can be passed in the body (`provider`, `model`, `base_url`) or by headers (`x-hg-model-provider`, `x-hg-model`, `x-hg-base-url`). The deterministic `stub` provider requires no network or credentials. Local OpenAI-compatible configuration is translated to the public `vllm` runtime adapter with the selected base URL and model.

## Planning and Workflows

- `POST /v1/plans`: create an editable structured plan from `request`.
- `GET /v1/plans`: list plans.
- `GET /v1/plans/{plan_id}`: read a plan.
- `PATCH /v1/plans/{plan_id}`: edit `steps` or `status`.
- `POST /v1/plans/{plan_id}/approve`: approve a plan and emit an authority-none receipt.
- `POST /v1/workflows`: create a workflow from a plan or supplied steps.
- `GET /v1/workflows`: list workflows.
- `GET /v1/workflows/{workflow_id}`: inspect workflow state.
- `POST /v1/workflows/{workflow_id}/run`: run to deterministic completion with artifact.
- `POST /v1/workflows/{workflow_id}/pause`: pause a workflow.
- `POST /v1/workflows/{workflow_id}/resume`: resume a workflow.
- `POST /v1/workflows/{workflow_id}/retry`: retry workflow execution.
- `POST /v1/workflows/{workflow_id}/cancel`: cancel a workflow.

## Research, Documents and Memory

- `POST /v1/research`: create a deterministic research report with source claim boundaries.
- `POST /v1/documents`: ingest text content and store chunk provenance.
- `GET /v1/documents`: list documents.
- `GET /v1/documents/query?q=...`: query chunks with document and location citations.
- `DELETE /v1/documents/{document_id}`: delete a document.
- `POST /v1/memory`: create a memory candidate. Memory grants no action authority.
- `GET /v1/memory`: list memory records.
- `PATCH /v1/memory/{memory_id}`: edit text or status and append a revision.
- `DELETE /v1/memory/{memory_id}`: delete memory.

## Governance, Tools and Export

- `POST /v1/leases`: request a bounded capability lease.
- `GET /v1/leases`: list leases.
- `POST /v1/leases/{lease_id}/approve`: activate a lease.
- `POST /v1/leases/{lease_id}/revoke`: revoke a lease.
- `POST /v1/leases/{lease_id}/expire`: expire a lease.
- `GET /v1/tools`: list public community tools.
- `POST /v1/tools/{tool_id}/run`: run only when an active bounded lease permits the tool; otherwise fail closed with a denial receipt.
- `GET /v1/receipts`: read the local hash-chained receipt log.
- `GET /v1/export`: export local community data in `hydrogenuine-community-export-v1` format.
