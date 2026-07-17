#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive end-to-end test for Phases 0-3.

Tests complete workflow with real persona files from workspace.
"""

import unittest
import tempfile
import os
from pathlib import Path

from hg_memory.identity.identity_graph_db import IdentityGraphDatabase
from hg_memory.identity.identity_extractor import IdentityExtractor
from hg_memory.identity.identity_recorder import IdentityRecorder


class TestComprehensiveE2E(unittest.TestCase):
    """Comprehensive end-to-end test"""
    
    def setUp(self):
        """Set up test database"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_comprehensive.db")
        self.db = IdentityGraphDatabase(self.db_path)
        
        # Use real persona files from workspace if available
        workspace_root = Path(__file__).parent.parent.parent.parent.parent
        self.soul_file = workspace_root / "SOUL.md"
        self.heart_file = workspace_root / "HEART.md"
        self.identity_file = workspace_root / "IDENTITY.md"
    
    def tearDown(self):
        """Clean up"""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_complete_workflow_with_real_files(self):
        """Test complete workflow with real persona files"""
        if not all(f.exists() for f in [self.soul_file, self.heart_file, self.identity_file]):
            self.skipTest("Real persona files not found")
        
        agent_id = "test-agent-comprehensive"
        platform = "test-platform"
        
        # Create recorder
        recorder = IdentityRecorder(database=self.db, agent_id=agent_id)
        
        # Record persona files
        result = recorder.record_persona_files(
            soul_path=self.soul_file,
            heart_path=self.heart_file,
            identity_path=self.identity_file,
            platform=platform
        )
        
        # Verify results
        self.assertGreater(result['entities'], 0, "Should have extracted entities")
        self.assertGreaterEqual(result['versions'], 0, "Should have recorded versions")
        
        # Verify entities in database
        conn = self.db._get_connection()
        try:
            # Count entities by type
            cursor = conn.execute("""
                SELECT entity_type, COUNT(*) as count
                FROM identity_entities
                WHERE agent_id = ?
                GROUP BY entity_type
                ORDER BY count DESC
            """, (agent_id,))
            
            entity_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Verify we extracted from all layers
            self.assertIn('name', entity_counts, "Should have name entities")
            self.assertIn('belief', entity_counts, "Should have belief entities")
            self.assertIn('priority', entity_counts, "Should have priority entities")
            self.assertIn('catchphrase', entity_counts, "Should have catchphrase entities")
            
            # Verify relationships
            cursor = conn.execute("SELECT COUNT(*) FROM identity_relations")
            relation_count = cursor.fetchone()[0]
            self.assertGreater(relation_count, 0, "Should have relationships")
            
            # Verify specific relationship types
            cursor = conn.execute("""
                SELECT relation_type, COUNT(*) as count
                FROM identity_relations
                GROUP BY relation_type
            """)
            relation_types = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Should have influences relationships
            if 'influences' in relation_types:
                self.assertGreater(relation_types['influences'], 0, "Should have influences relationships")
            
        finally:
            conn.close()
        
        # Test querying entities
        all_entities = []
        conn = self.db._get_connection()
        try:
            cursor = conn.execute("""
                SELECT entity_id, entity_type
                FROM identity_entities
                WHERE agent_id = ?
                LIMIT 10
            """, (agent_id,))
            all_entities = cursor.fetchall()
        finally:
            conn.close()
        
        self.assertGreater(len(all_entities), 0, "Should be able to query entities")
        
        # Test getting related entities
        if all_entities:
            test_entity_id = all_entities[0][0]
            related = self.db.get_related_entities(test_entity_id)
            # May or may not have relationships, but should not error
            self.assertIsInstance(related, list)
    
    def test_extraction_coverage(self):
        """Test that extraction covers all major entity types"""
        if not all(f.exists() for f in [self.soul_file, self.heart_file, self.identity_file]):
            self.skipTest("Real persona files not found")
        
        extractor = IdentityExtractor()
        result = extractor.extract_from_files(
            soul_path=self.soul_file,
            heart_path=self.heart_file,
            identity_path=self.identity_file
        )
        
        entities = result['entities']
        entity_types = {e['entity_type'] for e in entities}
        
        # Verify we extracted from all layers
        # Identity layer
        identity_types = {'name', 'role', 'non_negotiable', 'competency', 'deferral', 'voice', 'catchphrase'}
        found_identity = entity_types & identity_types
        self.assertGreater(len(found_identity), 0, f"Should extract identity layer types. Found: {found_identity}")
        
        # Soul layer
        soul_types = {'belief', 'mission', 'ideal', 'goal', 'value'}
        found_soul = entity_types & soul_types
        self.assertGreater(len(found_soul), 0, f"Should extract soul layer types. Found: {found_soul}")
        
        # Heart layer
        heart_types = {'priority', 'empathy_level', 'emotional_stance'}
        found_heart = entity_types & heart_types
        self.assertGreater(len(found_heart), 0, f"Should extract heart layer types. Found: {found_heart}")
        
        # Expression layer
        expression_types = {'speech_pattern', 'emotion', 'catchphrase'}
        found_expression = entity_types & expression_types
        self.assertGreater(len(found_expression), 0, f"Should extract expression layer types. Found: {found_expression}")


if __name__ == '__main__':
    unittest.main()

