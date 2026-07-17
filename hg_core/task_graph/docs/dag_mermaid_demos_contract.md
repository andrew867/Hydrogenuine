# DAG Mermaid and Demo Scripts Contract

## Mermaid

- **dag_to_mermaid(dag) -> str**: Accepts a DAG as dict (or DAG instance with `.to_dict()`). Returns a string that is valid Mermaid flowchart TD: first line `flowchart TD`, then one line per node with no deps as `  nid[nid]`, and one line per edge as `  dep --> nid`. The result may be wrapped in ` ```mermaid ` code fence for use in docs.

## Demo scripts

- **run_goal_to_dag_demo**: CLI `--goal <string>` and optional `--out <dir>` (default `./.dag_plans`). Uses `DagPlanner` from `hg_core.task_graph` with real validator (validate_dag_with_diagnostics). Writes DAG JSON to `{out}/{graph_id}.json` and prints mermaid. Exits 2 if planner returns no DAG.
- **run_reviewed_dag_demo**: CLI `--dag <path>` (path to DAG JSON) and optional `--out <dir>` (default `./.dag_reviews`). Loads DAG, calls `review_dag(dag, ReviewPolicy())` from `hg_core.task_graph` (optionally after `annotate_in_loop_body(dag)`). Writes `{graph_id}.review_report.json` and, if not blocked, `{graph_id}.reviewed.json`. Exits 2 if review blocked.

## Example goals

Example goal JSON files (e.g. `goal_01.json`, `goal_02.json`) may live under `.cursor/plans/dag/chapter2/examples/planner_goals/` and can be referenced by demos or tests.
