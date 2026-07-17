"""CNT continuity boundary — continuity is not immortality."""

from hg_runtime.continuity_boundary.evaluation import (
    FIXTURE_CLOCK,
    evaluate_continuity_claim,
    evaluate_continuity_risk,
    refuse_identity_continuity,
    refuse_stale_authority_inheritance,
)
from hg_runtime.continuity_boundary.events import planned_cnt_event_refs
from hg_runtime.continuity_boundary.types import (
    ContinuityClaim,
    ContinuityRisk,
    claim_from_fixture,
    risk_from_fixture,
)

__all__ = [
    "FIXTURE_CLOCK",
    "ContinuityClaim",
    "ContinuityRisk",
    "claim_from_fixture",
    "evaluate_continuity_claim",
    "evaluate_continuity_risk",
    "planned_cnt_event_refs",
    "refuse_identity_continuity",
    "refuse_stale_authority_inheritance",
    "risk_from_fixture",
]
