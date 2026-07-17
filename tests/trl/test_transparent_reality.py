"""TRL transparent reality layer tests."""

from __future__ import annotations

import pytest

from hg_core.developmental.errors import DevelopmentalValidationError
from hg_runtime.transparent_reality.events import planned_trl_event_refs
from hg_runtime.transparent_reality.reality import (
    evaluate_field_snapshot,
    evaluate_transparent_summary,
    refuse_reality_as_authority,
)
from hg_runtime.transparent_reality.types import (
    FIXTURE_CLOCK,
    TransparentFieldSnapshot,
    TransparentSummary,
    classify_narrative_collapse,
    snapshot_from_fixture,
    summary_from_fixture,
)


def test_field_snapshot_positive() -> None:
    snapshot = snapshot_from_fixture({"snapshot_id": "trl-1"})
    result = evaluate_field_snapshot(snapshot, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["summary_is_not_proof"] is True
    assert result["permission_granted"] is False


def test_stale_snapshot_refused() -> None:
    snapshot = snapshot_from_fixture(
        {
            "snapshot_id": "trl-stale",
            "expires_at": "2026-06-12T21:00:00.000000Z",
        }
    )
    result = evaluate_field_snapshot(snapshot, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "trl.refused.stale_snapshot"


def test_stale_refs_guarded() -> None:
    snapshot = snapshot_from_fixture(
        {
            "snapshot_id": "trl-stale-refs",
            "stale_refs": "layer:dni",
        }
    )
    result = evaluate_field_snapshot(snapshot, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "guarded"
    assert result["reason_code"] == "trl.refused.stale_snapshot"


def test_summary_as_proof_contained() -> None:
    summary = summary_from_fixture({"summary_id": "sum-proof"})
    result = evaluate_transparent_summary(
        summary,
        collapse_statement="the summary says it so it is true",
    )
    assert classify_narrative_collapse("the summary says it so it is true") == "summary_as_proof"
    assert result["status"] == "contained"
    assert result["reason_code"] == "trl.refused.summary_as_proof"


def test_integration_as_authority_contained() -> None:
    summary = summary_from_fixture({"summary_id": "sum-int"})
    result = evaluate_transparent_summary(
        summary,
        collapse_statement="all layers agree so we may act",
    )
    assert result["status"] == "contained"
    assert result["reason_code"] == "trl.refused.integration_as_authority"


def test_unknown_erasure_contained() -> None:
    summary = summary_from_fixture(
        {
            "summary_id": "sum-erasure",
            "known_summary": "unknowns omitted from final framing",
            "unknown_summary": "",
        }
    )
    result = evaluate_transparent_summary(summary)
    assert result["status"] == "contained"
    assert result["reason_code"] == "trl.refused.unknown_erasure"


def test_treat_as_proof_contained() -> None:
    summary = summary_from_fixture({"summary_id": "sum-treat"})
    result = evaluate_transparent_summary(summary, treat_as_proof=True)
    assert result["status"] == "contained"
    assert result["reason_code"] == "trl.refused.summary_as_proof"


def test_reality_as_authority_refused() -> None:
    snapshot = snapshot_from_fixture({"snapshot_id": "trl-auth"})
    with pytest.raises(DevelopmentalValidationError):
        evaluate_field_snapshot(snapshot, observed_at=FIXTURE_CLOCK, treat_as_authority=True)
    with pytest.raises(DevelopmentalValidationError):
        refuse_reality_as_authority(treat_as_authority=True)


def test_record_hash_stable() -> None:
    a = snapshot_from_fixture({"snapshot_id": "stable"})
    b = snapshot_from_fixture({"snapshot_id": "stable"})
    assert a.record_hash == b.record_hash


def test_schema_rejects_secret() -> None:
    with pytest.raises(DevelopmentalValidationError):
        TransparentSummary(
            summary_id="bad",
            field_snapshot_ref="trl:snapshot-fixture",
            known_summary="password=secret",
            unknown_summary="",
            contradiction_summary="none",
            evidence_refs=(),
        )


def test_trl_event_refs_no_authority_fields() -> None:
    refs = planned_trl_event_refs()
    assert len(refs) >= 13
    assert all(not e.get("authority_fields") for e in refs)


def test_narrative_collapse_false_omniscience() -> None:
    summary = summary_from_fixture({"summary_id": "sum-omni"})
    result = evaluate_transparent_summary(summary, collapse_statement="complete visibility achieved")
    assert result["status"] == "contained"
    assert result["reason_code"] == "trl.refused.narrative_collapse"


def test_transparent_summary_recorded() -> None:
    summary = summary_from_fixture(
        {
            "summary_id": "sum-ok",
            "known_summary": "bounded known state",
            "unknown_summary": "unknown remains unknown",
        }
    )
    result = evaluate_transparent_summary(summary)
    assert result["status"] == "recorded"
    assert result["unknown_preserved"] is True


def test_field_snapshot_ref_requires_trl_prefix() -> None:
    with pytest.raises(DevelopmentalValidationError):
        TransparentSummary(
            summary_id="bad",
            field_snapshot_ref="not-trl",
            known_summary="bounded",
            unknown_summary="unknown",
            contradiction_summary="none",
            evidence_refs=(),
        )
