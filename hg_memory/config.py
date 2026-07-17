#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration for memory engine. Uses hg_lib.config for workspace paths.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from hg_lib.config import get_workspace_root


class MemoryEngineConfig:
    """Configuration for memory engine"""

    def __init__(
        self,
        workspace_root: Optional[Path] = None,
        config_file: Optional[Path] = None,
    ):
        """
        Initialize configuration.

        Args:
            workspace_root: Root of workspace (defaults to hg_lib.get_workspace_root)
            config_file: Path to config JSON file
        """
        self.workspace_root = (
            Path(workspace_root) if workspace_root else get_workspace_root()
        ).resolve()

        if config_file is None:
            config_file = (
                self.workspace_root / "memory" / "memory_engine_config.json"
            )

        self.config_file = Path(config_file)
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file or create default."""
        if self.config_file.exists():
            try:
                with open(
                    self.config_file, "r", encoding="utf-8"
                ) as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(
                    f"Warning: Could not load config from {self.config_file}: {e}"
                )
                return self._get_default_config()
        else:
            default_config = self._get_default_config()
            self._save_config(default_config)
            return default_config

    def _save_config(self, config: Dict[str, Any]) -> None:
        """Save configuration to JSON file."""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "languages": {
                "en": {"tokenizer": "english", "enabled": True},
                "zh": {"tokenizer": "jieba", "enabled": True},
                "ja": {"tokenizer": "jieba", "enabled": True},
                "ko": {"tokenizer": "jieba", "enabled": True},
            },
            "default_language": "en",
            "auto_detect": True,
            "fallback_to_english": True,
            "database": {
                "agent_memory_db": "agent_memory.db",
                "context_graph_db": "context_graph.db",
            },
            "indexing": {
                "chunk_size": 1000,
                "overlap": 200,
                "incremental": True,
            },
            "bose_integration": {
                "enabled": True,
                "agent_id": "memory-engine",
                "metrics_interval_seconds": 300,
            },
        }

    def get_agent_memory_db_path(self, agent_id: str) -> Path:
        """Get path to agent memory database."""
        db_name = self.config.get("database", {}).get(
            "agent_memory_db", "agent_memory.db"
        )
        return (
            self.workspace_root
            / "memory"
            / "automation"
            / f"automation-{agent_id}"
            / db_name
        )

    def get_context_graph_db_path(self) -> Path:
        """Get path to context graph database."""
        db_name = self.config.get("database", {}).get(
            "context_graph_db", "context_graph.db"
        )
        return self.workspace_root / "memory" / db_name

    def get_agent_memory_dir(self, agent_id: str) -> Path:
        """Get directory for agent memory files."""
        return (
            self.workspace_root / "memory" / "automation" / f"automation-{agent_id}"
        )

    def get_language_config(self, language_code: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a language."""
        return self.config.get("languages", {}).get(language_code)

    def is_language_enabled(self, language_code: str) -> bool:
        """Check if a language is enabled."""
        lang_config = self.get_language_config(language_code)
        return (
            lang_config is not None and lang_config.get("enabled", False)
        )

    def get_default_language(self) -> str:
        """Get default language code."""
        return self.config.get("default_language", "en")

    def get_indexing_config(self) -> Dict[str, Any]:
        """Get indexing configuration."""
        return self.config.get(
            "indexing",
            {"chunk_size": 1000, "overlap": 200, "incremental": True},
        )

    def get_bose_config(self) -> Dict[str, Any]:
        """Get BOSE integration configuration."""
        return self.config.get(
            "bose_integration",
            {
                "enabled": True,
                "agent_id": "memory-engine",
                "metrics_interval_seconds": 300,
            },
        )


_config: Optional[MemoryEngineConfig] = None


def get_config() -> MemoryEngineConfig:
    """Get global configuration instance."""
    global _config
    if _config is None:
        _config = MemoryEngineConfig()
    return _config


def set_config(config: MemoryEngineConfig) -> None:
    """Set global configuration instance (for testing)."""
    global _config
    _config = config
