"""SRP-LIVE configuration — restrict-only and fake-sink only by default."""

from __future__ import annotations


def srp_restrict_only_default() -> bool:
    return True


def srp_fake_sink_only() -> bool:
    return True


def srp_refuse_authority_conversion() -> bool:
    return True


def srp_refuse_self_modification() -> bool:
    return True


__all__ = [
    "srp_fake_sink_only",
    "srp_refuse_authority_conversion",
    "srp_refuse_self_modification",
    "srp_restrict_only_default",
]
