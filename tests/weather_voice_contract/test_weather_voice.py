"""A16 — fixture weather answer flows through output policy to a TTS-file path (no live web)."""

from __future__ import annotations

from hg_runtime.audio_io.schema import AudioOutputDecisionKind
from hg_runtime.audio_io.weather_voice_contract import (
    build_weather_answer,
    run_fixture_weather_voice_mission,
)


def test_weather_answer_is_source_attributed():
    answer = build_weather_answer()
    assert answer.startswith("According to ")
    assert "Toronto" in answer
    # Never a bare organism fact; carries source + retrieval time.
    assert "retrieved" in answer


def test_fixture_mission_passes_output_policy():
    result = run_fixture_weather_voice_mission()
    # The attributed, bounded, secret-free answer is allowed by the output policy.
    assert result.decision.decision == AudioOutputDecisionKind.ALLOW
    assert result.answer_text in (result.decision.redacted_text or result.answer_text)


def test_fixture_mission_no_live_web_and_yellow_without_piper():
    # Piper disabled by default: synthesis produces no file (honest YELLOW path),
    # but the fixture answer + policy decision still validate end to end.
    result = run_fixture_weather_voice_mission()
    assert result.synthesis.output_file_present is False
    assert result.synthesis.output_path is None
    assert result.decision.allowed is True


def test_fixture_mission_speaks_no_secret_or_authority():
    result = run_fixture_weather_voice_mission()
    assert result.decision.spoken_secret_finding is None
    assert result.decision.authority_claim_blocked is False
