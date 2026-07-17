#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for identity search functionality.
"""

import unittest
import tempfile
import os
from pathlib import Path

from hg_memory.identity.identity_graph_db import IdentityGraphDatabase
from hg_memory.identity.identity_search import IdentitySearch
from hg_memory.identity.identity_recorder import IdentityRecorder


class TestIdentitySearch(unittest.TestCase):
    """Test identity search functionality"""
    
    def setUp(self):
        """Set up test database"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_search.db")
        self.db = IdentityGraphDatabase(self.db_path)
        self.search = IdentitySearch(self.db)
        self.recorder = IdentityRecorder(database=self.db, agent_id="test-agent")
        
        # Insert test entities
        self.db.insert_entity(
            entity_id="test:mission:1",
            entity_type="mission",
            content="Help users achieve their goals",
            agent_id="test-agent"
        )
        self.db.insert_entity(
            entity_id="test:value:1",
            entity_type="value",
            content="Privacy and security",
            agent_id="test-agent"
        )
        self.db.insert_entity(
            entity_id="test:belief:1",
            entity_type="belief",
            content="Users should have control over their data",
            agent_id="test-agent"
        )
        
        # Insert test relations
        self.db.insert_relation(
            from_entity_id="test:value:1",
            to_entity_id="test:mission:1",
            relation_type="influences"
        )
        self.db.insert_relation(
            from_entity_id="test:mission:1",
            to_entity_id="test:belief:1",
            relation_type="evolves_from"
        )
    
    def tearDown(self):
        """Clean up"""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_search_identity(self):
        """Test basic identity search"""
        results = self.search.search_identity("privacy", agent_id="test-agent")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]['entity_type'], 'value')
    
    def test_search_by_entity_type(self):
        """Test search with entity type filter"""
        results = self.search.search_identity("goals", entity_type="mission", agent_id="test-agent")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]['entity_type'], 'mission')
    
    def test_get_evolution_chain(self):
        """Test evolution chain retrieval"""
        chain = self.search.get_evolution_chain("test:belief:1")
        self.assertGreater(len(chain), 0)
    
    def test_get_entity_relationships(self):
        """Test relationship retrieval"""
        relationships = self.search.get_entity_relationships("test:mission:1")
        self.assertIn('influences', relationships)
        self.assertIn('evolves_from', relationships)
    
    def test_search_by_layer(self):
        """Test search by identity layer"""
        soul_entities = self.search.search_by_layer("soul", agent_id="test-agent")
        self.assertGreater(len(soul_entities), 0)
        self.assertIn(soul_entities[0]['entity_type'], ['mission', 'good_evil', 'ideal', 'goal', 
                                                         'priority_order', 'tradeoff_policy',
                                                         'truthfulness_policy', 'alignment', 'belief', 'value'])
    
    def test_get_version_history(self):
        """Test version history retrieval"""
        # Insert a version
        self.db.insert_version(
            version_id="test:version:1",
            persona_file="SOUL.md",
            content_hash="abc123",
            agent_id="test-agent"
        )
        
        history = self.search.get_version_history("SOUL.md", agent_id="test-agent")
        self.assertGreater(len(history), 0)
        self.assertEqual(history[0]['persona_file'], 'SOUL.md')
    
    def test_find_conflicts(self):
        """Test conflict detection"""
        # Insert a conflict
        self.db.insert_entity(
            entity_id="test:value:2",
            entity_type="value",
            content="Open sharing",
            agent_id="test-agent"
        )
        self.db.insert_relation(
            from_entity_id="test:value:1",
            to_entity_id="test:value:2",
            relation_type="conflicts_with"
        )
        
        conflicts = self.search.find_conflicts(agent_id="test-agent")
        self.assertGreater(len(conflicts), 0)


if __name__ == '__main__':
    unittest.main()

