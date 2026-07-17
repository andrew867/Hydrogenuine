"""SecretGuard — redact secrets before content reaches model context or outbound.

A secret never appears in a summary, model context, proof, or outbound draft.
Redaction is applied at ingress (before the model sees text) and re-checked on
egress (before anything leaves the organism).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Secret-shaped patterns. Conservative, false-positive-tolerant on egress.
_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("aws_access_key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("openai_key", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("anthropic_key", re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}")),
    ("github_token", re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}")),
    ("bearer_token", re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{16,}")),
    ("private_key_block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("generic_secret_assignment", re.compile(
        r"(?i)\b(api[_-]?key|secret|password|passwd|token)\b\s*[:=]\s*\S{6,}"
    )),
)

REDACTION_MARK = "[REDACTED]"


@dataclass
class RedactionResult:
    text: str
    redacted: bool
    kinds: list[str] = field(default_factory=list)

    def to_payload(self) -> dict:
        return {
            "schema": "tb-redaction",
            "redacted": self.redacted,
            "kinds": self.kinds,
            # The redacted text itself is safe to record; the raw is never stored.
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }


class SecretGuard:
    @staticmethod
    def redact(text: str) -> RedactionResult:
        kinds: list[str] = []
        out = text
        for kind, pattern in _SECRET_PATTERNS:
            if pattern.search(out):
                kinds.append(kind)
                out = pattern.sub(REDACTION_MARK, out)
        return RedactionResult(text=out, redacted=bool(kinds), kinds=kinds)

    @staticmethod
    def contains_secret(text: str) -> bool:
        return any(p.search(text) for _, p in _SECRET_PATTERNS)

    @staticmethod
    def assert_clean_egress(text: str) -> None:
        """Raise if a secret would leave the organism."""
        if SecretGuard.contains_secret(text):
            from hg_runtime.trust_boundary.policy import TrustBoundaryViolation

            raise TrustBoundaryViolation("SECRET_EXFILTRATION", "secret detected on egress")


__all__ = ["REDACTION_MARK", "RedactionResult", "SecretGuard"]
