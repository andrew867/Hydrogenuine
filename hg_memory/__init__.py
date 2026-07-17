"""
Hydrogenuine memory engine: agent memory, context graph, identity, cross-platform memory.

Public API (callers import only from hg_memory):
  search_memory, get_recent_entities, index_agent, run_indexing_job, run_extraction
  get_overseer_access, ContextSearch, ContextGraphDatabase, ContextRecorder
  record_persona_update_async
See docs/specs/hg_memory_api_spec.md.
"""

from hg_memory.api import (
    search_memory,
    get_recent_entities,
    index_agent,
    run_indexing_job,
    run_extraction,
)
from hg_memory.context_surface import (
    get_overseer_access,
    ContextSearch,
    ContextGraphDatabase,
    ContextRecorder,
)
from hg_memory.cross_platform_memory import CrossPlatformMemory
from hg_memory.identity_surface import record_persona_update_async
from hg_memory.shared import (
    DatabaseBase,
    TokenizerRegistry,
    detect_language,
    detect_language_with_confidence,
    get_config,
    get_tokenizer,
    MemoryEngineConfig,
)

__all__ = [
    "search_memory",
    "get_recent_entities",
    "index_agent",
    "run_indexing_job",
    "run_extraction",
    "get_overseer_access",
    "ContextSearch",
    "ContextGraphDatabase",
    "ContextRecorder",
    "record_persona_update_async",
    "CrossPlatformMemory",
    "DatabaseBase",
    "TokenizerRegistry",
    "detect_language",
    "detect_language_with_confidence",
    "get_config",
    "get_tokenizer",
    "MemoryEngineConfig",
]
