#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Identity graph database.

Stores identity components (SOUL/HEART/IDENTITY) with entity-relationship model.
Tracks 37 entity types and 14 relation types.
"""

import sqlite3
import json
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from datetime import datetime

from hg_memory.shared import DatabaseBase
from hg_gateway.shared_storage import (
    get_identity_entity,
    get_identity_versions,
    get_related_identity_entities,
    search_identity_entities,
    upsert_identity_entity,
    upsert_identity_pattern,
    upsert_identity_relation,
    upsert_identity_version,
)


# Valid entity types (37 total)
ENTITY_TYPES = [
    # Identity Layer (12)
    "name", "role", "audience", "scope", "non_negotiable", "negotiable",
    "competency", "deferral", "voice", "formatting", "tool_permission", "escalation_rule",
    # Soul Layer (10)
    "mission", "good_evil", "ideal", "goal", "priority_order", "tradeoff_policy",
    "truthfulness_policy", "alignment", "belief", "value",
    # Heart Layer (10)
    "empathy_level", "emotional_stance", "anger_handling", "insult_handling",
    "crisis_handling", "correction_style", "question_style", "de_escalation",
    "escalation", "priority",
    # Expression Layer (5)
    "trait", "speech_pattern", "emotion", "catchphrase", "engagement_pattern"
]

# Valid relation types (14 total)
RELATION_TYPES = [
    "evolves_from", "influences", "conflicts_with", "reinforces",
    "expressed_through", "relates_to", "constrains", "enables",
    "defers_to", "aligns_with", "triggers", "mitigates",
    "shapes", "governs"
]


class IdentityGraphDatabase(DatabaseBase):
    """SQLite database for identity graph with FTS5 and graph tables"""

    def __init__(self, database_path: str):
        """
        Initialize identity graph database.

        Args:
            database_path: Path to SQLite database file
        """
        self._metadata_table_name = 'identity_metadata'
        super().__init__(database_path)

    def _create_schema(self):
        """Create database schema (FTS5 table, entity table, relation table, version table, pattern table, metadata table)"""
        if self._shared_gateway_db:
            return
        conn = self._get_connection()

        try:
            # Create FTS5 virtual table for full-text search
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS identity_fts USING fts5(
                    content,
                    entity_id,
                    entity_type,
                    agent_id,
                    platform,
                    timestamp,
                    language,
                    content_normalized,
                    tokenize='unicode61'
                )
            """)

            # Create entity table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS identity_entities (
                    entity_id TEXT PRIMARY KEY,
                    entity_type TEXT NOT NULL,
                    agent_id TEXT,
                    platform TEXT,
                    timestamp TEXT NOT NULL,
                    properties TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT,
                    deleted_at TEXT
                )
            """)

            # Create relation table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS identity_relations (
                    relation_id TEXT PRIMARY KEY,
                    from_entity_id TEXT NOT NULL,
                    to_entity_id TEXT NOT NULL,
                    relation_type TEXT NOT NULL,
                    timestamp TEXT,
                    properties TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (from_entity_id) REFERENCES identity_entities(entity_id),
                    FOREIGN KEY (to_entity_id) REFERENCES identity_entities(entity_id)
                )
            """)

            # Create version table (persona file versions)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS identity_versions (
                    version_id TEXT PRIMARY KEY,
                    persona_file TEXT NOT NULL,
                    platform TEXT,
                    persona_set TEXT,
                    agent_id TEXT,
                    timestamp TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    diff_before TEXT,
                    diff_after TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            # Create pattern table (extracted patterns)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS identity_patterns (
                    pattern_id TEXT PRIMARY KEY,
                    pattern_type TEXT NOT NULL,
                    agent_id TEXT,
                    platform TEXT,
                    timestamp TEXT NOT NULL,
                    properties TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            # Create metadata table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS identity_metadata (
                    entity_id TEXT PRIMARY KEY,
                    source_file TEXT,
                    agent_id TEXT,
                    platform TEXT,
                    last_indexed TEXT,
                    file_hash TEXT,
                    FOREIGN KEY (entity_id) REFERENCES identity_entities(entity_id)
                )
            """)

            # Create schema version table for migrations
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
            """)

            # Initialize schema version if not exists
            cursor = conn.execute("SELECT COUNT(*) FROM schema_version")
            if cursor.fetchone()[0] == 0:
                conn.execute("""
                    INSERT INTO schema_version (version, applied_at)
                    VALUES (1, ?)
                """, (datetime.now().isoformat(),))

            # Create indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_type ON identity_entities(entity_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_agent ON identity_entities(agent_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_platform ON identity_entities(platform)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_timestamp ON identity_entities(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_deleted ON identity_entities(deleted_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_relations_from ON identity_relations(from_entity_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_relations_to ON identity_relations(to_entity_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_relations_type ON identity_relations(relation_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_versions_file ON identity_versions(persona_file)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_versions_agent ON identity_versions(agent_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_patterns_type ON identity_patterns(pattern_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_patterns_agent ON identity_patterns(agent_id)")

            conn.commit()
        finally:
            conn.close()

    def insert_entity(
        self,
        entity_id: str,
        entity_type: str,
        content: str,
        agent_id: Optional[str] = None,
        platform: Optional[str] = None,
        timestamp: Optional[str] = None,
        language: Optional[str] = None,
        properties: Optional[Dict] = None
    ) -> bool:
        """
        Insert an entity into the graph.

        Args:
            entity_id: Unique entity identifier
            entity_type: Type of entity (must be in ENTITY_TYPES)
            content: Text content of the entity
            agent_id: Optional agent ID
            platform: Optional platform identifier
            timestamp: Optional timestamp (ISO format)
            language: Optional language code
            properties: Optional additional properties (dict, will be JSON-encoded)

        Returns:
            True if successful, False otherwise
        """
        # Validate entity type
        if entity_type not in ENTITY_TYPES:
            raise ValueError(f"Invalid entity_type: {entity_type}. Must be one of {ENTITY_TYPES}")

        if timestamp is None:
            timestamp = datetime.now().isoformat()

        if language is None:
            from hg_memory.shared import detect_language
            language = detect_language(content)

        content_normalized = self._normalize_unicode(content)
        properties_json = json.dumps(properties or {}, ensure_ascii=False)
        now = datetime.now().isoformat()
        if self._shared_gateway_db:
            upsert_identity_entity(
                entity_id=entity_id,
                entity_type=entity_type,
                agent_id=agent_id,
                platform=platform,
                timestamp=timestamp,
                properties=properties or {},
                content=content,
                language=language,
                content_normalized=content_normalized,
            )
            return True

        conn = self._get_connection()
        try:
            # Insert into entity table
            conn.execute("""
                INSERT OR REPLACE INTO identity_entities (
                    entity_id, entity_type, agent_id, platform, timestamp, properties, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?,
                    COALESCE((SELECT created_at FROM identity_entities WHERE entity_id = ?), ?),
                    ?
                )
            """, (entity_id, entity_type, agent_id, platform, timestamp, properties_json, entity_id, now, now))

            # Insert into FTS5 table
            conn.execute("""
                INSERT OR REPLACE INTO identity_fts (
                    content, entity_id, entity_type, agent_id, platform, timestamp, language, content_normalized
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (content, entity_id, entity_type, agent_id, platform, timestamp, language, content_normalized))

            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    def insert_relation(
        self,
        from_entity_id: str,
        to_entity_id: str,
        relation_type: str,
        timestamp: Optional[str] = None,
        properties: Optional[Dict] = None
    ) -> bool:
        """
        Insert a relation between entities.

        Args:
            from_entity_id: Source entity ID
            to_entity_id: Target entity ID
            relation_type: Type of relation (must be in RELATION_TYPES)
            timestamp: Optional timestamp
            properties: Optional additional properties

        Returns:
            True if successful, False otherwise
        """
        # Validate relation type
        if relation_type not in RELATION_TYPES:
            raise ValueError(f"Invalid relation_type: {relation_type}. Must be one of {RELATION_TYPES}")

        relation_id = f"{from_entity_id}::{relation_type}::{to_entity_id}"
        properties_json = json.dumps(properties or {}, ensure_ascii=False)
        now = datetime.now().isoformat()
        if self._shared_gateway_db:
            upsert_identity_relation(
                relation_id,
                from_entity_id,
                to_entity_id,
                relation_type,
                timestamp,
                properties or {},
            )
            return True

        conn = self._get_connection()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO identity_relations (
                    relation_id, from_entity_id, to_entity_id, relation_type, timestamp, properties, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (relation_id, from_entity_id, to_entity_id, relation_type, timestamp, properties_json, now))

            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    def insert_version(
        self,
        version_id: str,
        persona_file: str,
        content_hash: str,
        platform: Optional[str] = None,
        persona_set: Optional[str] = None,
        agent_id: Optional[str] = None,
        timestamp: Optional[str] = None,
        diff_before: Optional[str] = None,
        diff_after: Optional[str] = None
    ) -> bool:
        """
        Insert a persona file version.

        Args:
            version_id: Unique version identifier
            persona_file: Persona file name (SOUL.md, HEART.md, IDENTITY.md)
            content_hash: SHA256 hash of file content
            platform: Optional platform identifier
            persona_set: Optional persona set identifier
            agent_id: Optional agent ID
            timestamp: Optional timestamp (ISO format)
            diff_before: Optional before content for diff
            diff_after: Optional after content for diff

        Returns:
            True if successful, False otherwise
        """
        if timestamp is None:
            timestamp = datetime.now().isoformat()

        now = datetime.now().isoformat()
        if self._shared_gateway_db:
            upsert_identity_version(
                version_id,
                persona_file,
                content_hash,
                platform,
                persona_set,
                agent_id,
                timestamp,
                diff_before,
                diff_after,
            )
            return True

        conn = self._get_connection()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO identity_versions (
                    version_id, persona_file, platform, persona_set, agent_id, timestamp,
                    content_hash, diff_before, diff_after, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (version_id, persona_file, platform, persona_set, agent_id, timestamp,
                  content_hash, diff_before, diff_after, now))

            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    def insert_pattern(
        self,
        pattern_id: str,
        pattern_type: str,
        agent_id: Optional[str] = None,
        platform: Optional[str] = None,
        timestamp: Optional[str] = None,
        properties: Optional[Dict] = None
    ) -> bool:
        """
        Insert an extracted pattern.

        Args:
            pattern_id: Unique pattern identifier
            pattern_type: Type of pattern (e.g., "speech", "emotion", "engagement")
            agent_id: Optional agent ID
            platform: Optional platform identifier
            timestamp: Optional timestamp (ISO format)
            properties: Optional pattern properties (dict, will be JSON-encoded)

        Returns:
            True if successful, False otherwise
        """
        if timestamp is None:
            timestamp = datetime.now().isoformat()

        properties_json = json.dumps(properties or {}, ensure_ascii=False)
        now = datetime.now().isoformat()
        if self._shared_gateway_db:
            upsert_identity_pattern(
                pattern_id,
                pattern_type,
                agent_id,
                platform,
                timestamp,
                properties or {},
            )
            return True

        conn = self._get_connection()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO identity_patterns (
                    pattern_id, pattern_type, agent_id, platform, timestamp, properties, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (pattern_id, pattern_type, agent_id, platform, timestamp, properties_json, now))

            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            raise
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
            entity = get_identity_entity(entity_id)
            if entity and entity.get("deleted_at") is None:
                return entity
            return None
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                SELECT entity_id, entity_type, agent_id, platform, timestamp, properties, created_at, updated_at
                FROM identity_entities
                WHERE entity_id = ? AND deleted_at IS NULL
            """, (entity_id,))
            result = cursor.fetchone()

            if result is None:
                return None

            properties = json.loads(result[5]) if result[5] else {}

            return {
                'entity_id': result[0],
                'entity_type': result[1],
                'agent_id': result[2],
                'platform': result[3],
                'timestamp': result[4],
                'properties': properties,
                'created_at': result[6],
                'updated_at': result[7]
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
            return get_related_identity_entities(entity_id, relation_type, direction)
        conn = self._get_connection()
        try:
            if direction == "from":
                if relation_type:
                    cursor = conn.execute("""
                        SELECT to_entity_id, relation_type, timestamp, properties
                        FROM identity_relations
                        WHERE from_entity_id = ? AND relation_type = ?
                    """, (entity_id, relation_type))
                else:
                    cursor = conn.execute("""
                        SELECT to_entity_id, relation_type, timestamp, properties
                        FROM identity_relations
                        WHERE from_entity_id = ?
                    """, (entity_id,))
            elif direction == "to":
                if relation_type:
                    cursor = conn.execute("""
                        SELECT from_entity_id, relation_type, timestamp, properties
                        FROM identity_relations
                        WHERE to_entity_id = ? AND relation_type = ?
                    """, (entity_id, relation_type))
                else:
                    cursor = conn.execute("""
                        SELECT from_entity_id, relation_type, timestamp, properties
                        FROM identity_relations
                        WHERE to_entity_id = ?
                    """, (entity_id,))
            else:  # both
                if relation_type:
                    cursor = conn.execute("""
                        SELECT
                            CASE WHEN from_entity_id = ? THEN to_entity_id ELSE from_entity_id END as related_id,
                            relation_type, timestamp, properties
                        FROM identity_relations
                        WHERE (from_entity_id = ? OR to_entity_id = ?) AND relation_type = ?
                    """, (entity_id, entity_id, entity_id, relation_type))
                else:
                    cursor = conn.execute("""
                        SELECT
                            CASE WHEN from_entity_id = ? THEN to_entity_id ELSE from_entity_id END as related_id,
                            relation_type, timestamp, properties
                        FROM identity_relations
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

    def update_entity(
        self,
        entity_id: str,
        content: Optional[str] = None,
        properties: Optional[Dict] = None,
        timestamp: Optional[str] = None
    ) -> bool:
        """
        Update an entity (creates evolves_from relationship if entity exists).

        Args:
            entity_id: Entity ID
            content: Optional new content
            properties: Optional new properties
            timestamp: Optional timestamp

        Returns:
            True if successful, False otherwise
        """
        # Get existing entity
        existing = self.get_entity(entity_id)
        if not existing:
            # Entity doesn't exist, can't update
            return False

        if timestamp is None:
            timestamp = datetime.now().isoformat()

        now = datetime.now().isoformat()

        # Update properties
        if properties:
            existing_props = existing.get('properties', {})
            existing_props.update(properties)
            properties = existing_props
        else:
            properties = existing.get('properties', {})

        properties_json = json.dumps(properties, ensure_ascii=False)

        if self._shared_gateway_db:
            return self.insert_entity(
                entity_id=entity_id,
                entity_type=existing.get("entity_type"),
                content=content or existing.get("content", ""),
                agent_id=existing.get("agent_id"),
                platform=existing.get("platform"),
                timestamp=timestamp,
                properties=properties,
            )
        conn = self._get_connection()
        try:
            # Update entity
            if content:
                content_normalized = self._normalize_unicode(content)
                from hg_memory.shared import detect_language
                language = detect_language(content)

                conn.execute("""
                    UPDATE identity_entities
                    SET properties = ?, updated_at = ?
                    WHERE entity_id = ?
                """, (properties_json, now, entity_id))

                conn.execute("""
                    UPDATE identity_fts
                    SET content = ?, content_normalized = ?, language = ?
                    WHERE entity_id = ?
                """, (content, content_normalized, language, entity_id))
            else:
                conn.execute("""
                    UPDATE identity_entities
                    SET properties = ?, updated_at = ?
                    WHERE entity_id = ?
                """, (properties_json, now, entity_id))

            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    def delete_entity(self, entity_id: str, soft_delete: bool = True) -> bool:
        """
        Delete an entity (soft delete by default).

        Args:
            entity_id: Entity ID
            soft_delete: If True, mark as deleted (don't actually delete)

        Returns:
            True if successful, False otherwise
        """
        if self._shared_gateway_db:
            return False
        conn = self._get_connection()
        try:
            if soft_delete:
                now = datetime.now().isoformat()
                conn.execute("""
                    UPDATE identity_entities
                    SET deleted_at = ?
                    WHERE entity_id = ?
                """, (now, entity_id))
            else:
                # Hard delete
                conn.execute("DELETE FROM identity_fts WHERE entity_id = ?", (entity_id,))
                conn.execute("DELETE FROM identity_relations WHERE from_entity_id = ? OR to_entity_id = ?", (entity_id, entity_id))
                conn.execute("DELETE FROM identity_entities WHERE entity_id = ?", (entity_id,))

            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_schema_version(self) -> int:
        """Get current schema version."""
        if self._shared_gateway_db:
            return 1
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT MAX(version) FROM schema_version")
            result = cursor.fetchone()
            return result[0] if result[0] else 1
        finally:
            conn.close()
