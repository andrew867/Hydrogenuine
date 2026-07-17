#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Automatic indexing job for memory engine.

Background job that indexes new daily logs and agent data periodically.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

from hg_memory.config import get_config
from hg_memory.agent.agent_memory_indexer import AgentMemoryIndexer

from hg_memory.error_handling import retry_on_failure
from hg_memory.performance import monitor_performance


def run_indexer_for_agent(workspace_root: Path, agent_id: str) -> None:
    """
    Run agent memory FTS indexer for one agent with the given workspace root.
    Used by memory-maintenance after GC so the index stays up to date.
    """
    config = get_config()
    orig_workspace = config.workspace_root
    try:
        config.workspace_root = Path(workspace_root).resolve()
        indexer = AgentMemoryIndexer(agent_id)
        indexer.index_all()
    finally:
        config.workspace_root = orig_workspace


@monitor_performance("indexing_job")
def index_all_agents() -> Dict[str, Dict[str, int]]:
    """
    Index all agents' memory.

    Returns:
        Dictionary mapping agent_id to indexing statistics
    """
    config = get_config()
    workspace_root = config.workspace_root
    automation_dir = workspace_root / "memory" / "automation"

    if not automation_dir.exists():
        return {}

    results = {}

    # Get all agent directories
    agent_dirs = [
        item for item in automation_dir.iterdir()
        if item.is_dir() and item.name.startswith("automation-")
    ]

    for agent_dir in agent_dirs:
        agent_id = agent_dir.name.replace("automation-", "", 1)

        try:
            indexer = AgentMemoryIndexer(agent_id)
            stats = indexer.index_all()
            results[agent_id] = stats
            print(f"[OK] Indexed {agent_id}: {stats['indexed']} files, {stats['errors']} errors")
        except Exception as e:
            print(f"[ERROR] Failed to index {agent_id}: {e}")
            results[agent_id] = {"indexed": 0, "skipped": 0, "errors": 1}

    return results


@retry_on_failure(max_retries=3, delay=5.0)
def run_indexing_job() -> Dict[str, Any]:
    """
    Run indexing job (main entry point for cron).

    Returns:
        Dictionary with job results
    """
    print(f"[{datetime.now().isoformat()}] Starting memory engine indexing job...")

    results = index_all_agents()

    total_indexed = sum(r.get("indexed", 0) for r in results.values())
    total_errors = sum(r.get("errors", 0) for r in results.values())

    print(f"[{datetime.now().isoformat()}] Indexing job complete: {total_indexed} files indexed, {total_errors} errors")

    return {
        "timestamp": datetime.now().isoformat(),
        "agents_processed": len(results),
        "total_indexed": total_indexed,
        "total_errors": total_errors,
        "per_agent": results,
    }


if __name__ == "__main__":
    """CLI entry point for cron job"""
    try:
        results = run_indexing_job()
        sys.exit(0 if results["total_errors"] == 0 else 1)
    except Exception as e:
        print(f"[ERROR] Indexing job failed: {e}")
        sys.exit(1)
