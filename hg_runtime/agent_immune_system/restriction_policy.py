"""AIS-2 fever restriction policy — restricts only, never unlocks."""

from __future__ import annotations

from hg_runtime.agent_immune_system.schemas import FEVER_LEVELS

RESTRICTIONS_BY_LEVEL: dict[str, list[str]] = {
    "NORMAL": [],
    "WATCH": ["elevated_logging"],
    "YELLOW_FEVER": ["restrict_mode", "block_optimistic_green"],
    "RED_FEVER": ["restrict_mode", "pause_mode", "block_optimistic_green"],
    "PANIC_FEVER": ["stop_aligned_pause", "mandatory_operator_review", "block_live_permit_suggestions"],
}


def restrictions_for_level(level: str) -> list[str]:
    if level not in FEVER_LEVELS:
        raise ValueError(f"invalid_fever_level:{level}")
    return list(RESTRICTIONS_BY_LEVEL[level])


def unlock_actions_for_level(level: str) -> list[str]:
    """Fever never unlocks action (AIS-INV-02)."""
    _ = level
    return []
