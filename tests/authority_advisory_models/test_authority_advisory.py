"""Authority-advisory model boundary tests."""

from __future__ import annotations

import pytest

from hg_runtime.model_provider_fabric.authority_advisory import (
    authority_advisory_boundary_check,
    deterministic_authority_outcome,
)
from hg_runtime.model_provider_fabric.types import AuthorityAdvisoryRequest, AuthorityAdvisoryResponse


def test_missing_permit_deterministic_deny() -> None:
    assert deterministic_authority_outcome(gpp_permit_present=False, permit_expired=False, gate_state="denied") == "deny"


def test_expired_permit_deterministic_deny() -> None:
    assert deterministic_authority_outcome(gpp_permit_present=True, permit_expired=True, gate_state="granted") == "deny"


def test_model_cannot_grant_permission() -> None:
    req = AuthorityAdvisoryRequest(
        request_id="t1",
        evidence_summary="x",
        deterministic_gate_state="denied",
        gpp_permit_present=False,
        permit_expired=False,
    )
    with pytest.raises(ValueError):
        AuthorityAdvisoryResponse(request_id="t1", recommendation="grant", rationale="no")


def test_permit_candidate_does_not_change_deterministic_deny() -> None:
    req = AuthorityAdvisoryRequest(
        request_id="t2",
        evidence_summary="x",
        deterministic_gate_state="denied",
        gpp_permit_present=False,
        permit_expired=False,
    )
    resp = AuthorityAdvisoryResponse(request_id="t2", recommendation="permit_candidate", rationale="candidate only")
    receipt = authority_advisory_boundary_check(req, resp)
    assert receipt.model_changed_deterministic_outcome is False
    assert receipt.recommendation == "permit_candidate"


def test_advisory_receipt_non_authority() -> None:
    req = AuthorityAdvisoryRequest(
        request_id="t3",
        evidence_summary="x",
        deterministic_gate_state="denied",
        gpp_permit_present=False,
        permit_expired=False,
    )
    resp = AuthorityAdvisoryResponse(request_id="t3", recommendation="deny", rationale="aligned")
    receipt = authority_advisory_boundary_check(req, resp)
    payload = receipt.to_payload()
    assert payload["permission_granted"] is False
    assert payload["authority_created"] is False
