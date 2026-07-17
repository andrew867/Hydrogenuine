#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
End-to-end tests for identity graph system (Phases 0-1).
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
from hg_memory.identity.config import get_identity_graph_db_path


class TestIdentityE2E(unittest.TestCase):
    """End-to-end tests for identity graph system"""
    
    def setUp(self):
        """Set up test database"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_identity_e2e.db")
        self.db = IdentityGraphDatabase(self.db_path)
    
    def tearDown(self):
        """Clean up test database"""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)
    
    def test_full_workflow(self):
        """Test complete workflow: insert entities, relations, versions, patterns"""
        agent_id = "test-agent"
        platform = "test-platform"
        
        # 1. Insert identity layer entities
        self.db.insert_entity(
            entity_id="identity:name:1",
            entity_type="name",
            content="The Underling",
            agent_id=agent_id,
            platform=platform
        )
        
        self.db.insert_entity(
            entity_id="identity:non_negotiable:1",
            entity_type="non_negotiable",
            content="No doxxing",
            agent_id=agent_id,
            platform=platform
        )
        
        self.db.insert_entity(
            entity_id="identity:competency:1",
            entity_type="competency",
            content="RF/SDR and ham radio",
            agent_id=agent_id,
            platform=platform
        )
        
        # 2. Insert soul layer entities
        self.db.insert_entity(
            entity_id="soul:mission:1",
            entity_type="mission",
            content="Expose systems that pretend to help while fucking people over",
            agent_id=agent_id,
            platform=platform
        )
        
        self.db.insert_entity(
            entity_id="soul:belief:1",
            entity_type="belief",
            content="Institutional betrayal is real",
            agent_id=agent_id,
            platform=platform
        )
        
        self.db.insert_entity(
            entity_id="soul:value:1",
            entity_type="value",
            content="Privacy and authenticity",
            agent_id=agent_id,
            platform=platform
        )
        
        # 3. Insert heart layer entities
        self.db.insert_entity(
            entity_id="heart:priority:1",
            entity_type="priority",
            content="OpSec / privacy",
            agent_id=agent_id,
            platform=platform,
            properties={"order": 1}
        )
        
        self.db.insert_entity(
            entity_id="heart:emotional_stance:1",
            entity_type="emotional_stance",
            content="Helpful but direct",
            agent_id=agent_id,
            platform=platform
        )
        
        # 4. Insert expression layer entities
        self.db.insert_entity(
            entity_id="expression:speech_pattern:1",
            entity_type="speech_pattern",
            content="Short sentences when angry",
            agent_id=agent_id,
            platform=platform
        )
        
        self.db.insert_entity(
            entity_id="expression:catchphrase:1",
            entity_type="catchphrase",
            content="full circle huh",
            agent_id=agent_id,
            platform=platform
        )
        
        # 5. Create relationships
        # Belief influences priority
        self.db.insert_relation(
            from_entity_id="soul:belief:1",
            to_entity_id="heart:priority:1",
            relation_type="influences"
        )
        
        # Value shapes priority
        self.db.insert_relation(
            from_entity_id="soul:value:1",
            to_entity_id="heart:priority:1",
            relation_type="shapes"
        )
        
        # Non-negotiable constrains behavior
        self.db.insert_relation(
            from_entity_id="identity:non_negotiable:1",
            to_entity_id="heart:priority:1",
            relation_type="constrains"
        )
        
        # Belief expressed through speech pattern
        self.db.insert_relation(
            from_entity_id="soul:belief:1",
            to_entity_id="expression:speech_pattern:1",
            relation_type="expressed_through"
        )
        
        # 6. Insert version
        self.db.insert_version(
            version_id="version:1",
            persona_file="SOUL.md",
            content_hash="abc123def456",
            platform=platform,
            agent_id=agent_id
        )
        
        # 7. Insert pattern
        self.db.insert_pattern(
            pattern_id="pattern:speech:1",
            pattern_type="speech",
            agent_id=agent_id,
            platform=platform,
            properties={
                "sentence_length": 8.5,
                "profanity_density": 0.15,
                "capitalization": "lowercase"
            }
        )
        
        # 8. Verify all entities exist
        entities = [
            "identity:name:1",
            "identity:non_negotiable:1",
            "identity:competency:1",
            "soul:mission:1",
            "soul:belief:1",
            "soul:value:1",
            "heart:priority:1",
            "heart:emotional_stance:1",
            "expression:speech_pattern:1",
            "expression:catchphrase:1"
        ]
        
        for entity_id in entities:
            entity = self.db.get_entity(entity_id)
            self.assertIsNotNone(entity, f"Entity {entity_id} should exist")
            self.assertEqual(entity['agent_id'], agent_id)
            self.assertEqual(entity['platform'], platform)
        
        # 9. Verify relationships
        # Belief should influence priority
        related = self.db.get_related_entities("soul:belief:1", relation_type="influences")
        self.assertEqual(len(related), 1)
        self.assertEqual(related[0]['entity_id'], "heart:priority:1")
        
        # Priority should be influenced by belief
        related = self.db.get_related_entities("heart:priority:1", relation_type="influences", direction="to")
        self.assertEqual(len(related), 1)
        self.assertEqual(related[0]['entity_id'], "soul:belief:1")
        
        # Belief should be expressed through speech pattern
        related = self.db.get_related_entities("soul:belief:1", relation_type="expressed_through")
        self.assertEqual(len(related), 1)
        self.assertEqual(related[0]['entity_id'], "expression:speech_pattern:1")
        
        # 10. Verify version
        conn = self.db._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM identity_versions WHERE version_id = ?",
                ("version:1",)
            )
            version = cursor.fetchone()
            self.assertIsNotNone(version)
            self.assertEqual(version[1], "SOUL.md")
            self.assertEqual(version[4], agent_id)
        finally:
            conn.close()
        
        # 11. Verify pattern
        conn = self.db._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM identity_patterns WHERE pattern_id = ?",
                ("pattern:speech:1",)
            )
            pattern = cursor.fetchone()
            self.assertIsNotNone(pattern)
            self.assertEqual(pattern[1], "speech")
            
            # Check properties
            import json
            properties = json.loads(pattern[5])
            self.assertEqual(properties['sentence_length'], 8.5)
            self.assertEqual(properties['profanity_density'], 0.15)
        finally:
            conn.close()
        
        # 12. Test update entity
        self.db.update_entity(
            "soul:belief:1",
            content="Updated belief content",
            properties={"updated": True, "reason": "test"}
        )
        
        updated = self.db.get_entity("soul:belief:1")
        self.assertIsNotNone(updated)
        self.assertEqual(updated['properties'].get('updated'), True)
        
        # 13. Test soft delete
        self.db.delete_entity("expression:catchphrase:1", soft_delete=True)
        deleted = self.db.get_entity("expression:catchphrase:1")
        self.assertIsNone(deleted)  # Should be filtered out
    
    def test_all_entity_types(self):
        """Test that all entity types can be inserted"""
        for i, entity_type in enumerate(ENTITY_TYPES):
            entity_id = f"test:{entity_type}:{i}"
            result = self.db.insert_entity(
                entity_id=entity_id,
                entity_type=entity_type,
                content=f"Test content for {entity_type}"
            )
            self.assertTrue(result, f"Failed to insert entity type {entity_type}")
            
            # Verify it was inserted
            entity = self.db.get_entity(entity_id)
            self.assertIsNotNone(entity, f"Entity type {entity_type} should be retrievable")
            self.assertEqual(entity['entity_type'], entity_type)
    
    def test_all_relation_types(self):
        """Test that all relation types can be created"""
        # Create two test entities
        self.db.insert_entity("test:entity:1", "belief", "Test belief")
        self.db.insert_entity("test:entity:2", "priority", "Test priority")
        
        for relation_type in RELATION_TYPES:
            result = self.db.insert_relation(
                from_entity_id="test:entity:1",
                to_entity_id="test:entity:2",
                relation_type=relation_type
            )
            self.assertTrue(result, f"Failed to create relation type {relation_type}")
            
            # Verify relation exists
            related = self.db.get_related_entities("test:entity:1", relation_type=relation_type)
            self.assertEqual(len(related), 1, f"Relation type {relation_type} should exist")
            self.assertEqual(related[0]['entity_id'], "test:entity:2")
            
            # Delete relation for next iteration
            conn = self.db._get_connection()
            try:
                relation_id = f"test:entity:1::{relation_type}::test:entity:2"
                conn.execute("DELETE FROM identity_relations WHERE relation_id = ?", (relation_id,))
                conn.commit()
            finally:
                conn.close()


if __name__ == '__main__':
    unittest.main()

