# Deterministic Replay Harness Contract (MVP)

## Goal
Given a completed run, you can replay it deterministically without calling real tools or LLMs, and verify identical:
- node terminal statuses
- node outputs (or declared output hashes)
- summary fields
- (optional) state_history snapshots hashes

This is a foundation for:
- regression test suite
- time-travel debugging with guaranteed repeatability
- proving whether a change altered runtime semantics

## Definitions
- attempt: one dispatch invocation for a node (includes retries)
- recording: immutable log of attempts and their observed results
- replay: execution using recorded results instead of live dispatch

## Artifact format
Within run_dir add:
- recordings/attempts.jsonl (append-only)
- recordings/index.json (optional convenience)
Each attempt record MUST include:
- run_id, graph_id
- node_id
- attempt_no (1-based within node and iteration)
- loop_id and iteration if applicable
- gate_parent and gate_taken if applicable
- dispatched_at_ts, completed_at_ts
- request: canonicalized dispatch request (node type, assigned_entity, resolved_inputs, policy subset)
- response: canonicalized dispatch response (status, outputs, error_code, error_message, tool_call metadata)
- response_digest: hash of canonical response (for quick comparisons)

## Canonicalization rules
To keep replay deterministic:
- Remove non-deterministic fields from request/response (wall-clock durations can be recorded but excluded from digest)
- Sort dict keys, normalize lists where order is not semantic
- Normalize paths (run_dir) out of payloads

## Replay dispatcher
Provide a ReplayDispatcher that:
- loads attempts.jsonl
- for each live dispatch request, selects the next recorded attempt by (node_id, attempt_no, loop context)
- returns the recorded response
- errors loudly on mismatch (missing record, different request digest if strict)

ReplayConfig:
- strict_requests: bool — when True, verify request_digest matches recorded request_digest before returning response; when False, match only by (node_id, attempt_no, loop context).

Dispatch contract: ReplayDispatcher.dispatch(...) returns the same shape as dispatch_node: a dict with "ok", "outputs", and optionally "error" keys.

## Strictness levels
- strict_requests: verify request_digest matches recorded request_digest before returning response
- loose_requests: match only by (node_id, attempt_no, loop context)

MVP recommendation:
- strict_requests enabled for tests, loose option for interactive debugging.

## Integration points
Executor should call a RecordingHook on:
- before dispatch (record request)
- after dispatch (record response)
- on node terminal transition (record final status and outputs digest)

Recording should be safe:
- append-only
- flushed to disk after each attempt (or after each node) to survive crashes

## Acceptance tests
1) Record a run (live dispatcher).
2) Replay with ReplayDispatcher.
3) Assert:
   - same terminal statuses map
   - same outputs for selected nodes
   - same final_status in summary
4) Modify a recorded request slightly; strict replay should fail with a mismatch error.

## Regression harness (Phase 4)
- **Golden DAGs:** A small set of deterministic DAGs (e.g. linear eval-only graphs) are run with recording to produce reference attempts.jsonl.
- **Fixture location:** Recordings are stored under `tests/hg_core/fixtures/replay_golden/<dag_id>/recordings/attempts.jsonl` (or `attempts.jsonl` directly in `<dag_id>/`). Each `<dag_id>` is a stable name (e.g. `golden_linear_2`, `golden_linear_3`).
- **Record:** Run `python scripts/run_replay_regression.py --record` to run each golden DAG with the live dispatcher and recorder, then copy the recordings into the fixture directory. Commit the fixture files so they serve as the baseline.
- **Compare:** Run `python scripts/run_replay_regression.py` (or `--compare`). The script runs each golden DAG with recording, extracts digest lists (request_digest and response_digest per attempt) from the new run, loads the fixture attempts.jsonl for that DAG, and compares digest lists. If any digest differs, the script exits with non-zero and reports which DAG and which attempt differ. Use in CI or locally to detect changes in executor/recording semantics across commits.
