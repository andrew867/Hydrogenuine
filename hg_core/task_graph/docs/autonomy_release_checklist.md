# Autonomy release checklist (Phase 6)

Before marking a workflow **autonomy-ready** or releasing autonomy features:

1. **Trace:** Every run emits a structured trace with run_id; artifacts link to run_id.
2. **Failure class:** Every failure has a failure_class (F1) in summary.
3. **Idempotency:** Dedupe ledger and keys; forced retry does not duplicate side effects.
4. **Retry/DLQ/breaker:** Retry policy by class; DLQ on terminal failure; circuit breakers trip and reset.
5. **Capabilities:** Undeclared scopes/destinations denied; safety gate blocks when ON; approval tiers applied.
6. **Governance:** Proposals validated; rollback one-step and tested; audit trail recorded.
7. **Budget:** Per-run and daily budgets enforced; trace has budget fields; retries same bucket.
8. **Concurrency:** Lock prevents duplicate run per (workflow_id, time_bucket); caps enforced.
9. **E2E:** At least one primary workflow passes E2E test with fake destination; assert trace, dedupe, budget, safety.

See [.cursor/plans/autonomy/chapter1/checklists/ACCEPTANCE_CRITERIA.md](.cursor/plans/autonomy/chapter1/checklists/ACCEPTANCE_CRITERIA.md) for workflow-level autonomy-ready criteria.
