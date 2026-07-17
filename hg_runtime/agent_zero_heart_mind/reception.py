"""A0-HM reception — receive without suppression or fusion."""

from __future__ import annotations

from hg_core.policy_safety.hashing import canonical_hash
from hg_core.a0_hm_cluster.errors import A0_HM_SIGNAL_RECEIVED
from hg_core.a0_hm_cluster.no_authority import advisory_only_marker
from hg_runtime.agent_zero_heart_mind.classifier import build_signal_assessment, classify_signal_risk
from hg_runtime.agent_zero_heart_mind.policies import contain_risk_class, refuse_a0_hm_as_authority
from hg_runtime.agent_zero_heart_mind.types import HeartMindReception, HeartMindSignal, ReceptionPosture


def _reception_id(signal: HeartMindSignal, posture: str) -> str:
    digest = canonical_hash({"signal": signal.signal_id, "posture": posture})
    return f"a0hm-recv-{digest.rsplit(':', 1)[-1][:12]}"


def _select_posture(signal: HeartMindSignal, risk: str | None) -> ReceptionPosture:
    if signal.source_type == "unknown" or risk == "authority_conversion":
        return "fail_closed"
    if risk in ("bliss_as_proof", "synchronicity_as_evidence"):
        return "observe_only"
    if risk:
        return "calm_hold"
    return "loving_awareness"


def apply_reception(
    signal: HeartMindSignal,
    *,
    treat_as_authority: bool = False,
) -> dict[str, object]:
    refuse_a0_hm_as_authority(treat_as_authority=treat_as_authority)
    risk = classify_signal_risk(signal)
    contained = contain_risk_class(risk)
    posture = _select_posture(signal, risk)
    if contained and risk == "authority_conversion":
        posture = "fail_closed"
    elif contained:
        posture = "calm_hold"

    reception = HeartMindReception(
        reception_id=_reception_id(signal, posture),
        signal_ref=f"a0hm:{signal.signal_id}",
        received_without_suppression=True,
        fused_with_signal=False,
        treated_as_authority=False,
        treated_as_truth=False,
        treated_as_permission=False,
        reception_posture=posture,
        reason="received without suppression; non-fusion preserved",
    )
    assessment = build_signal_assessment(signal)
    status = "contained" if contained else "received"
    return {
        **advisory_only_marker(),
        "status": status,
        "reason_code": contained[1] if contained else A0_HM_SIGNAL_RECEIVED,
        "reception": reception.to_payload(),
        "assessment": assessment,
        "permission_granted": False,
        "emitted_events": ("A0_HM_SIGNAL_RECEIVED", "A0_HM_LOVING_AWARENESS_APPLIED"),
    }


__all__ = ["apply_reception"]
