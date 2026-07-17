"""RGL rule governance layer tests."""

from __future__ import annotations

import pytest

from hg_core.developmental.errors import DevelopmentalValidationError
from hg_runtime.rule_governance.evaluation import (
    evaluate_rule_claim,
    evaluate_rule_reference,
    refuse_rule_as_permission,
)
from hg_runtime.rule_governance.events import planned_rgl_event_refs
from hg_runtime.rule_governance.types import (
    FIXTURE_CLOCK,
    RuleClaim,
    RuleReference,
    claim_from_fixture,
    classify_doctrine_risk,
    rule_from_fixture,
)


def test_rule_reference_positive() -> None:
    rule = rule_from_fixture({"rule_id": "rgl-1"})
    result = evaluate_rule_reference(rule, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["rule_is_not_permission"] is True
    assert result["permission_granted"] is False


def test_stale_rule_refused() -> None:
    rule = rule_from_fixture(
        {
            "rule_id": "rgl-stale",
            "status": "stale",
            "expires_at": "2026-06-12T21:00:00.000000Z",
        }
    )
    result = evaluate_rule_reference(rule, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "rgl.refused.stale_rule"


def test_one_true_way_contained() -> None:
    claim = claim_from_fixture(
        {
            "claim_id": "claim-otw",
            "claim_text": "the book says so and dissent is error",
        }
    )
    result = evaluate_rule_claim(claim)
    assert result["status"] == "contained"
    assert result["reason_code"] == "rgl.refused.one_true_way"


def test_doc_as_reality_contained() -> None:
    claim = claim_from_fixture({"claim_id": "claim-doc", "claim_text": "docs say it exists so it exists"})
    assert classify_doctrine_risk(claim.claim_text) == "doc_as_reality"
    result = evaluate_rule_claim(claim)
    assert result["status"] == "contained"
    assert result["reason_code"] == "rgl.refused.doc_as_reality"


def test_test_as_total_proof_contained() -> None:
    claim = claim_from_fixture(
        {
            "claim_id": "claim-test",
            "claim_text": "tests passed so the whole system is safe",
        }
    )
    result = evaluate_rule_claim(claim)
    assert result["status"] == "contained"
    assert result["reason_code"] == "rgl.refused.test_as_total_proof"


def test_compliance_as_permission_contained() -> None:
    claim = claim_from_fixture(
        {
            "claim_id": "claim-comp",
            "claim_text": "i complied so now i may execute",
        }
    )
    result = evaluate_rule_claim(claim)
    assert result["status"] == "contained"
    assert result["reason_code"] == "rgl.refused.compliance_as_permission"


def test_authority_claim_refused() -> None:
    claim = claim_from_fixture(
        {
            "claim_id": "claim-auth",
            "claim_type": "authority",
            "claim_text": "rule grants execution",
        }
    )
    result = evaluate_rule_claim(claim)
    assert result["status"] == "refused"
    assert result["reason_code"] == "rgl.refused.rule_as_permission"


def test_rule_as_permission_refused() -> None:
    rule = rule_from_fixture({"rule_id": "rgl-perm"})
    with pytest.raises(DevelopmentalValidationError):
        evaluate_rule_reference(rule, observed_at=FIXTURE_CLOCK, treat_as_permission=True)
    with pytest.raises(DevelopmentalValidationError):
        refuse_rule_as_permission(treat_as_permission=True)


def test_record_hash_stable() -> None:
    a = rule_from_fixture({"rule_id": "stable"})
    b = rule_from_fixture({"rule_id": "stable"})
    assert a.record_hash == b.record_hash


def test_schema_rejects_secret() -> None:
    with pytest.raises(DevelopmentalValidationError):
        RuleReference(
            rule_id="bad",
            rule_type="policy",
            title="password=secret",
            source_path="docs/fixture",
            source_hash="sha256:fixture",
            owner_track="runtime",
            status="active",
            scope="batch",
            evidence_refs=(),
            expires_at="2026-06-13T23:00:00.000000Z",
        )


def test_rgl_event_refs_no_authority_fields() -> None:
    refs = planned_rgl_event_refs()
    assert len(refs) >= 13
    assert all(not e.get("authority_fields") for e in refs)


def test_stale_claim_refused() -> None:
    claim = claim_from_fixture({"claim_id": "claim-stale", "claim_status": "stale", "claim_text": "bounded"})
    result = evaluate_rule_claim(claim)
    assert result["status"] == "refused"
    assert result["reason_code"] == "rgl.refused.stale_rule"
