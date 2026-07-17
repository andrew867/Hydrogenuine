"""LEB-6 evidence fever hooks.

Aggregates evidence health findings into a fever report using the AIS fever
classifier and restriction policy. Fever restricts, never unlocks: a fever report
carries restrictions but no unlock actions.
"""

from __future__ import annotations

from hg_runtime.agent_immune_system.fever_classifier import classify_fever
from hg_runtime.agent_immune_system.restriction_policy import restrictions_for_level, unlock_actions_for_level
from hg_runtime.local_evidence_bridge.schemas import (
    assert_neutral,
    neutral_flags,
    record_hash,
)

RESTRICTING_LEVELS = ("YELLOW_FEVER", "RED_FEVER", "PANIC_FEVER")


def _as_signals(health_findings: list[dict]) -> list[dict]:
    return [
        {
            "signal_id": f["finding_id"],
            "severity": f["severity"],
            "signal_type": f["signal_type"],
            "record_hash": f["record_hash"],
        }
        for f in health_findings
    ]


def build_evidence_fever_report(health_findings: list[dict], *, report_id: str = "evfr-001") -> dict:
    level, contributing = classify_fever(_as_signals(health_findings))
    restrictions = restrictions_for_level(level)
    report = {
        "schema_version": "1",
        "record_type": "evidence_fever_report_v1",
        "report_id": report_id,
        "fever_level": level,
        "contributing_signal_ids": contributing,
        "restrictions": restrictions,
        "unlock_actions": unlock_actions_for_level(level),
        "fever_restricts": level in RESTRICTING_LEVELS,
        "fever_unlocks_action": False,
        "fever_is_authority": False,
        **neutral_flags(),
    }
    report["record_hash"] = record_hash(report)
    assert_neutral(report)
    return report
