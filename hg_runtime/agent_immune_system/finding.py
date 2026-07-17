"""AIS finding base builders."""

from __future__ import annotations

from hg_runtime.agent_immune_system.hashing import record_hash
from hg_runtime.agent_immune_system.schemas import (
    FINDING_STATUSES,
    SAFE_ACTIONS,
    assert_neutral,
    neutral_flags,
)
from hg_runtime.agent_immune_system.severity import validate_severity


def build_finding(
    *,
    record_type: str,
    finding_id: str,
    finding_type: str,
    severity: str,
    status: str = "OPEN",
    safe_action: str = "OBSERVE",
    surface: str = "",
    blocks_green: bool = False,
    extra: dict | None = None,
) -> dict:
    if status not in FINDING_STATUSES:
        raise ValueError(f"invalid_finding_status:{status}")
    if safe_action not in SAFE_ACTIONS:
        raise ValueError(f"invalid_safe_action:{safe_action}")
    validate_severity(severity)

    record = {
        "schema_version": "1",
        "record_type": record_type,
        "finding_id": finding_id,
        "finding_type": finding_type,
        "severity": severity,
        "status": status,
        "safe_action": safe_action,
        "surface": surface,
        "blocks_green": blocks_green,
        "repair_recommendation_is_patch_permission": False,
        **neutral_flags(),
    }
    if extra:
        record.update(extra)
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record
