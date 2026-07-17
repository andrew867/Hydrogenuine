# DAG Execution Artifacts Contract (run_dir)

When `TaskGraphExecutor.run()` is called with an optional `run_dir` path, the executor writes standard artifacts into that directory. See also `.cursor/plans/dag/chapter2/docs/specs/dag_execution_artifacts.md`.

## run_dir parameter

- **run_dir: Optional[Path] = None** on `TaskGraphExecutor.run(dag, graph_inputs=..., run_id=..., run_dir=...)`.
- When **run_dir** is provided:
  - The directory is created if it does not exist.
  - The following files are written (see below).
- When **run_dir** is None, behavior is unchanged: no artifact files are written (StateStore still persists by run_id elsewhere if configured).

## Artifacts written

| File | When | Content |
|------|------|--------|
| graph.json | Before run | Input DAG as JSON (dag.to_dict()). |
| state.json | After run (all exit paths) | RunState: node_states, node_outputs, state, loop_state. |
| summary.json | After run | Final summary (see below). |
| events.jsonl | During run | One JSON object per telemetry event (append). |

## summary.json recommended fields

- **run_id**, **graph_id**, **started_at**, **ended_at**
- **final_status**: `completed` | `failed` | `partial`
- **counts**: `done`, `failed`, `skipped`, `blocked` (node counts)
- **outputs**: selected node outputs or declared final outputs (optional)
- **error_summary**: list of `{node_id, code, message}` for failed/blocked nodes
- **run_dir**: path to run_dir (string)

## max_node_executions cap

- When **run_policy.max_node_executions** is set (integer >= 1):
  - The executor maintains a **global execution count**: each transition of a node to RUNNING counts as one execution.
  - Before scheduling the next batch of nodes, if the count would exceed **max_node_executions**, the run stops:
    - No further nodes are scheduled.
    - **final_status** is set to `failed` (or `partial`) and the summary includes an error indicating the cap was exceeded.
  - Deterministic scheduling (sorted ready nodes) is unchanged; only the cap check is added.
