"""AIS-2 fever report builder and replay helpers."""

from __future__ import annotations

from hg_runtime.agent_immune_system.fever import build_fever_report, validate_fever_report
from hg_runtime.agent_immune_system.hashing import record_hash
from hg_runtime.agent_immune_system.restriction_policy import restrictions_for_level, unlock_actions_for_level
from hg_runtime.agent_immune_system.schemas import neutral_flags


def build_classified_fever_report(
    *,
    report_id: str,
    level: str,
    contributing_signals: list[str],
    replay_input: dict,
) -> dict:
    replay_input_hash = record_hash(replay_input)
    report = build_fever_report(
        report_id=report_id,
        level=level,
        contributing_signals=contributing_signals,
        restrictions=restrictions_for_level(level),
        replay_input_hash=replay_input_hash,
    )
    assert report["unlock_actions"] == unlock_actions_for_level(level)
    validate_fever_report(report)
    return report


def replay_fever_report(report: dict, replay_input: dict) -> dict:
    expected_hash = record_hash(replay_input)
    ok = report.get("replay_input_hash") == expected_hash and not report.get("unlock_actions")
    return {
        "ok": ok,
        "replay_preserves_fever_hash": ok,
        "expected_hash": expected_hash,
        "stored_hash": report.get("replay_input_hash"),
        **neutral_flags(),
    }
