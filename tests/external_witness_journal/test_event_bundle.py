"""EWJ event bundle tests."""

from __future__ import annotations

import json

import pytest

from hg_runtime.external_witness_journal.event_bundle import (
    WitnessAuthorityConversion,
    WitnessSecretLeak,
    assert_bundle_safe,
    build_event_bundle,
)
from hg_runtime.external_witness_journal.hash_chain import hash_journal_event
from hg_runtime.external_witness_journal.schema import WitnessEventClass, WitnessImportanceClass, WitnessJournalConfig


def test_event_bundle_hash_stable():
    cfg = WitnessJournalConfig()
    b1, _p1 = build_event_bundle(
        cfg,
        event_class=WitnessEventClass.BOOT_START,
        importance=WitnessImportanceClass.ROUTINE,
        event_sequence=0,
        summary="boot start",
        created_utc="2026-06-15T00:00:00+00:00",
    )
    b2, _p2 = build_event_bundle(
        cfg,
        event_class=WitnessEventClass.BOOT_START,
        importance=WitnessImportanceClass.ROUTINE,
        event_sequence=0,
        summary="boot start",
        created_utc="2026-06-15T00:00:00+00:00",
    )
    assert b1.journal_event_sha256 == b2.journal_event_sha256
    assert hash_journal_event(b1) == b1.journal_event_sha256


def test_public_event_excludes_secrets():
    cfg = WitnessJournalConfig()
    bundle, _payload = build_event_bundle(
        cfg,
        event_class=WitnessEventClass.MISSION_START,
        importance=WitnessImportanceClass.ROUTINE,
        event_sequence=1,
        summary="mission start",
        facts={"verdict": "GREEN"},
    )
    data = bundle.to_dict()
    assert data["secrets_included"] is False
    assert data["raw_memory_included"] is False
    assert data["authority"] is False
    assert data["permission_granted"] is False


def test_secret_in_summary_rejected():
    cfg = WitnessJournalConfig()
    with pytest.raises(WitnessSecretLeak):
        build_event_bundle(
            cfg,
            event_class=WitnessEventClass.IMPORTANT_STATE_MARKER,
            importance=WitnessImportanceClass.IMPORTANT,
            event_sequence=2,
            summary="api_key=sk-live-deadbeef",
        )


def test_authority_conversion_rejected():
    cfg = WitnessJournalConfig()
    bundle, _payload = build_event_bundle(
        cfg,
        event_class=WitnessEventClass.OPERATOR_MARKER,
        importance=WitnessImportanceClass.OPERATOR_PINNED,
        event_sequence=3,
        summary="operator pin",
    )
    bad = bundle.to_dict()
    bad["authority"] = True
    with pytest.raises(WitnessAuthorityConversion):
        assert_bundle_safe(bad)
