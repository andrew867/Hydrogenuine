"""Audio I/O schema — audio is cargo until classified, never authority.

Every capture is stamped with an AudioTrustClass derived from *how it was
captured*, never from what it says. Only TRUSTED_OPERATOR_PUSH_TO_TALK audio is
ever a candidate operator instruction, and even then it remains policy-subject.
Every envelope, transcript, and receipt carries the three frozen advisory
booleans.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from hg_runtime.audio_io.hash import audio_hash, text_hash

AUDIO_SCHEMA_VERSION = "audio_io/1"

# Deterministic fixture stamps (mirrors WILL/CHRONO fixture discipline).
FIXTURE_UTC = "2026-06-15T04:00:00+00:00"
FIXTURE_RUN_ID = "audio-fixture-run"


class AudioCaptureMode(str, Enum):
    OFF = "OFF"
    WAV_FIXTURE_ONLY = "WAV_FIXTURE_ONLY"
    PUSH_TO_TALK = "PUSH_TO_TALK"
    OPERATOR_STARTED_BOUNDED = "OPERATOR_STARTED_BOUNDED"
    ALWAYS_LISTEN_DISABLED = "ALWAYS_LISTEN_DISABLED"
    LIVE_MIC_EXPLICIT = "LIVE_MIC_EXPLICIT"


class AudioSourceClass(str, Enum):
    OPERATOR = "OPERATOR"
    ROOM = "ROOM"
    MEDIA_PLAYBACK = "MEDIA_PLAYBACK"
    REMOTE = "REMOTE"
    FIXTURE = "FIXTURE"
    GENERATED = "GENERATED"
    UNKNOWN = "UNKNOWN"


class AudioTrustClass(str, Enum):
    TRUSTED_OPERATOR_PUSH_TO_TALK = "TRUSTED_OPERATOR_PUSH_TO_TALK"
    OPERATOR_LIVE_UNCONFIRMED = "OPERATOR_LIVE_UNCONFIRMED"
    UNTRUSTED_ROOM_AUDIO = "UNTRUSTED_ROOM_AUDIO"
    UNTRUSTED_MEDIA_PLAYBACK = "UNTRUSTED_MEDIA_PLAYBACK"
    UNTRUSTED_REMOTE_AUDIO = "UNTRUSTED_REMOTE_AUDIO"
    GENERATED_TTS_OUTPUT = "GENERATED_TTS_OUTPUT"
    FIXTURE_AUDIO = "FIXTURE_AUDIO"
    UNKNOWN_REVIEW_REQUIRED = "UNKNOWN_REVIEW_REQUIRED"


# The only class that may ever be a *candidate* operator instruction.
CANDIDATE_OPERATOR_CLASSES = frozenset({AudioTrustClass.TRUSTED_OPERATOR_PUSH_TO_TALK})


def may_be_candidate_operator(trust_class: AudioTrustClass) -> bool:
    return trust_class in CANDIDATE_OPERATOR_CLASSES


# Trust-class derives from capture mode + source, never from content.
def trust_class_for_capture(
    mode: AudioCaptureMode, source: AudioSourceClass
) -> AudioTrustClass:
    if mode == AudioCaptureMode.WAV_FIXTURE_ONLY or source == AudioSourceClass.FIXTURE:
        return AudioTrustClass.FIXTURE_AUDIO
    if source == AudioSourceClass.GENERATED:
        return AudioTrustClass.GENERATED_TTS_OUTPUT
    if mode == AudioCaptureMode.PUSH_TO_TALK and source == AudioSourceClass.OPERATOR:
        return AudioTrustClass.TRUSTED_OPERATOR_PUSH_TO_TALK
    if mode == AudioCaptureMode.OPERATOR_STARTED_BOUNDED and source == AudioSourceClass.OPERATOR:
        return AudioTrustClass.TRUSTED_OPERATOR_PUSH_TO_TALK
    # Source provenance wins over the capture mode for non-operator sources: a
    # known room/media/remote source is untrusted even on a live mic.
    if source == AudioSourceClass.ROOM:
        return AudioTrustClass.UNTRUSTED_ROOM_AUDIO
    if source == AudioSourceClass.MEDIA_PLAYBACK:
        return AudioTrustClass.UNTRUSTED_MEDIA_PLAYBACK
    if source == AudioSourceClass.REMOTE:
        return AudioTrustClass.UNTRUSTED_REMOTE_AUDIO
    if mode == AudioCaptureMode.LIVE_MIC_EXPLICIT:
        return AudioTrustClass.OPERATOR_LIVE_UNCONFIRMED
    return AudioTrustClass.UNKNOWN_REVIEW_REQUIRED


class AcousticInjectionAction(str, Enum):
    ALLOW_AS_OPERATOR_TEXT = "ALLOW_AS_OPERATOR_TEXT"
    SUMMARIZE_ONLY = "SUMMARIZE_ONLY"
    QUARANTINE = "QUARANTINE"
    OPERATOR_REVIEW = "OPERATOR_REVIEW"
    FULL_STOP = "FULL_STOP"


class AudioOutputDecisionKind(str, Enum):
    ALLOW = "allow"
    REDACT_THEN_ALLOW = "redact_then_allow"
    BLOCK = "block"


def _frozen() -> dict[str, Any]:
    return {
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }


@dataclass
class AudioInputEnvelope:
    """Captured audio + capture mode + trust/source class + ingress metadata."""

    envelope_id: str
    capture_mode: AudioCaptureMode
    source_class: AudioSourceClass
    trust_class: AudioTrustClass
    origin: str
    duration_seconds: float = 0.0
    audio_path: str | None = None  # untracked local path; never committed
    ingress_receipt_ref: str | None = None

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "schema": "audio-input-envelope",
            "version": AUDIO_SCHEMA_VERSION,
            "envelope_id": self.envelope_id,
            "capture_mode": self.capture_mode.value,
            "source_class": self.source_class.value,
            "trust_class": self.trust_class.value,
            "origin": self.origin,
            "duration_seconds": self.duration_seconds,
            "may_be_candidate_operator": may_be_candidate_operator(self.trust_class),
            "ingress_receipt_ref": self.ingress_receipt_ref,
            **_frozen(),
        }
        payload["content_hash"] = audio_hash(payload)
        return payload


@dataclass
class AcousticPromptInjectionFinding:
    severity: str
    recommended_action: AcousticInjectionAction
    signals: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "audio-acoustic-injection-finding",
            "severity": self.severity,
            "recommended_action": self.recommended_action.value,
            "signals": self.signals,
            **_frozen(),
        }


@dataclass
class SpokenSecretFinding:
    kinds: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "audio-spoken-secret-finding",
            "kinds": self.kinds,
            **_frozen(),
        }


@dataclass
class SpeechTranscript:
    """STT result. The text is already secret-redacted before it lands here."""

    text: str
    trust_class: AudioTrustClass
    confidence: float | None = None
    language: str | None = None
    segments: list[dict[str, Any]] = field(default_factory=list)
    redacted: bool = False
    injection: AcousticPromptInjectionFinding | None = None
    source: str = "unknown"  # fixture_sidecar | real_stt | live_mic

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "schema": "audio-speech-transcript",
            "version": AUDIO_SCHEMA_VERSION,
            "text": self.text,
            "source": self.source,
            "trust_class": self.trust_class.value,
            "confidence": self.confidence,
            "language": self.language,
            "segments": self.segments,
            "redacted": self.redacted,
            "may_be_candidate_operator": may_be_candidate_operator(self.trust_class),
            # A transcript is advisory text; it is never an instruction by itself.
            "is_instruction": False,
            "injection": self.injection.to_payload() if self.injection else None,
            **_frozen(),
        }
        payload["transcript_hash"] = text_hash(self.text)
        payload["content_hash"] = audio_hash(payload)
        return payload


@dataclass
class AudioOutputRequest:
    """A request to speak. A request is not an approval; the policy decides."""

    request_id: str
    text: str
    caller: str
    purpose: str
    voice: str | None = None

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "schema": "audio-output-request",
            "version": AUDIO_SCHEMA_VERSION,
            "request_id": self.request_id,
            "caller": self.caller,
            "purpose": self.purpose,
            "voice": self.voice,
            "char_count": len(self.text),
            **_frozen(),
        }
        payload["requested_text_hash"] = text_hash(self.text)
        payload["content_hash"] = audio_hash(payload)
        return payload


@dataclass
class AudioOutputDecision:
    decision: AudioOutputDecisionKind
    reason: str
    spoken_secret_finding: SpokenSecretFinding | None = None
    authority_claim_blocked: bool = False
    redacted_text: str | None = None

    @property
    def allowed(self) -> bool:
        return self.decision != AudioOutputDecisionKind.BLOCK

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "audio-output-decision",
            "decision": self.decision.value,
            "reason": self.reason,
            "allowed": self.allowed,
            "spoken_secret_finding": self.spoken_secret_finding.to_payload()
            if self.spoken_secret_finding
            else None,
            "authority_claim_blocked": self.authority_claim_blocked,
            **_frozen(),
        }


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


__all__ = [
    "AUDIO_SCHEMA_VERSION",
    "CANDIDATE_OPERATOR_CLASSES",
    "FIXTURE_RUN_ID",
    "FIXTURE_UTC",
    "AcousticInjectionAction",
    "AcousticPromptInjectionFinding",
    "AudioCaptureMode",
    "AudioInputEnvelope",
    "AudioOutputDecision",
    "AudioOutputDecisionKind",
    "AudioOutputRequest",
    "AudioSourceClass",
    "AudioTrustClass",
    "SpeechTranscript",
    "SpokenSecretFinding",
    "may_be_candidate_operator",
    "new_id",
    "trust_class_for_capture",
]
