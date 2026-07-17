"""Explicit UI state model for EXCITON views."""

from __future__ import annotations

from enum import Enum
from typing import Any


class UIViewState(str, Enum):
    EMPTY = "EMPTY"
    LOADING = "LOADING"
    STALE = "STALE"
    ERROR = "ERROR"
    DEGRADED = "DEGRADED"
    GREEN = "GREEN"
    RED = "RED"


def describe_ui_state(state: UIViewState, *, detail: str = "") -> dict[str, Any]:
    meta = {
        UIViewState.EMPTY: ("No items yet.", "Nothing to review.", "safe to wait"),
        UIViewState.LOADING: ("Loading…", "Fetching latest state.", "wait"),
        UIViewState.STALE: ("Data stale", "Backend may be unreachable.", "refresh before approving"),
        UIViewState.ERROR: ("Error", detail or "Something failed.", "check Dev Details"),
        UIViewState.DEGRADED: ("Degraded", detail or "Partial data.", "proceed with caution"),
        UIViewState.GREEN: ("Healthy", "Data current.", "review as needed"),
        UIViewState.RED: ("Blocked", detail or "Unsafe state.", "resolve blockers first"),
    }
    human, meaning, next_action = meta[state]
    return {
        "state": state.value,
        "human_explanation": human,
        "what_it_means": meaning,
        "safe_next_action": next_action,
        "approvals_disabled": state in (UIViewState.STALE, UIViewState.ERROR, UIViewState.RED, UIViewState.LOADING),
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }


__all__ = ["UIViewState", "describe_ui_state"]
