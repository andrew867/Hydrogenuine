"""AIO organ bus events and lifecycle receipts.

The bus carries events and receipts only — never raw audio bytes, voice models,
or secrets. A policy block is published (AUDIO_OUTPUT_BLOCKED), never swallowed,
so blocks are observable in proof.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hg_runtime.audio_io.hash import audio_hash

AUDIO_BUS_EVENTS = (
    # Config / mode
    "AUDIO_IO_CONFIG_LOADED",
    "AUDIO_INPUT_MODE_SET",
    # Capture
    "AUDIO_CAPTURE_STARTED",
    "AUDIO_CAPTURE_STOPPED",
    "AUDIO_FILE_RECEIVED",
    # Transcription
    "AUDIO_TRANSCRIPTION_STARTED",
    "AUDIO_TRANSCRIPTION_COMPLETED",
    "AUDIO_TRANSCRIPTION_FAILED",
    "AUDIO_TRANSCRIPT_TAINTED",
    "AUDIO_PROMPT_INJECTION_DETECTED",
    # Output
    "AUDIO_OUTPUT_REQUESTED",
    "AUDIO_OUTPUT_POLICY_CHECKED",
    "AUDIO_TTS_STARTED",
    "AUDIO_TTS_COMPLETED",
    "AUDIO_TTS_FAILED",
    "AUDIO_OUTPUT_PLAYBACK_REQUESTED",
    "AUDIO_OUTPUT_PLAYBACK_COMPLETED",
    "AUDIO_OUTPUT_BLOCKED",
    # CHRONO
    "CHRONO_TIME_SYNC_STARTED",
    "CHRONO_TIME_SYNC_COMPLETED",
    "CHRONO_CLOCK_DRIFT_DETECTED",
)

AUDIO_ORGAN_ID = "AIO"

# Raw-audio / secret keys that must never appear in a bus payload.
_FORBIDDEN_PAYLOAD_KEYS = frozenset({"audio_bytes", "raw_audio", "pcm", "wav_bytes", "voice_model", "secret"})


class BusPayloadViolation(Exception):
    code = "AUDIO_BUS_RAW_PAYLOAD"


@dataclass
class AudioBusEvent:
    event: str
    organ: str = AUDIO_ORGAN_ID
    data: dict[str, Any] = field(default_factory=dict)
    time_receipt_ref: str | None = None

    def __post_init__(self) -> None:
        if self.event not in AUDIO_BUS_EVENTS:
            raise ValueError(f"unknown AIO bus event: {self.event}")
        bad = _FORBIDDEN_PAYLOAD_KEYS & set(self.data)
        if bad:
            raise BusPayloadViolation(f"bus payload may not carry raw audio/secret keys: {sorted(bad)}")

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "schema": "audio-bus-event",
            "event": self.event,
            "organ": self.organ,
            "data": self.data,
            "time_receipt_ref": self.time_receipt_ref,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }
        payload["hash"] = audio_hash(payload)
        return payload


@dataclass
class OrganLifecycleReceipt:
    phase: str  # BOOT / HEARTBEAT / STOP
    organ: str = AUDIO_ORGAN_ID
    time_receipt_ref: str | None = None

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "schema": "audio-organ-lifecycle-receipt",
            "organ": self.organ,
            "phase": self.phase,
            "time_receipt_ref": self.time_receipt_ref,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }
        payload["hash"] = audio_hash(payload)
        return payload


__all__ = [
    "AUDIO_BUS_EVENTS",
    "AUDIO_ORGAN_ID",
    "AudioBusEvent",
    "BusPayloadViolation",
    "OrganLifecycleReceipt",
]
