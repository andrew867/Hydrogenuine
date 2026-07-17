# DAG Validator Diagnostics Contract

This document defines the diagnostics API for DAG validation. See also `.cursor/plans/dag/chapter2/docs/specs/dag_validator_diagnostics.md`.

## Diagnostic type

```python
@dataclass
class Diagnostic:
    level: str   # "error" | "warn"
    code: str    # standard code (see below)
    message: str
    node_id: Optional[str] = None
    field_path: Optional[str] = None
    suggestion: Optional[str] = None
```

## API

- **validate_dag_with_diagnostics(dag, strict=False)**  
  - `dag`: `DAG` instance or dict (dict is converted via `DAG.from_dict`).  
  - Returns: `{"ok": bool, "errors": list[Diagnostic], "warnings": list[Diagnostic]}`.  
  - `ok` is `True` when there are no errors (warnings may be non-empty).  
  - All validation failures are returned as errors with a standard `code`.

## Standard diagnostic codes

| Code | Description |
|------|-------------|
| DUPLICATE_NODE_ID | Duplicate node id |
| UNKNOWN_DEPENDENCY | depends_on references unknown node |
| CYCLE_DETECTED | Cycle in dependency graph |
| INVALID_NODE_TYPE | Node type not in NODE_TYPES |
| INVALID_GATE_TARGET | Gate true_targets/false_targets references unknown node |
| INVALID_LOOP_BODY | Loop body references unknown node or body node depends outside loop |
| NESTED_LOOP_DISALLOWED | Loop body contains another loop node |
| WRITE_IN_LOOP_BLOCKED | Write node in loop body without allow_side_effects_in_loops and checkpoint |
| WRITE_RETRY_NO_IDEMPOTENCY | Write node with max_retries > 0 must have idempotency_key |
| MISSING_GRAPH_ID | graph_id is required |
| MISSING_FIELD | Required node/graph field missing (assigned_entity, policy, checkpoints, etc.) |
| INVALID_POLICY_VALUE | policy or run_policy value out of allowed set or range |
| INVALID_RUN_POLICY | run_policy field invalid (max_concurrency, failure_mode, input_binding_mode, etc.) |

Optional (when strict expression validation is implemented):

- EXPRESSION_STRICT_VAR_MISSING

## WRITE_RETRY_NO_IDEMPOTENCY

- **Rule**: For any node with `policy.effect_class == "write"` and `policy.max_retries > 0`, `policy.idempotency_key` must be set (non-empty string or expression).
- **Rationale**: Retried write operations need an idempotency key to avoid duplicate side effects.
- **Validation**: Emit error with code `WRITE_RETRY_NO_IDEMPOTENCY`, node_id set, suggestion e.g. "Set policy.idempotency_key for write nodes with max_retries > 0."
