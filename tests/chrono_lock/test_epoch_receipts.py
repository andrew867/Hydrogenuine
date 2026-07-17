"""Boot epoch receipt binding tests."""

from __future__ import annotations

from hg_runtime.chrono.agent0_context import next_receipt_sequence
from hg_runtime.chrono.drift import detect_backward_ordering
from hg_runtime.chrono.lock import create_chrono_lock
from hg_runtime.chrono.receipts import create_epoch_receipt, stamp_mission_receipt
from hg_runtime.chrono.schema import FIXTURE_MONOTONIC, FIXTURE_UTC, TimeConfidence, TimeSourceKind, TimeSyncResult
from hg_runtime.chrono.sync import ChronoConfig


def test_receipts_include_epoch_lock_id():
    outcome = create_chrono_lock(config=ChronoConfig(offline_fixture=True))
    receipt = create_epoch_receipt(
        outcome.sync_outcome.result,
        epoch_id=outcome.lock.epoch_id,
        epoch_lock_id=outcome.lock.epoch_lock_id,
        receipt_sequence=0,
    )
    payload = receipt.to_payload()
    assert payload["epoch_id"] == outcome.lock.epoch_id
    assert payload["epoch_lock_id"] == outcome.lock.epoch_lock_id
    assert payload["receipt_sequence"] == 0
    assert payload["monotonic_ns"] is not None


def test_mission_receipt_sequence_increments():
    outcome = create_chrono_lock(config=ChronoConfig(offline_fixture=True))
    r0 = create_epoch_receipt(
        outcome.sync_outcome.result,
        epoch_id=outcome.lock.epoch_id,
        epoch_lock_id=outcome.lock.epoch_lock_id,
        receipt_sequence=0,
    )
    r1 = stamp_mission_receipt(
        create_epoch_receipt(
            outcome.sync_outcome.result,
            epoch_id=outcome.lock.epoch_id,
            epoch_lock_id=outcome.lock.epoch_lock_id,
            receipt_sequence=next_receipt_sequence(0),
        ),
        epoch_id=outcome.lock.epoch_id,
        epoch_lock_id=outcome.lock.epoch_lock_id,
        receipt_sequence=1,
    )
    assert r0.receipt_sequence == 0
    assert r1.receipt_sequence == 1
    assert r1.monotonic_ns >= r0.monotonic_ns


def test_backward_wall_clock_jump_detected():
    previous = TimeSyncResult(
        utc="2026-06-15T12:00:00+00:00",
        monotonic_seconds=100.0,
        source=TimeSourceKind.FIXTURE,
        confidence=TimeConfidence.HIGH,
    )
    current = TimeSyncResult(
        utc="2026-06-15T11:00:00+00:00",
        monotonic_seconds=101.0,
        source=TimeSourceKind.FIXTURE,
        confidence=TimeConfidence.HIGH,
    )
    finding = detect_backward_ordering(previous, current)
    assert finding is not None
    assert finding.kind.value == "BACKWARD_ORDERING"


def test_receipt_ordering_uses_monotonic_sequence_not_wall_clock():
    seq_a = 5
    assert next_receipt_sequence(seq_a) == 6
    # Wall clock could jump backward; monotonic receipt_sequence still orders correctly
