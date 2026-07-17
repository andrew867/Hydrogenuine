# Operator Interface (UI + API) for Workflow Operations

Complete operator interface exposing workflow registry, failure injection harness, retention/redaction/purge, operator actions (status overview, run detail, incident queue, approvals queue, pause/resume, replay shadow, rollback, export report), and SLA reporting. All endpoints under `/api/v1` with API-key auth.

## API surface

Base path: `/api/v1`. Auth: `Authorization: Bearer <API_KEY>` or `X-API-Key: <API_KEY>`.

### Workflows (primary workflow registry)

- **GET /workflows** — List primary workflows. Returns `{ "ok": true, "workflows": [ { "workflow_id", "display_name", "category", "readiness", ... }, ... ] }`. Uses `hg_core.task_graph.workflow_registry.load_workflow_registry` and `get_primary_workflow_ids`.
- **GET /workflows/{workflow_id}** — Workflow declaration detail. Returns `{ "ok": true, "workflow": { ... } }` or 404.
- **POST /workflows/{workflow_id}/acceptance-checks** — Run acceptance checks (optional body: `run_context`). Returns `{ "ok": true, "results": [ { "check_id", "passed", "message" }, ... ] }`.

### Fault scenarios (failure injection harness)

- **GET /fault/scenarios** — List fault scenario IDs and per-workflow coverage. Returns `{ "ok": true, "scenarios": [ ... ], "by_workflow": { "workflow_id": [ "scenario_id", ... ], ... } }`.
- **POST /fault/run** — Run a single scenario (body: `workflow_id`, `scenario_id`, `step_index?`, `fake_destination_ledger?`). Returns `{ "ok": true, "outcome": { "failure_class", "terminal", "dead_letter?", ... } }`. No side effects; fake ledger only.

### Retention, redaction, purge

- **POST /retention/redact-preview** — Preview redaction (body: `payload`). Returns `{ "ok": true, "redacted": { ... } }`. Uses `redact_for_storage`.
- **POST /retention/purge** — Purge by run_id (body: `run_id`). Returns `{ "ok": true, "removed_count": N, "audit_entry": { ... } }`. Writes audit log.
- **GET /retention/audit** — List recent purge audit entries. Returns `{ "ok": true, "entries": [ ... ] }`.

### Operator actions (status, run detail, incident queue, approvals, actions)

- **GET /operator/status-overview** — Status overview (recent, paused, failing, expensive, breaker_states). Returns `{ "ok": true, "recent": [], "paused": [], "failing": [], "expensive": [], "breaker_states": {} }`. Uses `operator_ux.get_status_overview`.
- **GET /operator/run-detail/{run_id}** — Run detail (summary, trace link, failure class, retries). Returns `{ "ok": true, "run_id", "summary", ... }`. Uses `operator_ux.get_run_detail`.
- **GET /operator/incident-queue** — Incident queue. Returns `{ "ok": true, "items": [ ... ] }`. Uses `operator_ux.get_dead_letter_queue`.
- **GET /operator/approvals** — Approvals queue. Returns `{ "ok": true, "items": [ ... ] }`. Uses `operator_ux.get_approvals_queue`.
- **POST /operator/replay-incident** — Replay incident entry in shadow (body: `incident_id`, `shadow`: true). Returns `{ "ok": true, "shadow": true, ... }`. Uses `operator_ux.replay_dead_letter`.
- **POST /operator/pause** — Pause workflow (body: `workflow_id`). Returns `{ "ok": true }`. Uses `operator_ux.pause_workflow`.
- **POST /operator/resume** — Resume workflow (body: `workflow_id`). Returns `{ "ok": true }`. Uses `operator_ux.resume_workflow`.
- **POST /operator/rollback** — Rollback to last known good (body: `workflow_id`). Returns `{ "ok": true }`. Uses `operator_ux.rollback_to_last_good`.
- **POST /operator/export-weekly-report** — Export weekly report. Returns `{ "ok": true, "report_path"?, "summary": { ... } }`. Uses `operator_ux.export_weekly_report`.
- **POST /operator/approval/evaluate** — Evaluate approval (body: `workflow_id`, `action_summary`). Returns `{ "ok": true, "decision", "policy_basis", "allow_external_call" }`. Uses `operator_ux.evaluate_approval`.

### SLA reporting

- **GET /sla/daily** — Daily report (query: `traces?` optional JSON array or load from workspace). Returns `{ "ok": true, "report": { "runs_by_workflow", "failure_classes", "top_failures", "budget_used_per_workflow", "side_effects_per_destination" } }`. Uses `sla_reporting.generate_daily_report`.
- **GET /sla/weekly** — Weekly report. Returns `{ "ok": true, "report": { "success_rate", "per_workflow", "duplicate_side_effects", "regressions_vs_prior_week" } }`. Uses `sla_reporting.generate_weekly_report`.

## UI screens

- **Workflows** — List primary workflows (table: workflow_id, display_name, category, readiness); click row → Workflow detail (declaration, acceptance checks, Run acceptance checks button).
- **Fault scenarios** — List scenarios and per-workflow coverage; form: select workflow + scenario → Run scenario (result: outcome, failure_class, dead_letter).
- **Retention / Purge** — Redact preview (paste JSON → Preview); Purge by run_id (input + Confirm); link to Audit log (recent purge entries).
- **Incident queue** — Table of terminal failures; actions: Replay (shadow), Annotate, Close.
- **Approvals queue** — Table of approval decisions; filter by workflow; show policy_basis; Evaluate approval (form: workflow_id, action_summary).
- **SLA reports** — Tabs or links: Daily report, Weekly report; display report JSON or key metrics (success_rate, duplicate_side_effects, per_workflow).

Navigation: add links to existing nav (Runs, Run DAG, Run detail, Entities, Knowledge, Config, Activity, Status) for: **Workflows**, **Fault**, **Retention**, **Dead-letter**, **Approvals**, **SLA**.

## Documentation index

- **Primary workflow registry** — `hg_core/task_graph/docs/primary_workflow_registry_spec.md`, `primary_workflow_declaration_template.md`
- **Failure injection harness** — `failure_injection_harness_spec.md`
- **Retention, redaction, purge** — `retention_redaction_purge_spec.md`
- **Operator UX minimum** — `operator_ux_spec.md`, `approval_policy_spec.md`
- **SLA reporting** — `sla_reporting_spec.md`
- **Exit criteria** — `workflow_operations_exit_criteria.md`
- **Operator console (existing)** — `operator_console_spec.md` (graphs, runs, artifacts, snapshots, checkpoints, ownership, analytics, entities, knowledge, config, activity, status)
- **Operator interface workflow operations (this)** — API + UI for workflows, fault, retention, operator actions, SLA
