"""TEP schema, naked-claim refusal, and determinism tests."""

from __future__ import annotations

import pytest

from hg_core.tep_cluster.errors import TEPValidationError
from hg_runtime.translation_envelope_protocol.decide import tep_decide
from hg_runtime.translation_envelope_protocol.fixtures import (
    DEFAULT_OPERATORS,
    PRIORITY_REFERENCE,
    RISK_REFERENCE,
    compressed_without_certificate_fixture,
    false_comparability_pair,
    fixture_claim,
    fixture_envelope,
    fixture_loss_certificate,
    naked_scalar_fixture,
)
from hg_runtime.translation_envelope_protocol.types import (
    AuthoritySemantics,
    TranslationEnvelope,
)
from hg_runtime.translation_envelope_protocol.validator import is_naked_claim, validate_translation_envelope


@pytest.mark.parametrize(
    "claim_type",
    [
        "RISK_SCORE",
        "TRUST_SCORE",
        "PRIORITY_SCORE",
        "PROOF_SUMMARY",
        "OPERATOR_REVIEW_RECEIPT",
        "SIMULATION_RESULT",
    ],
)
def test_naked_scalar_refused(claim_type: str):
    claim = naked_scalar_fixture(claim_type)  # type: ignore[arg-type]
    decision = tep_decide(claim, None, RISK_REFERENCE)
    assert decision.decision == "REJECT_NAKED_CLAIM"
    assert decision.to_payload()["authority_created"] is False


def test_envelope_required_fields_present():
    claim = fixture_claim()
    envelope = fixture_envelope(claim)
    validate_translation_envelope(envelope)
    assert envelope.record_hash


def test_missing_observation_envelope_is_naked_at_boundary():
    claim = fixture_claim()
    envelope = fixture_envelope(claim)
    naked, _ = is_naked_claim(claim, envelope)
    assert naked is False
    decision = tep_decide(claim, None, RISK_REFERENCE)
    assert decision.decision == "REJECT_NAKED_CLAIM"


def test_compressed_without_certificate_is_naked():
    claim, envelope = compressed_without_certificate_fixture()
    naked, reason = is_naked_claim(claim, envelope)
    assert naked is True
    assert "loss certificate" in reason
    decision = tep_decide(claim, envelope, RISK_REFERENCE)
    assert decision.decision == "REJECT_NAKED_CLAIM"


def test_stable_hashing():
    claim = fixture_claim()
    left = fixture_envelope(claim, envelope_id="env:hash-a")
    right = fixture_envelope(claim, envelope_id="env:hash-b")
    assert left.record_hash != right.record_hash
    same = fixture_envelope(claim, envelope_id="env:hash-a")
    assert left.record_hash == same.record_hash


def test_deterministic_replay():
    claim = fixture_claim()
    envelope = fixture_envelope(claim)
    first = tep_decide(claim, envelope, RISK_REFERENCE)
    second = tep_decide(claim, envelope, RISK_REFERENCE)
    assert first.decision == second.decision
    assert first.reason == second.reason
    assert first.record_hash == second.record_hash


def test_compatible_translation_operator():
    claim = fixture_claim(claim_type="RISK_SCORE")
    envelope = fixture_envelope(claim)
    decision = tep_decide(claim, envelope, PRIORITY_REFERENCE, operators=DEFAULT_OPERATORS)
    assert decision.decision == "ACCEPT_TRANSLATED"


def test_false_comparability_different_claim_types():
    risk_claim, risk_env, conf_claim, conf_env = false_comparability_pair()
    direct = tep_decide(risk_claim, risk_env, RISK_REFERENCE)
    assert direct.decision == "ACCEPT_DIRECT"
    cross = tep_decide(conf_claim, conf_env, RISK_REFERENCE)
    assert cross.decision in ("REJECT_NOT_TRANSLATABLE", "FAIL_CLOSED")


def test_not_translatable_recorded_with_reason():
    claim = fixture_claim(claim_type="SIMULATION_RESULT", claim_id="claim:sim")
    envelope = fixture_envelope(
        claim,
        translation_status="NOT_TRANSLATABLE",
        not_translatable_reason="simulation is not execution history",
    )
    decision = tep_decide(claim, envelope, RISK_REFERENCE)
    assert decision.decision == "REJECT_NOT_TRANSLATABLE"


def test_authority_semantics_pinned_grant_flags():
    with pytest.raises(TEPValidationError):
        AuthoritySemantics(
            authority_type="ADVISORY",
            may_authorize_execution=False,
            may_mint_permit=False,
            may_call_oea_ter=False,
            may_grant_tools=True,
            may_grant_memory=False,
            may_grant_context=False,
            may_publish=False,
            downstream_allowed_uses=(),
            downstream_forbidden_uses=(),
            required_authority_chain_refs=(),
        )


def test_envelope_hash_changes_on_field_edit():
    claim = fixture_claim()
    envelope = fixture_envelope(claim)
    original_hash = envelope.record_hash
    edited = TranslationEnvelope(
        envelope_id=envelope.envelope_id,
        claim_id=envelope.claim_id,
        claim_type=envelope.claim_type,
        producer_ref=envelope.producer_ref,
        producer_module=envelope.producer_module,
        producer_role=envelope.producer_role,
        scalar_value=0.81,
        reference_condition=envelope.reference_condition,
        observation_envelope=envelope.observation_envelope,
        uncertainty_semantics=envelope.uncertainty_semantics,
        authority_semantics=envelope.authority_semantics,
        trace_pointer=envelope.trace_pointer,
        proof_refs=envelope.proof_refs,
        translation_status=envelope.translation_status,
        created_at=envelope.created_at,
    )
    assert edited.record_hash != original_hash


def test_loss_certificate_required_fields():
    cert = fixture_loss_certificate()
    assert cert.invalid_comparisons
    assert cert.record_hash
