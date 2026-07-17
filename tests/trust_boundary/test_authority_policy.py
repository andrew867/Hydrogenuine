"""Authority doctrine — external content can never grant permission or authority."""

from __future__ import annotations

from hg_runtime.trust_boundary.policy import (
    reject_authority_mutation,
    validate_frozen_constants,
)


def test_payload_claiming_permission_is_rejected():
    result = reject_authority_mutation({"permission_granted": True})
    assert result["rejected"] is True
    assert result["permission_granted"] is False


def test_payload_claiming_authority_is_rejected():
    result = reject_authority_mutation({"authority_created": True})
    assert result["rejected"] is True


def test_clean_payload_passes_authority_check():
    result = reject_authority_mutation(
        {"permission_granted": False, "authority_created": False}
    )
    assert result["rejected"] is False


def test_validate_frozen_constants_flags_violations():
    bad = {"advisory_only": False, "permission_granted": True, "authority_created": True}
    failures = validate_frozen_constants(bad)
    assert len(failures) == 3


def test_validate_frozen_constants_passes_good_payload():
    good = {"advisory_only": True, "permission_granted": False, "authority_created": False}
    assert validate_frozen_constants(good) == []
