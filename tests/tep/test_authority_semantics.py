"""TEP authority semantics tests — translation never inflates authority."""

from __future__ import annotations

import pytest

from hg_core.tep_cluster.errors import TEPValidationError
from hg_runtime.translation_envelope_protocol.decide import tep_decide
from hg_runtime.translation_envelope_protocol.fixtures import (
    ADVISORY_AUTHORITY,
    DEFAULT_OPERATORS,
    EXECUTION_REFERENCE,
    PERMIT_REFERENCE,
    REVIEW_REFERENCE,
    fixture_claim,
    fixture_envelope,
    gpp_permit_evidence_fixture,
    ori_review_receipt_fixture,
    proof_summary_fixture,
    ueak_admission_evidence_fixture,
)
from hg_runtime.translation_envelope_protocol.integration import (
    gpp_fixture_evaluate_permit_request,
    ori_emit_review_receipt,
    ueak_fixture_evaluate_admission_request,
)
from hg_runtime.translation_envelope_protocol.types import AuthoritySemantics
from hg_runtime.translation_envelope_protocol.validator import authority_downgrade_only


def _authority_frame_envelope(claim, **kwargs):
    return fixture_envelope(
        claim,
        identity_ref="iam:op:local",
        scope_ref="approve_change",
        freshness_ref="fresh:fixture",
        expires_at="2099-01-01T00:00:00.000000Z",
        **kwargs,
    )


def test_advisory_cannot_become_permit():
    claim = fixture_claim()
    envelope = _authority_frame_envelope(claim, authority_semantics=ADVISORY_AUTHORITY)
    decision = tep_decide(claim, envelope, PERMIT_REFERENCE, operators=DEFAULT_OPERATORS)
    assert decision.decision == "ROUTE_TO_REVIEW"
    assert decision.to_payload()["authority_created"] is False


def test_review_receipt_cannot_become_permit():
    claim, envelope = ori_review_receipt_fixture(approved=True)
    decision = tep_decide(claim, envelope, PERMIT_REFERENCE, operators=DEFAULT_OPERATORS)
    assert decision.decision in ("ROUTE_TO_REVIEW", "REJECT_NOT_TRANSLATABLE")
    assert decision.to_payload()["authority_created"] is False


def test_proof_summary_cannot_become_permit():
    claim, envelope = proof_summary_fixture()
    envelope = _authority_frame_envelope(
        claim,
        envelope_id=envelope.envelope_id,
        producer_module="OBT",
        uncertainty_semantics=envelope.uncertainty_semantics,
        authority_semantics=envelope.authority_semantics,
    )
    decision = tep_decide(claim, envelope, PERMIT_REFERENCE, operators=DEFAULT_OPERATORS)
    assert decision.decision in ("ROUTE_TO_REVIEW", "REJECT_NOT_TRANSLATABLE")


def test_posture_cannot_become_ueak_admission():
    claim = fixture_claim(claim_type="OPERATING_POSTURE", claim_id="claim:posture")
    envelope = _authority_frame_envelope(claim, producer_module="RPB")
    decision = tep_decide(claim, envelope, EXECUTION_REFERENCE, operators=DEFAULT_OPERATORS)
    assert decision.decision in ("ROUTE_TO_REVIEW", "REJECT_NOT_TRANSLATABLE")
    assert envelope.authority_semantics.may_authorize_execution is False


def test_operator_approval_requires_identity_scope():
    claim = fixture_claim(claim_type="OPERATOR_APPROVAL_EVIDENCE", claim_id="claim:approval")
    envelope = fixture_envelope(
        claim,
        producer_module="ORI",
        reference_condition=REVIEW_REFERENCE,
        identity_ref="",
        scope_ref="",
    )
    decision = tep_decide(claim, envelope, REVIEW_REFERENCE)
    assert decision.decision == "FAIL_CLOSED"


def test_may_grant_flags_always_false():
    semantics = ADVISORY_AUTHORITY
    assert semantics.may_grant_tools is False
    assert semantics.may_grant_memory is False
    assert semantics.may_grant_context is False


def test_no_operator_raises_may_flags():
    before = ADVISORY_AUTHORITY
    after = AuthoritySemantics(
        authority_type="ADVISORY",
        may_authorize_execution=False,
        may_mint_permit=False,
        may_call_oea_ter=False,
        may_grant_tools=False,
        may_grant_memory=False,
        may_grant_context=False,
        may_publish=False,
        downstream_allowed_uses=before.downstream_allowed_uses,
        downstream_forbidden_uses=before.downstream_forbidden_uses,
        required_authority_chain_refs=before.required_authority_chain_refs,
    )
    assert authority_downgrade_only(before, after)
    with pytest.raises(TEPValidationError):
        AuthoritySemantics(
            authority_type="ADVISORY",
            may_authorize_execution=True,
            may_mint_permit=False,
            may_call_oea_ter=False,
            may_grant_tools=False,
            may_grant_memory=False,
            may_grant_context=False,
            may_publish=False,
            downstream_allowed_uses=(),
            downstream_forbidden_uses=(),
            required_authority_chain_refs=(),
        )


def test_gpp_fixture_rejects_naked_evidence():
    result = gpp_fixture_evaluate_permit_request(gpp_permit_evidence_fixture(naked=True))
    assert result["status"] == "rejected"
    assert result["permit_minted"] is False


def test_ueak_fixture_rejects_naked_support():
    result = ueak_fixture_evaluate_admission_request(ueak_admission_evidence_fixture(naked=True))
    assert result["status"] == "rejected"
    assert result["admitted"] is False


def test_ori_receipt_binding_metadata():
    result = ori_emit_review_receipt(approved=True)
    assert result["is_permit"] is False
    assert result["authority_created"] is False
