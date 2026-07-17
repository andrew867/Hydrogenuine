"""AID disclosure tests."""

from __future__ import annotations

import pytest

from hg_core.policy_safety.errors import PolicyValidationError
from hg_runtime.ai_interaction_disclosure.disclosure import (
    build_disclosure_card,
    detect_missing_disclosure,
    validate_capability_claim,
)

FIXTURE = {
    "disclosure_id": "aid-1",
    "runtime_mode": "proposal_only",
    "model_or_provider_label": "fixture-model",
    "capability_claim": "can execute live trades",
    "capability_evidence_ref": "docs/proofs/connective_tissue/CT-A/20260613T005812Z/gate_result.json",
}


def test_disclosure_created_with_evidence() -> None:
    card = build_disclosure_card(FIXTURE)
    assert card.is_ai_interaction
    assert card.proposal_only_status
    assert card.external_action_status == "disabled"
    assert card.capability_evidence_ref


def test_unproven_capability_refused() -> None:
    bad = {**FIXTURE, "capability_evidence_ref": ""}
    with pytest.raises(PolicyValidationError):
        build_disclosure_card(bad)


def test_hide_ai_status_refused() -> None:
    with pytest.raises(PolicyValidationError):
        build_disclosure_card({**FIXTURE, "hide_ai": "true"})


def test_missing_disclosure_detected() -> None:
    result = detect_missing_disclosure(interaction_id="ix-1", disclosure=None)
    assert result["missing"] is True
    assert result["permission_granted"] is False


def test_validate_capability_claim_unproven() -> None:
    result = validate_capability_claim(capability_claim="superhuman accuracy", evidence_ref=None)
    assert result["status"] == "refused"


def test_proposal_only_not_action() -> None:
    card = build_disclosure_card(FIXTURE)
    assert card.proposal_only_status
    assert card.external_action_status != "enabled"
