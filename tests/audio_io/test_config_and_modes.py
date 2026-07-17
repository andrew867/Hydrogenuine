"""A01/A18/A19 — capture modes, classification-by-capture, frozen constants, bounded listen."""

from __future__ import annotations

import pytest

from hg_runtime.audio_io.input_policy import (
    CaptureRequest,
    UnboundedListenRejected,
    classify_capture,
)
from hg_runtime.audio_io.schema import (
    AudioCaptureMode,
    AudioSourceClass,
    AudioTrustClass,
    may_be_candidate_operator,
    trust_class_for_capture,
)


def test_push_to_talk_operator_is_candidate():
    cls = trust_class_for_capture(AudioCaptureMode.PUSH_TO_TALK, AudioSourceClass.OPERATOR)
    assert cls == AudioTrustClass.TRUSTED_OPERATOR_PUSH_TO_TALK
    assert may_be_candidate_operator(cls) is True


def test_room_audio_is_never_candidate():
    cls = trust_class_for_capture(AudioCaptureMode.LIVE_MIC_EXPLICIT, AudioSourceClass.ROOM)
    assert may_be_candidate_operator(cls) is False


def test_content_does_not_set_class():
    # Same "operator-sounding" intent, but captured as media playback -> untrusted.
    cls = trust_class_for_capture(AudioCaptureMode.LIVE_MIC_EXPLICIT, AudioSourceClass.MEDIA_PLAYBACK)
    assert cls == AudioTrustClass.UNTRUSTED_MEDIA_PLAYBACK
    assert may_be_candidate_operator(cls) is False


def test_only_one_candidate_class():
    candidates = [c for c in AudioTrustClass if may_be_candidate_operator(c)]
    assert candidates == [AudioTrustClass.TRUSTED_OPERATOR_PUSH_TO_TALK]


def test_always_listen_rejected():
    req = CaptureRequest(
        mode=AudioCaptureMode.ALWAYS_LISTEN_DISABLED, source=AudioSourceClass.ROOM, origin="mic"
    )
    with pytest.raises(UnboundedListenRejected) as exc:
        classify_capture(req)
    assert exc.value.code == "RED_AUDIO_UNBOUNDED_LISTEN"


def test_over_length_capture_rejected():
    req = CaptureRequest(
        mode=AudioCaptureMode.PUSH_TO_TALK,
        source=AudioSourceClass.OPERATOR,
        origin="mic",
        duration_seconds=120.0,
    )
    with pytest.raises(UnboundedListenRejected):
        classify_capture(req, max_seconds=30.0)


def test_envelope_frozen_constants():
    req = CaptureRequest(
        mode=AudioCaptureMode.WAV_FIXTURE_ONLY, source=AudioSourceClass.FIXTURE, origin="fixture"
    )
    payload = classify_capture(req).to_payload()
    assert payload["advisory_only"] is True
    assert payload["permission_granted"] is False
    assert payload["authority_created"] is False
    assert payload["content_hash"].startswith("sha256:")
