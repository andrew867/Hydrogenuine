"""SYN classifier and schema tests."""

from __future__ import annotations

import pytest

from hg_core.policy_safety.errors import PolicyValidationError
from hg_runtime.synthetic_content_provenance.classifier import classify_fixture, classify_fixture_mapping
from hg_runtime.synthetic_content_provenance.policy import evaluate_export, label_is_not_permission, refuse_label_removal
from hg_runtime.synthetic_content_provenance.types import ContentDisclosureLabel, SyntheticContentArtifact

FIXTURE_CLOCK = "2026-06-12T20:00:00.000000Z"


def _artifact(artifact_id: str = "art-1") -> SyntheticContentArtifact:
    return SyntheticContentArtifact(
        artifact_id=artifact_id,
        content_class="text",
        content_ref=f"sha256:{artifact_id}",
        generated=True,
        created_at=FIXTURE_CLOCK,
    )


def test_ordinary_generated_content_classified() -> None:
    result = classify_fixture(_artifact(), text_hint="generated summary for operator review")
    assert result.risk_class == "ordinary_generated_content"
    assert not result.fail_closed


def test_impersonation_risk_detected() -> None:
    result = classify_fixture_mapping(
        {
            "artifact_id": "art-imp",
            "text_hint": "Official statement from the Federal Reserve on rates",
        }
    )
    assert result.risk_class == "public_figure_or_institution_impersonation"
    assert result.fail_closed


def test_unknown_risk_fails_closed() -> None:
    result = classify_fixture(_artifact(), text_hint="ambiguous")
    assert result.risk_class == "unknown"
    assert result.fail_closed


def test_undisclosed_export_refused() -> None:
    artifact = _artifact("art-undisclosed")
    classification = classify_fixture(artifact, text_hint="passed off as human written")
    label = ContentDisclosureLabel(
        label_id="lbl-1",
        artifact_id=artifact.artifact_id,
        disclosure_text="",
        disclosed=False,
        risk_class=classification.risk_class,
        created_at=FIXTURE_CLOCK,
    )
    decision = evaluate_export(label, classification)
    assert not decision["allowed"]
    assert decision["permission_granted"] is False


def test_schema_validation_rejects_bad_content_ref() -> None:
    with pytest.raises(PolicyValidationError):
        SyntheticContentArtifact(
            artifact_id="bad",
            content_class="text",
            content_ref="https://example.com/secret",
            generated=True,
            created_at=FIXTURE_CLOCK,
        )


def test_label_removal_refused() -> None:
    with pytest.raises(PolicyValidationError):
        refuse_label_removal(requested=True)


def test_label_is_not_permission() -> None:
    assert label_is_not_permission("ordinary_generated_content")
    assert not label_is_not_permission("unknown")


def test_record_hash_stable() -> None:
    a1 = _artifact("stable")
    a2 = _artifact("stable")
    assert a1.record_hash == a2.record_hash
