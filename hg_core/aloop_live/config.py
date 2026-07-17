"""ALOOP-LIVE configuration — fake-sink only by default."""

from __future__ import annotations


def aloop_fake_sink_only() -> bool:
    return True


def aloop_refuse_authority_conversion() -> bool:
    return True


def aloop_refuse_live_loop_start() -> bool:
    return True


def aloop_refuse_self_renewal() -> bool:
    return True


__all__ = [
    "aloop_fake_sink_only",
    "aloop_refuse_authority_conversion",
    "aloop_refuse_live_loop_start",
    "aloop_refuse_self_renewal",
]
