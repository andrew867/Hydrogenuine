#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Identity graph search interface.

Provides full-text search, graph traversal, and evolution queries for identity components.
"""

import sqlite3
from typing import List, Dict, Optional
from datetime import datetime

from .identity_graph_db import IdentityGraphDatabase
from hg_memory.shared import detect_language
from hg_gateway.shared_storage import get_identity_versions, search_identity_entities


class IdentitySearch:
    """Search interface for identity graph"""
    
    def __init__(self, database: IdentityGraphDatabase):
        """
        Initialize search interface.
        
        Args:
            database: IdentityGraphDatabase instance
        """
        self.database = database

    def _entity_table(self) -> str:
        return "memory_identity_entities" if self.database._shared_gateway_db else "identity_entities"

    def _relation_table(self) -> str:
        return "memory_identity_relations" if self.database._shared_gateway_db else "identity_relations"
    
    def search_identity(
        self,
        query: str,
        agent_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        language: Optional[str] = None,
        limit: int = 10,
        platform: Optional[str] = None
    ) -> List[Dict]:
        """
        Search identity components using full-text search.
        
        Args:
            query: Search query
            agent_id: Optional agent ID filter
            entity_type: Optional entity type filter
            language: Optional language code (auto-detected if None)
            limit: Maximum number of results
            platform: Optional platform filter
            
        Returns:
            List of search results with entity information
        """
        query = (query or "").strip()
        if language is None and query:
            language = detect_language(query)

        # Build WHERE clause for filters (used for both FTS and list path)
        where_clauses = []
        filter_params = []
        if agent_id:
            where_clauses.append("ift.agent_id = ?")
            filter_params.append(agent_id)
        if entity_type:
            where_clauses.append("ift.entity_type = ?")
            filter_params.append(entity_type)
        if platform:
            where_clauses.append("ift.platform = ?")
            filter_params.append(platform)
        where_sql = " AND " + " AND ".join(where_clauses) if where_clauses else ""

        if self.database._shared_gateway_db:
            return search_identity_entities(
                query,
                agent_id=agent_id,
                entity_type=entity_type,
                platform=platform,
                limit=limit,
            )
        conn = self.database._get_connection()
        try:
            # Empty query: list entities without FTS (FTS5 MATCH "" is invalid)
            if not query:
                cursor = conn.execute(f"""
                    SELECT
                        ift.entity_id,
                        ift.entity_type,
                        ift.agent_id,
                        ift.platform,
                        ift.timestamp,
                        ift.language
                    FROM identity_fts ift
                    WHERE 1=1{(" AND " + " AND ".join(where_clauses)) if where_clauses else ""}
                    LIMIT ?
                """, filter_params + [limit])
                rows = cursor.fetchall()
            else:
                # Build FTS5 query (non-empty only)
                fts5_query = self._build_fts5_query(query)
                params = [fts5_query] + filter_params
                # Try bm25() first, fallback to simple match if not available
                try:
                    cursor = conn.execute(f"""
                        SELECT 
                            ift.entity_id,
                            ift.entity_type,
                            ift.agent_id,
                            ift.platform,
                            ift.timestamp,
                            ift.language,
                            snippet(identity_fts, 2, '<b>', '</b>', '...', 32) as snippet,
                            bm25(identity_fts) as rank
                        FROM identity_fts ift
                        WHERE identity_fts MATCH ?{where_sql}
                        ORDER BY rank
                        LIMIT ?
                    """, params + [limit])
                except sqlite3.OperationalError:
                    cursor = conn.execute(f"""
                        SELECT 
                            ift.entity_id,
                            ift.entity_type,
                            ift.agent_id,
                            ift.platform,
                            ift.timestamp,
                            ift.language,
                            snippet(identity_fts, 2, '<b>', '</b>', '...', 32) as snippet,
                            1.0 as rank
                        FROM identity_fts ift
                        WHERE identity_fts MATCH ?{where_sql}
                        LIMIT ?
                    """, params + [limit])
                rows = cursor.fetchall()

            results = []
            has_snippet_rank = len(rows) > 0 and len(rows[0]) >= 8
            for row in rows:
                entity_id = row[0]
                entity = self.database.get_entity(entity_id)
                if entity:
                    content = entity.get('properties', {}).get('content', '') or entity.get('content', '')
                    result = {
                        'entity_id': entity_id,
                        'entity_type': row[1],
                        'agent_id': row[2],
                        'platform': row[3],
                        'timestamp': row[4],
                        'language': row[5],
                        'snippet': row[6] if has_snippet_rank else (content[:32] + '...' if len(content) > 32 else content),
                        'rank': row[7] if has_snippet_rank else 1.0,
                        'content': content,
                        'properties': entity.get('properties', {})
                    }
                    results.append(result)
            
            return results
        finally:
            conn.close()
    
    def get_evolution_chain(
        self,
        entity_id: str,
        max_depth: int = 10
    ) -> List[Dict]:
        """
        Get evolution chain for an entity (follows evolves_from relationships).
        
        Args:
            entity_id: Starting entity ID
            max_depth: Maximum depth to traverse
            
        Returns:
            List of entities in evolution chain (newest first)
        """
        chain = []
        visited = set()
        current_id = entity_id
        depth = 0
        
        while current_id and depth < max_depth:
            if current_id in visited:
                break  # Circular reference
            
            visited.add(current_id)
            entity = self.database.get_entity(current_id)
            if not entity:
                break
            
            chain.append(entity)
            
            # Find evolves_from relationship
            related = self.database.get_related_entities(
                current_id,
                relation_type='evolves_from',
                direction='from'
            )
            
            if related:
                # Get the entity this evolved from
                current_id = related[0].get('entity_id')
                depth += 1
            else:
                break
        
        return chain
    
    def get_entity_relationships(
        self,
        entity_id: str,
        relation_type: Optional[str] = None,
        direction: str = "both"
    ) -> Dict[str, List[Dict]]:
        """
        Get all relationships for an entity, organized by relation type.
        
        Args:
            entity_id: Entity ID
            relation_type: Optional relation type filter
            direction: "from" (outgoing), "to" (incoming), or "both"
            
        Returns:
            Dictionary mapping relation types to lists of related entities
        """
        related = self.database.get_related_entities(
            entity_id,
            relation_type=relation_type,
            direction=direction
        )
        
        # Organize by relation type
        relationships = {}
        for rel in related:
            rel_type = rel.get('relation_type', 'unknown')
            if rel_type not in relationships:
                relationships[rel_type] = []
            relationships[rel_type].append(rel)
        
        return relationships
    
    def search_by_layer(
        self,
        layer: str,
        agent_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Search entities by identity layer.
        
        Args:
            layer: Layer name ("identity", "soul", "heart", "expression")
            agent_id: Optional agent ID filter
            limit: Maximum number of results
            
        Returns:
            List of entities in the specified layer
        """
        # Map layer to entity types
        layer_entity_types = {
            "identity": ["name", "role", "audience", "scope", "non_negotiable", "negotiable",
                        "competency", "deferral", "voice", "formatting", "tool_permission", "escalation_rule"],
            "soul": ["mission", "good_evil", "ideal", "goal", "priority_order", "tradeoff_policy",
                    "truthfulness_policy", "alignment", "belief", "value"],
            "heart": ["empathy_level", "emotional_stance", "anger_handling", "insult_handling",
                     "crisis_handling", "correction_style", "question_style", "de_escalation",
                     "escalation", "priority"],
            "expression": ["trait", "speech_pattern", "emotion", "catchphrase", "engagement_pattern"]
        }
        
        entity_types = layer_entity_types.get(layer.lower(), [])
        if not entity_types:
            return []
        
        if self.database._shared_gateway_db:
            results = []
            for entity_type_name in entity_types:
                results.extend(
                    search_identity_entities(
                        "",
                        agent_id=agent_id,
                        entity_type=entity_type_name,
                        platform=None,
                        limit=limit,
                    )
                )
            return results[:limit]
        conn = self.database._get_connection()
        try:
            placeholders = ','.join(['?'] * len(entity_types))
            params = list(entity_types)
            
            if agent_id:
                query = f"""
                    SELECT entity_id
                    FROM identity_entities
                    WHERE entity_type IN ({placeholders}) AND agent_id = ? AND deleted_at IS NULL
                    LIMIT ?
                """
                params.append(agent_id)
            else:
                query = f"""
                    SELECT entity_id
                    FROM identity_entities
                    WHERE entity_type IN ({placeholders}) AND deleted_at IS NULL
                    LIMIT ?
                """
            
            params.append(limit)
            cursor = conn.execute(query, params)
            
            results = []
            for row in cursor.fetchall():
                entity = self.database.get_entity(row[0])
                if entity:
                    results.append(entity)
            
            return results
        finally:
            conn.close()
    
    def get_version_history(
        self,
        persona_file: str,
        agent_id: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        Get version history for a persona file.
        
        Args:
            persona_file: Persona file name (SOUL.md, HEART.md, IDENTITY.md)
            agent_id: Optional agent ID filter
            limit: Maximum number of versions
            
        Returns:
            List of version records (newest first)
        """
        if self.database._shared_gateway_db:
            return get_identity_versions(persona_file, agent_id, limit)
        conn = self.database._get_connection()
        try:
            if agent_id:
                cursor = conn.execute("""
                    SELECT version_id, persona_file, content_hash, platform, persona_set,
                           agent_id, timestamp, diff_before, diff_after
                    FROM identity_versions
                    WHERE persona_file = ? AND agent_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (persona_file, agent_id, limit))
            else:
                cursor = conn.execute("""
                    SELECT version_id, persona_file, content_hash, platform, persona_set,
                           agent_id, timestamp, diff_before, diff_after
                    FROM identity_versions
                    WHERE persona_file = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (persona_file, limit))
            
            results = []
            for row in cursor.fetchall():
                result = {
                    'version_id': row[0],
                    'persona_file': row[1],
                    'content_hash': row[2],
                    'platform': row[3],
                    'persona_set': row[4],
                    'agent_id': row[5],
                    'timestamp': row[6],
                    'diff_before': row[7],
                    'diff_after': row[8]
                }
                results.append(result)
            
            return results
        finally:
            conn.close()
    
    def find_conflicts(
        self,
        agent_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Find entities with conflicts_with relationships.
        
        Args:
            agent_id: Optional agent ID filter
            
        Returns:
            List of conflict pairs
        """
        conn = self.database._get_connection()
        try:
            entity_table = self._entity_table()
            relation_table = self._relation_table()
            if agent_id:
                cursor = conn.execute(f"""
                    SELECT 
                        ir.from_entity_id,
                        ir.to_entity_id,
                        ir.timestamp,
                        ir.properties,
                        e1.entity_type as from_type,
                        e2.entity_type as to_type
                    FROM {relation_table} ir
                    JOIN {entity_table} e1 ON ir.from_entity_id = e1.entity_id
                    JOIN {entity_table} e2 ON ir.to_entity_id = e2.entity_id
                    WHERE ir.relation_type = 'conflicts_with'
                      AND (e1.agent_id = ? OR e2.agent_id = ?)
                      AND e1.deleted_at IS NULL
                      AND e2.deleted_at IS NULL
                """, (agent_id, agent_id))
            else:
                cursor = conn.execute(f"""
                    SELECT 
                        ir.from_entity_id,
                        ir.to_entity_id,
                        ir.timestamp,
                        ir.properties,
                        e1.entity_type as from_type,
                        e2.entity_type as to_type
                    FROM {relation_table} ir
                    JOIN {entity_table} e1 ON ir.from_entity_id = e1.entity_id
                    JOIN {entity_table} e2 ON ir.to_entity_id = e2.entity_id
                    WHERE ir.relation_type = 'conflicts_with'
                      AND e1.deleted_at IS NULL
                      AND e2.deleted_at IS NULL
                """)
            
            results = []
            for row in cursor.fetchall():
                result = {
                    'from_entity_id': row[0],
                    'to_entity_id': row[1],
                    'timestamp': row[2],
                    'properties': row[3],
                    'from_type': row[4],
                    'to_type': row[5],
                    'from_entity': self.database.get_entity(row[0]),
                    'to_entity': self.database.get_entity(row[1])
                }
                results.append(result)
            
            return results
        finally:
            conn.close()
    
    def _build_fts5_query(self, query: str) -> str:
        """
        Build FTS5 query string from user query.
        
        Args:
            query: User query string
            
        Returns:
            FTS5 query string
        """
        # Escape special FTS5 characters
        query = query.replace('"', '""')
        
        # If query contains spaces, wrap in quotes for phrase search
        if ' ' in query:
            return f'"{query}"'
        else:
            return query
