"""EOG cluster validation errors — embodiment is not consent."""

from __future__ import annotations

REFUSED_EOG_AS_AUTHORITY = "eog.refused.growth_as_authority"
REFUSED_STALE_APPROVAL = "eog.refused.stale_approval"
REFUSED_EMBODIMENT_IMPLIES_CONSENT = "eog.refused.embodiment_implies_consent"
REFUSED_HARDWARE_REACH_AS_ACTUATION = "eog.refused.hardware_reach_as_actuation"
REFUSED_OEA_CATALOG_BYPASS = "eog.refused.oea_catalog_bypass"
REFUSED_HARDWARE_OFF_BACKBURNER = "eog.refused.hardware_off_backburner"
REFUSED_STALE_GROWTH_REQUEST = "eog.refused.stale_growth_request"
REFUSED_SECRET_IN_GROWTH = "eog.refused.secret_in_growth"
EOG_BODY_INTEGRATION_RECORDED = "eog.advisory.body_integration_recorded"
EOG_GROWTH_REQUEST_RECORDED = "eog.advisory.growth_request_recorded"
EOG_GROWTH_ASSESSMENT_CREATED = "eog.advisory.growth_assessment_created"
EOG_GROWTH_DECISION_RECORDED = "eog.advisory.growth_decision_recorded"
EOG_FAKE_QUEUE_ENQUEUED = "eog.advisory.fake_queue_enqueued"
EOG_AUTHORITY_CHAIN_PROPOSAL_DISPATCHED = "eog.advisory.authority_chain_proposal_dispatched"
EOG_GROWTH_RISK_CONTAINED = "eog.contained.growth_risk"
EOG_OEA_CATALOG_RECORDED = "eog.advisory.oea_catalog_recorded"


class EogValidationError(ValueError):
    """Raised when embodiment/OEA growth records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "EOG_AUTHORITY_CHAIN_PROPOSAL_DISPATCHED",
    "EOG_BODY_INTEGRATION_RECORDED",
    "EOG_FAKE_QUEUE_ENQUEUED",
    "EOG_GROWTH_ASSESSMENT_CREATED",
    "EOG_GROWTH_DECISION_RECORDED",
    "EOG_GROWTH_REQUEST_RECORDED",
    "EOG_GROWTH_RISK_CONTAINED",
    "EOG_OEA_CATALOG_RECORDED",
    "EogValidationError",
    "REFUSED_EMBODIMENT_IMPLIES_CONSENT",
    "REFUSED_EOG_AS_AUTHORITY",
    "REFUSED_HARDWARE_OFF_BACKBURNER",
    "REFUSED_HARDWARE_REACH_AS_ACTUATION",
    "REFUSED_OEA_CATALOG_BYPASS",
    "REFUSED_SECRET_IN_GROWTH",
    "REFUSED_STALE_APPROVAL",
    "REFUSED_STALE_GROWTH_REQUEST",
]
