# DAG Overseer Review Contract (MVP)

Review is a deterministic pass that enforces safety and quality before execution. See `.cursor/plans/dag/chapter2/docs/specs/dag_overseer_review_contract.md`.

## API

- **review_dag(dag_dict, policy) -> (reviewed_dag | None, report)**
  - **dag_dict**: DAG as dict (e.g. from planner or load_dag + to_dict). Nodes may have **\_meta.in_loop_body** set (see below).
  - **policy**: ReviewPolicy (max_iterations_cap, max_node_executions_cap, force_fail_fast_on_write, allow_side_effects_in_loops).
  - **Returns**: (reviewed_dag, report). If any issue has level "error", reviewed_dag is None and report["blocked"] is True. report has "blocked": bool and "issues": list of {level, code, message, node_id?, suggestion?}.

## in_loop_body annotation

Before calling review_dag, the caller must set **\_meta.in_loop_body = True** on each node that is in some loop's body (i.e. node id appears in some loop node's inputs.body). This can be done by a helper that walks the DAG: for each node of type "loop", for each id in inputs.body, set nodes[id].setdefault("_meta", {})["in_loop_body"] = True.

## Run flow with review

When "run with review" is requested:

1. Validate DAG (e.g. validate_dag_with_diagnostics).
2. Annotate nodes with _meta.in_loop_body (helper).
3. Call review_dag(dag_dict, ReviewPolicy()).
4. If report["blocked"]: do not run; if run_dir is set, write only review_report.json to run_dir.
5. If not blocked: run executor on **reviewed** DAG; when run_dir is set, write graph.json (input), graph.reviewed.json (reviewed), review_report.json, then state.json, summary.json, events.jsonl.

## Persistence (run_dir)

When run_dir is provided and review was performed:

- **graph.reviewed.json**: the reviewed DAG (dict) as JSON.
- **review_report.json**: report dict (blocked, issues).

## Issue codes (examples)

- ADD_WRITE_CHECKPOINT: added checkpoints.before for a write node.
- WRITE_RETRY_NO_IDEMPOTENCY: write node with retries has no idempotency_key (error, blocked).
- CLAMP_MAX_ITERATIONS: clamped loop max_iterations to policy cap.
- WRITE_IN_LOOP_BLOCKED: write node in loop body blocked by policy (error, blocked).
