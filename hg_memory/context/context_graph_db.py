#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Context graph database.

Stores decision context, conversations, thread relationships with entity-relationship model.
"""

import sqlite3
import json
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from datetime import datetime

from hg_memory.shared import DatabaseBase
from hg_gateway.shared_storage import (
    get_context_decision_chain,
    get_context_entity,
    get_related_context_entities,
    upsert_context_entity,
    upsert_context_relation,
)


class ContextGraphDatabase(DatabaseBase):
    """SQLite database for context graph with FTS5 and graph tables"""
    
    def __init__(self, database_path: str):
        """
        Initialize context graph database.
        
        Args:
            database_path: Path to SQLite database file
        """
        self._metadata_table_name = 'context_metadata'
        super().__init__(database_path)
    
    def _create_schema(self):
        """Create database schema (FTS5 table, entity table, relation table, metadata table)"""
        if self._shared_gateway_db:
            return
        conn = self._get_connection()
        
        try:
            # Create FTS5 virtual table for full-text search
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS context_fts USING fts5(
                    content,
                    entity_id,
                    entity_type,
                    agent_id,
                    timestamp,
                    language,
                    content_normalized,
                    tokenize='unicode61'
                )
            """)
            
            # Create entity table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS context_entities (
                    entity_id TEXT PRIMARY KEY,
                    entity_type TEXT NOT NULL,
                    agent_id TEXT,
                    timestamp TEXT NOT NULL,
                    properties TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            
            # Create relation table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS context_relations (
                    relation_id TEXT PRIMARY KEY,
                    from_entity_id TEXT NOT NULL,
                    to_entity_id TEXT NOT NULL,
                    relation_type TEXT NOT NULL,
                    timestamp TEXT,
                    properties TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (from_entity_id) REFERENCES context_entities(entity_id),
                    FOREIGN KEY (to_entity_id) REFERENCES context_entities(entity_id)
                )
            """)
            
            # Create metadata table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS context_metadata (
                    entity_id TEXT PRIMARY KEY,
                    source_file TEXT,
                    agent_id TEXT,
                    last_indexed TEXT,
                    file_hash TEXT,
                    FOREIGN KEY (entity_id) REFERENCES context_entities(entity_id)
                )
            """)
            
            # Create indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_type ON context_entities(entity_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_agent ON context_entities(agent_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_timestamp ON context_entities(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_relations_from ON context_relations(from_entity_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_relations_to ON context_relations(to_entity_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_relations_type ON context_relations(relation_type)")
            
            conn.commit()
        finally:
            conn.close()
    
    def insert_entity(
        self,
        entity_id: str,
        entity_type: str,
        content: str,
        agent_id: Optional[str] = None,
        timestamp: Optional[str] = None,
        language: Optional[str] = None,
        properties: Optional[Dict] = None
    ):
        """
        Insert an entity into the graph.
        
        Args:
            entity_id: Unique entity identifier
            entity_type: Type of entity (e.g., "decision", "conversation", "thread", "event")
            content: Text content of the entity
            agent_id: Optional agent ID
            timestamp: Optional timestamp (ISO format)
            language: Optional language code
            properties: Optional additional properties (dict, will be JSON-encoded)
        """
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        if language is None:
            from .shared.language_detector import detect_language
            language = detect_language(content)
        
        content_normalized = self._normalize_unicode(content)
        properties_json = json.dumps(properties or {}, ensure_ascii=False)
        now = datetime.now().isoformat()
        if self._shared_gateway_db:
            upsert_context_entity(
                entity_id=entity_id,
                entity_type=entity_type,
                agent_id=agent_id,
                timestamp=timestamp,
                properties=properties or {},
                content=content,
                language=language,
                content_normalized=content_normalized,
            )
            return
        
        conn = self._get_connection()
        try:
            # Insert into entity table
            conn.execute("""
                INSERT OR REPLACE INTO context_entities (
                    entity_id, entity_type, agent_id, timestamp, properties, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (entity_id, entity_type, agent_id, timestamp, properties_json, now))
            
            # Insert into FTS5 table
            conn.execute("""
                INSERT OR REPLACE INTO context_fts (
                    content, entity_id, entity_type, agent_id, timestamp, language, content_normalized
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (content, entity_id, entity_type, agent_id, timestamp, language, content_normalized))
            
            conn.commit()
        finally:
            conn.close()
    
    def insert_relation(
        self,
        from_entity_id: str,
        to_entity_id: str,
        relation_type: str,
        timestamp: Optional[str] = None,
        properties: Optional[Dict] = None
    ):
        """
        Insert a relation between entities.
        
        Args:
            from_entity_id: Source entity ID
            to_entity_id: Target entity ID
            relation_type: Type of relation (e.g., "precedes", "follows", "references", "responds_to", "causes", "involves")
            timestamp: Optional timestamp
            properties: Optional additional properties
        """
        relation_id = f"{from_entity_id}::{relation_type}::{to_entity_id}"
        properties_json = json.dumps(properties or {}, ensure_ascii=False)
        now = datetime.now().isoformat()
        if self._shared_gateway_db:
            upsert_context_relation(
                relation_id=relation_id,
                from_entity_id=from_entity_id,
                to_entity_id=to_entity_id,
                relation_type=relation_type,
                timestamp=timestamp,
                properties=properties or {},
            )
            return
        
        if self._shared_gateway_db:
            return get_context_entity(entity_id)
        conn = self._get_connection()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO context_relations (
                    relation_id, from_entity_id, to_entity_id, relation_type, timestamp, properties, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (relation_id, from_entity_id, to_entity_id, relation_type, timestamp, properties_json, now))
            
            conn.commit()
        finally:
            conn.close()
    
    def get_entity(self, entity_id: str) -> Optional[Dict]:
        """
        Get entity by ID.
        
        Args:
            entity_id: Entity ID
            
        Returns:
            Entity dictionary or None if not found
        """
        if self._shared_gateway_db:
            return get_context_entity(entity_id)
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT entity_id, entity_type, agent_id, timestamp, properties, created_at "
                "FROM context_entities WHERE entity_id = ?",
                (entity_id,)
            )
            result = cursor.fetchone()
            
            if result is None:
                return None
            
            properties = json.loads(result[4]) if result[4] else {}
            
            return {
                'entity_id': result[0],
                'entity_type': result[1],
                'agent_id': result[2],
                'timestamp': result[3],
                'properties': properties,
                'created_at': result[5]
            }
        finally:
            conn.close()
    
    def get_related_entities(
        self,
        entity_id: str,
        relation_type: Optional[str] = None,
        direction: str = "both"
    ) -> List[Dict]:
        """
        Get entities related to a given entity.
        
        Args:
            entity_id: Entity ID
            relation_type: Optional relation type filter
            direction: "from" (outgoing), "to" (incoming), or "both"
            
        Returns:
            List of related entity dictionaries
        """
        if self._shared_gateway_db:
            return get_related_context_entities(
                entity_id,
                relation_type=relation_type,
                direction=direction,
            )
        conn = self._get_connection()
        try:
            if direction == "from":
                if relation_type:
                    cursor = conn.execute("""
                        SELECT to_entity_id, relation_type, timestamp, properties
                        FROM context_relations
                        WHERE from_entity_id = ? AND relation_type = ?
                    """, (entity_id, relation_type))
                else:
                    cursor = conn.execute("""
                        SELECT to_entity_id, relation_type, timestamp, properties
                        FROM context_relations
                        WHERE from_entity_id = ?
                    """, (entity_id,))
            elif direction == "to":
                if relation_type:
                    cursor = conn.execute("""
                        SELECT from_entity_id, relation_type, timestamp, properties
                        FROM context_relations
                        WHERE to_entity_id = ? AND relation_type = ?
                    """, (entity_id, relation_type))
                else:
                    cursor = conn.execute("""
                        SELECT from_entity_id, relation_type, timestamp, properties
                        FROM context_relations
                        WHERE to_entity_id = ?
                    """, (entity_id,))
            else:  # both
                if relation_type:
                    cursor = conn.execute("""
                        SELECT 
                            CASE WHEN from_entity_id = ? THEN to_entity_id ELSE from_entity_id END as related_id,
                            relation_type, timestamp, properties
                        FROM context_relations
                        WHERE (from_entity_id = ? OR to_entity_id = ?) AND relation_type = ?
                    """, (entity_id, entity_id, entity_id, relation_type))
                else:
                    cursor = conn.execute("""
                        SELECT 
                            CASE WHEN from_entity_id = ? THEN to_entity_id ELSE from_entity_id END as related_id,
                            relation_type, timestamp, properties
                        FROM context_relations
                        WHERE from_entity_id = ? OR to_entity_id = ?
                    """, (entity_id, entity_id, entity_id))
            
            results = []
            for row in cursor.fetchall():
                related_id = row[0]
                entity = self.get_entity(related_id)
                if entity:
                    entity['relation_type'] = row[1]
                    entity['relation_timestamp'] = row[2]
                    if row[3]:
                        entity['relation_properties'] = json.loads(row[3])
                    results.append(entity)
            
            return results
        finally:
            conn.close()
    
    def get_decision_chain(self, topic: str, agent_id: Optional[str] = None) -> List[Dict]:
        """
        Get decision chain for a topic (decisions linked by "precedes" or "follows").
        
        Args:
            topic: Topic to search for
            agent_id: Optional agent ID filter
            
        Returns:
            List of decisions in chronological order
        """
        # First, find entities related to the topic
        conn = self._get_connection()
        try:
            # Search FTS5 for topic
            cursor = conn.execute("""
                SELECT entity_id, entity_type, agent_id, timestamp
                FROM context_fts
                WHERE context_fts MATCH ? AND entity_type = 'decision'
                ORDER BY timestamp ASC
            """, (f'"{topic}"',))
            
            entity_ids = [row[0] for row in cursor.fetchall()]
            
            if not entity_ids:
                return []
            
            # Filter by agent_id if provided
            if agent_id:
                filtered_ids = []
                for eid in entity_ids:
                    entity = self.get_entity(eid)
                    if entity and entity.get('agent_id') == agent_id:
                        filtered_ids.append(eid)
                entity_ids = filtered_ids
            
            # Get all related decisions
            all_decisions = []
            for eid in entity_ids:
                entity = self.get_entity(eid)
                if entity:
                    all_decisions.append(entity)
                    # Get related decisions
                    related = self.get_related_entities(eid, relation_type="precedes", direction="from")
                    all_decisions.extend(related)
                    related = self.get_related_entities(eid, relation_type="follows", direction="to")
                    all_decisions.extend(related)
            
            # Sort by timestamp
            all_decisions.sort(key=lambda x: x.get('timestamp', ''))
            
            # Remove duplicates
            seen = set()
            unique_decisions = []
            for decision in all_decisions:
                if decision['entity_id'] not in seen:
                    seen.add(decision['entity_id'])
                    unique_decisions.append(decision)
            
            return unique_decisions
        finally:
            conn.close()
