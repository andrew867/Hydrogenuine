# Run trace and failure classification contract (Autonomy Ch1 Phase 0)

Single source of truth for structured run traces (O1, O2), failure classification (F1), and minimal run summary. Every run must produce a trace record with a single `run_id`; every failure must emit a failure class.

## O1. Structured run trace (per run)

One **run_id** per execution (UUID or short hex). Emit a structured record per run:

- **Format:** JSON object or JSONL stream. When `run_dir` is set, written as `summary.json` plus `events.jsonl` in that directory.
- **Required fields:**
  - `run_id`, `workflow_id` (graph_id), `start_time`, `end_time`
  - **Node list:** for each node: `node_id`, `type`, `duration` (ms), `inputs_hash`, `outputs_hash` (when available)
  - `decisions`: selected topic/entity, seeds, policy checks (when applicable)
  - **Tool calls summary:** count and types only; no secrets
  - **Token/cost:** token estimates and budget fields (estimate acceptable if exact unavailable); cost estimate when model pricing is available
- **Artifact linking (O2):** Every output artifact (e.g. state.json, summary.json, recordings) must reference `run_id`. The run trace (summary + events) must reference output artifact identifiers (e.g. `run_dir`, artifact paths).

Existing behavior: executor writes `summary.json` and `state.json` to `run_dir`; telemetry writes `events.jsonl`. Summary already contains `run_id`, `graph_id`, `started_at`, `ended_at`, `final_status`, `counts`, `error_summary`, `run_dir`. Events contain `run_id` in payload. Extend summary and/or events to include node-level duration, inputs_hash/outputs_hash when available, and ensure every failure in `error_summary` includes a **failure_class** (F1).

## F1. Failure classification

Every failure must be classified into exactly one of:

| Class | Description |
|-------|-------------|
| `transient_network` | Network timeout, connection reset, temporary unreachable |
| `rate_limited` | HTTP 429 or provider rate limit |
| `dependency_unavailable` | Required service/file/config missing or down |
| `validation_failed` | Input or output validation error |
| `safety_blocked` | Content or action blocked by safety gate |
| `permission_denied` | Capability or scope denied |
| `timeout` | Execution or operation timeout |
| `internal_error` | Unexpected exception in our code |
| `unknown` | Fallback when no other class fits |

**Acceptance:** Every failure produces a `failure_class`, `message`, and minimal `context` (e.g. node_id, attempt). These must appear in run trace and run summary (e.g. `error_summary[].failure_class`, `error_summary[].code` aligned with class).

## Minimal run summary

The run summary (e.g. `summary.json`) must include at minimum:

- `run_id`
- `graph_id` (workflow_id)
- `started_at`, `ended_at`
- `final_status`: completed | failed | partial
- `counts`: done, failed, skipped, blocked
- `failure_class`: when final_status is failed, the primary failure class for the run (F1)
- `error_summary`: list of `{ node_id?, code, message, failure_class? }` for each failed/blocked node and run-level error

Existing `_summary_dict_for_run_dir` already provides run_id, graph_id, started_at, ended_at, final_status, counts, error_summary. Add `failure_class` to each error_summary entry and a top-level `failure_class` when the run failed.

## References

- [observability_run_logs.md](observability_run_logs.md) — events and metrics
- [.cursor/plans/autonomy/chapter1/specs/SPEC_OBSERVABILITY_AND_AUDIT.md](.cursor/plans/autonomy/chapter1/specs/SPEC_OBSERVABILITY_AND_AUDIT.md)
- [.cursor/plans/autonomy/chapter1/specs/SPEC_FAILURE_HANDLING.md](.cursor/plans/autonomy/chapter1/specs/SPEC_FAILURE_HANDLING.md)
