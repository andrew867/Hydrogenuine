"""Phase 27 replay facade."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.memory_ledger.schemas import OperationControl
from hg_runtime.skill_graph.graph import SkillGraph, SkillReplayResult


def replay_skill_graph(path: Path, *, control: OperationControl | None = None) -> SkillReplayResult:
    return SkillGraph(path).replay(control=control)


__all__ = ["replay_skill_graph"]
