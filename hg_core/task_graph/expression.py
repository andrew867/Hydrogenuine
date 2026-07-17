"""
Safe expression engine for task graph control flow (eval, gate, loop conditions).

JSONLogic-style subset: no arbitrary code execution. Supports $state.*, $node.<id>.<key>,
$graph.inputs.*, and inside loop body $loop.id, $loop.iteration, $loop.max_iterations, $loop.state.
Dot-path only in MVP. Lenient mode: missing vars → null; strict mode: missing paths → error.
Null in boolean context is false; lenient arithmetic with null yields null; strict raises.
See .cursor/plans/task_graph_tc_implementation.plan.md Part 1.6 and Part 2c.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

# Sentinel for "missing variable" to distinguish from explicit null in context
_MISSING: Any = object()


def _get_by_dot_path(obj: Any, path: str) -> Any:
    """Resolve dot path (no array indexing in MVP). Returns _MISSING if any segment missing."""
    if obj is None or obj is _MISSING:
        return _MISSING
    for key in path.split("."):
        key = key.strip()
        if not key:
            return _MISSING
        if not isinstance(obj, dict):
            return _MISSING
        if key not in obj:
            return _MISSING
        obj = obj[key]
    return obj


def resolve_var(path: str, context: Dict[str, Any]) -> Any:
    """
    Resolve a variable path to a value. Path format: leading namespace then dot path.

    Supported namespaces:
      - state.<path>   → context["state"] dot path
      - node.<node_id>.<output_key>  → context["node"].get(node_id, {}).get(output_key)
      - graph.inputs.<key>  → context["graph"]["inputs"].get(key)
      - loop.id | loop.iteration | loop.max_iterations | loop.state  (when in loop body)

    Returns resolved value or _MISSING if not found. Caller treats _MISSING as null in lenient mode.
    """
    path = (path or "").strip()
    if not path:
        return _MISSING

    # state.*
    if path.startswith("state."):
        state = context.get("state")
        if state is None:
            return _MISSING
        return _get_by_dot_path(state, path[6:].strip("."))

    # node.<node_id>.<output_key>
    if path.startswith("node."):
        rest = path[5:].strip(".")
        node_outputs = context.get("node") or {}
        if "." not in rest:
            return _MISSING
        nid, out_key = rest.split(".", 1)
        nid, out_key = nid.strip(), out_key.strip()
        if nid not in node_outputs:
            return _MISSING
        out = node_outputs[nid]
        if isinstance(out, dict) and out_key in out:
            return out[out_key]
        return _MISSING

    # graph.inputs.*
    if path.startswith("graph.inputs."):
        graph = context.get("graph") or {}
        inputs = graph.get("inputs") or {}
        key = path[13:].strip(".")
        return inputs.get(key, _MISSING) if key else _MISSING

    # loop.* (when in loop body)
    if path.startswith("loop."):
        loop = context.get("loop") or {}
        rest = path[5:].strip(".")
        if rest == "id":
            return loop.get("id", _MISSING)
        if rest == "iteration":
            return loop.get("iteration", _MISSING)
        if rest == "max_iterations":
            return loop.get("max_iterations", _MISSING)
        if rest == "state":
            return loop.get("state", _MISSING)
        return _MISSING

    return _MISSING


def _is_missing(v: Any) -> bool:
    return v is _MISSING


def _norm(v: Any) -> Any:
    """Convert _MISSING to None for internal use after resolution."""
    return None if v is _MISSING else v


def _evaluate(
    expr: Any,
    context: Dict[str, Any],
    strict: bool,
    missing_paths: Optional[Set[str]] = None,
) -> Any:
    """
    Evaluate a JSONLogic-style expression. Returns value or raises in strict mode on null/missing.
    If missing_paths is provided (strict validation), collects missing var paths instead of raising.
    """
    collecting = missing_paths is not None
    # When collecting missing paths for validation, do not raise on missing or null
    effective_strict = strict and not collecting

    # Literals
    if expr is None or isinstance(expr, (bool, int, float, str)):
        return expr

    # Variable reference: {"var": "state.loops.x.counter"} or {"var": ["path", default]}
    if isinstance(expr, dict) and "var" in expr and len(expr) == 1:
        var_spec = expr["var"]
        if isinstance(var_spec, list):
            path = var_spec[0] if var_spec else ""
            default = var_spec[1] if len(var_spec) > 1 else None
        else:
            path = str(var_spec)
            default = None
        v = resolve_var(path, context)
        if _is_missing(v):
            if missing_paths is not None:
                missing_paths.add(path)
            if effective_strict:
                if default is not None:
                    return default
                raise ValueError(f"Missing variable path: {path}")
            return None
        return v

    # Single-key operators
    if isinstance(expr, dict) and len(expr) == 1:
        op, args = next(iter(expr.items()))

        if op == "!":
            a = _evaluate(args, context, strict, missing_paths)
            if effective_strict and _is_missing(a):
                raise ValueError("null in logical not (strict)")
            return not (_norm(a) if _is_missing(a) else a)

        if op == "and":
            if not isinstance(args, list):
                args = [args]
            for a in args:
                val = _evaluate(a, context, strict, missing_paths)
                if effective_strict and _is_missing(val):
                    raise ValueError("null in and (strict)")
                if _is_missing(val) or not (val if val is not None else False):
                    return val if not strict else (None if _is_missing(val) else val)
            return True

        if op == "or":
            if not isinstance(args, list):
                args = [args]
            last = None
            for a in args:
                val = _evaluate(a, context, strict, missing_paths)
                last = val
                if effective_strict and _is_missing(val):
                    raise ValueError("null in or (strict)")
                if not _is_missing(val) and (val if val is not None else False):
                    return val
            return _norm(last) if last is not None else None

        if op in ("==", "!=", "<", "<=", ">", ">="):
            if not isinstance(args, list) or len(args) < 2:
                raise ValueError(f"Binary operator {op} requires [a, b]")
            a = _evaluate(args[0], context, strict, missing_paths)
            b = _evaluate(args[1], context, strict, missing_paths)
            if effective_strict:
                if _is_missing(a) or _is_missing(b) or a is None or b is None:
                    raise ValueError(f"null in comparison {op} (strict)")
            if _is_missing(a) or _is_missing(b):
                return False  # lenient: comparison with null → false
            a, b = _norm(a), _norm(b)
            if op == "==":
                return a == b
            if op == "!=":
                return a != b
            if a is None or b is None:
                return False
            if op == "<":
                return a < b
            if op == "<=":
                return a <= b
            if op == ">":
                return a > b
            if op == ">=":
                return a >= b

        if op in ("+", "-", "*", "%"):
            if not isinstance(args, list):
                args = [args]
            if op in ("-", "*", "%") and len(args) < 2:
                raise ValueError(f"Operator {op} requires at least two operands")
            vals = [_evaluate(x, context, strict, missing_paths) for x in args]
            if effective_strict:
                for v in vals:
                    if _is_missing(v):
                        raise ValueError(f"null in arithmetic {op} (strict)")
            if any(_is_missing(v) for v in vals):
                return None  # lenient: arithmetic with null → null
            vals = [_norm(v) for v in vals]
            if any(v is None for v in vals):
                if effective_strict:
                    raise ValueError(f"null in arithmetic {op} (strict)")
                return None
            # In strict, reject explicit None in arithmetic (already handled above)
            if op == "+":
                if len(vals) == 1:
                    return vals[0]
                try:
                    return sum(vals)
                except TypeError:
                    return (vals[0] or "") if len(vals) == 1 else (str(vals[0]) + str(vals[1]))
            if op == "-":
                return vals[0] - vals[1]
            if op == "*":
                acc = vals[0]
                for v in vals[1:]:
                    acc *= v
                return acc
            if op == "%":
                return vals[0] % vals[1]

    # Not a recognized expression
    raise ValueError(f"Unsupported expression: {expr!r}")


def evaluate(
    expression: Any,
    context: Dict[str, Any],
    strict: bool = False,
) -> Any:
    """
    Evaluate an expression with the given context.

    Context should have keys: state (dict), node (dict of node_id -> outputs), graph (inputs dict),
    and optionally loop (id, iteration, max_iterations, state).

    strict: if True, missing variable paths and null in arithmetic/comparison raise ValueError.
    Lenient (default): missing → null, null in boolean = false, arithmetic with null → null.
    """
    return _evaluate(expression, context, strict=strict)


def validate_expression_paths(
    expression: Any,
    context: Dict[str, Any],
) -> Tuple[bool, Set[str]]:
    """
    In strict validation mode, collect all variable paths referenced in the expression
    and return (True, set()) if all exist in context, else (False, set of missing paths).
    Does not evaluate fully; only checks var references.
    """
    missing: Set[str] = set()
    try:
        _evaluate(expression, context, strict=True, missing_paths=missing)
        return (len(missing) == 0, missing)
    except ValueError:
        return (False, missing)
