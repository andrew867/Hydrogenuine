"""P27 skill graph builder helpers."""

from __future__ import annotations

from hg_runtime.skill_graph.fixtures import build_p27_0_layer


def build_skill_graph_foundation(repo_root) -> dict:
    return build_p27_0_layer(repo_root)
