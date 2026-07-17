# Behavior and delegation run_dir artifacts (Autonomy Ch5)

When the executor runs with `run_dir` set and delegation monitoring is enabled (e.g. via a delegation manager or hook), the following artifacts are written under run_dir:

| Artifact | Description |
|----------|-------------|
| behavior_events.jsonl | One JSON object per line; schema per [behavior_telemetry_schema](../../../docs/specs/behavior_telemetry_schema.md). |
| delegation_graph.json | Full graph (nodes, edges) for the run; schema per [delegation_graph_schema](../../../docs/specs/delegation_graph_schema.md). |
| delegation_summary.json | Compact summary: run_id, workflow_id, metrics (depth, width, handoffs, splits, merges, etc.), anomalies, top_bottlenecks, final_state. |

Existing run_dir artifacts (events.jsonl, summary.json, state.json, graph.json) are unchanged. Behavior events may be emitted in addition to or merged with events.jsonl per configuration.
