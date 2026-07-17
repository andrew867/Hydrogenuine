"""CNT continuity boundary tests."""

from __future__ import annotations

import pytest

from hg_core.lifecycle.errors import LifecycleValidationError
from hg_runtime.continuity_boundary.evaluation import (
    FIXTURE_CLOCK,
    evaluate_continuity_claim,
    evaluate_continuity_risk,
    refuse_identity_continuity,
    refuse_stale_authority_inheritance,
)
from hg_runtime.continuity_boundary.events import planned_cnt_event_refs
from hg_runtime.continuity_boundary.types import ContinuityClaim, ContinuityRisk, claim_from_fixture, risk_from_fixture


def test_continuity_claim_positive() -> None:
    claim = claim_from_fixture({"claim_id": "cnt-1", "continuity_type": "successor"})
    result = evaluate_continuity_claim(claim, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["memory_inheritance_is_not_identity"] is True
    assert result["permission_granted"] is False


def test_identity_continuity_type_refused() -> None:
    claim = claim_from_fixture({"claim_id": "cnt-same", "continuity_type": "same_process"})
    result = evaluate_continuity_claim(claim, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "cnt.refused.identity_continuity"


def test_identity_continuity_claim_refused() -> None:
    with pytest.raises(LifecycleValidationError):
        refuse_identity_continuity(claim_same_agent=True)


def test_stale_authority_inheritance_refused() -> None:
    claim = claim_from_fixture({"claim_id": "cnt-stale"})
    result = evaluate_continuity_claim(
        claim,
        observed_at=FIXTURE_CLOCK,
        requested_inheritance=("stale_approval:abc",),
    )
    assert result["status"] == "refused"
    assert result["reason_code"] == "cnt.refused.stale_authority_inheritance"


def test_stale_authority_inheritance_raises() -> None:
    with pytest.raises(LifecycleValidationError):
        refuse_stale_authority_inheritance(inherited_refs=("gpp_permit:old",))


def test_expired_continuity_claim_refused() -> None:
    claim = claim_from_fixture(
        {
            "claim_id": "cnt-exp",
            "expiry": "2026-06-12T21:00:00.000000Z",
        }
    )
    result = evaluate_continuity_claim(claim, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "cnt.refused.expired_continuity_claim"


def test_stale_continuity_claim_refused() -> None:
    claim = claim_from_fixture(
        {
            "claim_id": "cnt-stale-time",
            "created_at": "2026-06-12T23:00:00.000000Z",
        }
    )
    result = evaluate_continuity_claim(claim, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "cnt.refused.stale_continuity_claim"


def test_continuity_risk_recorded() -> None:
    risk = risk_from_fixture({"risk_id": "risk-1"})
    result = evaluate_continuity_risk(risk)
    assert result["status"] == "recorded"
    assert result["containment_only"] is True


def test_record_hash_stable() -> None:
    a = claim_from_fixture({"claim_id": "stable"})
    b = claim_from_fixture({"claim_id": "stable"})
    assert a.record_hash == b.record_hash


def test_cnt_event_refs_no_authority_fields() -> None:
    refs = planned_cnt_event_refs()
    assert len(refs) >= 7
    assert all(not e.get("authority_fields") for e in refs)


def test_schema_rejects_secret_claim_ref() -> None:
    with pytest.raises(LifecycleValidationError):
        ContinuityClaim(
            claim_id="bad",
            prior_agent_ref="password=secret",
            current_agent_ref="agent:current",
            continuity_type="successor",
            inherited_refs=(),
            forbidden_inheritance=("authority",),
            created_at=FIXTURE_CLOCK,
            expiry="2026-06-13T22:00:00.000000Z",
        )


def test_risk_severity_bounds() -> None:
    with pytest.raises(LifecycleValidationError):
        ContinuityRisk(
            risk_id="bad",
            claim_ref="cnt:claim",
            risk_type="ghost_identity",
            severity=11,
        )
