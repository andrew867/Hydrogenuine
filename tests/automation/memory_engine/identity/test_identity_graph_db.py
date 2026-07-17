#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for identity graph database.
"""

import unittest
import tempfile
import os
from pathlib import Path

from hg_memory.identity.identity_graph_db import (
    IdentityGraphDatabase,
    ENTITY_TYPES,
    RELATION_TYPES
)


class TestIdentityGraphDatabase(unittest.TestCase):
    """Test identity graph database"""
    
    def setUp(self):
        """Set up test database"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_identity.db")
        self.db = IdentityGraphDatabase(self.db_path)
    
    def tearDown(self):
        """Clean up test database"""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)
    
    def test_schema_creation(self):
        """Test that schema is created correctly"""
        conn = self.db._get_connection()
        try:
            # Check that all tables exist
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' 
                ORDER BY name
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            expected_tables = [
                'identity_entities', 'identity_fts', 'identity_metadata',
                'identity_patterns', 'identity_relations', 'identity_versions',
                'schema_version'
            ]
            
            for table in expected_tables:
                self.assertIn(table, tables, f"Table {table} should exist")
        finally:
            conn.close()
    
    def test_insert_entity(self):
        """Test inserting an entity"""
        entity_id = "test:entity:1"
        result = self.db.insert_entity(
            entity_id=entity_id,
            entity_type="belief",
            content="Test belief content",
            agent_id="test-agent",
            platform="test-platform"
        )
        
        self.assertTrue(result)
        
        # Verify entity was inserted
        entity = self.db.get_entity(entity_id)
        self.assertIsNotNone(entity)
        self.assertEqual(entity['entity_type'], "belief")
        self.assertEqual(entity['agent_id'], "test-agent")
        self.assertEqual(entity['platform'], "test-platform")
    
    def test_insert_entity_invalid_type(self):
        """Test that invalid entity type raises error"""
        with self.assertRaises(ValueError):
            self.db.insert_entity(
                entity_id="test:entity:1",
                entity_type="invalid_type",
                content="Test content"
            )
    
    def test_insert_relation(self):
        """Test inserting a relation"""
        # Insert two entities first
        self.db.insert_entity("entity:1", "belief", "Belief 1")
        self.db.insert_entity("entity:2", "priority", "Priority 1")
        
        # Insert relation
        result = self.db.insert_relation(
            from_entity_id="entity:1",
            to_entity_id="entity:2",
            relation_type="influences"
        )
        
        self.assertTrue(result)
        
        # Verify relation
        related = self.db.get_related_entities("entity:1", relation_type="influences")
        self.assertEqual(len(related), 1)
        self.assertEqual(related[0]['entity_id'], "entity:2")
    
    def test_insert_relation_invalid_type(self):
        """Test that invalid relation type raises error"""
        self.db.insert_entity("entity:1", "belief", "Belief 1")
        self.db.insert_entity("entity:2", "priority", "Priority 1")
        
        with self.assertRaises(ValueError):
            self.db.insert_relation(
                from_entity_id="entity:1",
                to_entity_id="entity:2",
                relation_type="invalid_relation"
            )
    
    def test_insert_version(self):
        """Test inserting a version"""
        result = self.db.insert_version(
            version_id="version:1",
            persona_file="SOUL.md",
            content_hash="abc123",
            platform="test-platform",
            agent_id="test-agent"
        )
        
        self.assertTrue(result)
        
        # Verify version was inserted
        conn = self.db._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM identity_versions WHERE version_id = ?",
                ("version:1",)
            )
            result = cursor.fetchone()
            self.assertIsNotNone(result)
            self.assertEqual(result[1], "SOUL.md")
        finally:
            conn.close()
    
    def test_insert_pattern(self):
        """Test inserting a pattern"""
        result = self.db.insert_pattern(
            pattern_id="pattern:1",
            pattern_type="speech",
            agent_id="test-agent",
            properties={"sentence_length": 10, "profanity_density": 0.1}
        )
        
        self.assertTrue(result)
        
        # Verify pattern was inserted
        conn = self.db._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM identity_patterns WHERE pattern_id = ?",
                ("pattern:1",)
            )
            result = cursor.fetchone()
            self.assertIsNotNone(result)
            self.assertEqual(result[1], "speech")
        finally:
            conn.close()
    
    def test_get_entity(self):
        """Test getting an entity"""
        self.db.insert_entity("entity:1", "belief", "Test belief")
        
        entity = self.db.get_entity("entity:1")
        self.assertIsNotNone(entity)
        self.assertEqual(entity['entity_id'], "entity:1")
        self.assertEqual(entity['entity_type'], "belief")
    
    def test_get_entity_not_found(self):
        """Test getting non-existent entity"""
        entity = self.db.get_entity("nonexistent")
        self.assertIsNone(entity)
    
    def test_get_related_entities(self):
        """Test getting related entities"""
        # Insert entities
        self.db.insert_entity("entity:1", "belief", "Belief 1")
        self.db.insert_entity("entity:2", "priority", "Priority 1")
        self.db.insert_entity("entity:3", "value", "Value 1")
        
        # Insert relations
        self.db.insert_relation("entity:1", "entity:2", "influences")
        self.db.insert_relation("entity:1", "entity:3", "shapes")
        
        # Get related entities
        related = self.db.get_related_entities("entity:1")
        self.assertEqual(len(related), 2)
        
        # Get related with specific relation type
        related = self.db.get_related_entities("entity:1", relation_type="influences")
        self.assertEqual(len(related), 1)
        self.assertEqual(related[0]['entity_id'], "entity:2")
    
    def test_update_entity(self):
        """Test updating an entity"""
        self.db.insert_entity("entity:1", "belief", "Original content")
        
        result = self.db.update_entity(
            "entity:1",
            content="Updated content",
            properties={"updated": True}
        )
        
        self.assertTrue(result)
        
        entity = self.db.get_entity("entity:1")
        self.assertIsNotNone(entity)
        self.assertEqual(entity['properties'].get('updated'), True)
    
    def test_delete_entity_soft(self):
        """Test soft deleting an entity"""
        self.db.insert_entity("entity:1", "belief", "Test content")
        
        result = self.db.delete_entity("entity:1", soft_delete=True)
        self.assertTrue(result)
        
        # Entity should still exist but be marked as deleted
        entity = self.db.get_entity("entity:1")
        self.assertIsNone(entity)  # get_entity filters out deleted
    
    def test_delete_entity_hard(self):
        """Test hard deleting an entity"""
        self.db.insert_entity("entity:1", "belief", "Test content")
        
        result = self.db.delete_entity("entity:1", soft_delete=False)
        self.assertTrue(result)
        
        # Entity should be completely removed
        entity = self.db.get_entity("entity:1")
        self.assertIsNone(entity)
    
    def test_get_schema_version(self):
        """Test getting schema version"""
        version = self.db.get_schema_version()
        self.assertEqual(version, 1)


if __name__ == '__main__':
    unittest.main()

