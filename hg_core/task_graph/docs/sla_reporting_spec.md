# Spec: SLA targets and reporting

## Baseline SLA targets (initial)
Applies to the 3 primary "analysis styles" workflows and the 45-minute knowledge task.
- Duplicate side effects: **0 tolerated** for workflows with external writes (enforced via idempotency).
- Weekly unattended success rate target (when marked unattended): **>= 95%** successful runs.
- Budget compliance: **no per-day budget overruns**; degrade or skip when exceeded.

## Definitions
- Successful run: all must-level acceptance checks pass.
- Degraded success: must-level checks pass, but optional steps skipped and recorded.
- Failure: any must-level check fails.

## Reporting requirements
Daily:
- runs by workflow and status (success, degraded, failed)
- top failure classes and counts
- budget used per workflow
- side effects count per destination label
Weekly:
- success rate per primary workflow
- duplicate side-effect incidents (should be zero)
- top regressions vs prior week

## Acceptance
- Reports can be generated from run traces without manual reconstruction.
