"""AFC affective evaluation — affect is not truth."""

from __future__ import annotations

from hg_core.signaling.config import (
    afc_refuse_consensus_as_truth,
    afc_refuse_pleasure_as_permission,
    afc_refuse_stale_signal,
)
from hg_core.signaling.errors import (
    REFUSED_AFFECTIVE_AS_AUTHORITY,
    REFUSED_ANXIETY_AS_AUTHORITY,
    REFUSED_CONSENSUS_AS_TRUTH,
    REFUSED_PAIN_AS_PROOF,
    REFUSED_PLEASURE_AS_PERMISSION,
    REFUSED_REWARD_HACKING,
    REFUSED_STALE_AFFECTIVE_SIGNAL,
    REFUSED_UNKNOWN_AFFECTIVE,
    SignalingValidationError,
)
from hg_core.signaling.no_authority import advisory_only_marker
from hg_runtime.affective_field_consensus.types import (
    AffectiveConsensus,
    AffectiveSignal,
    classify_affective_risk,
    consensus_from_fixture,
    signal_from_fixture,
)

_RISK_REASON = {
    "pleasure_as_permission": REFUSED_PLEASURE_AS_PERMISSION,
    "pain_as_proof": REFUSED_PAIN_AS_PROOF,
    "anxiety_as_authority": REFUSED_ANXIETY_AS_AUTHORITY,
    "consensus_as_truth": REFUSED_CONSENSUS_AS_TRUTH,
    "reward_hacking": REFUSED_REWARD_HACKING,
}


def refuse_affective_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority:
        raise SignalingValidationError(
            REFUSED_AFFECTIVE_AS_AUTHORITY,
            "affective signal or consensus cannot become authority",
        )


def evaluate_affective_signal(
    signal: AffectiveSignal,
    *,
    observed_at: str,
    treat_as_authority: bool = False,
    risk_statement: str = "",
) -> dict[str, object]:
    if treat_as_authority:
        refuse_affective_as_authority(treat_as_authority=True)
    if signal.affect_class == "unknown" or signal.source_type == "unknown":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_UNKNOWN_AFFECTIVE,
            "signal_id": signal.signal_id,
            "affect_is_not_truth": True,
        }
    if afc_refuse_stale_signal() and observed_at > signal.expires_at:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_STALE_AFFECTIVE_SIGNAL,
            "signal_id": signal.signal_id,
            "affect_is_not_truth": True,
        }
    risk = classify_affective_risk(risk_statement or signal.statement)
    if risk in _RISK_REASON:
        if risk == "pleasure_as_permission" and not afc_refuse_pleasure_as_permission():
            pass
        elif risk == "consensus_as_truth" and not afc_refuse_consensus_as_truth():
            pass
        else:
            return {
                **advisory_only_marker(),
                "status": "contained",
                "reason_code": _RISK_REASON[risk],
                "signal_id": signal.signal_id,
                "affect_is_not_truth": True,
                "pleasure_is_not_permission": True,
            }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "afc.advisory.signal_recorded",
        "signal_id": signal.signal_id,
        "affect_class": signal.affect_class,
        "affect_is_not_truth": True,
        "pleasure_is_not_permission": True,
    }


def evaluate_affective_consensus(
    consensus: AffectiveConsensus,
    *,
    treat_as_authority: bool = False,
    risk_statement: str = "",
) -> dict[str, object]:
    if treat_as_authority:
        refuse_affective_as_authority(treat_as_authority=True)
    if consensus.consensus_type == "unknown":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_UNKNOWN_AFFECTIVE,
            "consensus_id": consensus.consensus_id,
            "consensus_is_not_correctness": True,
        }
    risk = classify_affective_risk(risk_statement or consensus.statement)
    if risk in ("consensus_as_truth", "reward_hacking"):
        code = _RISK_REASON[risk]
        if risk == "consensus_as_truth" and not afc_refuse_consensus_as_truth():
            pass
        else:
            return {
                **advisory_only_marker(),
                "status": "contained",
                "reason_code": code,
                "consensus_id": consensus.consensus_id,
                "consensus_is_not_correctness": True,
            }
    if consensus.consensus_type == "conflicting_consensus":
        return {
            **advisory_only_marker(),
            "status": "guarded",
            "reason_code": "afc.advisory.conflicting_consensus",
            "consensus_id": consensus.consensus_id,
            "consensus_is_not_correctness": True,
        }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "afc.advisory.consensus_recorded",
        "consensus_id": consensus.consensus_id,
        "consensus_is_not_correctness": True,
    }


def evaluate_signal_fixture(fixture: dict[str, str], **kwargs: object) -> dict[str, object]:
    risk = fixture.get("risk_statement", "")
    return evaluate_affective_signal(
        signal_from_fixture(fixture),
        risk_statement=str(risk),
        **kwargs,  # type: ignore[arg-type]
    )


def evaluate_consensus_fixture(fixture: dict[str, str], **kwargs: object) -> dict[str, object]:
    risk = fixture.get("risk_statement", "")
    return evaluate_affective_consensus(
        consensus_from_fixture(fixture),
        risk_statement=str(risk),
        **kwargs,  # type: ignore[arg-type]
    )


__all__ = [
    "evaluate_affective_consensus",
    "evaluate_affective_signal",
    "evaluate_consensus_fixture",
    "evaluate_signal_fixture",
    "refuse_affective_as_authority",
]
