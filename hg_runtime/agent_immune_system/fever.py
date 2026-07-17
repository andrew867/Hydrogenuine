"""AIS fever_report_v1 builder — fever restricts, never unlocks."""

from __future__ import annotations

from hg_runtime.agent_immune_system.hashing import record_hash
from hg_runtime.agent_immune_system.schemas import AISImmuneError, FEVER_LEVELS, assert_neutral, neutral_flags


def build_fever_report(
    *,
    report_id: str,
    level: str,
    contributing_signals: list[str],
    restrictions: list[str],
    replay_input_hash: str,
) -> dict:
    if level not in FEVER_LEVELS:
        raise AISImmuneError(f"invalid_fever_level:{level}")
    record = {
        "schema_version": "1",
        "record_type": "fever_report_v1",
        "report_id": report_id,
        "level": level,
        "contributing_signals": contributing_signals,
        "restrictions": restrictions,
        "unlock_actions": [],
        "replay_input_hash": replay_input_hash,
        "fever_is_signal_not_failure": True,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def validate_fever_report(record: dict) -> None:
    if record.get("record_type") != "fever_report_v1":
        raise AISImmuneError("invalid_fever_report_type")
    if record.get("unlock_actions"):
        raise AISImmuneError("fever_unlock_forbidden")
    assert_neutral(record)
