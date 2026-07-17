# DAG Planner Contract (MVP)

The planner turns a goal (and optional context/constraints) into a DAG dict. It does **not** execute.

## Inputs

- **goal**: string
- **context**: dict, optional (e.g. `{"inputs": {...}}`)
- **constraints**: `PlannerConstraints` (optional)
  - `disallowed_tools`: list of tool names to exclude
  - `max_iterations_default`: default max_iterations for loop nodes (e.g. 10)
  - `max_node_executions_cap`: cap for run_policy.max_node_executions (e.g. 500)
  - `strict_mode`: passed to validator (expression_strict_mode, etc.)
  - `failure_mode`: "continue" | "fail_fast"
  - `allow_side_effects_in_loops`: bool

## Outputs

- **PlannerResult**
  - `dag`: dict or None (DAG JSON compatible with `DAG.from_dict` / `load_dag`)
  - `diagnostics`: list of `Diagnostic` (from validator diagnostics)
  - `confidence`: float (e.g. 0.0 on failure, 0.6 on success)

## Validator adapter (for planner use)

The planner expects a validator with this shape:

- `validate(dag_dict, strict) -> {"ok": bool, "errors": list[dict], "warnings": list[dict]}`
- Each error dict: `code`, `message`, optional `node_id`, `field_path`, `suggestion`

Adapter implementation:

- Accept DAG as dict.
- Call `validate_dag_with_diagnostics(dag_dict, strict)` (from `hg_core.task_graph.validator_diagnostics`).
- Return `{"ok": result["ok"], "errors": [d.to_dict() for d in result["errors"]], "warnings": [d.to_dict() for d in result["warnings"]]}`.

So the planner uses the same diagnostic codes and messages as the main validator.

## MVP behavior

- **Template-first**: select a template by goal intent (e.g. job_search_weekly_diff, research_summary, generic_workflow).
- Fill template placeholders from context.
- Apply conservative defaults (timeouts, retries, effect_class, checkpoints, run_policy).
- Validate; if invalid, return `dag=None` and `diagnostics` from the validator.
- No execution: planner only returns DAG JSON and diagnostics.

## Templates (minimum set)

- **job_search_weekly_diff**: goal hints "job" + "weekly"/"diff"
- **research_summary**: goal hints "research" or "summar"
- **generic_workflow**: fallback

Template functions have signature `(goal, context, constraints) -> dict` (DAG dict).
