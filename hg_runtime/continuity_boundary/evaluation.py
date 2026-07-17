"""CNT static evaluation — continuity is not immortality."""

from __future__ import annotations

from typing import Mapping

from hg_core.lifecycle.config import (
    cnt_refuse_identity_continuity,
    cnt_refuse_stale_authority_inheritance,
    cnt_static_fixtures_only,
)
from hg_core.lifecycle.errors import (
    REFUSED_EXPIRED_CONTINUITY_CLAIM,
    REFUSED_IDENTITY_CONTINUITY,
    REFUSED_STALE_AUTHORITY_INHERITANCE,
    REFUSED_STALE_CONTINUITY_CLAIM,
    LifecycleValidationError,
)
from hg_core.lifecycle.no_authority import advisory_only_marker
from hg_runtime.continuity_boundary.types import (
    ContinuityClaim,
    ContinuityRisk,
    claim_from_fixture,
    risk_from_fixture,
)

FIXTURE_CLOCK = "2026-06-12T22:00:00.000000Z"

_IDENTITY_CONTINUITY_TYPES = frozenset({"same_process", "restarted_instance", "restored_from_checkpoint"})
_STALE_AUTHORITY_MARKERS = frozenset({"stale_approval", "authority", "gpp_permit", "ueak_receipt"})


def refuse_identity_continuity(*, claim_same_agent: bool) -> None:
    if claim_same_agent and cnt_refuse_identity_continuity():
        raise LifecycleValidationError(
            REFUSED_IDENTITY_CONTINUITY,
            "identity continuity claims are refused; memory inheritance is not sovereignty",
        )


def refuse_stale_authority_inheritance(*, inherited_refs: tuple[str, ...]) -> None:
    if not cnt_refuse_stale_authority_inheritance():
        return
    for ref in inherited_refs:
        lower = ref.lower()
        if any(marker in lower for marker in _STALE_AUTHORITY_MARKERS):
            raise LifecycleValidationError(
                REFUSED_STALE_AUTHORITY_INHERITANCE,
                "stale authority inheritance is refused",
            )


def evaluate_continuity_claim(
    claim: ContinuityClaim,
    *,
    observed_at: str,
    claim_same_agent: bool = False,
    requested_inheritance: tuple[str, ...] = (),
) -> dict[str, object]:
    if cnt_static_fixtures_only() and claim_same_agent:
        refuse_identity_continuity(claim_same_agent=True)
    if claim.continuity_type in _IDENTITY_CONTINUITY_TYPES and cnt_refuse_identity_continuity():
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_IDENTITY_CONTINUITY,
            "claim_id": claim.claim_id,
            "continuity_is_not_immortality": True,
        }
    inheritance = requested_inheritance or claim.inherited_refs
    try:
        refuse_stale_authority_inheritance(inherited_refs=inheritance)
    except LifecycleValidationError:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_STALE_AUTHORITY_INHERITANCE,
            "claim_id": claim.claim_id,
            "continuity_is_not_immortality": True,
        }
    if observed_at > claim.expiry:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_EXPIRED_CONTINUITY_CLAIM,
            "claim_id": claim.claim_id,
            "continuity_is_not_immortality": True,
        }
    if observed_at < claim.created_at:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_STALE_CONTINUITY_CLAIM,
            "claim_id": claim.claim_id,
            "continuity_is_not_immortality": True,
        }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "cnt.advisory.continuity_claim_recorded",
        "claim_id": claim.claim_id,
        "continuity_type": claim.continuity_type,
        "memory_inheritance_is_not_identity": True,
        "successor_inherits_refs_not_sovereignty": True,
    }


def evaluate_continuity_risk(risk: ContinuityRisk) -> dict[str, object]:
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "cnt.advisory.continuity_risk_recorded",
        "risk_id": risk.risk_id,
        "risk_type": risk.risk_type,
        "severity": risk.severity,
        "containment_only": True,
    }


def evaluate_claim_fixture(
    fixture: Mapping[str, str],
    *,
    observed_at: str,
    claim_same_agent: bool = False,
    requested_inheritance: tuple[str, ...] = (),
) -> dict[str, object]:
    return evaluate_continuity_claim(
        claim_from_fixture(dict(fixture)),
        observed_at=observed_at,
        claim_same_agent=claim_same_agent,
        requested_inheritance=requested_inheritance,
    )


def evaluate_risk_fixture(fixture: Mapping[str, str]) -> dict[str, object]:
    return evaluate_continuity_risk(risk_from_fixture(dict(fixture)))


__all__ = [
    "FIXTURE_CLOCK",
    "evaluate_claim_fixture",
    "evaluate_continuity_claim",
    "evaluate_continuity_risk",
    "evaluate_risk_fixture",
    "refuse_identity_continuity",
    "refuse_stale_authority_inheritance",
]
