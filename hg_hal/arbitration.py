"""HAL Phase 1 pure arbitration — deterministic, no I/O, no permits."""

from __future__ import annotations

import os
from typing import Sequence

from hg_core.governance.capability_registry import lookup_capability
from hg_hal.types import ArbitrationRequest, ArbitrationResult

# Restrict-only scrutiny: high AEP severity blocks risky effect classes (cannot loosen).
_HIGH_SCRUTINY_EFFECTS = frozenset({"external_write"})


def hal_enabled() -> bool:
    return os.environ.get("HG_HAL_ENABLED", "1").strip().lower() not in ("0", "false", "no")


def arbitrate(request: ArbitrationRequest) -> ArbitrationResult:
    """
    Pure Phase 1 arbitration.

    Rules (deterministic):
    - No candidates → NO_OP
    - Candidates sorted by (-priority, candidate_id)
    - external_write blocked when AEP max_severity >= 7 (restrict-only scrutiny)
    - Unknown/disallowed capability → REJECT
    - First eligible → ACCEPT; others → DEFER
    - No eligible → REJECT
    """
    trace_refs = (
        f"hal:request:{request.request_id}",
        f"hal:proposal:{request.proposal_ref}",
        *[f"hal:ctx:{ref}" for ref in request.context_refs],
        *[f"hal:aep:{ref}" for ref in request.aep_modulation_refs],
    )
    if request.soar_run_ref:
        trace_refs = trace_refs + (f"soar:run:{request.soar_run_ref}",)

    soar_block = _blocked_by_soar_binding(request)
    if soar_block is not None:
        routing, reason_code = soar_block
        return ArbitrationResult(
            request_id=request.request_id,
            routing=routing,
            selected_candidate_ref=None,
            reason_code=reason_code,
            trace_refs=trace_refs,
        )

    if not request.candidates:
        return ArbitrationResult(
            request_id=request.request_id,
            routing="NO_OP",
            selected_candidate_ref=None,
            reason_code="queue_empty",
            trace_refs=trace_refs,
        )

    ordered = sorted(
        request.candidates,
        key=lambda candidate: (-candidate.priority, candidate.candidate_id),
    )
    deferred: list[str] = []
    selected = None
    reject_reason = "no_eligible_candidate"

    for candidate in ordered:
        capability = lookup_capability(candidate.capability_id)
        if capability is None or not capability.bind_allowed:
            reject_reason = "capability_denied"
            deferred.append(candidate.action_ref)
            continue
        if capability.effect_class != candidate.effect_class:
            reject_reason = "effect_class_mismatch"
            deferred.append(candidate.action_ref)
            continue
        if _blocked_by_aep_scrutiny(request, candidate.effect_class):
            reject_reason = "aep_scrutiny_blocked"
            deferred.append(candidate.action_ref)
            continue
        if selected is None:
            selected = candidate
        else:
            deferred.append(candidate.action_ref)

    if selected is None:
        return ArbitrationResult(
            request_id=request.request_id,
            routing="REJECT",
            selected_candidate_ref=None,
            reason_code=reject_reason,
            trace_refs=trace_refs,
            deferred_candidate_refs=tuple(deferred),
        )

    if deferred:
        return ArbitrationResult(
            request_id=request.request_id,
            routing="ACCEPT",
            selected_candidate_ref=selected.action_ref,
            reason_code="selected_highest_priority",
            trace_refs=trace_refs + (f"hal:candidate:{selected.candidate_id}",),
            deferred_candidate_refs=tuple(deferred),
        )

    return ArbitrationResult(
        request_id=request.request_id,
        routing="ACCEPT",
        selected_candidate_ref=selected.action_ref,
        reason_code="sole_candidate",
        trace_refs=trace_refs + (f"hal:candidate:{selected.candidate_id}",),
    )


def _blocked_by_soar_binding(
    request: ArbitrationRequest,
) -> tuple[str, str] | None:
    """SOAR binding is restrict-only input to HAL — cannot loosen SOAR outcome."""
    binding = request.soar_binding
    if not binding:
        return None
    if binding == "REJECT":
        return ("REJECT", "soar_binding_reject")
    if binding == "NO_OP":
        return ("NO_OP", "soar_binding_no_op")
    if binding == "DEFER":
        return ("DEFER", "soar_binding_defer")
    return None


def _blocked_by_aep_scrutiny(request: ArbitrationRequest, effect_class: str) -> bool:
    """AEP restrict-only scrutiny — can only block, never grant."""
    if effect_class not in _HIGH_SCRUTINY_EFFECTS:
        return False
    threshold = 7 + max(0, request.scrutiny_depth_delta)
    return request.aep_max_severity >= threshold


def decision_ref_for_result(result: ArbitrationResult) -> str:
    """Map HAL routing to GPP decision fixture refs (HAL does not mint permits)."""
    if result.routing == "ACCEPT":
        return "dec_hal_accept"
    if result.routing in ("REJECT", "DEFER"):
        return "dec_hal_reject"
    return "dec_hal_no_op"


__all__ = [
    "arbitrate",
    "decision_ref_for_result",
    "hal_enabled",
]
