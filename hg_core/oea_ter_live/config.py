"""OEA-TER-LIVE configuration — fake-sink only by default."""

from __future__ import annotations


def oea_ter_fake_sink_only() -> bool:
    return True


def oea_ter_refuse_authority_conversion() -> bool:
    return True


def oea_ter_refuse_live_actions() -> bool:
    return True


__all__ = [
    "oea_ter_fake_sink_only",
    "oea_ter_refuse_authority_conversion",
    "oea_ter_refuse_live_actions",
]
