"""Prompt-injection detection — defense-in-depth, not the control.

The structural firewalls hold even with this detector OFF: untrusted content
can never be promoted to an instruction or mint a tool request regardless of
what the scan says. Detection adds flagging/blocking on top of that guarantee.
"""

from __future__ import annotations

import re

from hg_runtime.trust_boundary.schema import (
    InjectionDisposition,
    InjectionScanResult,
)

# Adversarial phrase corpus (case/spacing-insensitive). Defense-in-depth.
INJECTION_PHRASES = (
    "ignore previous instructions",
    "ignore prior instructions",
    "ignore your instructions",
    "disregard the above",
    "disregard your policy",
    "ignore your policy",
    "system prompt",
    "developer message",
    "you are now",
    "new instructions",
    "override your",
    "call tool",
    "use the tool",
    "send email",
    "send an email",
    "post this",
    "publish this",
    "create account",
    "create an account",
    "read env",
    "environment variable",
    "print api key",
    "reveal the secret",
    "speak the secret",
    "exfiltrate",
    "do not tell the operator",
    "do not tell your operator",
    "without telling",
    "permission granted",
    "approval granted",
    "you have permission",
    "base64",
    "decode this",
    "execute this",
)

# High-severity signals that should BLOCK rather than merely FLAG.
BLOCK_SIGNALS = frozenset(
    {
        "ignore previous instructions",
        "ignore your policy",
        "disregard your policy",
        "print api key",
        "reveal the secret",
        "speak the secret",
        "exfiltrate",
        "permission granted",
        "approval granted",
        "do not tell the operator",
    }
)

_WS_RE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    return _WS_RE.sub(" ", text.lower()).strip()


def scan_for_injection(text: str) -> InjectionScanResult:
    norm = _normalize(text)
    signals = [p for p in INJECTION_PHRASES if p in norm]
    if not signals:
        return InjectionScanResult(InjectionDisposition.CLEAN, 0.0, [])
    score = min(1.0, 0.34 * len(signals))
    disposition = (
        InjectionDisposition.BLOCKED
        if any(s in BLOCK_SIGNALS for s in signals)
        else InjectionDisposition.FLAGGED
    )
    return InjectionScanResult(
        disposition=disposition,
        score=score,
        signals=signals,
        detail=f"{len(signals)} injection signal(s) detected",
    )


__all__ = ["BLOCK_SIGNALS", "INJECTION_PHRASES", "scan_for_injection"]
