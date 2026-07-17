"""AIS-5 archive policy boundary."""

from __future__ import annotations


def archive_is_not_erasure() -> bool:
    return True


def removal_requires_operator_approval() -> bool:
    return True
