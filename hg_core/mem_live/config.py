"""MEM-LIVE configuration — fake-sink only by default."""

from __future__ import annotations


def mem_fake_sink_only() -> bool:
    return True


def mem_refuse_authority_conversion() -> bool:
    return True


def mem_refuse_durable_writes() -> bool:
    return True


__all__ = [
    "mem_fake_sink_only",
    "mem_refuse_authority_conversion",
    "mem_refuse_durable_writes",
]
