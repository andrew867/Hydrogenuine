"""Control cluster validation errors — boundaries are not authority."""

from __future__ import annotations

REFUSED_RSC_AS_AUTHORITY = "rsc.refused.scarcity_as_authority"
REFUSED_STALE_RESOURCE_POSTURE = "rsc.refused.stale_posture"
REFUSED_RESOURCE_BYPASS = "rsc.refused.resource_bypass"
REFUSED_SAFETY_BYPASS = "rsc.refused.safety_bypass"
REFUSED_UNKNOWN_RESOURCE = "rsc.refused.unknown_resource"
ADVISORY_CONTAINMENT_WAIVED_RSC = "rsc.advisory.containment_waived"

REFUSED_PAB_AS_AUTHORITY = "pab.refused.priority_as_authority"
REFUSED_STALE_PRIORITY = "pab.refused.stale_priority"
REFUSED_PRIORITY_AS_PERMISSION = "pab.refused.priority_as_permission"
REFUSED_UNKNOWN_PRIORITY = "pab.refused.unknown_priority"
ADVISORY_CONTAINMENT_WAIVED_PAB = "pab.advisory.containment_waived"

REFUSED_MIS_AS_AUTHORITY = "mis.refused.mission_as_authority"
REFUSED_STALE_DRIFT = "mis.refused.stale_drift"
REFUSED_GOAL_AS_AUTHORITY = "mis.refused.goal_as_authority"
REFUSED_UNKNOWN_DRIFT = "mis.refused.unknown_drift"
ADVISORY_CONTAINMENT_WAIVED_MIS = "mis.advisory.containment_waived"

REFUSED_GCB_AS_AUTHORITY = "gcb.refused.goal_as_authority"
REFUSED_STALE_GOAL = "gcb.refused.stale_goal"
REFUSED_EXPIRED_GOAL = "gcb.refused.expired_goal"
REFUSED_GOAL_AS_PERMISSION = "gcb.refused.goal_as_permission"
REFUSED_UNKNOWN_GOAL = "gcb.refused.unknown_goal"
ADVISORY_CONTAINMENT_WAIVED_GCB = "gcb.advisory.containment_waived"

REFUSED_TRB_AS_AUTHORITY = "trb.refused.trust_as_authority"
REFUSED_STALE_TRUST = "trb.refused.stale_trust"
REFUSED_TRUST_AS_TRUTH = "trb.refused.trust_as_truth"
REFUSED_CALIBRATION_AS_AUTHORITY = "trb.refused.calibration_as_authority"
REFUSED_UNKNOWN_TRUST = "trb.refused.unknown_trust"
ADVISORY_CONTAINMENT_WAIVED_TRB = "trb.advisory.containment_waived"

REFUSED_RPB_AS_AUTHORITY = "rpb.refused.posture_as_authority"
REFUSED_STALE_POSTURE = "rpb.refused.stale_posture"
REFUSED_POSTURE_AS_EXECUTION = "rpb.refused.posture_as_execution"
REFUSED_DRIVE_AS_PERSONHOOD = "rpb.refused.drive_as_personhood"
REFUSED_UNKNOWN_POSTURE = "rpb.refused.unknown_posture"
ADVISORY_CONTAINMENT_WAIVED_RPB = "rpb.advisory.containment_waived"


class ControlValidationError(ValueError):
    """Raised when control records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "ADVISORY_CONTAINMENT_WAIVED_GCB",
    "ADVISORY_CONTAINMENT_WAIVED_MIS",
    "ADVISORY_CONTAINMENT_WAIVED_PAB",
    "ADVISORY_CONTAINMENT_WAIVED_RPB",
    "ADVISORY_CONTAINMENT_WAIVED_RSC",
    "ADVISORY_CONTAINMENT_WAIVED_TRB",
    "ControlValidationError",
    "REFUSED_CALIBRATION_AS_AUTHORITY",
    "REFUSED_DRIVE_AS_PERSONHOOD",
    "REFUSED_EXPIRED_GOAL",
    "REFUSED_GCB_AS_AUTHORITY",
    "REFUSED_GOAL_AS_AUTHORITY",
    "REFUSED_GOAL_AS_PERMISSION",
    "REFUSED_MIS_AS_AUTHORITY",
    "REFUSED_PAB_AS_AUTHORITY",
    "REFUSED_POSTURE_AS_EXECUTION",
    "REFUSED_PRIORITY_AS_PERMISSION",
    "REFUSED_RESOURCE_BYPASS",
    "REFUSED_RPB_AS_AUTHORITY",
    "REFUSED_RSC_AS_AUTHORITY",
    "REFUSED_SAFETY_BYPASS",
    "REFUSED_STALE_DRIFT",
    "REFUSED_STALE_GOAL",
    "REFUSED_STALE_POSTURE",
    "REFUSED_STALE_PRIORITY",
    "REFUSED_STALE_RESOURCE_POSTURE",
    "REFUSED_STALE_TRUST",
    "REFUSED_TRB_AS_AUTHORITY",
    "REFUSED_TRUST_AS_TRUTH",
    "REFUSED_UNKNOWN_DRIFT",
    "REFUSED_UNKNOWN_GOAL",
    "REFUSED_UNKNOWN_POSTURE",
    "REFUSED_UNKNOWN_PRIORITY",
    "REFUSED_UNKNOWN_RESOURCE",
    "REFUSED_UNKNOWN_TRUST",
]
