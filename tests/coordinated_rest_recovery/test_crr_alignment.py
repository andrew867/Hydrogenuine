"""CRR integration alignment tests."""

from __future__ import annotations

import pytest

from hg_core.lifecycle.errors import LifecycleValidationError
from hg_runtime.coordinated_rest_recovery.alignment import (
    FIXTURE_CLOCK,
    evaluate_alignment,
    refuse_process_kill,
    refuse_recovery_as_permission,
    refuse_successor_spawn,
)
from hg_runtime.coordinated_rest_recovery.events import planned_crr_event_refs
from hg_runtime.coordinated_rest_recovery.types import RecoveryAlignmentRecord, alignment_from_fixture


def test_alignment_positive() -> None:
    record = alignment_from_fixture(
        {
            "alignment_id": "crr-1",
            "source_module": "els",
            "snapshot_hash_ref": "sha256:snapshot-fixture",
        }
    )
    result = evaluate_alignment(record, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "aligned"
    assert result["recovery_is_not_permission"] is True
    assert result["permission_granted"] is False


def test_expired_alignment_refused() -> None:
    record = alignment_from_fixture(
        {
            "alignment_id": "crr-exp",
            "expiry": "2026-06-12T19:00:00.000000Z",
        }
    )
    result = evaluate_alignment(record, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "crr.refused.expired_alignment"


def test_stale_alignment_refused() -> None:
    record = alignment_from_fixture(
        {
            "alignment_id": "crr-stale",
            "created_at": "2026-06-12T21:00:00.000000Z",
        }
    )
    result = evaluate_alignment(record, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "crr.refused.stale_alignment"


def test_recovery_active_conflict_refused() -> None:
    record = alignment_from_fixture(
        {
            "alignment_id": "crr-active",
            "source_module": "msc",
            "recovery_active": "1",
        }
    )
    result = evaluate_alignment(record, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "crr.refused.recovery_active_conflict"


def test_els_snapshot_missing_refused() -> None:
    record = alignment_from_fixture(
        {
            "alignment_id": "crr-miss",
            "source_module": "els",
            "snapshot_hash_ref": "",
        }
    )
    result = evaluate_alignment(record, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "crr.refused.snapshot_missing"


def test_recovery_not_permission_refused() -> None:
    with pytest.raises(LifecycleValidationError):
        refuse_recovery_as_permission(treat_as_permit=True)


def test_process_kill_refused() -> None:
    with pytest.raises(LifecycleValidationError):
        refuse_process_kill(requested=True)


def test_successor_spawn_refused() -> None:
    with pytest.raises(LifecycleValidationError):
        refuse_successor_spawn(requested=True)


def test_record_hash_stable() -> None:
    a = alignment_from_fixture({"alignment_id": "stable"})
    b = alignment_from_fixture({"alignment_id": "stable"})
    assert a.record_hash == b.record_hash


def test_crr_event_refs_no_authority_fields() -> None:
    refs = planned_crr_event_refs()
    assert len(refs) >= 8
    assert all(not e.get("authority_fields") for e in refs)


def test_schema_rejects_secret_recovery_ref() -> None:
    with pytest.raises(LifecycleValidationError):
        RecoveryAlignmentRecord(
            alignment_id="bad",
            source_module="els",
            recovery_marker_ref="password=secret",
            snapshot_hash_ref=None,
            recovery_active=False,
            created_at=FIXTURE_CLOCK,
            expiry="2026-06-13T20:00:00.000000Z",
        )
