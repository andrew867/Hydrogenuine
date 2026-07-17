"""
Agent memory and entity graph (FTS, indexing, search).
"""

from hg_memory.agent.agent_memory_db import AgentMemoryDatabase
from hg_memory.agent.agent_memory_search import AgentMemorySearch, get_wake_fts_snippets
from hg_memory.agent.agent_memory_indexer import AgentMemoryIndexer
from hg_memory.agent.entity_graph_db import (
    EntityGraphDatabase,
    get_entity_graph_db_path,
    get_recent_entities,
)
from hg_memory.agent.entity_graph_indexer import (
    index_life_dir,
    run_entity_graph_indexer,
)
from hg_memory.agent.agent_task_integration import (
    search_agent_memory,
    search_with_knowledge,
    search_agent_identity,
)

__all__ = [
    "AgentMemoryDatabase",
    "AgentMemorySearch",
    "get_wake_fts_snippets",
    "AgentMemoryIndexer",
    "EntityGraphDatabase",
    "get_entity_graph_db_path",
    "get_recent_entities",
    "index_life_dir",
    "run_entity_graph_indexer",
    "search_agent_memory",
    "search_with_knowledge",
    "search_agent_identity",
]
