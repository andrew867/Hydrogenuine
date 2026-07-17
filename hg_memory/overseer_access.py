#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Overseer hierarchical access to memory graphs.

Provides overseer with access to agent and sub-agent memory graphs
while maintaining isolation boundaries.
"""

from typing import List, Dict, Optional, Set, Any
from pathlib import Path

from hg_memory.config import get_config
from hg_lib.language_detector import detect_language
from hg_memory.agent.agent_memory_db import AgentMemoryDatabase
from hg_memory.agent.agent_memory_search import AgentMemorySearch
from hg_memory.context.context_graph_db import ContextGraphDatabase
from hg_memory.context.context_search import ContextSearch
from hg_memory.unified_search import UnifiedSearch
from hg_gateway.shared_storage import use_shared_gateway_db

# Import identity graph (optional)
try:
    from hg_memory.identity.identity_graph_db import IdentityGraphDatabase
    from hg_memory.identity.identity_search import IdentitySearch
    from hg_memory.identity.identity_analytics import IdentityAnalytics
    from hg_memory.identity.config import get_identity_graph_db_path
    IDENTITY_GRAPH_AVAILABLE = True
except ImportError:
    IDENTITY_GRAPH_AVAILABLE = False
    IdentityGraphDatabase = None
    IdentitySearch = None
    IdentityAnalytics = None
    get_identity_graph_db_path = None


class OverseerAccess:
    """Hierarchical access control for overseer to query agent memory graphs"""
    
    def __init__(self):
        """Initialize overseer access"""
        self.config = get_config()
        self.unified_search = UnifiedSearch()
        self.overseer_id = "overseer"
    
    def _is_overseer(self, requester_id: str) -> bool:
        """Check if requester is the overseer"""
        return requester_id == self.overseer_id
    
    def _get_agent_ids(self) -> List[str]:
        """
        Get list of all agent IDs from memory directories.
        
        Returns:
            List of agent IDs (e.g., ["fourclaw-engage", "moltbook-auto-post"])
        """
        workspace_root = self.config.workspace_root
        automation_dir = workspace_root / "memory" / "automation"
        
        if not automation_dir.exists():
            return []
        
        agent_ids = []
        for item in automation_dir.iterdir():
            if item.is_dir() and item.name.startswith("automation-"):
                agent_id = item.name.replace("automation-", "", 1)
                agent_ids.append(agent_id)
        
        return agent_ids
    
    def _can_access_agent(self, requester_id: str, target_agent_id: str) -> bool:
        """
        Check if requester can access target agent's memory.
        
        Rules:
        - Overseer can access any agent
        - Agents can only access their own memory
        
        Args:
            requester_id: ID of the requester
            target_agent_id: ID of the target agent
            
        Returns:
            True if access is allowed
        """
        if self._is_overseer(requester_id):
            return True
        
        return requester_id == target_agent_id
    
    def search_agent_memory(
        self,
        requester_id: str,
        target_agent_id: str,
        query: str,
        language: Optional[str] = None,
        limit: int = 10,
        include_metadata: bool = False,
    ) -> List[Dict]:
        """
        Search a specific agent's memory (overseer only, or agent's own memory).
        
        Args:
            requester_id: ID of the requester (must be overseer or target_agent_id)
            target_agent_id: ID of the agent whose memory to search
            query: Search query
            language: Optional language code
            limit: Maximum number of results
            include_metadata: Whether to load per-result metadata
            
        Returns:
            List of search results
            
        Raises:
            PermissionError: If requester doesn't have access
        """
        if not self._can_access_agent(requester_id, target_agent_id):
            raise PermissionError(
                f"Agent '{requester_id}' cannot access memory of agent '{target_agent_id}'. "
                "Only overseer can access other agents' memory."
            )
        
        try:
            config = get_config()
            db_path = config.get_agent_memory_db_path(target_agent_id)
            if not db_path.exists() and not use_shared_gateway_db(db_path):
                return []
            
            db = AgentMemoryDatabase(str(db_path))
            search = AgentMemorySearch(db)
            return search.search_agent_memory(
                query,
                language,
                limit,
                include_metadata=include_metadata,
            )
        except Exception as e:
            print(f"Error searching agent memory for {target_agent_id}: {e}")
            return []
    
    def search_all_agents(
        self,
        requester_id: str,
        query: str,
        language: Optional[str] = None,
        limit_per_agent: int = 10,
        include_metadata: bool = False,
    ) -> Dict[str, List[Dict]]:
        """
        Search across all agents' memory (overseer only).
        
        Args:
            requester_id: ID of the requester (must be overseer)
            query: Search query
            language: Optional language code
            limit_per_agent: Maximum results per agent
            include_metadata: Whether to load per-result metadata
            
        Returns:
            Dictionary mapping agent_id to search results
            
        Raises:
            PermissionError: If requester is not overseer
        """
        if not self._is_overseer(requester_id):
            raise PermissionError(
                f"Only overseer can search across all agents. "
                f"Requester '{requester_id}' is not authorized."
            )
        
        results = {}
        agent_ids = self._get_agent_ids()
        
        for agent_id in agent_ids:
            try:
                agent_results = self.search_agent_memory(
                    requester_id,
                    agent_id,
                    query,
                    language,
                    limit_per_agent,
                    include_metadata=include_metadata,
                )
                if agent_results:
                    results[agent_id] = agent_results
            except Exception as e:
                print(f"Error searching agent {agent_id}: {e}")
                continue
        
        return results
    
    def compare_decision_patterns(
        self,
        requester_id: str,
        agent_ids: Optional[List[str]] = None,
        topic: Optional[str] = None,
        hours: int = 24
    ) -> Dict[str, Dict]:
        """
        Compare decision patterns across agents (overseer only).
        
        Args:
            requester_id: ID of the requester (must be overseer)
            agent_ids: Optional list of agent IDs to compare (all if None)
            topic: Optional topic filter
            hours: Number of hours to look back
            
        Returns:
            Dictionary mapping agent_id to decision pattern statistics
            
        Raises:
            PermissionError: If requester is not overseer
        """
        if not self._is_overseer(requester_id):
            raise PermissionError(
                f"Only overseer can compare decision patterns. "
                f"Requester '{requester_id}' is not authorized."
            )
        
        if agent_ids is None:
            agent_ids = self._get_agent_ids()
        
        patterns = {}
        
        try:
            config = get_config()
            context_db_path = config.get_context_graph_db_path()
            if not context_db_path.exists() and not use_shared_gateway_db(context_db_path):
                return patterns
            
            context_db = ContextGraphDatabase(str(context_db_path))
            context_search = ContextSearch(context_db)
            
            for agent_id in agent_ids:
                # Get decision chain for this agent
                if topic:
                    decisions = context_search.get_decision_chain(topic, agent_id=agent_id)
                else:
                    # Get all recent decisions for this agent
                    decisions = context_search.search_context(
                        query="*",
                        agent_id=agent_id,
                        limit=100
                    )
                    # Filter to decisions only
                    decisions = [d for d in decisions if d.get("entity_type") == "decision"]
                
                # Calculate pattern statistics
                pattern = {
                    "agent_id": agent_id,
                    "decision_count": len(decisions),
                    "topics": {},
                    "avg_rationale_length": 0,
                    "common_alternatives": {}
                }
                
                if decisions:
                    rationale_lengths = []
                    for decision in decisions:
                        rationale = decision.get("content", "")
                        if rationale:
                            rationale_lengths.append(len(rationale))
                        
                        # Extract topic from metadata
                        metadata = decision.get("metadata", {})
                        decision_topic = metadata.get("topic") or topic or "general"
                        pattern["topics"][decision_topic] = pattern["topics"].get(decision_topic, 0) + 1
                    
                    if rationale_lengths:
                        pattern["avg_rationale_length"] = sum(rationale_lengths) / len(rationale_lengths)
                
                patterns[agent_id] = pattern
        except Exception as e:
            print(f"Error comparing decision patterns: {e}")
        
        return patterns
    
    def find_common_issues(
        self,
        requester_id: str,
        agent_ids: Optional[List[str]] = None,
        hours: int = 24
    ) -> List[Dict]:
        """
        Find common issues across agents (overseer only).
        
        Searches for common patterns in feedback, errors, or violations.
        
        Args:
            requester_id: ID of the requester (must be overseer)
            agent_ids: Optional list of agent IDs to analyze (all if None)
            topic: Optional topic filter
            hours: Number of hours to look back
            
        Returns:
            List of common issues with agent counts
            
        Raises:
            PermissionError: If requester is not overseer
        """
        if not self._is_overseer(requester_id):
            raise PermissionError(
                f"Only overseer can find common issues. "
                f"Requester '{requester_id}' is not authorized."
            )
        
        if agent_ids is None:
            agent_ids = self._get_agent_ids()
        
        # Search for common terms across all agents
        common_terms = ["error", "failed", "violation", "issue", "problem", "feedback"]
        issue_counts = {}
        
        for term in common_terms:
            all_results = self.search_all_agents(
                requester_id,
                term,
                limit_per_agent=5,
                include_metadata=False,
            )
            agent_count = sum(1 for results in all_results.values() if results)
            if agent_count > 0:
                issue_counts[term] = {
                    "term": term,
                    "affected_agents": agent_count,
                    "total_occurrences": sum(len(results) for results in all_results.values()),
                    "agents": list(all_results.keys())
                }
        
        # Sort by affected agents (most common first)
        common_issues = sorted(
            issue_counts.values(),
            key=lambda x: x["affected_agents"],
            reverse=True
        )
        
        return common_issues
    
    def get_most_referenced_knowledge(
        self,
        requester_id: str,
        agent_ids: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        Find knowledge most referenced by successful agents (overseer only).
        
        Searches agent memory for references to knowledge files and counts occurrences.
        
        Args:
            requester_id: ID of the requester (must be overseer)
            agent_ids: Optional list of agent IDs to analyze (all if None)
            limit: Maximum number of results
            
        Returns:
            List of knowledge references with agent counts
            
        Raises:
            PermissionError: If requester is not overseer
        """
        if not self._is_overseer(requester_id):
            raise PermissionError(
                f"Only overseer can analyze knowledge references. "
                f"Requester '{requester_id}' is not authorized."
            )
        
        if agent_ids is None:
            agent_ids = self._get_agent_ids()
        
        # Search for knowledge references in agent memory
        # Look for patterns like "knowledge/", "KNOWLEDGE_SOURCES", file paths, etc.
        knowledge_terms = ["knowledge", "KNOWLEDGE_SOURCES", "knowledge/", ".md"]
        knowledge_refs = {}
        
        for agent_id in agent_ids:
            for term in knowledge_terms:
                try:
                    results = self.search_agent_memory(
                        requester_id, agent_id, term, limit=50
                    )
                    for result in results:
                        file_path = result.get("file_path", "")
                        # Extract knowledge file references
                        if "knowledge" in file_path.lower() or ".md" in file_path:
                            if file_path not in knowledge_refs:
                                knowledge_refs[file_path] = {
                                    "file_path": file_path,
                                    "referenced_by": set(),
                                    "reference_count": 0
                                }
                            knowledge_refs[file_path]["referenced_by"].add(agent_id)
                            knowledge_refs[file_path]["reference_count"] += 1
                except Exception as e:
                    print(f"Error searching knowledge references for {agent_id}: {e}")
                    continue
        
        # Convert to list and sort by reference count
        ref_list = []
        for file_path, ref_data in knowledge_refs.items():
            ref_list.append({
                "file_path": file_path,
                "referenced_by": list(ref_data["referenced_by"]),
                "agent_count": len(ref_data["referenced_by"]),
                "reference_count": ref_data["reference_count"]
            })
        
        ref_list.sort(key=lambda x: x["reference_count"], reverse=True)
        return ref_list[:limit]
    
    def find_similar_context_patterns(
        self,
        requester_id: str,
        agent_ids: Optional[List[str]] = None,
        similarity_threshold: float = 0.7
    ) -> List[Dict]:
        """
        Find agents with similar context patterns (overseer only).
        
        Args:
            requester_id: ID of the requester (must be overseer)
            agent_ids: Optional list of agent IDs to compare (all if None)
            similarity_threshold: Minimum similarity score (0-1)
            
        Returns:
            List of similar agent pairs with similarity scores
            
        Raises:
            PermissionError: If requester is not overseer
        """
        if not self._is_overseer(requester_id):
            raise PermissionError(
                f"Only overseer can find similar context patterns. "
                f"Requester '{requester_id}' is not authorized."
            )
        
        if agent_ids is None:
            agent_ids = self._get_agent_ids()
        
        if len(agent_ids) < 2:
            return []
        
        # Get decision patterns for all agents
        patterns = self.compare_decision_patterns(requester_id, agent_ids)
        
        # Calculate similarity between agents
        similarities = []
        
        for i, agent1_id in enumerate(agent_ids):
            for agent2_id in agent_ids[i+1:]:
                pattern1 = patterns.get(agent1_id, {})
                pattern2 = patterns.get(agent2_id, {})
                
                # Simple similarity: compare topic distributions
                topics1 = set(pattern1.get("topics", {}).keys())
                topics2 = set(pattern2.get("topics", {}).keys())
                
                if topics1 or topics2:
                    intersection = len(topics1 & topics2)
                    union = len(topics1 | topics2)
                    similarity = intersection / union if union > 0 else 0.0
                    
                    if similarity >= similarity_threshold:
                        similarities.append({
                            "agent1": agent1_id,
                            "agent2": agent2_id,
                            "similarity": similarity,
                            "common_topics": list(topics1 & topics2)
                        })
        
        # Sort by similarity (highest first)
        similarities.sort(key=lambda x: x["similarity"], reverse=True)
        
        return similarities
    
    def search_agent_identity(
        self,
        requester_id: str,
        target_agent_id: str,
        query: str,
        language: Optional[str] = None,
        limit: int = 10,
        entity_type: Optional[str] = None
    ) -> List[Dict]:
        """
        Search a specific agent's identity graph (overseer only, or agent's own identity).
        
        Args:
            requester_id: ID of the requester (must be overseer or target_agent_id)
            target_agent_id: ID of the agent whose identity to search
            query: Search query
            language: Optional language code
            limit: Maximum number of results
            entity_type: Optional entity type filter
            
        Returns:
            List of identity search results
            
        Raises:
            PermissionError: If requester doesn't have access
        """
        if not self._can_access_agent(requester_id, target_agent_id):
            raise PermissionError(
                f"Agent '{requester_id}' cannot access identity of agent '{target_agent_id}'. "
                "Only overseer can access other agents' identity."
            )
        
        if not IDENTITY_GRAPH_AVAILABLE:
            return []
        
        try:
            identity_db_path = get_identity_graph_db_path(target_agent_id)
            if not identity_db_path.exists() and not use_shared_gateway_db(identity_db_path):
                return []
            
            identity_db = IdentityGraphDatabase(str(identity_db_path))
            identity_search = IdentitySearch(identity_db)
            return identity_search.search_identity(
                query=query,
                agent_id=target_agent_id,
                entity_type=entity_type,
                language=language,
                limit=limit
            )
        except Exception as e:
            print(f"Error searching agent identity for {target_agent_id}: {e}")
            return []
    
    def search_all_agents_identity(
        self,
        requester_id: str,
        query: str,
        language: Optional[str] = None,
        limit_per_agent: int = 10,
        entity_type: Optional[str] = None
    ) -> Dict[str, List[Dict]]:
        """
        Search across all agents' identity graphs (overseer only).
        
        Args:
            requester_id: ID of the requester (must be overseer)
            query: Search query
            language: Optional language code
            limit_per_agent: Maximum results per agent
            entity_type: Optional entity type filter
            
        Returns:
            Dictionary mapping agent_id to identity search results
            
        Raises:
            PermissionError: If requester is not overseer
        """
        if not self._is_overseer(requester_id):
            raise PermissionError(
                f"Only overseer can search across all agents' identity. "
                f"Requester '{requester_id}' is not authorized."
            )
        
        results = {}
        agent_ids = self._get_agent_ids()
        
        for agent_id in agent_ids:
            try:
                agent_results = self.search_agent_identity(
                    requester_id, agent_id, query, language, limit_per_agent, entity_type
                )
                if agent_results:
                    results[agent_id] = agent_results
            except Exception as e:
                print(f"Error searching identity for agent {agent_id}: {e}")
                continue
        
        return results

    def resolve_target_id(
        self,
        requester_id: str,
        target_agent_id: str,
        target_id: str,
        target_type: Optional[str] = None,
        unknown_target_ok: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Map target_id to identity graph entity (person/org/policy). Fail closed on ambiguous
        unless spec allows unknown_target_ok or explicit fallback.

        Args:
            requester_id: Requester (must have access to target_agent_id)
            target_agent_id: Agent whose identity graph to use
            target_id: Target identifier to resolve
            target_type: Optional filter (person, org, policy, topic, entity)
            unknown_target_ok: If True, return unresolved on unknown/ambiguous; if False, fail closed. If None, read from spec opinion_taxonomy.

        Returns:
            {"resolved": bool, "entity_id": str|None, "entity": dict|None, "error": str|None}
        """
        if not self._can_access_agent(requester_id, target_agent_id):
            return {"resolved": False, "entity_id": None, "entity": None, "error": "access_denied"}
        if not IDENTITY_GRAPH_AVAILABLE or IdentityGraphDatabase is None or get_identity_graph_db_path is None:
            return {"resolved": False, "entity_id": None, "entity": None, "error": "identity_graph_unavailable"}
        if unknown_target_ok is None:
            try:
                from spec_validator import get_spec_validator
                taxonomy = get_spec_validator().get_opinion_taxonomy()
                unknown_target_ok = bool(taxonomy.get("unknown_target_ok", False))
            except Exception:
                unknown_target_ok = False
        try:
            db_path = get_identity_graph_db_path(target_agent_id)
            if not db_path.exists() and not use_shared_gateway_db(db_path):
                return {"resolved": False, "entity_id": None, "entity": None, "error": "no_identity_graph"}
            identity_db = IdentityGraphDatabase(str(db_path))
            entity = identity_db.get_entity(target_id)
            if entity is not None:
                et = entity.get("entity_type") or ""
                if target_type is None or et == target_type:
                    return {"resolved": True, "entity_id": entity.get("entity_id"), "entity": entity, "error": None}
            identity_search = IdentitySearch(identity_db)
            results = identity_search.search_identity(
                query=target_id, agent_id=target_agent_id, entity_type=target_type, limit=2
            )
            if not results:
                return {"resolved": False, "entity_id": None, "entity": None, "error": "unknown_target"}
            if len(results) == 1:
                r = results[0]
                eid = r.get("entity_id")
                ent = identity_db.get_entity(eid) if eid else r
                return {"resolved": True, "entity_id": eid, "entity": ent, "error": None}
            if unknown_target_ok:
                r = results[0]
                eid = r.get("entity_id")
                ent = identity_db.get_entity(eid) if eid else r
                return {"resolved": True, "entity_id": eid, "entity": ent, "error": None}
            return {"resolved": False, "entity_id": None, "entity": None, "error": "ambiguous_target"}
        except Exception as e:
            return {"resolved": False, "entity_id": None, "entity": None, "error": str(e)}

    def compare_identity_patterns(
        self,
        requester_id: str,
        agent_ids: Optional[List[str]] = None,
        layer: Optional[str] = None
    ) -> Dict[str, Dict]:
        """
        Compare identity patterns across agents (overseer only).
        
        Compares identity components (SOUL/HEART/IDENTITY) across agents to find
        similarities and differences.
        
        Args:
            requester_id: ID of the requester (must be overseer)
            agent_ids: Optional list of agent IDs to compare (all if None)
            layer: Optional layer filter ("identity", "soul", "heart", "expression")
            
        Returns:
            Dictionary mapping agent_id to identity pattern statistics
            
        Raises:
            PermissionError: If requester is not overseer
        """
        if not self._is_overseer(requester_id):
            raise PermissionError(
                f"Only overseer can compare identity patterns. "
                f"Requester '{requester_id}' is not authorized."
            )
        
        if not IDENTITY_GRAPH_AVAILABLE:
            return {}
        
        if agent_ids is None:
            agent_ids = self._get_agent_ids()
        
        patterns = {}
        
        for agent_id in agent_ids:
            try:
                identity_db_path = get_identity_graph_db_path(agent_id)
                if not identity_db_path.exists() and not use_shared_gateway_db(identity_db_path):
                    continue
                
                identity_db = IdentityGraphDatabase(str(identity_db_path))
                identity_search = IdentitySearch(identity_db)
                
                # Get entities by layer
                if layer:
                    entities = identity_search.search_by_layer(layer, agent_id=agent_id, limit=1000)
                else:
                    entities = identity_search.search_identity("", agent_id=agent_id, limit=1000)
                
                # Calculate pattern statistics
                pattern = {
                    "agent_id": agent_id,
                    "entity_count": len(entities),
                    "entity_types": {},
                    "layers": {
                        "identity": 0,
                        "soul": 0,
                        "heart": 0,
                        "expression": 0
                    }
                }
                
                # Count by entity type and layer
                for entity in entities:
                    entity_type = entity.get("entity_type", "unknown")
                    pattern["entity_types"][entity_type] = pattern["entity_types"].get(entity_type, 0) + 1
                    
                    # Map to layer
                    if entity_type in ["name", "role", "audience", "scope", "non_negotiable", "negotiable",
                                      "competency", "deferral", "voice", "formatting", "tool_permission", "escalation_rule"]:
                        pattern["layers"]["identity"] += 1
                    elif entity_type in ["mission", "good_evil", "ideal", "goal", "priority_order", "tradeoff_policy",
                                         "truthfulness_policy", "alignment", "belief", "value"]:
                        pattern["layers"]["soul"] += 1
                    elif entity_type in ["empathy_level", "emotional_stance", "anger_handling", "insult_handling",
                                        "crisis_handling", "correction_style", "question_style", "de_escalation",
                                        "escalation", "priority"]:
                        pattern["layers"]["heart"] += 1
                    elif entity_type in ["trait", "speech_pattern", "emotion", "catchphrase", "engagement_pattern"]:
                        pattern["layers"]["expression"] += 1
                
                patterns[agent_id] = pattern
            except Exception as e:
                print(f"Error analyzing identity pattern for {agent_id}: {e}")
                continue
        
        return patterns
    
    def find_common_identity_elements(
        self,
        requester_id: str,
        agent_ids: Optional[List[str]] = None,
        entity_type: Optional[str] = None,
        min_agents: int = 2
    ) -> List[Dict]:
        """
        Find identity elements common across multiple agents (overseer only).
        
        Args:
            requester_id: ID of the requester (must be overseer)
            agent_ids: Optional list of agent IDs to analyze (all if None)
            entity_type: Optional entity type filter
            min_agents: Minimum number of agents that must have the element
            
        Returns:
            List of common identity elements with agent counts
            
        Raises:
            PermissionError: If requester is not overseer
        """
        if not self._is_overseer(requester_id):
            raise PermissionError(
                f"Only overseer can find common identity elements. "
                f"Requester '{requester_id}' is not authorized."
            )
        
        if not IDENTITY_GRAPH_AVAILABLE:
            return []
        
        if agent_ids is None:
            agent_ids = self._get_agent_ids()
        
        # Collect all entities from all agents
        entity_to_agents: Dict[str, Set[str]] = {}
        
        for agent_id in agent_ids:
            try:
                identity_db_path = get_identity_graph_db_path(agent_id)
                if not identity_db_path.exists() and not use_shared_gateway_db(identity_db_path):
                    continue
                
                identity_db = IdentityGraphDatabase(str(identity_db_path))
                identity_search = IdentitySearch(identity_db)
                
                # Get entities
                if entity_type:
                    entity_ids = [row.get("entity_id") for row in identity_search.search_identity("", agent_id=agent_id, entity_type=entity_type, limit=2000)]
                else:
                    entity_ids = [row.get("entity_id") for row in identity_search.search_identity("", agent_id=agent_id, limit=2000)]
                
                # Track which agents have which entities (by content hash)
                for entity_id in entity_ids:
                    entity = identity_db.get_entity(entity_id)
                    if entity:
                        # Use content hash as key for comparison
                        import hashlib
                        content = entity.get("content", "")
                        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
                        key = f"{entity.get('entity_type', 'unknown')}:{content_hash[:16]}"
                        
                        if key not in entity_to_agents:
                            entity_to_agents[key] = set()
                        entity_to_agents[key].add(agent_id)
            except Exception as e:
                print(f"Error analyzing identity for {agent_id}: {e}")
                continue
        
        # Find common elements
        common_elements = []
        for key, agents in entity_to_agents.items():
            if len(agents) >= min_agents:
                entity_type, content_hash = key.split(":", 1)
                common_elements.append({
                    "entity_type": entity_type,
                    "content_hash": content_hash,
                    "agent_count": len(agents),
                    "agents": list(agents)
                })
        
        # Sort by agent count (most common first)
        common_elements.sort(key=lambda x: x["agent_count"], reverse=True)
        
        return common_elements
    
    def find_similar_identity_profiles(
        self,
        requester_id: str,
        agent_ids: Optional[List[str]] = None,
        similarity_threshold: float = 0.5
    ) -> List[Dict]:
        """
        Find agents with similar identity profiles (overseer only).
        
        Args:
            requester_id: ID of the requester (must be overseer)
            agent_ids: Optional list of agent IDs to compare (all if None)
            similarity_threshold: Minimum similarity score (0.0 to 1.0)
            
        Returns:
            List of agent pairs with similarity scores
            
        Raises:
            PermissionError: If requester is not overseer
        """
        if not self._is_overseer(requester_id):
            raise PermissionError(
                f"Only overseer can find similar identity profiles. "
                f"Requester '{requester_id}' is not authorized."
            )
        
        if not IDENTITY_GRAPH_AVAILABLE:
            return []
        
        if agent_ids is None:
            agent_ids = self._get_agent_ids()
        
        # Get identity patterns for all agents
        patterns = self.compare_identity_patterns(requester_id, agent_ids)
        
        # Calculate similarity between agents
        similarities = []
        
        for i, agent1_id in enumerate(agent_ids):
            for agent2_id in agent_ids[i+1:]:
                pattern1 = patterns.get(agent1_id, {})
                pattern2 = patterns.get(agent2_id, {})
                
                if not pattern1 or not pattern2:
                    continue
                
                # Calculate similarity based on entity type distribution
                types1 = pattern1.get("entity_types", {})
                types2 = pattern2.get("entity_types", {})
                
                if types1 or types2:
                    # Jaccard similarity on entity types
                    set1 = set(types1.keys())
                    set2 = set(types2.keys())
                    
                    intersection = len(set1 & set2)
                    union = len(set1 | set2)
                    similarity = intersection / union if union > 0 else 0.0
                    
                    if similarity >= similarity_threshold:
                        similarities.append({
                            "agent1": agent1_id,
                            "agent2": agent2_id,
                            "similarity": similarity,
                            "common_types": list(set1 & set2),
                            "pattern1": pattern1,
                            "pattern2": pattern2
                        })
        
        # Sort by similarity (highest first)
        similarities.sort(key=lambda x: x["similarity"], reverse=True)
        
        return similarities

    def get_identity_evolution_report(
        self,
        requester_id: str,
        target_agent_id: str,
        days: int = 30
    ) -> Dict:
        """
        Get identity evolution report for an agent (overseer or agent's own).

        Args:
            requester_id: Requester (must be overseer or target_agent_id)
            target_agent_id: Agent whose identity evolution to report
            days: Number of days to look back

        Returns:
            Dict with total_evolutions, evolutions_by_type, evolution_timeline, etc.
        """
        if not self._can_access_agent(requester_id, target_agent_id):
            raise PermissionError(
                f"Agent '{requester_id}' cannot access identity evolution of '{target_agent_id}'."
            )
        if not IDENTITY_GRAPH_AVAILABLE or IdentityAnalytics is None:
            return {
                "period_days": days,
                "total_evolutions": 0,
                "evolutions_by_type": {},
                "most_evolved_entities": [],
                "evolution_timeline": [],
            }
        try:
            identity_db_path = get_identity_graph_db_path(target_agent_id)
            if not identity_db_path.exists() and not use_shared_gateway_db(identity_db_path):
                return {
                    "period_days": days,
                    "total_evolutions": 0,
                    "evolutions_by_type": {},
                    "most_evolved_entities": [],
                    "evolution_timeline": [],
                }
            identity_db = IdentityGraphDatabase(str(identity_db_path))
            analytics = IdentityAnalytics(identity_db)
            return analytics.get_evolution_report(agent_id=target_agent_id, days=days)
        except Exception as e:
            print(f"Error getting identity evolution report for {target_agent_id}: {e}")
            return {
                "period_days": days,
                "total_evolutions": 0,
                "evolutions_by_type": {},
                "most_evolved_entities": [],
                "evolution_timeline": [],
            }

    def get_identity_conflict_report(
        self,
        requester_id: str,
        target_agent_id: str
    ) -> Dict:
        """
        Get identity conflict report for an agent (overseer or agent's own).

        Args:
            requester_id: Requester (must be overseer or target_agent_id)
            target_agent_id: Agent whose identity conflicts to report

        Returns:
            Dict with total_conflicts, conflicts_by_type, conflicting_pairs.
        """
        if not self._can_access_agent(requester_id, target_agent_id):
            raise PermissionError(
                f"Agent '{requester_id}' cannot access identity conflicts of '{target_agent_id}'."
            )
        if not IDENTITY_GRAPH_AVAILABLE or IdentityAnalytics is None:
            return {"total_conflicts": 0, "conflicts_by_type": {}, "conflicting_pairs": []}
        try:
            identity_db_path = get_identity_graph_db_path(target_agent_id)
            if not identity_db_path.exists() and not use_shared_gateway_db(identity_db_path):
                return {"total_conflicts": 0, "conflicts_by_type": {}, "conflicting_pairs": []}
            identity_db = IdentityGraphDatabase(str(identity_db_path))
            analytics = IdentityAnalytics(identity_db)
            return analytics.get_conflict_report(agent_id=target_agent_id)
        except Exception as e:
            print(f"Error getting identity conflict report for {target_agent_id}: {e}")
            return {"total_conflicts": 0, "conflicts_by_type": {}, "conflicting_pairs": []}


# Global instance
_overseer_access_instance: Optional[OverseerAccess] = None


def get_overseer_access() -> OverseerAccess:
    """Get global overseer access instance"""
    global _overseer_access_instance
    if _overseer_access_instance is None:
        _overseer_access_instance = OverseerAccess()
    return _overseer_access_instance
