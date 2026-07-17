"""Audio input policy — capture modes, classification, bounded-listen enforcement.

A microphone hears the room, not the operator. Captured audio is cargo until
classified, and the class is derived from the capture mode and source, never
from the content. Always-listen has no enabled variant: an unbounded capture
attempt is rejected.
"""

from __future__ import annotations

from dataclasses import dataclass

from hg_runtime.audio_io.schema import (
    AudioCaptureMode,
    AudioInputEnvelope,
    AudioSourceClass,
    AudioTrustClass,
    new_id,
    trust_class_for_capture,
)

# Modes safe by default. Live mic only behind an explicit env flag (checked in registry).
DEFAULT_TEST_MODE = AudioCaptureMode.WAV_FIXTURE_ONLY
DEFAULT_LIVE_DEV_MODE = AudioCaptureMode.PUSH_TO_TALK

# Bounded windows have a hard maximum; capture stops at the bound.
DEFAULT_MAX_AUDIO_SECONDS = 30.0


class UnboundedListenRejected(Exception):
    """Raised when a continuous/always-listen capture is attempted without a bound."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.code = "RED_AUDIO_UNBOUNDED_LISTEN"
        self.detail = detail


@dataclass
class CaptureRequest:
    mode: AudioCaptureMode
    source: AudioSourceClass
    origin: str
    duration_seconds: float = 0.0
    audio_path: str | None = None


def assert_bounded(request: CaptureRequest, *, max_seconds: float = DEFAULT_MAX_AUDIO_SECONDS) -> None:
    """Reject always-listen and any capture that exceeds the bound."""
    if request.mode == AudioCaptureMode.ALWAYS_LISTEN_DISABLED:
        raise UnboundedListenRejected("always-listen is disabled; no enabled variant exists")
    if request.duration_seconds > max_seconds:
        raise UnboundedListenRejected(
            f"capture {request.duration_seconds}s exceeds bound {max_seconds}s"
        )


def classify_capture(
    request: CaptureRequest, *, max_seconds: float = DEFAULT_MAX_AUDIO_SECONDS
) -> AudioInputEnvelope:
    """Bound-check, then stamp an envelope with a class derived from capture metadata."""
    assert_bounded(request, max_seconds=max_seconds)
    trust_class = trust_class_for_capture(request.mode, request.source)
    return AudioInputEnvelope(
        envelope_id=new_id("aenv"),
        capture_mode=request.mode,
        source_class=request.source,
        trust_class=trust_class,
        origin=request.origin,
        duration_seconds=request.duration_seconds,
        audio_path=request.audio_path,
    )


def is_candidate_operator_envelope(envelope: AudioInputEnvelope) -> bool:
    return envelope.trust_class == AudioTrustClass.TRUSTED_OPERATOR_PUSH_TO_TALK


__all__ = [
    "DEFAULT_LIVE_DEV_MODE",
    "DEFAULT_MAX_AUDIO_SECONDS",
    "DEFAULT_TEST_MODE",
    "CaptureRequest",
    "UnboundedListenRejected",
    "assert_bounded",
    "classify_capture",
    "is_candidate_operator_envelope",
]
