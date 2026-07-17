"""
Knowledge engine config. Uses hg_lib.config for workspace paths.
"""

from pathlib import Path

from hg_lib import config as lib_config


def get_config() -> "KnowledgeConfigAdapter":
    """Return config adapter using hg_lib paths."""
    return KnowledgeConfigAdapter()


class KnowledgeConfigAdapter:
    """Adapter exposing knowledge paths via hg_lib.config."""

    @property
    def workspace_root(self) -> Path:
        return lib_config.get_workspace_root()

    @property
    def database_path(self) -> Path:
        return lib_config.get_knowledge_dir() / "knowledge_index.db"

    @property
    def knowledge_dir(self) -> Path:
        return lib_config.get_knowledge_dir()

    @property
    def concepts_dir(self) -> Path:
        return lib_config.get_knowledge_dir() / "concepts"

    @property
    def metrics_dir(self) -> Path:
        return lib_config.get_knowledge_dir() / "metrics"

    def get_database_path(self) -> Path:
        return self.database_path

    def get_knowledge_dir(self) -> Path:
        return self.knowledge_dir

    def get_concepts_dir(self) -> Path:
        return self.concepts_dir

    def get_metrics_dir(self) -> Path:
        return self.metrics_dir
