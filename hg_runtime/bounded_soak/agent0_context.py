"""Agent Zero bounded soak context."""

from __future__ import annotations

from typing import Any

from hg_runtime.bounded_soak.schema import _frozen


def agent0_soak_context() -> dict[str, Any]:
    return {
        "schema": "agent0-soak-context",
        "identity": "Agent Zero (Zero, A#0, agent0)",
        "soak_bounded": True,
        "may_request_stop": True,
        "may_not_resist_stop": True,
        "hidden_loops_forbidden": True,
        **_frozen(),
    }


__all__ = ["agent0_soak_context"]
