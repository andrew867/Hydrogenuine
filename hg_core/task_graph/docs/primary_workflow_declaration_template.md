# Primary Workflow Declaration (template)

workflow_id:
display_name:
category:
coordination_style: end_to_end|baton|parallel_contributors
checkpoints: []

side_effects: none|internal_write|external_write
destinations: []

success_criteria:
  -

acceptance_checks:
  - id:
    description:
    severity: must|should
    evaluation: machine|manual
  -

degraded_mode_rules:
  -

idempotency:
  required: yes|no
  dedupe_key_strategy:
  ledger_bucketing:

budgets:
  per_run:
  per_day:
  degrade_steps:
    -

sla_targets:
  reliability_target:
  duplicate_side_effects: zero

approvals_policy:
  mode: default_approve
  strict_blacklist_categories:
    -

retention_class:
readiness: supervised|unattended|blocked
