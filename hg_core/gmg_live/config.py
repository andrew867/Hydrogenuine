"""GMG-LIVE configuration — fake-sink only by default."""

from __future__ import annotations


def gmg_fake_sink_only() -> bool:
    return True


def gmg_refuse_authority_conversion() -> bool:
    return True


def gmg_refuse_live_grants() -> bool:
    return True


__all__ = [
    "gmg_fake_sink_only",
    "gmg_refuse_authority_conversion",
    "gmg_refuse_live_grants",
]
