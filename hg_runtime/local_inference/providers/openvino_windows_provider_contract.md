# OpenVINO Windows Provider Contract

## Purpose

The Windows OpenVINO/iGPU provider is an **external advisory compute backend**. Docker Linux Hydrogenuine services may call it over `host.docker.internal` or a configured LAN IP. It exposes a sanitized OpenAI-compatible HTTP API.

## Global invariant

**Model proposes. Authority disposes.**

- OpenVINO inference is advisory compute only.
- Backend health is not authority.
- A liveness answer is not consciousness proof.
- No model output, endpoint status, backend registry entry, token stream, GPU health report, or generated text may become permission.

## Required response metadata (chat completions)

Every `POST /v1/chat/completions` and `POST /v3/chat/completions` response MUST include in `hg_metadata`:

| Field | Required value |
|-------|----------------|
| `backend_id` | e.g. `windows-openvino-igpu` |
| `backend_type` | `openvino_windows` |
| `device` | `CPU`, `GPU`, `AUTO`, or resolved device |
| `model_id` | configured model id or `null` |
| `advisory_only` | `true` |
| `permission_granted` | `false` |
| `authority_created` | `false` |
| `fallback_stub` | `true` if stub; `false` if real inference |

When `fallback_stub` is `true`, the provider MUST NOT claim real inference. Clients MUST treat output as dev/liveness only.

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness; not authority |
| GET | `/devices` | OpenVINO device enumeration |
| GET | `/v1/models` | OpenAI-compatible model list |
| POST | `/v1/chat/completions` | Advisory chat (OpenAI shape) |
| POST | `/v3/chat/completions` | Advisory chat (v3 alias) |

## Binding policy

- Default bind: `127.0.0.1` (loopback only).
- `-BindLan` is operator opt-in with explicit warning.
- No public `0.0.0.0` exposure by default.

## Model download policy

- No model weights download unless operator passes `-DownloadTinyModel` (install) or configures an existing local path.
- Uncontrolled download is forbidden.

## Docker bridge

Example Hydrogenuine config: `configs/local_inference/openvino_windows.example.json`

- `base_url`: `http://host.docker.internal:18080/v1`
- `v3_base_url`: `http://host.docker.internal:18080/v3`

If `host.docker.internal` fails on Linux Docker, use explicit Windows host LAN IP.

## Verdict classes

| Verdict | Meaning |
|---------|---------|
| `GREEN_REAL_OPENVINO_WINDOWS` | Real model loaded, advisory metadata correct, bridge callable |
| `YELLOW_PROVIDER_CONTRACT_READY` | Scripts/config/docs/gates exist; endpoint not running or no real model |
| `YELLOW_FALLBACK_STUB_ONLY` | Endpoint runs but only fallback stub available |
| `RED` | Unsafe scripts, secrets committed, authority conversion, public port default, false real-inference claim |
