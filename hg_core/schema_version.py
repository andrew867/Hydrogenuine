"""
Schema version and minimal migration helper.

Ensures artifact dicts have a version field (v1); idempotent.
See docs/specs/packaging_spec.md.
"""

from typing import Any, Dict

SCHEMA_VERSION = 1


def ensure_schema_version(data: Dict[str, Any], expected: int = SCHEMA_VERSION) -> Dict[str, Any]:
    """
    Ensure data has version field; add if missing (v0 -> v1). Idempotent.

    Args:
        data: Artifact dict (e.g. timeseries row, performance-tracking).
        expected: Version to set if missing (default 1).

    Returns:
        Same dict (possibly with "version" added).
    """
    if not isinstance(data, dict):
        return data
    if "version" not in data:
        data = {**data, "version": expected}
    return data
