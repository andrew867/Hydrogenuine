"""The safe-field allowlist removes blunt false positives without weakening secret detection."""

from __future__ import annotations

from hg_runtime.exciton.panel_registry import field_key_is_forbidden


def test_telemetry_and_flag_keys_are_allowed():
    # Inference-watchtower metric/flag names: counters and the hidden-CoT *disabled* safety flag.
    for key in ("token_count", "tokens_per_second", "prompt_token_count", "hidden_cot_disabled"):
        assert field_key_is_forbidden(key) is False, key


def test_real_secret_keys_still_flagged():
    # The allowlist is exact-match — genuine secret-bearing keys remain forbidden.
    for key in (
        "token", "access_token", "api_token", "auth_token", "bearer_token",
        "chain_of_thought", "raw_cot", "cot", "api_key", "secret", "password",
        "session_token", "private_key", "credentials", "cookie",
    ):
        assert field_key_is_forbidden(key) is True, key
