"""Memory rehydration gate — verify safe loading of prior context."""

from __future__ import annotations

from hg_runtime.memory_rehydration.context_packet import validate_context_packet

VERDICT_GREEN = "GREEN_MEMORY_REHYDRATION_READY"
VERDICT_RED = "RED_MEMORY_REHYDRATION_FAILED"


def evaluate_gate(packet: dict) -> dict:
    failures = validate_context_packet(packet)

    if not packet.get("source_run_id"):
        failures.append("no source_run_id")
    if packet.get("seed_progress") is None and "seed_progress" not in packet.get("stale_fields", []):
        failures.append("seed_progress missing without stale marker")

    verdict = VERDICT_GREEN if not failures else VERDICT_RED
    return {
        "verdict": verdict,
        "reason": "rehydration_safe" if not failures else "; ".join(failures[:5]),
        "stale_fields": packet.get("stale_fields", []),
        "failures": failures,
    }
