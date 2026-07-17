#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Context search interface.

Provides search across context graph with temporal and causal queries.
"""

import sqlite3
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from hg_memory.context.context_graph_db import ContextGraphDatabase
from hg_lib.language_detector import detect_language
from hg_gateway.shared_storage import search_context_entities


class ContextSearch:
    """Search interface for context graph"""
    
    def __init__(self, database: ContextGraphDatabase):
        """
        Initialize search interface.
        
        Args:
            database: ContextGraphDatabase instance
        """
        self.database = database
    
    def search_context(
        self,
        query: str,
        agent_id: Optional[str] = None,
        language: Optional[str] = None,
        time_range: Optional[Tuple[str, str]] = None,
        entity_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        Search context graph.
        
        Args:
            query: Search query
            agent_id: Optional agent ID filter
            language: Optional language code (auto-detected if None)
            time_range: Optional tuple of (start_date, end_date) in YYYY-MM-DD format
            entity_type: Optional entity type filter (e.g., "decision", "conversation")
            limit: Maximum number of results
            
        Returns:
            List of search results
        """
        if language is None:
            language = detect_language(query)
        
        # Build FTS5 query
        fts5_query = self._build_fts5_query(query)
        
        # Build WHERE clause
        where_clauses = []
        params = [fts5_query]
        
        if agent_id:
            where_clauses.append("agent_id = ?")
            params.append(agent_id)
        
        if time_range:
            start_date, end_date = time_range
            where_clauses.append("timestamp >= ?")
            params.append(start_date)
            where_clauses.append("timestamp <= ?")
            params.append(end_date)
        
        if entity_type:
            where_clauses.append("entity_type = ?")
            params.append(entity_type)
        
        where_sql = " AND " + " AND ".join(where_clauses) if where_clauses else ""
        
        if self.database._shared_gateway_db:
            return search_context_entities(
                query,
                agent_id=agent_id,
                entity_type=entity_type,
                time_range=time_range,
                limit=limit,
            )
        conn = self.database._get_connection()
        try:
            # Try bm25() first, fallback to simple match
            try:
                cursor = conn.execute(f"""
                    SELECT 
                        entity_id,
                        entity_type,
                        agent_id,
                        timestamp,
                        snippet(context_fts, 2, '<b>', '</b>', '...', 32) as snippet,
                        bm25(context_fts) as rank
                    FROM context_fts
                    WHERE context_fts MATCH ?{where_sql}
                    ORDER BY rank
                    LIMIT ?
                """, params + [limit])
            except sqlite3.OperationalError:
                cursor = conn.execute(f"""
                    SELECT 
                        entity_id,
                        entity_type,
                        agent_id,
                        timestamp,
                        snippet(context_fts, 2, '<b>', '</b>', '...', 32) as snippet,
                        1.0 as rank
                    FROM context_fts
                    WHERE context_fts MATCH ?{where_sql}
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, params + [limit])
            
            results = []
            for row in cursor.fetchall():
                entity_id = row[0]
                entity = self.database.get_entity(entity_id)
                
                if entity:
                    result = {
                        'entity_id': entity_id,
                        'entity_type': row[1],
                        'agent_id': row[2],
                        'timestamp': row[3],
                        'snippet': row[4],
                        'rank': row[5],
                        'properties': entity.get('properties', {})
                    }
                    results.append(result)
            
            return results
        finally:
            conn.close()
    
    def get_decision_chain(
        self,
        topic: str,
        agent_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Get decision chain for a topic.
        
        Args:
            topic: Topic to search for
            agent_id: Optional agent ID filter
            
        Returns:
            List of decisions in chronological order
        """
        return self.database.get_decision_chain(topic, agent_id)
    
    def get_causal_chain(
        self,
        entity_id: str,
        relation_type: str = "causes",
        direction: str = "from"
    ) -> List[Dict]:
        """
        Get causal chain (what caused this, or what this caused).
        
        Args:
            entity_id: Entity ID
            relation_type: Relation type (default: "causes")
            direction: "from" (what caused this) or "to" (what this caused)
            
        Returns:
            List of related entities
        """
        return self.database.get_related_entities(entity_id, relation_type, direction)
    
    def get_temporal_context(
        self,
        timestamp: str,
        window_hours: int = 24,
        agent_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Get context that existed around a specific time.
        
        Args:
            timestamp: ISO timestamp
            window_hours: Hours before and after to include
            agent_id: Optional agent ID filter
            
        Returns:
            List of entities in the time window
        """
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except:
            dt = datetime.now()
        
        start_dt = dt.replace(hour=dt.hour - window_hours)
        end_dt = dt.replace(hour=dt.hour + window_hours)
        
        start_date = start_dt.strftime('%Y-%m-%d')
        end_date = end_dt.strftime('%Y-%m-%d')
        
        return self.search_context(
            query="*",
            agent_id=agent_id,
            time_range=(start_date, end_date),
            limit=100
        )
    
    def _build_fts5_query(self, query: str) -> str:
        """
        Build FTS5 query string from user query.
        
        Args:
            query: User search query
            
        Returns:
            FTS5 query string
        """
        # Escape special FTS5 characters
        query = query.replace('"', '""')
        return f'"{query}"'
