"""P26 gap reconciliation convenience accessors for tests/gate."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.generalist_gap_reconciliation.p26_gap_mapper import build_p26_layer, replay_p26

__all__ = ["build_p26_layer", "replay_p26", "p26_layer"]


def p26_layer(root: Path) -> dict:
    return build_p26_layer(root)
