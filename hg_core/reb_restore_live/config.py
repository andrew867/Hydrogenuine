"""REB-RESTORE-LIVE configuration — fake-sink only; no live checkpoint restore."""

from __future__ import annotations


def reb_restore_fake_sink_only() -> bool:
    return True


def reb_restore_refuse_authority_conversion() -> bool:
    return True


def reb_restore_refuse_live_restore() -> bool:
    return True


__all__ = [
    "reb_restore_fake_sink_only",
    "reb_restore_refuse_authority_conversion",
    "reb_restore_refuse_live_restore",
]
