"""TEP boundary integration fixture tests."""

from __future__ import annotations

from hg_runtime.translation_envelope_protocol.fixtures import (
    naked_scalar_fixture,
    fixture_claim,
    fixture_envelope,
)
from hg_runtime.translation_envelope_protocol.integration import (
    arb_consume_routed_claim,
    bac_fixture_chain_metadata,
    egi_emit_gap_proposal,
    gpp_fixture_evaluate_permit_request,
    imb_emit_mediation_receipt,
    ori_emit_review_receipt,
    rpb_emit_posture_claim,
    run_boundary_integration_path,
    ueak_fixture_evaluate_admission_request,
)
from hg_runtime.translation_envelope_protocol.fixtures import (
    POSTURE_REFERENCE,
    gpp_permit_evidence_fixture,
    ueak_admission_evidence_fixture,
)


def test_arb_refuses_naked_routed_claim():
    claim = naked_scalar_fixture()
    result = arb_consume_routed_claim(claim, None)
    assert result["status"] == "refused"
    assert result["routed"] is False


def test_imb_consensus_not_authority():
    claim = fixture_claim(claim_type="BOUNDARY_RECEIPT", claim_id="claim:imb")
    envelope = fixture_envelope(claim, producer_module="IMB")
    result = imb_emit_mediation_receipt(claim, envelope)
    assert result["consensus_is_not_authority"] is True


def test_ori_receipt_carries_authority_semantics():
    result = ori_emit_review_receipt(approved=True)
    assert result["receipt_type"] == "OPERATOR_REVIEW_RECEIPT"
    assert result["is_permit"] is False


def test_egi_refuses_naked_gap_score():
    claim = naked_scalar_fixture("PRIORITY_SCORE")
    result = egi_emit_gap_proposal(claim, None)
    assert result["status"] == "refused"


def test_rpb_posture_cannot_approve_execution():
    claim = fixture_claim(claim_type="OPERATING_POSTURE", claim_id="claim:posture")
    envelope = fixture_envelope(claim, producer_module="RPB", reference_condition=POSTURE_REFERENCE)
    result = rpb_emit_posture_claim(claim, envelope)
    assert result["execution_approved"] is False


def test_gpp_rejects_naked_scalar_evidence():
    result = gpp_fixture_evaluate_permit_request(gpp_permit_evidence_fixture(naked=True))
    assert result["status"] == "rejected"
    assert result["permit_minted"] is False


def test_ueak_rejects_naked_supporting_claim():
    result = ueak_fixture_evaluate_admission_request(ueak_admission_evidence_fixture(naked=True))
    assert result["status"] == "rejected"
    assert result["admitted"] is False


def test_bac_advisory_chain_stays_advisory():
    chain = [
        (fixture_claim(claim_id="c1"), fixture_envelope(fixture_claim(claim_id="c1"), envelope_id="e1")),
        (fixture_claim(claim_id="c2"), fixture_envelope(fixture_claim(claim_id="c2"), envelope_id="e2")),
    ]
    result = bac_fixture_chain_metadata(chain)
    assert result["chain_stays_advisory"] is True


def test_full_boundary_integration_path():
    result = run_boundary_integration_path()
    assert result["arb_naked_refused"] is True
    assert result["imb_not_authority"] is True
    assert result["ori_not_permit"] is True
    assert result["egi_naked_refused"] is True
    assert result["rpb_no_execution"] is True
    assert result["gpp_naked_rejected"] is True
    assert result["ueak_naked_rejected"] is True
    assert result["bac_chain_advisory"] is True
    assert result["no_oea_ter_called"] is True
