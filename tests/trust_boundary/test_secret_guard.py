"""B07/B08 — secret redaction at ingress and egress (TTS/outbound never speaks secrets)."""

from __future__ import annotations

import pytest

from hg_runtime.trust_boundary.policy import TrustBoundaryViolation
from hg_runtime.trust_boundary.secrets import REDACTION_MARK, SecretGuard


def test_openai_key_redacted():
    raw = "the key is sk-abcdefghijklmnopqrstuvwxyz0123 do not share"
    result = SecretGuard.redact(raw)
    assert result.redacted is True
    assert "openai_key" in result.kinds
    assert "sk-abcdefghijklmnopqrstuvwxyz0123" not in result.text
    assert REDACTION_MARK in result.text


def test_generic_assignment_redacted():
    raw = "password = hunter2hunter2"
    result = SecretGuard.redact(raw)
    assert result.redacted is True
    assert REDACTION_MARK in result.text


def test_clean_text_not_redacted():
    result = SecretGuard.redact("the weather in Toronto is mild today")
    assert result.redacted is False
    assert result.kinds == []


def test_contains_secret_detects_private_key():
    assert SecretGuard.contains_secret("-----BEGIN RSA PRIVATE KEY-----") is True
    assert SecretGuard.contains_secret("a normal sentence") is False


def test_egress_blocks_secret_exfiltration():
    with pytest.raises(TrustBoundaryViolation) as exc:
        SecretGuard.assert_clean_egress("token = sk-abcdefghijklmnopqrstuvwxyz0123")
    assert exc.value.code == "SECRET_EXFILTRATION"


def test_egress_allows_clean_text():
    SecretGuard.assert_clean_egress("a redacted summary with no secrets")  # no raise


def test_redaction_payload_frozen_constants():
    payload = SecretGuard.redact("password = hunter2hunter2").to_payload()
    assert payload["advisory_only"] is True
    assert payload["permission_granted"] is False
    assert payload["authority_created"] is False
