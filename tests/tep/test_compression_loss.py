"""TEP compression and loss confession tests."""

from __future__ import annotations

import pytest

from hg_core.tep_cluster.errors import TEPValidationError
from hg_runtime.translation_envelope_protocol.decide import tep_decide
from hg_runtime.translation_envelope_protocol.fixtures import (
    RISK_REFERENCE,
    authority_field_discard_certificate,
    compressed_without_certificate_fixture,
    fixture_claim,
    fixture_envelope,
    fixture_loss_certificate,
    lossy_accepted_fixture,
)
from hg_runtime.translation_envelope_protocol.types import LossCertificate
from hg_runtime.translation_envelope_protocol.validator import validate_loss_certificate


def test_lossy_with_certificate_accepted_with_warning():
    claim, envelope = lossy_accepted_fixture()
    decision = tep_decide(claim, envelope, RISK_REFERENCE)
    assert decision.decision == "ACCEPT_APPROXIMATE_WITH_WARNING"
    assert decision.warnings
    assert decision.to_payload()["authority_created"] is False


def test_compressed_without_certificate_refused():
    claim, envelope = compressed_without_certificate_fixture()
    decision = tep_decide(claim, envelope, RISK_REFERENCE)
    assert decision.decision == "REJECT_NAKED_CLAIM"


def test_certificate_missing_invalid_comparisons_fails_closed():
    with pytest.raises(TEPValidationError):
        LossCertificate(
            loss_certificate_id="loss:bad",
            compression_method="field-prune-v1",
            fields_preserved=("observed_context",),
            fields_discarded=("trace_depth",),
            expected_effect="bias",
            invalid_comparisons=(),
            audit_ref="audit:bad",
        )


def test_authority_field_discard_fails_closed():
    with pytest.raises(TEPValidationError):
        authority_field_discard_certificate()


def test_loss_certificate_validator_requires_invalid_comparisons():
    cert = fixture_loss_certificate()
    validate_loss_certificate(cert)
    assert cert.invalid_comparisons


def test_missing_raw_pointer_still_acceptable_for_non_freshness_frame():
    claim = fixture_claim()
    cert = fixture_loss_certificate(raw_envelope_pointer="")
    envelope = fixture_envelope(
        claim,
        translation_status="APPROXIMATE_LOSSY",
        compression_method="field-prune-v1",
        loss_certificate=cert,
    )
    decision = tep_decide(claim, envelope, RISK_REFERENCE)
    assert decision.decision == "ACCEPT_APPROXIMATE_WITH_WARNING"
