"""HAL → RTC event draft builders (no bus access)."""

from __future__ import annotations

from typing import Any

from hg_hal.types import ArbitrationRequest, ArbitrationResult


def arbitration_requested_draft(
    request: ArbitrationRequest,
    *,
    causal_parents: list[str],
) -> dict[str, Any]:
    return {
        "type": "HAL_ARBITRATION_REQUESTED",
        "payload": request.to_payload(),
        "causal_parents": list(causal_parents),
        "severity": None,
    }


def arbitration_recorded_draft(
    result: ArbitrationResult,
    *,
    causal_parents: list[str],
) -> dict[str, Any]:
    return {
        "type": "HAL_ARBITRATION_RECORDED",
        "payload": {
            **result.to_payload(),
            "enforcement": "hal_phase1_arbitration_only",
        },
        "causal_parents": list(causal_parents),
        "severity": None,
    }


__all__ = ["arbitration_recorded_draft", "arbitration_requested_draft"]
