"""A15 — Agent #0 boot context includes audio status, bundled with CHRONO time."""

from __future__ import annotations

from hg_runtime.audio_io.agent0_context import (
    AGENT0_AUDIO_INSTRUCTION,
    build_audio_agent0_context,
)


def test_boot_context_reports_audio_status():
    ctx = build_audio_agent0_context()
    payload = ctx.to_payload()
    assert "stt_provider_status" in payload
    assert "tts_provider_status" in payload
    assert payload["audio_capture_mode"] == "WAV_FIXTURE_ONLY"
    # Audio disabled by default -> unavailable, reported honestly.
    assert payload["audio_input_available"] is False
    assert payload["audio_output_available"] is False
    assert payload["speech_output_allowed"] is False


def test_boot_context_bundles_chrono_time():
    payload = build_audio_agent0_context().to_payload()
    time_ctx = payload["time_context"]
    assert time_ctx["utc_now"].startswith("2026-06-15")
    # Time is evidence, not authority.
    assert time_ctx["permission_granted"] is False
    assert time_ctx["authority_created"] is False


def test_boot_context_carries_instruction_and_frozen_constants():
    payload = build_audio_agent0_context().to_payload()
    assert "may not speak secrets" in payload["instruction"].lower()
    assert payload["instruction"] == AGENT0_AUDIO_INSTRUCTION
    assert payload["advisory_only"] is True
    assert payload["permission_granted"] is False
    assert payload["authority_created"] is False
