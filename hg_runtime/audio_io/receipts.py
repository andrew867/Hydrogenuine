"""Audio I/O receipts — evidence of what was heard/said and how it was governed.

Every audio input and output produces a hashable, frozen-constant receipt.
Hashes are over redacted content; raw audio bytes and unredacted secrets never
enter a receipt. Each receipt links a CHRONO time_receipt_ref.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hg_runtime.audio_io.hash import audio_hash, text_hash
from hg_runtime.audio_io.schema import (
    AUDIO_SCHEMA_VERSION,
    AudioCaptureMode,
    AudioOutputDecisionKind,
    AudioSourceClass,
    AudioTrustClass,
    new_id,
)

AUDIO_RECEIPT_KINDS = ("AUDIO_INPUT", "AUDIO_OUTPUT")


def _frozen() -> dict[str, Any]:
    return {"advisory_only": True, "permission_granted": False, "authority_created": False}


@dataclass
class AudioInputReceipt:
    capture_mode: AudioCaptureMode
    audio_source_class: AudioSourceClass
    audio_trust_class: AudioTrustClass
    duration_seconds: float
    stt_provider_id: str
    stt_enabled: bool
    model_present: bool
    transcript_present: bool
    transcript_text: str = ""  # redacted text only; hashed, never stored raw-secret
    confidence: float | None = None
    language: str | None = None
    acoustic_injection_finding: dict[str, Any] | None = None
    secret_redaction_applied: bool = False
    time_receipt_ref: str | None = None
    run_id: str = ""
    receipt_id: str = ""

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "schema": "audio-input-receipt",
            "version": AUDIO_SCHEMA_VERSION,
            "kind": "AUDIO_INPUT",
            "receipt_id": self.receipt_id or new_id("airx"),
            "run_id": self.run_id,
            "capture_mode": self.capture_mode.value,
            "audio_source_class": self.audio_source_class.value,
            "audio_trust_class": self.audio_trust_class.value,
            "duration_seconds": self.duration_seconds,
            "stt_provider_id": self.stt_provider_id,
            "stt_enabled": self.stt_enabled,
            "model_present": self.model_present,
            "transcript_present": self.transcript_present,
            "transcript_hash": text_hash(self.transcript_text) if self.transcript_present else None,
            "confidence": self.confidence,
            "language": self.language,
            "acoustic_injection_finding": self.acoustic_injection_finding,
            "secret_redaction_applied": self.secret_redaction_applied,
            "time_receipt_ref": self.time_receipt_ref,
            **_frozen(),
        }
        payload["hash"] = audio_hash(payload)
        return payload


@dataclass
class AudioOutputReceipt:
    caller: str
    purpose: str
    requested_text: str  # redacted text only
    output_decision: AudioOutputDecisionKind
    decision_reason: str
    tts_provider_id: str
    tts_enabled: bool
    voice_present: bool
    output_file_present: bool = False
    playback_performed: bool = False
    char_count: int = 0
    spoken_secret_finding: dict[str, Any] | None = None
    authority_claim_blocked: bool = False
    time_receipt_ref: str | None = None
    run_id: str = ""
    receipt_id: str = ""

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "schema": "audio-output-receipt",
            "version": AUDIO_SCHEMA_VERSION,
            "kind": "AUDIO_OUTPUT",
            "receipt_id": self.receipt_id or new_id("aorx"),
            "run_id": self.run_id,
            "caller": self.caller,
            "purpose": self.purpose,
            "requested_text_hash": text_hash(self.requested_text),
            "output_decision": self.output_decision.value,
            "decision_reason": self.decision_reason,
            "spoken_secret_finding": self.spoken_secret_finding,
            "authority_claim_blocked": self.authority_claim_blocked,
            "tts_provider_id": self.tts_provider_id,
            "tts_enabled": self.tts_enabled,
            "voice_present": self.voice_present,
            "output_file_present": self.output_file_present,
            "playback_performed": self.playback_performed,
            "char_count": self.char_count,
            "time_receipt_ref": self.time_receipt_ref,
            **_frozen(),
        }
        payload["hash"] = audio_hash(payload)
        return payload


__all__ = [
    "AUDIO_RECEIPT_KINDS",
    "AudioInputReceipt",
    "AudioOutputReceipt",
]
