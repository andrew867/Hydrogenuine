"""AIS-7 operator approval boundary."""

from __future__ import annotations


def operator_approval_required_for_patch() -> bool:
    return True


def repair_recommendation_is_not_patch_permission() -> bool:
    return True
