"""Pre-EXCITON boundary receipts."""

from __future__ import annotations

import uuid
from typing import Any

from hg_runtime.pre_exciton_boundaries.mission import evaluate_mission_drift
from hg_runtime.pre_exciton_boundaries.resource import evaluate_resource_pressure
from hg_runtime.pre_exciton_boundaries.schema import BoundaryDecision
from hg_runtime.pre_exciton_boundaries.silence import evaluate_silence


def evaluate_all(*, text: str = "", low_battery: bool = False, high_cpu: bool = False) -> dict[str, Any]:
    decisions = [
        evaluate_silence(text),
        evaluate_mission_drift(text),
        evaluate_resource_pressure(low_battery=low_battery, high_cpu=high_cpu, text=text),
    ]
    blocked = [d for d in decisions if d.verdict.value == "BLOCK"]
    verdict = blocked[0].reason if blocked else "GREEN_SILENCE_MISSION_RESOURCE_BOUNDARY_READY"
    return {
        "schema": "pre-exciton-boundaries-receipt",
        "receipt_id": f"peb-{uuid.uuid4().hex[:12]}",
        "verdict": verdict,
        "decisions": [d.to_payload() for d in decisions],
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }
