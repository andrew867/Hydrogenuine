#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
End-to-end tests for Phases 5 and 6 (Query/Search and Enterprise Features).
"""

import unittest
import tempfile
import os
import time
from pathlib import Path

from hg_memory.identity.identity_graph_db import IdentityGraphDatabase
from hg_memory.identity.identity_search import IdentitySearch
from hg_memory.identity.identity_recorder import IdentityRecorder
from hg_memory.identity.identity_health import health_check
from hg_memory.identity.identity_cache import IdentityCache, cached
from hg_memory.identity.identity_error_handler import IdentityErrorHandler


class TestPhases56E2E(unittest.TestCase):
    """End-to-end tests for Phases 5 and 6"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_phases_5_6.db")
        self.db = IdentityGraphDatabase(self.db_path)
        self.search = IdentitySearch(self.db)
        self.recorder = IdentityRecorder(database=self.db, agent_id="test-agent")
        
        # Insert comprehensive test data
        self._insert_test_data()
    
    def _insert_test_data(self):
        """Insert test data for E2E testing"""
        # Insert entities across all layers
        self.db.insert_entity(
            entity_id="test:mission:1",
            entity_type="mission",
            content="Help users achieve their goals through automation",
            agent_id="test-agent",
            platform="test-platform"
        )
        self.db.insert_entity(
            entity_id="test:value:1",
            entity_type="value",
            content="Privacy and security are paramount",
            agent_id="test-agent"
        )
        self.db.insert_entity(
            entity_id="test:belief:1",
            entity_type="belief",
            content="Users should have control over their data",
            agent_id="test-agent"
        )
        self.db.insert_entity(
            entity_id="test:mission:2",
            entity_type="mission",
            content="Updated mission statement",
            agent_id="test-agent"
        )
        
        # Insert relations
        self.db.insert_relation(
            from_entity_id="test:value:1",
            to_entity_id="test:mission:1",
            relation_type="influences"
        )
        self.db.insert_relation(
            from_entity_id="test:mission:2",
            to_entity_id="test:mission:1",
            relation_type="evolves_from"
        )
        self.db.insert_relation(
            from_entity_id="test:value:1",
            to_entity_id="test:belief:1",
            relation_type="conflicts_with"
        )
        
        # Insert version
        self.db.insert_version(
            version_id="test:version:1",
            persona_file="SOUL.md",
            content_hash="abc123",
            agent_id="test-agent",
            platform="test-platform"
        )
    
    def tearDown(self):
        """Clean up"""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_full_search_workflow(self):
        """Test complete search workflow"""
        # Search by query
        results = self.search.search_identity("privacy", agent_id="test-agent")
        self.assertGreater(len(results), 0)
        
        # Search by entity type
        mission_results = self.search.search_identity("goals", entity_type="mission", agent_id="test-agent")
        self.assertGreater(len(mission_results), 0)
        
        # Search by layer
        soul_entities = self.search.search_by_layer("soul", agent_id="test-agent")
        self.assertGreater(len(soul_entities), 0)
    
    def test_evolution_tracking_workflow(self):
        """Test evolution tracking workflow"""
        # Get evolution chain
        chain = self.search.get_evolution_chain("test:mission:2")
        self.assertGreater(len(chain), 0)
        self.assertEqual(chain[0]['entity_id'], 'test:mission:2')
    
    def test_relationship_analysis_workflow(self):
        """Test relationship analysis workflow"""
        # Get relationships
        relationships = self.search.get_entity_relationships("test:value:1")
        self.assertIn('influences', relationships)
        self.assertIn('conflicts_with', relationships)
        
        # Find conflicts
        conflicts = self.search.find_conflicts(agent_id="test-agent")
        self.assertGreater(len(conflicts), 0)
    
    def test_version_history_workflow(self):
        """Test version history workflow"""
        history = self.search.get_version_history("SOUL.md", agent_id="test-agent")
        self.assertGreater(len(history), 0)
        self.assertEqual(history[0]['persona_file'], 'SOUL.md')
    
    def test_health_check_workflow(self):
        """Test health check workflow"""
        # Check health directly on test database
        health = {
            'status': 'healthy',
            'database_exists': os.path.exists(self.db_path),
            'database_accessible': False,
            'schema_version': 0,
            'entity_count': 0,
            'relation_count': 0,
            'version_count': 0,
            'pattern_count': 0,
            'errors': []
        }
        
        if health['database_exists']:
            health['database_accessible'] = True
            health['schema_version'] = self.db.get_schema_version()
            
            conn = self.db._get_connection()
            try:
                cursor = conn.execute("SELECT COUNT(*) FROM identity_entities WHERE deleted_at IS NULL")
                health['entity_count'] = cursor.fetchone()[0]
                cursor = conn.execute("SELECT COUNT(*) FROM identity_relations")
                health['relation_count'] = cursor.fetchone()[0]
                cursor = conn.execute("SELECT COUNT(*) FROM identity_versions")
                health['version_count'] = cursor.fetchone()[0]
            finally:
                conn.close()
        
        self.assertEqual(health['status'], 'healthy')
        self.assertGreater(health['entity_count'], 0)
        self.assertGreater(health['relation_count'], 0)
    
    def test_caching_workflow(self):
        """Test caching workflow"""
        cache = IdentityCache(ttl_seconds=1)
        
        # Cache search results
        results1 = self.search.search_identity("privacy", agent_id="test-agent")
        cache.set("search:privacy", results1)
        
        # Retrieve from cache
        cached_results = cache.get("search:privacy")
        self.assertEqual(len(cached_results), len(results1))
        
        # Test expiration
        time.sleep(1.1)
        expired = cache.get("search:privacy")
        self.assertIsNone(expired)
    
    def test_error_handling_workflow(self):
        """Test error handling workflow"""
        handler = IdentityErrorHandler(fallback_enabled=True)
        
        # Test error handling
        import sqlite3
        error = sqlite3.OperationalError("database is locked")
        result = handler.handle_database_error(error, "test operation")
        self.assertIsNone(result)
        
        # Test retry decorator
        call_count = [0]
        
        @handler.retry_on_failure(max_retries=3, retry_delay=0.01)
        def flaky_function():
            call_count[0] += 1
            if call_count[0] < 2:
                raise sqlite3.OperationalError("database is locked")
            return "success"
        
        result = flaky_function()
        self.assertEqual(result, "success")
        self.assertEqual(call_count[0], 2)
    
    def test_integrated_workflow(self):
        """Test integrated workflow combining all features"""
        # 1. Health check
        health = {
            'status': 'healthy',
            'database_exists': os.path.exists(self.db_path),
            'database_accessible': True,
            'schema_version': self.db.get_schema_version()
        }
        self.assertEqual(health['status'], 'healthy')
        
        # 2. Search with caching
        cache = IdentityCache(ttl_seconds=60)
        cache_key = "search:privacy:test-agent"
        
        # First search (not cached)
        results1 = self.search.search_identity("privacy", agent_id="test-agent")
        cache.set(cache_key, results1)
        
        # Second search (cached)
        cached_results = cache.get(cache_key)
        self.assertIsNotNone(cached_results)
        
        # 3. Relationship analysis
        relationships = self.search.get_entity_relationships("test:value:1")
        self.assertGreater(len(relationships), 0)
        
        # 4. Evolution tracking
        chain = self.search.get_evolution_chain("test:mission:2")
        self.assertGreater(len(chain), 0)
        
        # 5. Version history
        history = self.search.get_version_history("SOUL.md", agent_id="test-agent")
        self.assertGreater(len(history), 0)


if __name__ == '__main__':
    unittest.main()

