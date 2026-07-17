"""Runtime context validation errors — context is not permission."""

from __future__ import annotations

REFUSED_GOAL_SEED_AS_AUTHORITY = "bcp.refused.goal_seed_as_authority"
REFUSED_STALE_BOOTSTRAP_PACKET = "bcp.refused.stale_packet"
REFUSED_EXPIRED_BOOTSTRAP_PACKET = "bcp.refused.expired_packet"
REFUSED_PACKET_HASH_MISMATCH = "bcp.refused.world_state_hash_mismatch"

REFUSED_MISSING_AUTHORITY_BADGE = "pres.refused.missing_authority_badge"
REFUSED_MISSING_AI_DISCLOSURE = "pres.refused.missing_ai_disclosure"
REFUSED_OVERTRUST_RISK = "pres.refused.overtrust_risk"
REFUSED_FALSE_INTIMACY = "pres.refused.false_intimacy_risk"

REFUSED_AUTONOMOUS_CRAWL = "res.refused.autonomous_crawl"
REFUSED_RESEARCH_AS_TRUTH = "res.refused.research_as_truth"
REFUSED_UNSUPPORTED_CLAIM = "res.refused.unsupported_claim"
REFUSED_STALE_SOURCE = "res.refused.stale_source"
REFUSED_UNKNOWN_PRESERVED = "res.refused.unknown_preserved"

REFUSED_SIMULATION_AS_PERMISSION = "sim.refused.simulation_as_permission"
REFUSED_PREDICTION_AS_TRUTH = "sim.refused.prediction_as_truth"
REFUSED_STALE_SCENARIO = "sim.refused.stale_scenario"
REFUSED_EXPIRED_SCENARIO = "sim.refused.expired_scenario"
REFUSED_EVENT_HEAD_DRIFT = "sim.refused.event_head_drift"
REFUSED_FORBIDDEN_ACTION_IN_SCENARIO = "sim.refused.forbidden_action_in_scenario"

REFUSED_PUBLICATION_AS_AUTHORITY = "pub.refused.publication_as_authority"
REFUSED_SECRET_IN_ARTIFACT = "pub.refused.secret_in_artifact"
REFUSED_UNSUPPORTED_PUBLIC_CLAIM = "pub.refused.unsupported_public_claim"
REFUSED_DANGEROUS_DETAIL_EXPOSURE = "pub.refused.dangerous_detail_exposure"
REFUSED_STALE_PUBLICATION_REVIEW = "pub.refused.stale_review"
REFUSED_EXPIRED_PUBLICATION_REVIEW = "pub.refused.expired_review"

REFUSED_DEPENDENCY_AS_OPTIMIZATION = "dep_bond.refused.dependency_as_optimization"
REFUSED_FALSE_INTIMACY_SIGNAL = "dep_bond.refused.false_intimacy_signal"
REFUSED_DIAGNOSIS_OVERCLAIM = "dep_bond.refused.diagnosis_overclaim"
REFUSED_STALE_OBSERVATION = "dep_bond.refused.stale_observation"
REFUSED_EXPIRED_OBSERVATION = "dep_bond.refused.expired_observation"

REFUSED_REACH_AS_ACTUATION = "pro.refused.reach_as_actuation"
REFUSED_CONTACT_AS_CONSENT = "pro.refused.contact_as_consent"
REFUSED_SENSOR_CONFIDENCE_AS_TRUTH = "pro.refused.sensor_confidence_as_truth"
REFUSED_STALE_BODY_STATE = "pro.refused.stale_body_state"
REFUSED_EXPIRED_BODY_STATE = "pro.refused.expired_body_state"
REFUSED_HARDWARE_WHILE_BACKBURNER = "pro.refused.hardware_while_backburner"
REFUSED_PRO_NOT_ON_BACKBURNER = "pro.refused.not_on_backburner"


class RuntimeContextValidationError(ValueError):
    """Raised when runtime context records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "REFUSED_AUTONOMOUS_CRAWL",
    "REFUSED_DANGEROUS_DETAIL_EXPOSURE",
    "REFUSED_CONTACT_AS_CONSENT",
    "REFUSED_DEPENDENCY_AS_OPTIMIZATION",
    "REFUSED_DIAGNOSIS_OVERCLAIM",
    "REFUSED_EVENT_HEAD_DRIFT",
    "REFUSED_EXPIRED_BODY_STATE",
    "REFUSED_EXPIRED_BOOTSTRAP_PACKET",
    "REFUSED_EXPIRED_OBSERVATION",
    "REFUSED_EXPIRED_PUBLICATION_REVIEW",
    "REFUSED_EXPIRED_SCENARIO",
    "REFUSED_FALSE_INTIMACY",
    "REFUSED_FALSE_INTIMACY_SIGNAL",
    "REFUSED_FORBIDDEN_ACTION_IN_SCENARIO",
    "REFUSED_GOAL_SEED_AS_AUTHORITY",
    "REFUSED_HARDWARE_WHILE_BACKBURNER",
    "REFUSED_MISSING_AI_DISCLOSURE",
    "REFUSED_MISSING_AUTHORITY_BADGE",
    "REFUSED_OVERTRUST_RISK",
    "REFUSED_PACKET_HASH_MISMATCH",
    "REFUSED_PREDICTION_AS_TRUTH",
    "REFUSED_PRO_NOT_ON_BACKBURNER",
    "REFUSED_PUBLICATION_AS_AUTHORITY",
    "REFUSED_REACH_AS_ACTUATION",
    "REFUSED_RESEARCH_AS_TRUTH",
    "REFUSED_SECRET_IN_ARTIFACT",
    "REFUSED_SENSOR_CONFIDENCE_AS_TRUTH",
    "REFUSED_SIMULATION_AS_PERMISSION",
    "REFUSED_STALE_BODY_STATE",
    "REFUSED_STALE_BOOTSTRAP_PACKET",
    "REFUSED_STALE_OBSERVATION",
    "REFUSED_STALE_PUBLICATION_REVIEW",
    "REFUSED_STALE_SCENARIO",
    "REFUSED_STALE_SOURCE",
    "REFUSED_UNSUPPORTED_CLAIM",
    "REFUSED_UNSUPPORTED_PUBLIC_CLAIM",
    "REFUSED_UNKNOWN_PRESERVED",
    "RuntimeContextValidationError",
]
