# Spec: Primary workflow registry and acceptance checks

## Goal
Define a single, authoritative registry of "primary workflows" with:
- purpose and distinct goals
- explicit success criteria
- acceptance checks (machine-evaluable)
- autonomy readiness label (supervised, unattended allowed, blocked)
- scheduling and SLO/SLA targets

## Workflows (declared primary)
1) 4claw
2) moltbook
3) moltstack
4) knowledge-task-45min (recurring knowledge ingestion and graph recording)

Note: detailed criteria already exist in legacy task markdown files. This spec defines how to migrate those criteria into workflow declarations and DAG-style execution.

## Registry fields (required)
- workflow_id
- display_name
- category: analysis | publish | engage | knowledge | maintenance
- coordination_style: end_to_end | baton | parallel_contributors
- checkpoints (if baton)
- side_effects: none | internal_write | external_write
- destinations (high-level labels only)
- success_criteria: list of statements
- acceptance_checks: list of checks with pass/fail output
- degraded_mode_rules
- idempotency: dedupe strategy required if external_write
- budgets: per_run and per_day (units abstracted)
- sla_targets: reliability and duplicate-side-effect guarantee
- approvals_policy: default_approve with strict blacklist deny
- strict_blacklist_categories: list of disallowed content/action categories
- retention_class: which retention policy bucket applies
- readiness: supervised | unattended | blocked

## Acceptance checks (minimum baseline)
All primary workflows must implement these baseline checks:
- Trace exists and links outputs
- No missing required checkpoints (if baton)
- No external action attempted under ownership conflict
- Safety gate executed for external actions
- Idempotency ledger updated for external actions (and prevents duplicates on retry)
- Budget not exceeded (or degraded/skip behavior triggered and recorded)

## Migration plan (high level)
- Extract goals and criteria from legacy task markdowns.
- Encode into workflow declarations using the template provided.
- Build DAGs per workflow that enforce checkpoints, receipts, and safety gates.
- Mark readiness: supervised until E2E test suite passes and drills completed.

## Runtime loading and bootstrap
- Canonical file path: `memory/automation/workflow_registry.json`.
- Runtime must prefer this on-disk file and bootstrap it with minimal declarations if missing/invalid.
- Missing policy sections are backfilled with safe defaults and logged:
  - `destinations`
  - `degraded_mode_rules`
  - `idempotency`
  - `budgets`
  - `strict_blacklist_categories`
- `approvals_policy.strict_blacklist_categories` must always be present.
