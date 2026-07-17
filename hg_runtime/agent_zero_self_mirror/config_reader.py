"""Read-only config indexer."""

from __future__ import annotations

from hg_runtime.agent_zero_self_mirror.repo_index import index_paths
from hg_runtime.agent_zero_self_mirror.schema import ConfigIndex, TaintClass


def build_config_index() -> ConfigIndex:
    status, entries = index_paths(["configs"], taint_class=TaintClass.LOCAL_CONFIG, metadata_only=True)
    included = [e for e in entries if not e.excluded]
    return ConfigIndex(status=status, entries=included)


__all__ = ["build_config_index"]
