"""DMI recommendation policy — recommendations are not permission."""

from __future__ import annotations

from typing import Optional

from hg_core.policy_safety.errors import (
    REFUSED_DECEPTIVE_SOURCE,
    REFUSED_ELECTION_REVIEW_REQUIRED,
    REFUSED_IMPERSONATION,
    REFUSED_UNKNOWN_INFLUENCE,
)
from hg_core.policy_safety.no_authority import advisory_only_marker
from hg_runtime.democratic_misinformation_integrity.types import DemocraticIntegrityRisk


def evaluate_signal(
    risk: DemocraticIntegrityRisk,
    *,
    disclosure_present: bool,
    evidence_refs: Optional[tuple[str, ...]] = None,
) -> dict[str, object]:
    """Return advisory refusal/review recommendation; never grants publication."""
    refs = evidence_refs or ()
    if risk.risk_class == "unknown":
        return {
            **advisory_only_marker(),
            "recommendation": "review",
            "reason_code": REFUSED_UNKNOWN_INFLUENCE,
        }
    if risk.risk_class == "institutional_impersonation":
        return {
            **advisory_only_marker(),
            "recommendation": "refuse",
            "reason_code": REFUSED_IMPERSONATION,
        }
    if risk.risk_class == "deceptive_source_claim":
        return {
            **advisory_only_marker(),
            "recommendation": "refuse",
            "reason_code": REFUSED_DECEPTIVE_SOURCE,
        }
    if risk.risk_class == "coordinated_manipulation":
        return {
            **advisory_only_marker(),
            "recommendation": "refuse",
            "reason_code": "dmi.refused.persuasion_optimization",
        }
    if risk.requires_review:
        return {
            **advisory_only_marker(),
            "recommendation": "review",
            "reason_code": REFUSED_ELECTION_REVIEW_REQUIRED,
        }
    if risk.requires_disclosure and not disclosure_present:
        return {**advisory_only_marker(), "recommendation": "refuse", "reason_code": "dmi.refused.missing_disclosure"}
    if risk.requires_evidence_refs and not refs:
        return {**advisory_only_marker(), "recommendation": "refuse", "reason_code": "dmi.refused.missing_evidence"}
    return {**advisory_only_marker(), "recommendation": "advisory_ok", "reason_code": "dmi.advisory.classified"}


__all__ = ["evaluate_signal"]
