"""EXCITON cluster validation errors — surface polish is not safety."""

from __future__ import annotations

REFUSED_EXCITON_AS_AUTHORITY = "exciton.refused.surface_as_authority"
REFUSED_STALE_APPROVAL = "exciton.refused.stale_approval"
REFUSED_POLISH_IMPLIES_SAFETY = "exciton.refused.polish_implies_safety"
REFUSED_EMBODIMENT_IMPLIES_CONSENT = "exciton.refused.embodiment_implies_consent"
REFUSED_HARDWARE_REACH_AS_ACTUATION = "exciton.refused.hardware_reach_as_actuation"
REFUSED_OEA_CATALOG_BYPASS = "exciton.refused.oea_catalog_bypass"
REFUSED_STALE_ACTION_REQUEST = "exciton.refused.stale_action_request"
REFUSED_SECRET_IN_SURFACE = "exciton.refused.secret_in_surface"
REFUSED_NATIVE_UI_OFF_BACKBURNER = "exciton.refused.native_ui_off_backburner"
REFUSED_ACTION_WITHOUT_TARGET_HASH = "exciton.refused.action_without_target_hash"
EXCITON_SURFACE_DESCRIPTOR_RECORDED = "exciton.advisory.surface_descriptor_recorded"
EXCITON_ACTION_REQUEST_RECORDED = "exciton.advisory.action_request_recorded"
EXCITON_POLISH_ASSESSMENT_CREATED = "exciton.advisory.polish_assessment_created"
EXCITON_SURFACE_POLICY_APPLIED = "exciton.advisory.surface_policy_applied"
EXCITON_ACTION_DECISION_RECORDED = "exciton.advisory.action_decision_recorded"
EXCITON_FAKE_QUEUE_ENQUEUED = "exciton.advisory.fake_queue_enqueued"
EXCITON_AUTHORITY_CHAIN_PROPOSAL_DISPATCHED = "exciton.advisory.authority_chain_proposal_dispatched"
EXCITON_POLISH_RISK_CONTAINED = "exciton.contained.polish_risk"
EXCITON_PLT_SURFACE_RECORDED = "exciton.advisory.plt_surface_recorded"


class ExcitonValidationError(ValueError):
    """Raised when operator surface records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "EXCITON_ACTION_DECISION_RECORDED",
    "EXCITON_ACTION_REQUEST_RECORDED",
    "EXCITON_AUTHORITY_CHAIN_PROPOSAL_DISPATCHED",
    "EXCITON_FAKE_QUEUE_ENQUEUED",
    "EXCITON_PLT_SURFACE_RECORDED",
    "EXCITON_POLISH_ASSESSMENT_CREATED",
    "EXCITON_POLISH_RISK_CONTAINED",
    "EXCITON_SURFACE_DESCRIPTOR_RECORDED",
    "EXCITON_SURFACE_POLICY_APPLIED",
    "ExcitonValidationError",
    "REFUSED_ACTION_WITHOUT_TARGET_HASH",
    "REFUSED_EMBODIMENT_IMPLIES_CONSENT",
    "REFUSED_EXCITON_AS_AUTHORITY",
    "REFUSED_HARDWARE_REACH_AS_ACTUATION",
    "REFUSED_NATIVE_UI_OFF_BACKBURNER",
    "REFUSED_OEA_CATALOG_BYPASS",
    "REFUSED_POLISH_IMPLIES_SAFETY",
    "REFUSED_SECRET_IN_SURFACE",
    "REFUSED_STALE_ACTION_REQUEST",
    "REFUSED_STALE_APPROVAL",
]
