#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent task integration helper for memory engine.

Provides easy-to-use functions for agents to search their memory graphs
with DB-first behavior.
"""

import time
from typing import List, Dict, Optional
from pathlib import Path

from hg_memory.agent.agent_memory_search import AgentMemorySearch
from hg_memory.agent.agent_memory_db import AgentMemoryDatabase
from hg_memory.config import get_config
from hg_lib.language_detector import detect_language
from hg_memory.memory_metrics import MemoryMetricsCollector
from hg_gateway.shared_storage import use_shared_gateway_db


def search_agent_memory(
    agent_id: str,
    query: str,
    language: Optional[str] = None,
    limit: int = 10,
    fallback_to_files: bool = True
) -> List[Dict]:
    """
    Search agent's memory graph using the DB-backed index only.
    
    This is the recommended function for agents to search their own memory.
    It returns DB-backed results when available and otherwise returns an
    empty result set. The fallback_to_files flag is retained only for
    compatibility and is ignored.
    
    Args:
        agent_id: Agent ID (e.g., "fourclaw-engage")
        query: Search query
        language: Optional language code (auto-detected if None)
        limit: Maximum number of results
        fallback_to_files: Deprecated compatibility flag; ignored.
        
    Returns:
        List of search results
    """
    config = get_config()
    metrics = MemoryMetricsCollector()
    
    if language is None:
        language = detect_language(query)
    
    start_time = time.time()
    
    # Try graph search first
    try:
        db_path = config.get_agent_memory_db_path(agent_id)
        if db_path.exists() or use_shared_gateway_db(db_path):
            db = AgentMemoryDatabase(str(db_path))
            search = AgentMemorySearch(db)
            results = search.search_agent_memory(query, language, limit)
            
            latency_ms = (time.time() - start_time) * 1000
            metrics.record_search(
                system="graph",
                query=query,
                result_count=len(results),
                latency_ms=latency_ms,
                language=language,
                success=True,
                search_type="agent_memory"
            )
            
            return results
        else:
            # Database doesn't exist yet; file fallback is retired.
            latency_ms = (time.time() - start_time) * 1000
            metrics.record_search(
                system="graph",
                query=query,
                result_count=0,
                latency_ms=latency_ms,
                language=language,
                success=False,
                search_type="agent_memory"
            )
            return []
    except Exception as e:
        # Graph search failed
        latency_ms = (time.time() - start_time) * 1000
        metrics.record_search(
            system="graph",
            query=query,
            result_count=0,
            latency_ms=latency_ms,
            language=language,
            success=False,
            search_type="agent_memory"
        )
        return []


def search_with_knowledge(
    agent_id: str,
    query: str,
    language: Optional[str] = None,
    limit: int = 10
) -> Dict[str, List[Dict]]:
    """
    Search both agent memory and knowledgebase.
    
    Args:
        agent_id: Agent ID
        query: Search query
        language: Optional language code
        limit: Maximum number of results per source
        
    Returns:
        Dictionary with "agent_memory" and "knowledge" keys
    """
    from hg_memory.unified_search import get_unified_search
    
    unified = get_unified_search()
    results = unified.search_all(
        query=query,
        language=language,
        limit=limit,
        agent_id=agent_id,
        include_knowledge=True,
        include_agent_memory=True,
        include_context=False,
        include_identity=False
    )
    
    return {
        "agent_memory": results.get("agent_memory", []),
        "knowledge": results.get("knowledge", [])
    }


def search_agent_identity(
    agent_id: str,
    query: str,
    language: Optional[str] = None,
    limit: int = 10,
    entity_type: Optional[str] = None,
    platform: Optional[str] = None
) -> List[Dict]:
    """
    Search agent's identity graph with graceful fallback.
    
    This function searches the agent's identity components (SOUL/HEART/IDENTITY)
    from the identity graph database.
    
    Args:
        agent_id: Agent ID (e.g., "fourclaw-auto-post")
        query: Search query
        language: Optional language code (auto-detected if None)
        limit: Maximum number of results
        entity_type: Optional entity type filter
        platform: Optional platform filter
        
    Returns:
        List of identity search results
    """
    try:
        from hg_memory.identity.identity_graph_db import IdentityGraphDatabase
        from hg_memory.identity.identity_search import IdentitySearch
        from hg_memory.identity.config import get_identity_graph_db_path
    except ImportError:
        # Identity graph not available
        return []
    
    config = get_config()
    
    if language is None:
        language = detect_language(query)
    
    start_time = time.time()
    
    # Try identity graph search
    try:
        identity_db_path = get_identity_graph_db_path(agent_id)
        if identity_db_path.exists() or use_shared_gateway_db(identity_db_path):
            identity_db = IdentityGraphDatabase(str(identity_db_path))
            identity_search = IdentitySearch(identity_db)
            results = identity_search.search_identity(
                query=query,
                agent_id=agent_id,
                entity_type=entity_type,
                language=language,
                limit=limit,
                platform=platform
            )
            
            latency_ms = (time.time() - start_time) * 1000
            metrics = MemoryMetricsCollector()
            metrics.record_search(
                system="graph",
                query=query,
                result_count=len(results),
                latency_ms=latency_ms,
                language=language,
                success=True,
                search_type="identity"
            )
            
            return results
        else:
            # Database doesn't exist yet
            return []
    except Exception as e:
        # Identity search failed
        latency_ms = (time.time() - start_time) * 1000
        metrics = MemoryMetricsCollector()
        metrics.record_search(
            system="graph",
            query=query,
            result_count=0,
            latency_ms=latency_ms,
            language=language,
            success=False,
            search_type="identity"
        )
        print(f"Error searching identity graph: {e}")
        return []
