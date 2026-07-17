"""Terminal state precedence resolver (CT-05)."""

from __future__ import annotations

from hg_core.failures.registry import ReasonCodeRegistry, load_registry, validate_reason_code


def resolve_aggregate_state(states: list[str], registry: ReasonCodeRegistry | None = None) -> str:
    """Return highest-precedence terminal state from a list."""
    reg = registry or load_registry()
    order = {state: index for index, state in enumerate(reg.precedence)}
    best = None
    best_rank = len(reg.precedence) + 1
    for state in states:
        if state not in reg.terminal_states:
            raise ValueError(f"unknown_terminal_state:{state}")
        rank = order.get(state, len(reg.precedence))
        if rank < best_rank:
            best_rank = rank
            best = state
    if best is None:
        raise ValueError("empty_state_list")
    return best


def resolve_aggregate_from_reason_codes(codes: list[str], registry: ReasonCodeRegistry | None = None) -> str:
    reg = registry or load_registry()
    states: list[str] = []
    for code in codes:
        result = validate_reason_code(code, registry=reg)
        if not result.ok or result.record is None:
            raise ValueError(result.reason)
        states.append(result.record.state)
    return resolve_aggregate_state(states, registry=reg)


__all__ = ["resolve_aggregate_from_reason_codes", "resolve_aggregate_state"]
