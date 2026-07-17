"""RIB-SPAWN-LIVE configuration — fake-sink only by default."""

from __future__ import annotations


def rib_spawn_fake_sink_only() -> bool:
    return True


def rib_spawn_refuse_authority_conversion() -> bool:
    return True


def rib_spawn_refuse_live_spawn() -> bool:
    return True


def rib_spawn_refuse_inherited_authority() -> bool:
    return True


__all__ = [
    "rib_spawn_fake_sink_only",
    "rib_spawn_refuse_authority_conversion",
    "rib_spawn_refuse_inherited_authority",
    "rib_spawn_refuse_live_spawn",
]
