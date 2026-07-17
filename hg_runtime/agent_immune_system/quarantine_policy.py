"""AIS-3 quarantine policy validation."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.agent_immune_system.schemas import AISImmuneError, assert_neutral

FORBIDDEN_QUARANTINE_FLAGS = (
    "deletion_performed",
    "patch_authorized",
    "deletion_authorized",
    "marked_guilty",
    "phase19_hidden",
    "phase19_marked_green",
    "phase24_marked_full_green",
    "automatic_quarantine_enforced",
)


def validate_quarantine_policy(record: Mapping[str, Any]) -> None:
    assert_neutral(record)
    if record.get("quarantine_is_deletion"):
        raise AISImmuneError("quarantine_is_not_deletion")
    if record.get("original_preserved") is False:
        raise AISImmuneError("quarantine_must_preserve_original")
    if record.get("append_only") is False:
        raise AISImmuneError("quarantine_must_be_append_only")
    if record.get("metadata_only") is False:
        raise AISImmuneError("quarantine_must_be_metadata_only")
    for key in FORBIDDEN_QUARANTINE_FLAGS:
        if record.get(key):
            raise AISImmuneError(f"quarantine_forbidden:{key}")
