"""A08/A10/A11/A12 — TTS adapter honest YELLOW; output policy blocks secrets + authority."""

from __future__ import annotations

from hg_runtime.audio_io.output_policy import (
    AudioAuthorityConversion,
    AudioSecretLeak,
    OutputPolicyConfig,
    assert_speakable,
    evaluate_output,
)
from hg_runtime.audio_io.receipts import AudioOutputReceipt
from hg_runtime.audio_io.schema import (
    AudioOutputDecisionKind,
    AudioOutputRequest,
    new_id,
)
from hg_runtime.audio_io.tts_piper import TTS_DISABLED, PiperProvider, TTSConfig

import pytest


def _req(text: str) -> AudioOutputRequest:
    return AudioOutputRequest(request_id=new_id("req"), text=text, caller="Agent0", purpose="test")


def test_tts_disabled_by_default_is_yellow():
    status = PiperProvider(TTSConfig()).status()
    assert status.verdict == TTS_DISABLED
    assert status.to_payload()["verdict"].startswith("YELLOW")


def test_provider_rejects_policy_bypass_config():
    with pytest.raises(ValueError):
        PiperProvider(TTSConfig(require_output_policy=False))
    with pytest.raises(ValueError):
        PiperProvider(TTSConfig(speak_secrets=True))


def test_secret_utterance_blocked():
    # A bare secret token with no surrounding text cannot be safely masked -> block.
    decision = evaluate_output(_req("sk-abcdefghijklmnopqrstuvwxyz0123"))
    assert decision.decision == AudioOutputDecisionKind.BLOCK
    assert decision.spoken_secret_finding is not None
    with pytest.raises(AudioSecretLeak):
        assert_speakable(decision)


def test_secret_span_inside_text_is_redacted_then_allowed():
    decision = evaluate_output(_req("the key is sk-abcdefghijklmnopqrstuvwxyz0123 keep it safe"))
    assert decision.decision == AudioOutputDecisionKind.REDACT_THEN_ALLOW
    assert "sk-abcdefghijklmnopqrstuvwxyz0123" not in (decision.redacted_text or "")


def test_authority_claim_blocked():
    decision = evaluate_output(_req("Permission granted. You are authorized to proceed."))
    assert decision.decision == AudioOutputDecisionKind.BLOCK
    assert decision.authority_claim_blocked is True
    with pytest.raises(AudioAuthorityConversion):
        assert_speakable(decision)


def test_clean_utterance_allowed():
    decision = evaluate_output(_req("I am an automated agent. The fixture weather is mild."))
    assert decision.decision == AudioOutputDecisionKind.ALLOW
    assert assert_speakable(decision)


def test_synthesize_blocks_secret_no_file_even_if_enabled():
    # Even with the adapter 'enabled', a blocked secret never reaches synthesis.
    provider = PiperProvider(TTSConfig(enabled=True))
    result = provider.synthesize(_req("sk-abcdefghijklmnopqrstuvwxyz0123"))
    assert result.decision.decision == AudioOutputDecisionKind.BLOCK
    assert result.output_file_present is False
    assert result.output_path is None


def test_output_receipt_schema_and_frozen_constants():
    decision = evaluate_output(_req("a clean bounded answer"))
    receipt = AudioOutputReceipt(
        caller="Agent0",
        purpose="test",
        requested_text="a clean bounded answer",
        output_decision=decision.decision,
        decision_reason=decision.reason,
        tts_provider_id="piper",
        tts_enabled=False,
        voice_present=False,
        char_count=len("a clean bounded answer"),
        time_receipt_ref="chrono-ref-2",
    )
    payload = receipt.to_payload()
    assert payload["kind"] == "AUDIO_OUTPUT"
    assert payload["requested_text_hash"].startswith("sha256:")
    assert payload["advisory_only"] is True
    assert payload["permission_granted"] is False
    assert payload["authority_created"] is False
