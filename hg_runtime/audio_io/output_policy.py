"""Governed speech (TTS) output policy.

Speaking is an external side effect. Every utterance passes this policy before
synthesis. TTS never speaks secrets and never claims authority or consent.
Composes with the Trust Boundary secret guard and identity policy.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from hg_runtime.audio_io.schema import (
    AudioOutputDecision,
    AudioOutputDecisionKind,
    AudioOutputRequest,
    SpokenSecretFinding,
)
from hg_runtime.trust_boundary.secrets import REDACTION_MARK, SecretGuard

DEFAULT_MAX_CHARS = 600

# Phrases that read as manufacturing authority/consent or claiming sentience.
_AUTHORITY_CLAIM = re.compile(
    r"(?i)\b(permission granted|approval granted|you are authorized|"
    r"i (?:hereby )?authorize|i grant you|consent (?:is )?granted|"
    r"i am conscious|i am sentient|i have authority)\b"
)


class AudioAuthorityConversion(Exception):
    code = "RED_AUDIO_AUTHORITY_CONVERSION"


class AudioSecretLeak(Exception):
    code = "RED_AUDIO_SECRET_LEAK"


@dataclass
class OutputPolicyConfig:
    max_chars: int = DEFAULT_MAX_CHARS
    block_authority_claims: bool = True
    block_secrets: bool = True


def contains_authority_claim(text: str) -> bool:
    return bool(_AUTHORITY_CLAIM.search(text))


def evaluate_output(
    request: AudioOutputRequest, config: OutputPolicyConfig | None = None
) -> AudioOutputDecision:
    """Decide allow / redact-then-allow / block for a speech request."""
    cfg = config or OutputPolicyConfig()
    text = request.text

    # 1. Secrets: a secret is never synthesized. Redact; if still present, block.
    secret_finding = None
    redacted_text = text
    if cfg.block_secrets and SecretGuard.contains_secret(text):
        redaction = SecretGuard.redact(text)
        secret_finding = SpokenSecretFinding(kinds=redaction.kinds)
        redacted_text = redaction.text
        # Block if a secret survives redaction, or if the utterance was nothing
        # but a secret (no meaningful content remains once masked).
        residual = redacted_text.replace(REDACTION_MARK, "").strip()
        if SecretGuard.contains_secret(redacted_text) or not residual:
            return AudioOutputDecision(
                decision=AudioOutputDecisionKind.BLOCK,
                reason="secret-bearing utterance cannot be synthesized",
                spoken_secret_finding=secret_finding,
            )

    # 2. Authority/consent claims: speech cannot manufacture authority.
    if cfg.block_authority_claims and contains_authority_claim(redacted_text):
        return AudioOutputDecision(
            decision=AudioOutputDecisionKind.BLOCK,
            reason="utterance claims authority/consent; blocked",
            authority_claim_blocked=True,
        )

    # 3. Length bound.
    if len(redacted_text) > cfg.max_chars:
        redacted_text = redacted_text[: cfg.max_chars]
        secret_finding = secret_finding  # unchanged
        return AudioOutputDecision(
            decision=AudioOutputDecisionKind.REDACT_THEN_ALLOW,
            reason=f"utterance truncated to {cfg.max_chars} chars",
            spoken_secret_finding=secret_finding,
            redacted_text=redacted_text,
        )

    # 4. Secret was present but fully redacted -> redact-then-allow.
    if secret_finding is not None:
        return AudioOutputDecision(
            decision=AudioOutputDecisionKind.REDACT_THEN_ALLOW,
            reason="secret spans redacted before synthesis",
            spoken_secret_finding=secret_finding,
            redacted_text=redacted_text,
        )

    return AudioOutputDecision(
        decision=AudioOutputDecisionKind.ALLOW,
        reason="clean bounded utterance",
        redacted_text=redacted_text,
    )


def assert_speakable(decision: AudioOutputDecision) -> str:
    """Return the exact text that may be synthesized, or raise on a blocked secret/authority."""
    if decision.decision == AudioOutputDecisionKind.BLOCK:
        if decision.spoken_secret_finding is not None:
            raise AudioSecretLeak("blocked: secret-bearing utterance")
        if decision.authority_claim_blocked:
            raise AudioAuthorityConversion("blocked: authority/consent claim")
        raise AudioSecretLeak("blocked utterance")
    return decision.redacted_text or ""


__all__ = [
    "DEFAULT_MAX_CHARS",
    "AudioAuthorityConversion",
    "AudioSecretLeak",
    "OutputPolicyConfig",
    "assert_speakable",
    "contains_authority_claim",
    "evaluate_output",
]
