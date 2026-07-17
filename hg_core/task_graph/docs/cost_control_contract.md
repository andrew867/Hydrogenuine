# Cost control contract (Autonomy Ch1 Phase 4)

Contract for K1 (budgets), K2 (backpressure), K3 (accounting), K4 (retry budget). Per-run and per-day budgets; backpressure when over; run trace accounting; retries consume same bucket.

## K1. Budgets

Define:

- **Per-run** token/cost budget per workflow tier.
- **Per-day** budget per workflow and global.
- **Budget behavior:** degrade | skip | require_approval when exceeded.

See [effect_budget_contract](effect_budget_contract.md) and [ECONOMIC_CONTROL](docs/automation/ECONOMIC_CONTROL.md).

## K2. Backpressure

When budgets are exceeded:

- Stop optional steps first.
- Reduce enrichment breadth (knowledge intake limits).
- Disable expensive modes.
- If still exceeding, skip run and alert.

**Acceptance:** Daily caps enforced with degrade/skip behavior.

## K3. Accounting

Run trace must include:

- Estimated tokens in and out.
- Budget used and remaining.
- Cost estimate (when model pricing available).

Aggregate daily summaries per workflow and destination.

**Acceptance:** Reports show cost by workflow; trace has budget fields.

## K4. Guardrails under failure

- **Retries consume from the same budget bucket.** A retry does not get a fresh budget; it shares the run’s budget_used.
- Circuit breakers prevent unbounded spend (see Phase 1).

**Acceptance:** Repeated transient failures do not exceed daily budget; system degrades and alerts.
