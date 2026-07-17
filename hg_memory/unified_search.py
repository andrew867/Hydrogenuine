#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified search interface.

Searches across knowledgebase, agent memory, and context graph.
"""

from typing import List, Dict, Optional
from pathlib import Path

from hg_memory.config import get_config
from hg_memory.shared import detect_language
from hg_memory.agent.agent_memory_db import AgentMemoryDatabase
from hg_memory.agent.agent_memory_search import AgentMemorySearch
from hg_memory.context.context_graph_db import ContextGraphDatabase
from hg_memory.context.context_search import ContextSearch
from hg_gateway.shared_storage import use_shared_gateway_db

# Import identity graph
try:
    from hg_memory.identity.identity_graph_db import IdentityGraphDatabase
    from hg_memory.identity.identity_search import IdentitySearch
    from hg_memory.identity.config import get_identity_graph_db_path
    IDENTITY_GRAPH_AVAILABLE = True
except ImportError:
    IDENTITY_GRAPH_AVAILABLE = False
    IdentityGraphDatabase = None
    IdentitySearch = None

# Import knowledge engine
try:
    from skills.knowledge.api import get_api as get_knowledge_api, KnowledgeEngineAPI
    KNOWLEDGE_ENGINE_AVAILABLE = True
except ImportError:
    KNOWLEDGE_ENGINE_AVAILABLE = False
    KnowledgeEngineAPI = None


class UnifiedSearch:
    """Unified search across all memory systems"""

    def __init__(self):
        """Initialize unified search"""
        self.config = get_config()
        self.knowledge_api = None

        if KNOWLEDGE_ENGINE_AVAILABLE:
            try:
                self.knowledge_api = get_knowledge_api()
            except Exception as e:
                print(f"Warning: Could not initialize knowledge engine: {e}")

    def search_all(
        self,
        query: str,
        language: Optional[str] = None,
        limit: int = 10,
        agent_id: Optional[str] = None,
        include_knowledge: bool = True,
        include_agent_memory: bool = True,
        include_context: bool = True,
        include_identity: bool = True
    ) -> Dict[str, List[Dict]]:
        """
        Search across all systems (knowledgebase, agent memory, context graph).

        Args:
            query: Search query
            language: Optional language code (auto-detected if None)
            limit: Maximum number of results per system
            agent_id: Optional agent ID (for agent memory search)
            include_knowledge: Whether to search knowledgebase
            include_agent_memory: Whether to search agent memory
            include_context: Whether to search context graph
            include_identity: Whether to search identity graph

        Returns:
            Dictionary with keys: "knowledge", "agent_memory", "context", "identity"
            Each value is a list of search results
        """
        if language is None:
            language = detect_language(query)

        results = {
            "knowledge": [],
            "agent_memory": [],
            "context": [],
            "identity": []
        }

        # Search knowledgebase
        if include_knowledge and self.knowledge_api:
            try:
                knowledge_results = self.knowledge_api.search(query, language, limit)
                results["knowledge"] = knowledge_results
            except Exception as e:
                print(f"Error searching knowledgebase: {e}")

        # Search agent memory
        if include_agent_memory and agent_id:
            try:
                config = get_config()
                db_path = config.get_agent_memory_db_path(agent_id)
                if db_path.exists() or use_shared_gateway_db(db_path):
                    db = AgentMemoryDatabase(str(db_path))
                    search = AgentMemorySearch(db)
                    agent_results = search.search_agent_memory(query, language, limit)
                    results["agent_memory"] = agent_results
            except Exception as e:
                print(f"Error searching agent memory: {e}")

        # Search context graph
        if include_context:
            try:
                config = get_config()
                context_db_path = config.get_context_graph_db_path()
                if context_db_path.exists() or use_shared_gateway_db(context_db_path):
                    context_db = ContextGraphDatabase(str(context_db_path))
                    context_search = ContextSearch(context_db)
                    context_results = context_search.search_context(
                        query, agent_id=agent_id, language=language, limit=limit
                    )
                    results["context"] = context_results
            except Exception as e:
                print(f"Error searching context graph: {e}")

        # Search identity graph
        if include_identity and IDENTITY_GRAPH_AVAILABLE and agent_id:
            try:
                identity_db_path = get_identity_graph_db_path(agent_id)
                if identity_db_path.exists() or use_shared_gateway_db(identity_db_path):
                    identity_db = IdentityGraphDatabase(str(identity_db_path))
                    identity_search = IdentitySearch(identity_db)
                    identity_results = identity_search.search_identity(
                        query, agent_id=agent_id, language=language, limit=limit
                    )
                    results["identity"] = identity_results
            except Exception as e:
                print(f"Error searching identity graph: {e}")

        return results

    def search_connected(
        self,
        query: str,
        graph_type: str = "all",
        language: Optional[str] = None,
        limit: int = 10,
        agent_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Find entities connected across graphs.

        Example: "civitai" → finds in knowledge, agent posts, context decisions

        Args:
            query: Search query
            graph_type: "all", "knowledge", "agent_memory", or "context"
            language: Optional language code
            limit: Maximum number of results
            agent_id: Optional agent ID

        Returns:
            List of connected entities with cross-references
        """
        if language is None:
            language = detect_language(query)

        # Search all systems (use default include flags)
        all_results = self.search_all(
            query, language, limit, agent_id,
            include_knowledge=(graph_type in ["all", "knowledge"]),
            include_agent_memory=(graph_type in ["all", "agent_memory"]),
            include_context=(graph_type in ["all", "context"]),
            include_identity=(graph_type in ["all", "identity"])
        )

        # Collect entity IDs and references
        entity_map = {}  # entity_id -> {source, data}
        connections = []  # List of connected entities

        # Process knowledge results
        if graph_type in ["all", "knowledge"] and all_results["knowledge"]:
            for result in all_results["knowledge"]:
                entity_id = f"knowledge:{result.get('file_path', 'unknown')}"
                entity_map[entity_id] = {
                    "source": "knowledge",
                    "entity_id": entity_id,
                    "data": result,
                    "references": []
                }

        # Process agent memory results
        if graph_type in ["all", "agent_memory"] and all_results["agent_memory"]:
            for result in all_results["agent_memory"]:
                entity_id = f"agent_memory:{result.get('file_path', 'unknown')}"
                entity_map[entity_id] = {
                    "source": "agent_memory",
                    "entity_id": entity_id,
                    "data": result,
                    "references": []
                }

        # Process context results
        if graph_type in ["all", "context"] and all_results["context"]:
            for result in all_results["context"]:
                entity_id = result.get("entity_id", "unknown")
                if entity_id not in entity_map:
                    entity_map[entity_id] = {
                        "source": "context",
                        "entity_id": entity_id,
                        "data": result,
                        "references": []
                    }

                # Get related entities from context graph
                try:
                    config = get_config()
                    context_db_path = config.get_context_graph_db_path()
                    if context_db_path.exists() or use_shared_gateway_db(context_db_path):
                        context_db = ContextGraphDatabase(str(context_db_path))
                        related = context_db.get_related_entities(entity_id, direction="both")
                        entity_map[entity_id]["references"] = related
                except Exception as e:
                    print(f"Error getting related entities: {e}")

        # Process identity results
        if graph_type in ["all", "identity"] and all_results.get("identity"):
            for result in all_results["identity"]:
                entity_id = result.get("entity_id", "unknown")
                if entity_id not in entity_map:
                    entity_map[entity_id] = {
                        "source": "identity",
                        "entity_id": entity_id,
                        "data": result,
                        "references": []
                    }

                # Get related entities from identity graph
                try:
                    if agent_id:
                        identity_db_path = get_identity_graph_db_path(agent_id)
                        if identity_db_path.exists() or use_shared_gateway_db(identity_db_path):
                            identity_db = IdentityGraphDatabase(str(identity_db_path))
                            related = identity_db.get_related_entities(entity_id, direction="both")
                            entity_map[entity_id]["references"] = related
                except Exception as e:
                    print(f"Error getting identity related entities: {e}")

        # Build connections list
        for entity_id, entity_info in entity_map.items():
            connections.append({
                "entity_id": entity_id,
                "source": entity_info["source"],
                "data": entity_info["data"],
                "references": entity_info["references"],
                "reference_count": len(entity_info["references"])
            })

        # Sort by reference count (most connected first)
        connections.sort(key=lambda x: x["reference_count"], reverse=True)

        return connections[:limit]

    def get_connected_entities(
        self,
        entity_name: str,
        graph_type: str = "all",
        agent_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Get entities connected to a specific entity name across graphs.

        Args:
            entity_name: Entity name to search for (e.g., "civitai")
            graph_type: "all", "knowledge", "agent_memory", or "context"
            agent_id: Optional agent ID

        Returns:
            List of connected entities
        """
        return self.search_connected(entity_name, graph_type, agent_id=agent_id)

    def get_decision_chain(
        self,
        topic: str,
        agent_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Get decision chain for a topic (searches context graph).

        Args:
            topic: Topic to search for
            agent_id: Optional agent ID filter

        Returns:
            List of decisions in chronological order
        """
        try:
            config = get_config()
            context_db_path = config.get_context_graph_db_path()
            if not context_db_path.exists() and not use_shared_gateway_db(context_db_path):
                return []

            context_db = ContextGraphDatabase(str(context_db_path))
            context_search = ContextSearch(context_db)
            return context_search.get_decision_chain(topic, agent_id)
        except Exception as e:
            print(f"Error getting decision chain: {e}")
            return []


# Global instance
_unified_search_instance: Optional[UnifiedSearch] = None


def get_unified_search() -> UnifiedSearch:
    """Get global unified search instance"""
    global _unified_search_instance
    if _unified_search_instance is None:
        _unified_search_instance = UnifiedSearch()
    return _unified_search_instance


# Convenience functions
def search_all(
    query: str,
    language: Optional[str] = None,
    limit: int = 10,
    agent_id: Optional[str] = None
) -> Dict[str, List[Dict]]:
    """Search across all systems (convenience function)"""
    return get_unified_search().search_all(query, language, limit, agent_id)


def search_connected(
    query: str,
    graph_type: str = "all",
    language: Optional[str] = None,
    limit: int = 10,
    agent_id: Optional[str] = None
) -> List[Dict]:
    """Find entities connected across graphs (convenience function)"""
    return get_unified_search().search_connected(query, graph_type, language, limit, agent_id)


def get_connected_entities(
    entity_name: str,
    graph_type: str = "all",
    agent_id: Optional[str] = None
) -> List[Dict]:
    """Get entities connected to a specific entity name (convenience function)"""
    return get_unified_search().get_connected_entities(entity_name, graph_type, agent_id)
