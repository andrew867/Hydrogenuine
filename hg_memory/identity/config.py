#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration for identity graph system.

Extends memory engine config with identity-specific settings.
"""

from pathlib import Path
from typing import Optional

from hg_memory.shared import get_config


def get_identity_graph_db_path(agent_id: Optional[str] = None) -> Path:
    """
    Get path to identity graph database.

    Args:
        agent_id: Optional agent ID. If None, returns global identity graph path.

    Returns:
        Path to identity graph database
    """
    config = get_config()
    workspace_root = config.workspace_root

    if agent_id:
        # Per-agent identity graph
        return workspace_root / "memory" / "automation" / f"automation-{agent_id}" / "identity_graph.db"
    else:
        # Global identity graph
        return workspace_root / "memory" / "identity_graph.db"
