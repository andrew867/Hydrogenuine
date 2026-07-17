"""OpenVINO Watchtower errors — telemetry failures must not crash inference by default."""

from __future__ import annotations


class WatchtowerError(Exception):
    """Base watchtower error."""


class WatchtowerStrictError(WatchtowerError):
    """Raised when HG_OPENVINO_WATCHTOWER_STRICT=true and watchtower fails."""


class WatchtowerSchemaError(WatchtowerError):
    """Invalid event or snapshot shape."""


__all__ = ["WatchtowerError", "WatchtowerSchemaError", "WatchtowerStrictError"]
