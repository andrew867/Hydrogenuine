"""OUX-LIVE configuration — fixture-only by default."""

from __future__ import annotations


def oux_static_fixtures_only() -> bool:
    return True


def oux_refuse_authority_conversion() -> bool:
    return True


def oux_refuse_live_external_action() -> bool:
    return True


__all__ = [
    "oux_refuse_authority_conversion",
    "oux_refuse_live_external_action",
    "oux_static_fixtures_only",
]
