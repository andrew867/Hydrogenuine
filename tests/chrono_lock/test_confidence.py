"""ChronoLock confidence grading tests."""

from __future__ import annotations

from hg_runtime.chrono.epoch import EpochConfidence
from hg_runtime.chrono.lock import create_chrono_lock, grade_epoch_confidence
from hg_runtime.chrono.sync import ChronoConfig


def test_missing_ntp_lowers_confidence():
    outcome = create_chrono_lock(config=ChronoConfig(allow_network=False))
    assert outcome.lock.time_confidence in {EpochConfidence.LOW, EpochConfidence.MEDIUM, EpochConfidence.UNKNOWN}


def test_fixture_high_or_medium_without_anchor():
    outcome = create_chrono_lock(config=ChronoConfig(offline_fixture=True))
    assert outcome.lock.time_confidence in {EpochConfidence.HIGH, EpochConfidence.MEDIUM}


def test_verified_anchor_raises_confidence():
    without = create_chrono_lock(config=ChronoConfig(offline_fixture=True), external_anchor_verified=False)
    with_anchor = create_chrono_lock(
        config=ChronoConfig(offline_fixture=True),
        boot_bundle_sha256="deadbeef",
        external_anchor_commit_sha="abc123",
        external_anchor_verified=True,
    )
    levels = {EpochConfidence.HIGH: 3, EpochConfidence.MEDIUM: 2, EpochConfidence.LOW: 1, EpochConfidence.UNKNOWN: 0}
    assert levels[with_anchor.lock.time_confidence] >= levels[without.lock.time_confidence]


def test_grade_high_requires_ntp_and_anchor():
    assert grade_epoch_confidence(
        ntp_reachable=True,
        ntp_offset_seconds=0.5,
        monotonic_recorded=True,
        external_anchor_verified=True,
        system_only=False,
        time_uncertain=False,
    ) == EpochConfidence.HIGH


def test_chrono_lock_cannot_grant_permission():
    outcome = create_chrono_lock(config=ChronoConfig(offline_fixture=True))
    payload = outcome.lock.to_payload()
    assert payload["permission_granted"] is False
    assert payload["authority_created"] is False
    assert payload["advisory_only"] is True
