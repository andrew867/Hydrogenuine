"""Runtime evidence path labels (CT-03 PAR)."""

from __future__ import annotations

RUNTIME_PATH_LABELS = frozenset(
    {
        "demo_phase0",
        "phase1_integrated",
        "dep_appliance",
        "opt_in_srp",
        "opt_in_oea",
        "opt_in_live_cognition",
    }
)


def is_runtime_path_id(path_id: str | None) -> bool:
    if not path_id:
        return False
    if path_id in RUNTIME_PATH_LABELS:
        return True
    return path_id.startswith("mixed:")


def validate_runtime_path_id(path_id: str | None) -> str:
    if not path_id:
        raise ValueError("missing path_id")
    if not is_runtime_path_id(path_id):
        raise ValueError(f"unknown runtime path_id: {path_id!r}")
    return path_id


__all__ = ["RUNTIME_PATH_LABELS", "is_runtime_path_id", "validate_runtime_path_id"]
