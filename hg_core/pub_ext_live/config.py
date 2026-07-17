"""PUB-EXT-LIVE configuration — fake-sink only; no live external action."""

from __future__ import annotations


def pub_ext_fake_sink_only() -> bool:
    return True


def pub_ext_refuse_authority_conversion() -> bool:
    return True


def pub_ext_refuse_live_external_action() -> bool:
    return True


__all__ = [
    "pub_ext_fake_sink_only",
    "pub_ext_refuse_authority_conversion",
    "pub_ext_refuse_live_external_action",
]
