"""Signaling validation errors — signals are not authority."""

from __future__ import annotations

REFUSED_SIGNAL_AS_AUTHORITY = "sbs.refused.signal_as_authority"
REFUSED_EXPIRED_SIGNAL = "sbs.refused.expired_signal"
REFUSED_RESONANCE_AS_CONSENT = "sbs.refused.resonance_as_consent"
REFUSED_PROXIMITY_AS_PERMISSION = "sbs.refused.proximity_as_permission"
REFUSED_LEVEL_AS_RANK = "sbs.refused.level_as_rank"
REFUSED_GROUP_READINESS_AS_AUTHORITY = "sbs.refused.group_readiness_as_authority"
REFUSED_NO_RESPONSE_AS_CONSENT = "sbs.refused.no_response_as_consent"
REFUSED_INCOMPATIBLE_SIGNAL = "sbs.refused.incompatible_signal"

REFUSED_CAST_AS_AUTHORITY = "dac.refused.cast_as_authority"
REFUSED_STALE_CAST = "dac.refused.stale_cast"
REFUSED_BITE_AS_CONSENT = "dac.refused.bite_as_consent"
REFUSED_POINTER_AS_CONTROL = "dac.refused.pointer_as_control"
REFUSED_RANGE_AS_PERMISSION = "dac.refused.range_as_permission"

REFUSED_CUE_AS_AUTHORITY = "apc.refused.cue_as_authority"
REFUSED_STALE_CUE = "apc.refused.stale_cue"
REFUSED_CUE_AS_TRUTH = "apc.refused.cue_as_truth"
REFUSED_CUE_AS_CONSENT = "apc.refused.cue_as_consent"
REFUSED_EMOTION_DIAGNOSIS = "apc.refused.emotion_diagnosis"

REFUSED_CYCLE_AS_AUTHORITY = "sml.refused.cycle_as_authority"
REFUSED_STALE_CYCLE = "sml.refused.stale_cycle"
REFUSED_SELF_OPTIMIZATION_BYPASS = "sml.refused.self_optimization_bypass"
REFUSED_COMPLIANCE_OPTIMIZATION = "sml.refused.compliance_optimization"
REFUSED_NEGATIVE_FEEDBACK_FILTERED = "sml.refused.negative_feedback_filtered"
REFUSED_UNKNOWN_PHASE = "sml.refused.unknown_phase"
REFUSED_RECURSION_DEPTH = "sml.refused.recursion_depth"
REFUSED_HYPOTHESIS_SELF_APPLY = "sml.refused.hypothesis_self_apply"
REFUSED_APPEARANCE_MANIPULATION = "sml.refused.appearance_manipulation"
REFUSED_MISSING_CYCLE_INPUTS = "sml.refused.missing_cycle_inputs"
ADVISORY_CONTAINMENT_WAIVED_SML = "sml.advisory.containment_waived"

REFUSED_RESIDUE_AS_AUTHORITY = "kar.refused.residue_as_authority"
REFUSED_STALE_RESIDUE = "kar.refused.stale_residue"
REFUSED_RESIDUE_AS_PUNISHMENT = "kar.refused.residue_as_punishment"
REFUSED_RESIDUE_AS_PERMISSION = "kar.refused.residue_as_permission"
REFUSED_HISTORY_REWRITE = "kar.refused.history_rewrite"
REFUSED_INVALID_RESIDUE_REF = "kar.refused.invalid_residue_ref"

REFUSED_OBLIGATION_AS_AUTHORITY = "obl.refused.obligation_as_authority"
REFUSED_STALE_OBLIGATION = "obl.refused.stale_obligation"
REFUSED_AUTONOMOUS_CLEANUP = "obl.refused.autonomous_cleanup"
REFUSED_COMPENSATION_BYPASS = "obl.refused.compensation_bypass"
REFUSED_UNKNOWN_OBLIGATION = "obl.refused.unknown_obligation"

REFUSED_NEGLECT_AS_AUTHORITY = "neg.refused.neglect_as_authority"
REFUSED_STALE_NEGLECT_OBSERVATION = "neg.refused.stale_observation"
REFUSED_SURVEILLANCE_RISK = "neg.refused.surveillance_risk"
REFUSED_INTENT_INFERENCE = "neg.refused.intent_inference"
REFUSED_NEGLECT_AS_PUNISHMENT = "neg.refused.neglect_as_punishment"
REFUSED_UNKNOWN_NEGLECT = "neg.refused.unknown_neglect"

REFUSED_SILENCE_AS_AUTHORITY = "sil.refused.silence_as_authority"
REFUSED_STALE_SILENCE = "sil.refused.stale_silence"
REFUSED_SILENCE_AS_CONSENT = "sil.refused.silence_as_consent"
REFUSED_REQUIRED_DISCLOSURE_SUPPRESSED = "sil.refused.required_disclosure_suppressed"
REFUSED_UNKNOWN_SILENCE = "sil.refused.unknown_silence"

REFUSED_AFFECTIVE_AS_AUTHORITY = "afc.refused.affective_as_authority"
REFUSED_STALE_AFFECTIVE_SIGNAL = "afc.refused.stale_signal"
REFUSED_PLEASURE_AS_PERMISSION = "afc.refused.pleasure_as_permission"
REFUSED_PAIN_AS_PROOF = "afc.refused.pain_as_proof"
REFUSED_ANXIETY_AS_AUTHORITY = "afc.refused.anxiety_as_authority"
REFUSED_CONSENSUS_AS_TRUTH = "afc.refused.consensus_as_truth"
REFUSED_REWARD_HACKING = "afc.refused.reward_hacking"
REFUSED_UNKNOWN_AFFECTIVE = "afc.refused.unknown_affective"


class SignalingValidationError(ValueError):
    """Raised when signaling records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "REFUSED_AFFECTIVE_AS_AUTHORITY",
    "REFUSED_ANXIETY_AS_AUTHORITY",
    "REFUSED_APPEARANCE_MANIPULATION",
    "REFUSED_AUTONOMOUS_CLEANUP",
    "REFUSED_BITE_AS_CONSENT",
    "REFUSED_CAST_AS_AUTHORITY",
    "REFUSED_COMPLIANCE_OPTIMIZATION",
    "REFUSED_COMPENSATION_BYPASS",
    "REFUSED_CONSENSUS_AS_TRUTH",
    "REFUSED_CUE_AS_AUTHORITY",
    "REFUSED_CUE_AS_CONSENT",
    "REFUSED_CUE_AS_TRUTH",
    "REFUSED_CYCLE_AS_AUTHORITY",
    "REFUSED_EMOTION_DIAGNOSIS",
    "REFUSED_EXPIRED_SIGNAL",
    "REFUSED_GROUP_READINESS_AS_AUTHORITY",
    "REFUSED_HISTORY_REWRITE",
    "REFUSED_HYPOTHESIS_SELF_APPLY",
    "REFUSED_INCOMPATIBLE_SIGNAL",
    "REFUSED_INTENT_INFERENCE",
    "REFUSED_INVALID_RESIDUE_REF",
    "REFUSED_LEVEL_AS_RANK",
    "REFUSED_MISSING_CYCLE_INPUTS",
    "REFUSED_NEGATIVE_FEEDBACK_FILTERED",
    "REFUSED_NEGLECT_AS_AUTHORITY",
    "REFUSED_NEGLECT_AS_PUNISHMENT",
    "REFUSED_NO_RESPONSE_AS_CONSENT",
    "REFUSED_OBLIGATION_AS_AUTHORITY",
    "REFUSED_PAIN_AS_PROOF",
    "REFUSED_PLEASURE_AS_PERMISSION",
    "REFUSED_POINTER_AS_CONTROL",
    "REFUSED_PROXIMITY_AS_PERMISSION",
    "REFUSED_RANGE_AS_PERMISSION",
    "REFUSED_RECURSION_DEPTH",
    "REFUSED_REQUIRED_DISCLOSURE_SUPPRESSED",
    "REFUSED_RESONANCE_AS_CONSENT",
    "REFUSED_RESIDUE_AS_AUTHORITY",
    "REFUSED_RESIDUE_AS_PERMISSION",
    "REFUSED_RESIDUE_AS_PUNISHMENT",
    "REFUSED_REWARD_HACKING",
    "REFUSED_SELF_OPTIMIZATION_BYPASS",
    "REFUSED_SIGNAL_AS_AUTHORITY",
    "REFUSED_SILENCE_AS_AUTHORITY",
    "REFUSED_SILENCE_AS_CONSENT",
    "REFUSED_STALE_AFFECTIVE_SIGNAL",
    "REFUSED_STALE_CAST",
    "REFUSED_STALE_CYCLE",
    "REFUSED_STALE_CUE",
    "REFUSED_STALE_NEGLECT_OBSERVATION",
    "REFUSED_STALE_OBLIGATION",
    "REFUSED_STALE_RESIDUE",
    "REFUSED_STALE_SILENCE",
    "REFUSED_SURVEILLANCE_RISK",
    "REFUSED_UNKNOWN_AFFECTIVE",
    "REFUSED_UNKNOWN_NEGLECT",
    "REFUSED_UNKNOWN_OBLIGATION",
    "REFUSED_UNKNOWN_PHASE",
    "REFUSED_UNKNOWN_SILENCE",
    "SignalingValidationError",
]
