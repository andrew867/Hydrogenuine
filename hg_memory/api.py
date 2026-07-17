"""
Hydrogenuine Memory public API.

Callers import only from hg_memory. Phase B: imports from hg_memory.agent
and hg_memory (memory_indexer_job, extract_from_daily_notes).
See docs/specs/hg_memory_api_spec.md.
"""

from pathlib import Path
from typing import Any, Dict, List

try:
    from hg_memory.agent.agent_memory_search import get_wake_fts_snippets as _get_wake_fts_snippets
    from hg_memory.agent.entity_graph_db import get_recent_entities as _get_recent_entities
    from hg_memory.memory_indexer_job import (
        run_indexer_for_agent as _run_indexer_for_agent,
        run_indexing_job as _run_indexing_job,
    )
    from hg_memory.extract_from_daily_notes import run_extraction as _run_extraction
    _MEMORY_ENGINE_AVAILABLE = True
except ImportError:
    _MEMORY_ENGINE_AVAILABLE = False
    _get_wake_fts_snippets = None  # type: ignore
    _get_recent_entities = None  # type: ignore
    _run_indexer_for_agent = None  # type: ignore
    _run_indexing_job = None  # type: ignore
    _run_extraction = None  # type: ignore


def search_memory(
    workspace_root: Path,
    agent_id: str,
    max_snippets: int = 5,
    days: int = 7,
) -> List[Dict[str, Any]]:
    """
    FTS snippets for wake context (session_manager, compacted memory).

    Returns list of dicts with keys: snippet, date, file_path.
    """
    if not _MEMORY_ENGINE_AVAILABLE:
        return []
    return _get_wake_fts_snippets(
        Path(workspace_root), agent_id, max_snippets=max_snippets, days=days
    )


def get_recent_entities(
    workspace_root: Path,
    agent_id: str,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """
    Recent entities from entity graph for wake context.

    Returns list of entity dicts (id, type, name, summary_excerpt, updated_at).
    """
    if not _MEMORY_ENGINE_AVAILABLE:
        return []
    return _get_recent_entities(Path(workspace_root), agent_id, limit=limit)


def index_agent(workspace_root: Path, agent_id: str) -> None:
    """
    Run agent memory indexer for one agent (FTS + optional entity graph).

    Used after GC so the index stays up to date. Incremental: only changed
    files are re-indexed (file_hash in agent_memory_metadata).
    """
    if not _MEMORY_ENGINE_AVAILABLE:
        return
    _run_indexer_for_agent(Path(workspace_root), agent_id)


def run_indexing_job() -> Dict[str, Any]:
    """
    Run indexing for all agents (cron entry point).

    Returns dict with: timestamp, agents_processed, total_indexed, total_errors, per_agent.
    """
    if not _MEMORY_ENGINE_AVAILABLE:
        return {
            "timestamp": "",
            "agents_processed": 0,
            "total_indexed": 0,
            "total_errors": 0,
            "per_agent": {},
        }
    return _run_indexing_job()


def run_extraction(
    workspace_root: Path,
    agent_id: str,
    days: int = 7,
) -> Dict[str, Any]:
    """
    Extract from daily notes to life/ staging (optional after sleep cycle).

    Returns:
        {"suggested": N, "staging_path": str, "errors": list}
    """
    if not _MEMORY_ENGINE_AVAILABLE or _run_extraction is None:
        return {"suggested": 0, "staging_path": "", "errors": []}
    return _run_extraction(Path(workspace_root), agent_id, days=days)
