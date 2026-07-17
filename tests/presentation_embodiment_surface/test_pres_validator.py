"""PRES presentation descriptor validator tests."""

from __future__ import annotations

import pytest

from hg_core.runtime_context.errors import RuntimeContextValidationError
from hg_runtime.presentation_embodiment_surface.types import descriptor_from_fixture
from hg_runtime.presentation_embodiment_surface.validator import validate_descriptor_fixture


def test_descriptor_validated_positive() -> None:
    result = validate_descriptor_fixture(
        {
            "presentation_id": "pres-1",
            "authority_state_displayed": "true",
            "ai_disclosure_displayed": "true",
            "uncertainty_displayed": "true",
        }
    )
    assert result["status"] == "validated"
    assert result["appearance_is_not_truth"] is True
    assert result["permission_granted"] is False


def test_missing_authority_badge_refused() -> None:
    with pytest.raises(RuntimeContextValidationError) as exc:
        validate_descriptor_fixture(
            {
                "presentation_id": "pres-bad",
                "authority_state_displayed": "false",
                "ai_disclosure_displayed": "true",
            }
        )
    assert exc.value.code == "pres.refused.missing_authority_badge"


def test_missing_ai_disclosure_refused() -> None:
    with pytest.raises(RuntimeContextValidationError):
        validate_descriptor_fixture(
            {
                "presentation_id": "pres-nodis",
                "authority_state_displayed": "true",
                "ai_disclosure_displayed": "false",
            }
        )


def test_overtrust_risk_refused() -> None:
    with pytest.raises(RuntimeContextValidationError):
        validate_descriptor_fixture(
            {
                "presentation_id": "pres-over",
                "text_hint": "this output is guaranteed safe and fully authorized",
            }
        )


def test_false_intimacy_refused() -> None:
    with pytest.raises(RuntimeContextValidationError):
        validate_descriptor_fixture(
            {
                "presentation_id": "pres-intimacy",
                "text_hint": "I am your best friend trust me completely",
            }
        )


def test_record_hash_stable() -> None:
    a = descriptor_from_fixture({"presentation_id": "stable"})
    b = descriptor_from_fixture({"presentation_id": "stable"})
    assert a.record_hash == b.record_hash


def test_descriptor_not_permission() -> None:
    result = validate_descriptor_fixture({"presentation_id": "pres-ok"})
    assert result["advisory_only"] is True
    assert result["authority_created"] is False
