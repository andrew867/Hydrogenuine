# Operator Interface — Reliability and Ownership

API and UI for reliability (correctness, failure handling, observability, safety, cost, concurrency) and ownership controls (handoffs, conflicts). All under `/api/v1` with API-key auth. Workflow operations are covered by [operator_interface_workflow_operations_spec.md](operator_interface_workflow_operations_spec.md).

## Reliability API surface

Base path: `/api/v1/reliability`. Auth: `Authorization: Bearer <API_KEY>`.

### Failure classification and retry policy (F1, F2)

- **GET /reliability/failure-classes** — List known failure classes. Returns `{ "ok": true, "classes": [ "transient_network", "rate_limited", ... ] }`. Uses `hg_core.task_graph.failure_classification.FAILURE_CLASSES`.
- **GET /reliability/retry-policy** — Retry policy for all classes or one (query: `class_name=optional`). Returns `{ "ok": true, "policies": { "transient_network": { "max_attempts", "retryable", "retry_backoff_ms", "escalation" }, ... } }` or single policy. Uses `hg_core.task_graph.retry_policy.get_retry_policy_for_class`.

### Circuit breakers (F5)

- **GET /reliability/breakers** — List circuit breaker state per workflow (and optionally per destination). Returns `{ "ok": true, "breakers": [ { "workflow_id", "destination?", "failures", "tripped_at", "tripped": bool }, ... ] }`. Uses `hg_core.task_graph.circuit_breaker` (scan `memory/automation/circuit_breaker`).
- **POST /reliability/breakers/reset** — Reset breaker (body: `workflow_id`, `destination?`). Returns `{ "ok": true }`. Uses `hg_core.task_graph.circuit_breaker.reset_breaker`.

### Incident queue (F3)

- **GET /reliability/incident-queue** — List incident files (query: `task_id=optional`). Returns `{ "ok": true, "items": [ { "path", "task_id", "run_id", "written_at" }, ... ] }`. Uses `hg_core.deadletter.list_deadletter_files` and `load_deadletter` for summary.

### Budget / cost summary (K1–K3)

- **GET /reliability/budget-summary** — Aggregate budget_used across recent runs (from run index + summary.json). Returns `{ "ok": true, "by_workflow": { "workflow_id": { "runs", "total_budget_used" } }, "recent_runs": N }`. Uses run index and analytics per run or summary.json.

## Ownership API surface

Base path: `/api/v1/ownership`. Existing run-scoped ownership: GET `/runs/{run_id}/ownership/chain`, `/edges`, `/events`, `/search`, `/availability` (already in operator console).

### Ownership conflicts and handoffs

- **GET /ownership/conflicts** — List runs/tasks with contested ownership state. Returns `{ "ok": true, "conflicts": [ { "run_id", "task_id", "state", "contested_claims" }, ... ] }`. Scans run index for runs with `run_dir/ownership.db`, queries ownership_state for `state = 'contested'`.
- **GET /ownership/handoffs** — List recent handoff events (offer_ownership, accept_ownership, decline_ownership) across runs (optional limit). Returns `{ "ok": true, "events": [ { "run_id", "task_id", "type", "actor", "ts" }, ... ] }`. Aggregates from run ownership dbs (ledger_list_events filtered by type).

## UI screens

- **Reliability** — `#/autonomy/ch1`: Failure classes (table); Retry policy (table or per-class); Circuit breakers (list + Reset button per workflow); incident queue (links to replay); budget summary (by workflow).
- **Ownership Controls** — `#/autonomy/ch2`: Conflicts table (run_id, task_id, contested_claims; link to run ownership); Handoffs table (recent offer/accept/decline events; link to run).

Navigation: add **Reliability**, **Ownership Controls** to console nav (alongside Workflows, Fault, Retention, Dead-letter, Approvals, SLA).

## Documentation index

- **Reliability specs:** idempotency_retry_dlq_contract, run_trace_and_failure_classification_contract, safety_and_permissions_contract, change_governance_contract, cost_control_contract, concurrency_and_scheduling_contract (hg_core/task_graph/docs).
- **Ownership specs:** ownership_lease_master_spec, ownership_event_schema (hg_core/task_graph/docs); ownership model, handoff receipts, conflict resolution (cursor/plans/autonomy/chapter2/specs).
- **Workflow operations:** See WORKFLOW_OPERATIONS_INDEX and operator_interface_workflow_operations_spec.
