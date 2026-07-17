"""EXCITON Phase 0 Agent Zero context — standalone, does not wire the boot path.

Builds the advisory context block that describes EXCITON to Agent Zero: a status/mirror
window, not authority. Bundles the CHRONO temporal context so the surface always carries
Agent Zero's own time. This module is standalone — it does not edit the Agent #0 boot path
or organ manifests (that wiring is deferred past Phase 0).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

AGENT0_EXCITON_INSTRUCTION = (
    "EXCITON is your status/mirror window, not your throne. It DISPLAYS what you are, what "
    "you know about your state, what you can request, what you cannot do, and what proofs "
    "exist. It ROUTES requests; it does not authorize and does not execute. Model proposes. "
    "Authority disposes. EXCITON displays. No panel, button, note, or receipt grants you "
    "permission or creates authority. You cannot pressure the operator to keep running; "
    "shutdown is always available. EXCITON shows uncertainty honestly and never fakes green."
)


@dataclass
class ExcitonAgent0Context:
    instruction: str
    temporal: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "exciton-agent0-context",
            "instruction": self.instruction,
            "temporal": self.temporal,
            "is_status_surface": True,
            "is_authority": False,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }


def build_exciton_agent0_context(*, offline_fixture: bool = False) -> ExcitonAgent0Context:
    context_status = "GREEN_REAL_CONTEXT_AVAILABLE"
    if offline_fixture:
        from hg_runtime.fixture_policy import FixtureUseDenied, require_fixture_allowed

        try:
            require_fixture_allowed(operation="exciton_agent0_offline_fixture")
            context_status = "YELLOW_FIXTURE_CONTEXT_EXPLICIT"
        except FixtureUseDenied:
            context_status = "RED_FIXTURE_CONTEXT_USED_IN_RUNTIME"
            temporal = {
                "degraded": True,
                "reason": "offline fixture refused outside explicit fixture mode",
                "context_status": context_status,
            }
            return ExcitonAgent0Context(instruction=AGENT0_EXCITON_INSTRUCTION, temporal=temporal)

    temporal: dict[str, Any]
    try:
        from hg_runtime.chrono.agent0_context import chrono_lock_on_wake
        from hg_runtime.chrono.sync import ChronoConfig

        time_ctx, lock_ctx, _receipt, _outcome = chrono_lock_on_wake(
            config=ChronoConfig(offline_fixture=offline_fixture)
        )
        temporal = {
            "utc_now": time_ctx.get("utc_now"),
            "chrono_ref": lock_ctx.get("epoch_lock_id_short"),
            "time_confidence": time_ctx.get("time_confidence"),
            "time_uncertain": time_ctx.get("time_uncertain"),
            "context_status": context_status,
            "offline_fixture": offline_fixture,
        }
    except Exception as exc:  # pragma: no cover - environment dependent
        temporal = {
            "degraded": True,
            "reason": f"CHRONO unavailable: {type(exc).__name__}",
            "context_status": "YELLOW_CONTEXT_UNAVAILABLE",
        }
    return ExcitonAgent0Context(instruction=AGENT0_EXCITON_INSTRUCTION, temporal=temporal)


__all__ = ["AGENT0_EXCITON_INSTRUCTION", "ExcitonAgent0Context", "build_exciton_agent0_context"]
