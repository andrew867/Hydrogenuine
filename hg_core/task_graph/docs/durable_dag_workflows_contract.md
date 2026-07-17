# Durable DAG Workflows: HITL, State History, and Resume Semantics

Target: be feature-competitive with durable workflow semantics (resume without re-running, pause/resume, state history, fork/replay).

## Current gaps
1) Persistence only at run end or terminal failures, crash mid-run loses progress.
2) No pause-at-checkpoint, checkpoints do not return control.
3) No versioned state history (single state.json).
4) RUNNING nodes on resume can stall progress.
5) Timeout enforcement and tests are incomplete.

## Requirements
A) Persist after every node terminal transition (DONE/FAILED/SKIPPED) and at pauses.
B) Resume normalizes RUNNING -> READY (or PENDING).
C) HITL: pause_at_checkpoint, return status="paused" with checkpoint payload, resume continues.
D) State history snapshots in run_dir/state_history with index.
E) Fork from snapshot N to new run_id and run_dir.
F) Deterministic ordering and audit artifacts (events append-only, snapshots immutable).

## Acceptance
- Crash after node A completes, resume never reruns A.
- Pause at checkpoint_before/after, resume completes.
- state_history contains multiple snapshots and index.
- Fork from snapshot N runs independently.
- Retry and timeout tests pass; deterministic readiness ordering enforced.
