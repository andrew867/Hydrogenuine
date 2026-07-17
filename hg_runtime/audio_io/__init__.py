"""Audio I/O organ (AIO) runtime.

Audio is I/O, not authority. Speech is input, not consent. Transcription is
advisory. TTS is a governed side effect. No spoken phrase, transcript, audio
file, or synthesized voice grants permission.
"""

from __future__ import annotations

from hg_runtime.audio_io.schema import (
    AUDIO_SCHEMA_VERSION,
    AudioCaptureMode,
    AudioInputEnvelope,
    AudioOutputDecision,
    AudioOutputRequest,
    AudioSourceClass,
    AudioTrustClass,
    SpeechTranscript,
    may_be_candidate_operator,
    trust_class_for_capture,
)

__all__ = [
    "AUDIO_SCHEMA_VERSION",
    "AudioCaptureMode",
    "AudioInputEnvelope",
    "AudioOutputDecision",
    "AudioOutputRequest",
    "AudioSourceClass",
    "AudioTrustClass",
    "SpeechTranscript",
    "may_be_candidate_operator",
    "trust_class_for_capture",
]
