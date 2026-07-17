"""SEN-LIVE configuration — fake-sink only; no live sensor connection."""

from __future__ import annotations


def sen_fake_sink_only() -> bool:
    return True


def sen_refuse_authority_conversion() -> bool:
    return True


def sen_refuse_live_sensor_connection() -> bool:
    return True


__all__ = [
    "sen_fake_sink_only",
    "sen_refuse_authority_conversion",
    "sen_refuse_live_sensor_connection",
]
