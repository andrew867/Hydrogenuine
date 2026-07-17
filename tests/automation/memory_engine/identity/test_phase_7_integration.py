#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Phase 7 (Unified Search Integration).
"""

import unittest
import tempfile
import os
from pathlib import Path
from hg_memory.unified_search import UnifiedSearch, get_unified_search
from hg_memory.agent.agent_task_integration import search_agent_identity
from hg_memory.identity.identity_graph_db import IdentityGraphDatabase
from hg_memory.identity.identity_search import IdentitySearch
from hg_memory.identity.config import get_identity_graph_db_path


class TestPhase7Integration(unittest.TestCase):
    """Test Phase 7 unified search integration"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.agent_id = "test-agent-phase7"
        
        # Create test identity database
        identity_db_path = get_identity_graph_db_path(self.agent_id)
        identity_db_path.parent.mkdir(parents=True, exist_ok=True)
        self.identity_db = IdentityGraphDatabase(str(identity_db_path))
        
        # Insert test data
        self.identity_db.insert_entity(
            entity_id="test:mission:1",
            entity_type="mission",
            content="Help users achieve their goals through automation",
            agent_id=self.agent_id
        )
        self.identity_db.insert_entity(
            entity_id="test:value:1",
            entity_type="value",
            content="Privacy and security are paramount",
            agent_id=self.agent_id
        )
    
    def tearDown(self):
        """Clean up"""
        import shutil
        shutil.rmtree(self.temp_dir)
        # Clean up identity database
        identity_db_path = get_identity_graph_db_path(self.agent_id)
        if identity_db_path.exists():
            os.remove(identity_db_path)
            if identity_db_path.parent.exists():
                try:
                    identity_db_path.parent.rmdir()
                except OSError:
                    pass
    
    def test_unified_search_includes_identity(self):
        """Test that unified search includes identity graph"""
        unified = get_unified_search()
        
        results = unified.search_all(
            query="privacy",
            agent_id=self.agent_id,
            include_knowledge=False,
            include_agent_memory=False,
            include_context=False,
            include_identity=True,
            limit=10
        )
        
        self.assertIn("identity", results)
        self.assertGreater(len(results["identity"]), 0)
    
    def test_unified_search_all_systems(self):
        """Test unified search across all systems including identity"""
        unified = get_unified_search()
        
        results = unified.search_all(
            query="goals",
            agent_id=self.agent_id,
            include_knowledge=False,
            include_agent_memory=False,
            include_context=False,
            include_identity=True,
            limit=10
        )
        
        # Should have identity results
        self.assertIn("identity", results)
        # May or may not have results depending on data
        self.assertIsInstance(results["identity"], list)
    
    def test_search_connected_includes_identity(self):
        """Test that search_connected includes identity graph"""
        unified = get_unified_search()
        
        results = unified.search_connected(
            query="privacy",
            graph_type="identity",
            agent_id=self.agent_id,
            limit=10
        )
        
        # Should return results (may be empty if no connections)
        self.assertIsInstance(results, list)
    
    def test_search_agent_identity_function(self):
        """Test search_agent_identity convenience function"""
        results = search_agent_identity(
            agent_id=self.agent_id,
            query="privacy",
            limit=10
        )
        
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]['entity_type'], 'value')
    
    def test_search_agent_identity_with_filters(self):
        """Test search_agent_identity with entity type filter"""
        results = search_agent_identity(
            agent_id=self.agent_id,
            query="goals",
            entity_type="mission",
            limit=10
        )
        
        self.assertIsInstance(results, list)
        if results:
            self.assertEqual(results[0]['entity_type'], 'mission')
    
    def test_unified_search_graceful_degradation(self):
        """Test that unified search degrades gracefully when identity graph unavailable"""
        unified = get_unified_search()
        
        # Search with non-existent agent
        results = unified.search_all(
            query="test",
            agent_id="non-existent-agent",
            include_identity=True,
            limit=10
        )
        
        # Should return empty identity results, not crash
        self.assertIn("identity", results)
        self.assertEqual(len(results["identity"]), 0)


if __name__ == '__main__':
    unittest.main()

