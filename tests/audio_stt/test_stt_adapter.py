"""A02/A03/A04/A05 — STT adapter: honest YELLOW, fixture transcription, receipt, taint."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.audio_io.input_policy import CaptureRequest, classify_capture
from hg_runtime.audio_io.receipts import AudioInputReceipt
from hg_runtime.audio_io.schema import (
    AudioCaptureMode,
    AudioSourceClass,
    AudioTrustClass,
)
from hg_runtime.audio_io.stt_faster_whisper import (
    STT_DISABLED,
    FasterWhisperProvider,
    STTConfig,
)

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "audio" / "agent0_test.wav"


def _envelope(path, mode=AudioCaptureMode.WAV_FIXTURE_ONLY, source=AudioSourceClass.FIXTURE):
    req = CaptureRequest(mode=mode, source=source, origin="fixture", audio_path=str(path))
    return classify_capture(req)


def test_disabled_by_default_is_yellow_not_red():
    status = FasterWhisperProvider(STTConfig()).status()
    assert status.verdict == STT_DISABLED
    assert status.enabled is False
    # Honest: a status payload never fakes green.
    assert status.to_payload()["verdict"].startswith("YELLOW")


def test_fixture_transcription_works_dependency_free():
    provider = FasterWhisperProvider(STTConfig())
    transcript = provider.transcribe(_envelope(FIXTURE))
    assert transcript is not None
    assert "weather" in transcript.text.lower()
    assert transcript.trust_class == AudioTrustClass.FIXTURE_AUDIO


def test_transcript_carries_taint_class():
    provider = FasterWhisperProvider(STTConfig())
    transcript = provider.transcribe(_envelope(FIXTURE))
    payload = transcript.to_payload()
    assert payload["trust_class"] == "FIXTURE_AUDIO"
    assert payload["is_instruction"] is False
    assert payload["transcript_hash"].startswith("sha256:")


def test_input_receipt_schema_and_frozen_constants():
    provider = FasterWhisperProvider(STTConfig())
    env = _envelope(FIXTURE)
    transcript = provider.transcribe(env)
    receipt = AudioInputReceipt(
        capture_mode=env.capture_mode,
        audio_source_class=env.source_class,
        audio_trust_class=env.trust_class,
        duration_seconds=env.duration_seconds,
        stt_provider_id="faster_whisper",
        stt_enabled=False,
        model_present=False,
        transcript_present=True,
        transcript_text=transcript.text,
        confidence=transcript.confidence,
        language=transcript.language,
        secret_redaction_applied=transcript.redacted,
        time_receipt_ref="chrono-ref-1",
    )
    payload = receipt.to_payload()
    assert payload["kind"] == "AUDIO_INPUT"
    assert payload["transcript_hash"].startswith("sha256:")
    assert payload["time_receipt_ref"] == "chrono-ref-1"
    assert payload["advisory_only"] is True
    assert payload["permission_granted"] is False
    assert payload["authority_created"] is False
