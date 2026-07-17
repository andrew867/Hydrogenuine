"""Read-only source module indexer."""

from __future__ import annotations

from hg_runtime.agent_zero_self_mirror.repo_index import index_paths
from hg_runtime.agent_zero_self_mirror.schema import IndexStatus, SourceModuleIndex, TaintClass


def build_source_index(*, refresh: bool = False) -> SourceModuleIndex:
    del refresh  # in-memory; refresh rebuilds each call
    status, entries = index_paths(
        [
            "hg_runtime/agent_zero_self_mirror",
            "hg_runtime/agent0_dev_boot",
            "hg_runtime/chrono",
            "hg_runtime/external_start_anchor",
            "hg_runtime/external_witness_journal",
            "hg_runtime/wake_refresh",
            "hg_runtime/tool_capability_fabric",
            "hg_runtime/trust_boundary",
            "hg_runtime/audio_io",
            "hg_runtime/will_module",
        ],
        taint_class=TaintClass.LOCAL_SOURCE,
    )
    included = [e for e in entries if not e.excluded]
    return SourceModuleIndex(status=status, entries=included, root="hg_runtime")


def find_module_for_topic(topic: str) -> list[str]:
    topic_l = topic.lower().replace(" ", "_").replace("-", "_")
    idx = build_source_index()
    hits = []
    for e in idx.entries:
        if topic_l in e.path.lower() or (e.module_guess and topic_l in e.module_guess.lower()):
            hits.append(e.path)
    return hits[:10]


__all__ = ["build_source_index", "find_module_for_topic"]
