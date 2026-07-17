"""A0-HM non-fusion receipts — signal is not self, truth, permission, or authority."""

from __future__ import annotations

from hg_core.policy_safety.hashing import canonical_hash
from hg_core.a0_hm_cluster.errors import A0_HM_NON_FUSION_RECORDED
from hg_core.a0_hm_cluster.no_authority import advisory_only_marker
from hg_runtime.agent_zero_heart_mind.classifier import classify_signal_risk
from hg_runtime.agent_zero_heart_mind.types import (
    HeartMindNonFusionReceipt,
    HeartMindSignal,
    NON_FUSION_ASSERTIONS,
)


def _assertions_for_signal(signal: HeartMindSignal) -> tuple[str, ...]:
    assertions = list(NON_FUSION_ASSERTIONS)
    risk = classify_signal_risk(signal)
    if risk == "love_as_approval" or "love" in signal.signal_summary.lower():
        if "love_not_approval" not in assertions:
            assertions.append("love_not_approval")
    if risk == "bliss_as_proof" or "bliss" in signal.signal_summary.lower():
        pass  # bliss_not_proof already in tuple
    if signal.source_type == "synchronicity":
        pass  # synchronicity_not_evidence in tuple
    if "desire" in signal.signal_summary.lower():
        pass
    if "fear" in signal.signal_summary.lower():
        pass
    if signal.source_type in ("reentry", "reproduction"):
        pass  # continuity_not_identity in tuple
    return tuple(assertions)


def emit_non_fusion_receipt(
    signal: HeartMindSignal,
    *,
    reception_ref: str,
    route_decision_ref: str,
    emitted_events: tuple[str, ...],
) -> dict[str, object]:
    assertions = _assertions_for_signal(signal)
    receipt = HeartMindNonFusionReceipt(
        receipt_id=f"a0hm-receipt-{canonical_hash({'s': signal.signal_id}).rsplit(':', 1)[-1][:12]}",
        signal_ref=f"a0hm:{signal.signal_id}",
        reception_ref=reception_ref,
        route_decision_ref=route_decision_ref,
        non_fusion_assertions=assertions,
        emitted_events=emitted_events + ("A0_HM_NON_FUSION_RECORDED",),
    )
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": A0_HM_NON_FUSION_RECORDED,
        "non_fusion_receipt": receipt.to_payload(),
        "permission_granted": False,
    }


__all__ = ["emit_non_fusion_receipt"]
