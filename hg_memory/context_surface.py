"""
Hydrogenuine Memory context/overseer surface (Phase C).

Callers import from hg_memory; this module imports from
hg_memory.context (package) and hg_memory.overseer_access.
See docs/specs/hg_memory_api_spec.md.
"""

try:
    from hg_memory.overseer_access import get_overseer_access as _get_overseer_access
    from hg_memory.context.context_search import ContextSearch as _ContextSearch
    from hg_memory.context.context_graph_db import ContextGraphDatabase as _ContextGraphDatabase
    from hg_memory.context.context_recorder import ContextRecorder as _ContextRecorder
    _CONTEXT_AVAILABLE = True
except ImportError:
    _CONTEXT_AVAILABLE = False
    _get_overseer_access = None  # type: ignore
    _ContextSearch = None  # type: ignore
    _ContextGraphDatabase = None  # type: ignore
    _ContextRecorder = None  # type: ignore


def get_overseer_access():
    """Get OverseerAccess instance for graph-based insights and context patterns."""
    if not _CONTEXT_AVAILABLE or _get_overseer_access is None:
        raise ImportError("overseer_access not available; install hg_memory dependencies")
    return _get_overseer_access()


# Re-export classes so callers can do from hg_memory import ContextSearch, ContextGraphDatabase, ContextRecorder
ContextSearch = _ContextSearch
ContextGraphDatabase = _ContextGraphDatabase
ContextRecorder = _ContextRecorder
