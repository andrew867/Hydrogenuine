# Structured run logs and observability (plans o1–o4)

## o1. Structured run logs (JSONL)

When `run_dir` is set, the executor writes **events.jsonl** to the run directory. Each line is a JSON object: `{"event": "<name>", ...payload}`.

**Event types:** `dag_run_started`, `dag_run_completed`, `dag_node_started`, `dag_node_completed`, `dag_node_failed`, `dag_node_retried`, `dag_node_skipped`, `dag_node_blocked`, `budget_updated`, `budget_exceeded`.

**Payload fields (typical):**
- **dag_node_started:** `graph_id`, `run_id`, `node_id`, `started_at` (if set).
- **dag_node_completed:** `graph_id`, `run_id`, `node_id`, `status`, `attempt_count`, `duration_ms`, and optionally `tokens` (when dispatch returns them).
- **budget_updated:** `budget_used` (e.g. `{"tokens": N, "external_calls": M}`).

**summary.json** (same run_dir) contains `run_id`, `graph_id`, `final_status`, `counts`, `outputs`, `error_summary`, and when budgets are used, **budget_used** (token counts). Use summary for per-run totals; use events.jsonl for node-level timings and sequence.

**Output hashes:** When the recorder is used, request/response hashes can be written to the recorder sink; output hashes for dedupe or integrity can be added to node_completed payloads in a future iteration.

## o2. Metrics

- **Tokens per node/run:** From `budget_used` in summary and from `budget_updated` events (cumulative). Per-node tokens when dispatch returns them in node output.
- **Success rate, retries, loop iterations, latency:** From `counts` in summary (done, failed, skipped, blocked); from `dag_node_retried` count; from loop events (iteration); from `duration_ms` in node_completed/failed events.

Expose for dashboard or aggregator by reading summary.json and events.jsonl under run_dir (or aggregated under memory/automation/dag_runs).

## o3. Trace IDs

One **run_id** (UUID) is generated per run and flows through all nodes and file artifacts: it is included in every telemetry event, in summary.json, and in state.json. Use `run_id` to correlate events and artifacts for a single run.

## o4. Alert thresholds

Define thresholds and wire to overseer or notification as needed:

- **Token spike:** e.g. run tokens > 2× baseline for that graph.
- **Retry spike:** e.g. retries in last N runs > threshold.
- **Posting halted:** e.g. no successful post for task X in 24h.
- **Proposal flood:** e.g. number of entity DAG proposals in last hour > N.
- **Memory trim exceeded:** e.g. trimmed tokens in load_compacted_memory > 80% of requested cap.

Implementation: compare metrics (from o2) to thresholds and emit alerts (log, webhook, or overseer signal).
