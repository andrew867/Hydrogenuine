# E2E acceptance contract (Autonomy Ch1 Phase 6)

Contract for golden fixtures, fake destination, E2E assertions, and autonomy-ready checklist. Ensures one primary workflow runs end-to-end with fake destination; assertions on trace, dedupe, budget, safety, permissions.

## Golden fixtures

- **Frozen memory snapshot** + minimal inputs summary for deterministic replay.
- **Deterministic seed** for selection steps (e.g. topic choice) so retries reproduce same decisions.
- Stored under tests/fixtures/ or memory/automation/fixtures/.

## Fake destination

- **Fake destination tool** records events to a **local ledger** (no real outbound call).
- Ledger path: e.g. memory/automation/e2e_ledger.jsonl or test tmp dir.
- Each "would post" event: content hash, destination, time_bucket, run_id.

**Acceptance:** Publish workflow sends exactly one "would post" event to ledger; retry sends zero additional events (dedupe).

## E2E assertions

- **Run trace** exists and links to artifacts (run_id, summary.json, events.jsonl).
- **Failures** are classified (failure_class in summary).
- **Budgets** enforced under retries (budget_used in trace; cap respected).
- **Permissions** deny undeclared scopes (capability check when declaration exists).
- **Safety gate** blocks disallowed content when ON (no call when blocked).
- **Idempotency** prevents duplicates (ledger has one event per logical post).

## Autonomy-ready checklist

A workflow is **autonomy-ready** when (see chapter1 ACCEPTANCE_CRITERIA):

- It is idempotent for side effects.
- It has explicit success criteria and checks.
- It produces an audit summary.
- It respects permissions and safety policy.
- It stays within budgets in normal and degraded modes.
- It passes E2E tests using fake destinations.

## Release checklist

Before release: run TEST_PLAN and ACCEPTANCE_CRITERIA; sign off. Optional: label workflow in registry as autonomy-ready.
