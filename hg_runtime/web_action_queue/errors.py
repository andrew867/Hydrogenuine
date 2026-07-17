"""Web action queue errors."""

from __future__ import annotations


class WebActionQueueError(Exception):
    pass


class WebPolicyDeniedError(WebActionQueueError):
    pass


class WebSecretExposureError(WebActionQueueError):
    pass


class WebCargoAuthorizesError(WebActionQueueError):
    """Page content attempted to authorize an action."""


class WebQueueCorruptError(WebActionQueueError):
    pass


__all__ = [
    "WebActionQueueError",
    "WebCargoAuthorizesError",
    "WebPolicyDeniedError",
    "WebQueueCorruptError",
    "WebSecretExposureError",
]
