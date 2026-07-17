"""Read-only documentation indexer."""

from __future__ import annotations

from hg_runtime.agent_zero_self_mirror.repo_index import index_paths
from hg_runtime.agent_zero_self_mirror.schema import DocumentationIndex, TaintClass


def build_docs_index() -> DocumentationIndex:
    status, entries = index_paths(
        ["docs/planning", "docs/reports/phases"],
        taint_class=TaintClass.LOCAL_DOCS,
        metadata_only=True,
    )
    included = [e for e in entries if not e.excluded]
    return DocumentationIndex(status=status, entries=included)


def find_docs_for_topic(topic: str) -> list[str]:
    topic_l = topic.lower()
    idx = build_docs_index()
    return [e.path for e in idx.entries if topic_l in e.path.lower()][:10]


__all__ = ["build_docs_index", "find_docs_for_topic"]
