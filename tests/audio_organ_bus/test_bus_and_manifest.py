"""A13/A14 — AIO organ manifest validates; bus events + lifecycle receipts; no raw audio."""

from __future__ import annotations

import pytest

from hg_runtime.audio_io.audio_bus import (
    AUDIO_ORGAN_ID,
    AudioBusEvent,
    BusPayloadViolation,
    OrganLifecycleReceipt,
)
from hg_runtime.audio_io.organ_integration import (
    build_aio_manifest_entry,
    validate_manifest_entry,
)


def test_manifest_entry_validates():
    entry = build_aio_manifest_entry()
    assert entry["organ_id"] == AUDIO_ORGAN_ID
    assert validate_manifest_entry(entry) == []


def test_manifest_defaults_optional_and_disabled():
    entry = build_aio_manifest_entry()
    assert entry["default_status"] == "optional"
    assert entry["stt_enabled_default"] is False
    assert entry["tts_enabled_default"] is False
    assert entry["carries_raw_audio"] is False


def test_bus_event_validates_and_hashes():
    ev = AudioBusEvent(event="AUDIO_OUTPUT_BLOCKED", data={"reason": "secret"})
    payload = ev.to_payload()
    assert payload["event"] == "AUDIO_OUTPUT_BLOCKED"
    assert payload["hash"].startswith("sha256:")
    assert payload["advisory_only"] is True


def test_unknown_event_rejected():
    with pytest.raises(ValueError):
        AudioBusEvent(event="NOT_A_REAL_EVENT")


def test_bus_payload_cannot_carry_raw_audio():
    with pytest.raises(BusPayloadViolation):
        AudioBusEvent(event="AUDIO_FILE_RECEIVED", data={"raw_audio": "..."})


def test_lifecycle_receipt_has_chrono_ref_and_frozen_constants():
    receipt = OrganLifecycleReceipt(phase="BOOT", time_receipt_ref="chrono-ref-3").to_payload()
    assert receipt["phase"] == "BOOT"
    assert receipt["time_receipt_ref"] == "chrono-ref-3"
    assert receipt["permission_granted"] is False
    assert receipt["authority_created"] is False
