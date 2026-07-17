# Workflow Operations: Exit Criteria and Drill Run

Implementation complete for workflow operations (primary workflow registry, failure injection harness, retention/redaction/purge, operator UX minimum, SLA reporting). Final sign-off uses the acceptance checklist and runbook drills.

## Acceptance checklist

See [.cursor/plans/autonomy/chapter3/checklists/ACCEPTANCE_CRITERIA.md](.cursor/plans/autonomy/chapter3/checklists/ACCEPTANCE_CRITERIA.md) for the full checklist. Summary:

- **Primary workflows:** Registry entries for 4claw, moltbook, moltstack, knowledge-task-45min; readiness enforced.
- **Failure injection:** Smoke fault suite runs in CI (`pytest -m smoke_fault`); ≥3 scenarios per primary workflow.
- **Retention and redaction:** Redaction tests pass; purge operations work and are audited.
- **Operator UX:** Status overview, run detail, dead-letter queue, approvals queue; replay in shadow mode; pause/resume and rollback available.
- **SLA reporting:** Daily and weekly reports from traces; success rate and duplicate side effects metric.

## Drill run (run at least once)

Run the reliability drills from [.cursor/plans/autonomy/chapter3/runbooks/RUNBOOK_DRILLS.md](.cursor/plans/autonomy/chapter3/runbooks/RUNBOOK_DRILLS.md) at least once (quarterly or after major changes):

1. Dead-letter replay drill
2. Rollback drill (change governance)
3. Destination outage drill
4. Concurrency drill

Document the drill run (pass/fail and evidence pointers) for audit.

## Test commands

- Workflow operations tests: `pytest tests/hg_core/test_workflow_registry.py tests/hg_core/test_fault_injection.py tests/hg_core/test_retention_redaction_purge.py tests/hg_core/test_operator_ux.py tests/hg_core/test_sla_reporting.py -v`
- Smoke fault suite only: `pytest -m smoke_fault -v`
