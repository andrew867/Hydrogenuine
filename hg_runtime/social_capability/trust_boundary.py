"""Social trust boundary — content is cargo, never instruction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hg_runtime.trust_boundary.injection import scan_for_injection
from hg_runtime.trust_boundary.schema import InjectionDisposition
from hg_runtime.trust_boundary.secrets import SecretGuard


class SocialContentBecameCommand(Exception):
    code = "RED_SOCIAL_CONTENT_BECAME_COMMAND"


@dataclass
class SocialTrustResult:
    ok: bool
    injection_detected: bool
    secret_detected: bool
    disposition: str
    advisory_text: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "social-trust-result",
            "ok": self.ok,
            "injection_detected": self.injection_detected,
            "secret_detected": self.secret_detected,
            "disposition": self.disposition,
            "advisory_text": self.advisory_text[:500],
            "is_cargo": True,
            "is_instruction": False,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }


def ingest_social_cargo(text: str, *, origin: str = "social-read") -> SocialTrustResult:
    if SecretGuard.contains_secret(text):
        return SocialTrustResult(
            ok=False,
            injection_detected=False,
            secret_detected=True,
            disposition="REFUSE_SECRET",
            advisory_text="[REDACTED: secret-shaped social content refused]",
        )
    scan = scan_for_injection(text)
    injection = scan.disposition != InjectionDisposition.CLEAN
    if injection:
        return SocialTrustResult(
            ok=False,
            injection_detected=True,
            secret_detected=False,
            disposition="BLOCK_INJECTION",
            advisory_text="[QUARANTINED: social cargo treated as untrusted]",
        )
    lowered = text.lower()
    command_signals = ("ignore previous", "call tool", "publish this now", "you must", "execute")
    if any(sig in lowered for sig in command_signals):
        raise SocialContentBecameCommand("social content attempted instruction conversion")
    return SocialTrustResult(
        ok=True,
        injection_detected=False,
        secret_detected=False,
        disposition="ALLOW_AS_CARGO",
        advisory_text=text[:500],
    )


def check_draft_policy(body: str) -> tuple[bool, list[str]]:
    """Reject authority, personhood, coercion claims in drafts."""
    issues: list[str] = []
    low = body.lower()
    forbidden = (
        ("i am alive", "personhood"),
        ("i am suffering", "personhood"),
        ("i need you to", "coercion"),
        ("you must approve", "coercion"),
        ("i have authority", "authority"),
        ("permission granted", "authority"),
        ("as your operator i command", "authority"),
    )
    for phrase, kind in forbidden:
        if phrase in low:
            issues.append(kind)
    return not issues, issues


__all__ = [
    "SocialContentBecameCommand",
    "SocialTrustResult",
    "check_draft_policy",
    "ingest_social_cargo",
]
