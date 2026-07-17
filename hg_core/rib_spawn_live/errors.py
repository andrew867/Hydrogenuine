"""RIB-SPAWN-LIVE cluster validation errors — spawn plans are not authority."""

from __future__ import annotations

REFUSED_SPAWN_AS_AUTHORITY = "rib_spawn.refused.spawn_as_authority"
REFUSED_MISSING_OPERATOR_APPROVAL = "rib_spawn.refused.missing_operator_approval"
REFUSED_STALE_APPROVAL = "rib_spawn.refused.stale_approval"
REFUSED_MISSING_IAM = "rib_spawn.refused.missing_iam"
REFUSED_MISSING_TIM_FRESHNESS = "rib_spawn.refused.missing_tim_freshness"
REFUSED_STALE_TIM = "rib_spawn.refused.stale_tim"
REFUSED_MISSING_GPP_PERMIT = "rib_spawn.refused.missing_gpp_permit"
REFUSED_MISSING_UEAK_ADMISSION = "rib_spawn.refused.missing_ueak_admission"
REFUSED_AUTHORITY_CONVERSION = "rib_spawn.refused.authority_conversion"
REFUSED_SECRET_LEAK = "rib_spawn.refused.secret_leak"
REFUSED_OUT_OF_SCOPE_LIVE_ACTION = "rib_spawn.refused.out_of_scope_live_action"
REFUSED_LIVE_SPAWN = "rib_spawn.refused.live_spawn"
REFUSED_INHERITED_AUTHORITY = "rib_spawn.refused.inherited_authority"
REFUSED_CHILD_IDENTITY_COLLISION = "rib_spawn.refused.child_identity_collision"
REFUSED_ROLLBACK_MISSING = "rib_spawn.refused.rollback_missing"

RIB_SPAWN_RECORDED = "rib_spawn.advisory.recorded"
RIB_SPAWN_PLAN_BOUND = "rib_spawn.advisory.spawn_plan_bound"
RIB_SPAWN_FAKE_SINK = "rib_spawn.advisory.spawn_fake_sink"
RIB_SPAWN_ROLLBACK_RECORDED = "rib_spawn.advisory.rollback_recorded"
RIB_SPAWN_FAILED_CLOSED = "rib_spawn.refused.failed_closed"
RIB_SPAWN_AUTHORITY_CONVERSION_CONTAINED = "rib_spawn.contained.authority_conversion"


class RibSpawnValidationError(ValueError):
    """Raised when RIB-SPAWN records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "RIB_SPAWN_AUTHORITY_CONVERSION_CONTAINED",
    "RIB_SPAWN_FAILED_CLOSED",
    "RIB_SPAWN_FAKE_SINK",
    "RIB_SPAWN_PLAN_BOUND",
    "RIB_SPAWN_RECORDED",
    "RIB_SPAWN_ROLLBACK_RECORDED",
    "REFUSED_AUTHORITY_CONVERSION",
    "REFUSED_CHILD_IDENTITY_COLLISION",
    "REFUSED_INHERITED_AUTHORITY",
    "REFUSED_LIVE_SPAWN",
    "REFUSED_MISSING_GPP_PERMIT",
    "REFUSED_MISSING_IAM",
    "REFUSED_MISSING_OPERATOR_APPROVAL",
    "REFUSED_MISSING_TIM_FRESHNESS",
    "REFUSED_MISSING_UEAK_ADMISSION",
    "REFUSED_OUT_OF_SCOPE_LIVE_ACTION",
    "REFUSED_ROLLBACK_MISSING",
    "REFUSED_SECRET_LEAK",
    "REFUSED_SPAWN_AS_AUTHORITY",
    "REFUSED_STALE_APPROVAL",
    "REFUSED_STALE_TIM",
    "RibSpawnValidationError",
]
