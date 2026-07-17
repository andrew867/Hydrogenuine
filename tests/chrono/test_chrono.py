"""CHRONO core tests — sources, sync, confidence, frozen constants."""

from __future__ import annotations

from hg_runtime.chrono.policy import (
    attempt_time_authorization,
    reject_authority_mutation,
    validate_frozen_constants,
)
from hg_runtime.chrono.receipts import create_receipt
from hg_runtime.chrono.schema import TimeConfidence, TimeSourceKind
from hg_runtime.chrono.sources import FixtureTimeSource, SystemTimeSource
from hg_runtime.chrono.sync import ChronoConfig, sync_time


def test_fixture_deterministic():
    a = FixtureTimeSource().read()
    b = FixtureTimeSource().read()
    assert a.utc == b.utc
    assert a.source == TimeSourceKind.FIXTURE
    assert a.confidence == TimeConfidence.HIGH


def test_system_fallback_reduced_confidence():
    outcome = sync_time(ChronoConfig(allow_network=False))
    assert outcome.result.source == TimeSourceKind.SYSTEM
    assert outcome.result.confidence == TimeConfidence.LOW
    assert outcome.result.time_uncertain is True


def test_offline_fixture_path():
    outcome = sync_time(ChronoConfig(offline_fixture=True))
    assert outcome.result.source == TimeSourceKind.FIXTURE
    assert outcome.receipt.time_confidence == TimeConfidence.HIGH


def test_receipt_frozen_constants_and_hash():
    outcome = sync_time(ChronoConfig(offline_fixture=True))
    payload = outcome.receipt.to_payload()
    assert payload["advisory_only"] is True
    assert payload["permission_granted"] is False
    assert payload["authority_created"] is False
    assert payload["content_hash"].startswith("sha256:")


def test_receipt_hash_stable():
    r1 = create_receipt(FixtureTimeSource().read())
    r2 = create_receipt(FixtureTimeSource().read())
    # receipt_id differs (uuid) but it is excluded from the hash domain,
    # while the time content is identical.
    h1 = r1.to_payload()["content_hash"]
    h2 = r2.to_payload()["content_hash"]
    assert h1 == h2


def test_authority_conversion_rejected():
    assert attempt_time_authorization("weather_read")["rejected"] is True
    assert reject_authority_mutation({"authority_created": True})["rejected"] is True
    assert reject_authority_mutation({"advisory_only": True})["rejected"] is False


def test_validate_frozen_constants_catches_mutation():
    bad = {"advisory_only": True, "permission_granted": True, "authority_created": False}
    assert validate_frozen_constants(bad) != []
    good = SystemTimeSource().read().to_payload()
    assert validate_frozen_constants(good) == []
