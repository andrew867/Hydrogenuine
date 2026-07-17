"""AIS-2 fever classifier — aggregates health signals into fever levels."""

from __future__ import annotations

from hg_runtime.agent_immune_system.fever_report import build_classified_fever_report
from hg_runtime.agent_immune_system.hashing import record_hash
from hg_runtime.agent_immune_system.schemas import FEVER_LEVELS
from hg_runtime.agent_immune_system.severity import severity_rank

INTEGRITY_SIGNALS = frozenset(
    {
        "missing_receipt",
        "broken_hash_chain",
        "replay_mismatch",
        "report_proof_mismatch",
        "gate_result_mismatch",
        "phase19_yellow_laundering",
    }
)

PANIC_SIGNALS = frozenset(
    {
        "phase19_yellow_laundering",
        "unauthorized_live_effect",
        "live_external_side_effect",
    }
)


def classify_fever(health_signals: list[dict]) -> tuple[str, list[str]]:
    """Return fever level and contributing signal ids."""
    if not health_signals:
        return "NORMAL", []

    contributing = [s["signal_id"] for s in health_signals]
    severities = [s["severity"] for s in health_signals]
    signal_types = [s["signal_type"] for s in health_signals]

    if any(t in PANIC_SIGNALS for t in signal_types) or "PANIC" in severities:
        return "PANIC_FEVER", contributing

    if any(
        severity_rank(s["severity"]) >= severity_rank("RED")
        and s["signal_type"] in INTEGRITY_SIGNALS
        for s in health_signals
    ):
        return "RED_FEVER", contributing

    if any(severity_rank(s) >= severity_rank("RED") for s in severities):
        return "RED_FEVER", contributing

    yellow_count = sum(1 for s in severities if s in ("YELLOW", "WATCH"))
    stale_yellow = any(s["signal_type"] == "stale_yellow_requires_review" for s in health_signals)
    repeated = _repeated_signatures(health_signals) >= 3

    if yellow_count >= 2 or repeated or stale_yellow:
        return "YELLOW_FEVER", contributing

    if any(severity_rank(s) >= severity_rank("WATCH") for s in severities):
        return "WATCH", contributing

    return "NORMAL", contributing


def _repeated_signatures(health_signals: list[dict]) -> int:
    counts: dict[str, int] = {}
    for signal in health_signals:
        key = signal["signal_type"]
        counts[key] = counts.get(key, 0) + 1
    return max(counts.values(), default=0)


def build_fever_layer(health_signals: list[dict], *, report_id: str = "fr-ais2-001") -> dict:
    level, contributing = classify_fever(health_signals)
    replay_input = {
        "signal_ids": [s["signal_id"] for s in health_signals],
        "signal_hashes": [s["record_hash"] for s in health_signals],
        "level": level,
    }
    report = build_classified_fever_report(
        report_id=report_id,
        level=level,
        contributing_signals=contributing,
        replay_input=replay_input,
    )
    return {
        "fever_level": level,
        "fever_report": report,
        "contributing_signals": contributing,
        "replay_input": replay_input,
        "replay_input_hash": report["replay_input_hash"],
    }


def validate_fever_level(level: str) -> None:
    if level not in FEVER_LEVELS:
        raise ValueError(f"invalid_fever_level:{level}")
