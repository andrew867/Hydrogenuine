# Idempotency, retry by class, dead letter, circuit breakers (Autonomy Ch1 Phase 1)

Contract for C2 (dedupe/ledger), F2 (retry by failure class), F3 (dead letter and replay), and F5 (circuit breakers). Ensures forced retries do not duplicate side effects; terminal failures produce replayable DLQ artifacts; repeated failures trip breakers.

## C2. Idempotency for side effects

For any side-effect step:

- **Dedupe key:** Define a stable key for the effect (e.g. `hash(content) + destination + time_bucket` or `workflow_id + logical_item_id`). See [posting_dedupe](hg_core/posting_dedupe.py): `make_dedupe_key(task_id, date_bucket, content_hash)`, `check_already_posted`, `record_posted`.
- **Side-effect ledger:** Record attempted and completed side effects with that key (e.g. per-session `post_dedupe.json` or generic ledger path). Before external write, consult ledger; if key already completed, return existing result and do not call destination.
- **On retry:** Same inputs must produce same key; ledger consult prevents duplicate.

**Acceptance:** A forced retry with identical inputs does not emit duplicates to the destination.

## F2. Retry policy by failure class

Per failure class (F1), define:

- **max_attempts:** Total attempts (including first) before terminal failure.
- **backoff:** Strategy (e.g. exponential with jitter). See [dag_timeout_retry_contract](dag_timeout_retry_contract.md).
- **retryable:** yes/no. If no, do not retry (e.g. validation_failed, safety_blocked, permission_denied).
- **escalation:** On terminal failure: alert, halt workflow, or require approval.

Executor (or run_task) must load policy by class and apply consistently: e.g. transient_network → retry with backoff; validation_failed → no retry; rate_limited → retry with longer backoff.

**Acceptance:** Executor applies policy consistently across workflows; retryable classes get retries, non-retryable do not.

## F3. Dead-letter capture and replay

- **On terminal failure:** Write a dead-letter artifact containing: run_id, workflow_id (task_id), inputs summary, decisions, failure_class, error details, pointers to logs. Path: `memory/automation/deadletter/<task_id>/<timestamp>.json`. See [deadletter_replay](deadletter_replay.md) and [hg_core.deadletter](hg_core/deadletter.py).
- **Replay:** An entrypoint (script or API) must be able to load a DLQ file and re-run the workflow in **no-side-effects mode** (produce same internal decisions, do not execute external writes). Same inputs + same seed must produce same decisions.

**Acceptance:** Dead-letter includes enough data to reproduce in no-side-effects mode; replay produces same decisions.

## F5. Circuit breakers

- **Scope:** Per workflow and optionally per destination.
- **Trip condition:** After N consecutive failures (or M failures in window), trip the breaker.
- **When tripped:** Do not attempt side effects until cooldown expires or operator acknowledges (reset). Optionally stop scheduling the workflow until ack.
- **Purpose:** Avoid wasting tokens and spamming destinations on repeated failures.

**Acceptance:** Repeated failures stop attempts until cooldown or ack.

## References

- [.cursor/plans/autonomy/chapter1/specs/SPEC_CORRECTNESS_INVARIANTS.md](.cursor/plans/autonomy/chapter1/specs/SPEC_CORRECTNESS_INVARIANTS.md)
- [.cursor/plans/autonomy/chapter1/specs/SPEC_FAILURE_HANDLING.md](.cursor/plans/autonomy/chapter1/specs/SPEC_FAILURE_HANDLING.md)
- [dag_timeout_retry_contract](dag_timeout_retry_contract.md)
- [deadletter_replay](deadletter_replay.md)
