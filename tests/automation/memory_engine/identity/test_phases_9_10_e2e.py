#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
End-to-end tests for Phases 9 and 10 (Analytics & Final Polish).
"""

import unittest
import tempfile
import os
from pathlib import Path

from hg_memory.identity.identity_graph_db import IdentityGraphDatabase
from hg_memory.identity.identity_analytics import IdentityAnalytics
from hg_memory.identity.identity_recorder import IdentityRecorder
from hg_memory.identity.config import get_identity_graph_db_path


class TestPhases910E2E(unittest.TestCase):
    """End-to-end tests for Phases 9 and 10"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.agent_id = "test-phases-9-10"
        
        # Create test database with comprehensive data
        identity_db_path = get_identity_graph_db_path(self.agent_id)
        identity_db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = IdentityGraphDatabase(str(identity_db_path))
        
        # Insert test entities
        self.db.insert_entity(
            entity_id="test:mission:1",
            entity_type="mission",
            content="Help users achieve their goals",
            agent_id=self.agent_id
        )
        self.db.insert_entity(
            entity_id="test:value:1",
            entity_type="value",
            content="Privacy and security",
            agent_id=self.agent_id
        )
        self.db.insert_entity(
            entity_id="test:value:2",
            entity_type="value",
            content="User autonomy",
            agent_id=self.agent_id
        )
        self.db.insert_entity(
            entity_id="test:goal:1",
            entity_type="goal",
            content="Build trust",
            agent_id=self.agent_id
        )
        
        # Insert relations
        self.db.insert_relation(
            from_entity_id="test:mission:1",
            to_entity_id="test:value:1",
            relation_type="aligns_with"
        )
        self.db.insert_relation(
            from_entity_id="test:mission:1",
            to_entity_id="test:goal:1",
            relation_type="enables"
        )
        
        # Insert version
        import uuid
        self.db.insert_version(
            version_id=str(uuid.uuid4()),
            persona_file="SOUL.md",
            content_hash="abc123",
            agent_id=self.agent_id
        )
        
        self.analytics = IdentityAnalytics(self.db)
        self.recorder = IdentityRecorder(database=self.db, agent_id=self.agent_id)
    
    def tearDown(self):
        """Clean up"""
        import shutil
        shutil.rmtree(self.temp_dir)
        identity_db_path = get_identity_graph_db_path(self.agent_id)
        if identity_db_path.exists():
            os.remove(identity_db_path)
            if identity_db_path.parent.exists():
                try:
                    identity_db_path.parent.rmdir()
                except OSError:
                    pass
    
    def test_full_analytics_workflow(self):
        """Test complete analytics workflow"""
        # Get statistics
        stats = self.analytics.get_identity_statistics(agent_id=self.agent_id)
        self.assertGreater(stats['total_entities'], 0)
        self.assertGreater(stats['total_relations'], 0)
        
        # Get evolution report
        evolution = self.analytics.get_evolution_report(agent_id=self.agent_id, days=30)
        self.assertIn('total_evolutions', evolution)
        
        # Get conflict report
        conflicts = self.analytics.get_conflict_report(agent_id=self.agent_id)
        self.assertIn('total_conflicts', conflicts)
        
        # Get layer analysis
        layers = self.analytics.get_layer_analysis(agent_id=self.agent_id)
        self.assertIn('soul', layers)
        self.assertGreater(layers['soul']['count'], 0)
        
        # Get version history
        versions = self.analytics.get_version_history_report(agent_id=self.agent_id)
        self.assertIn('files', versions)
        self.assertIn('SOUL.md', versions['files'])
        
        # Get relationship network
        network = self.analytics.get_relationship_network(agent_id=self.agent_id)
        self.assertGreater(network['total_nodes'], 0)
        self.assertGreater(network['total_edges'], 0)
    
    def test_api_exports(self):
        """Test that all API exports work"""
        # Test direct imports (not from __init__)
        from hg_memory.identity.identity_search import IdentitySearch
        from hg_memory.identity.identity_graph_db import IdentityGraphDatabase
        from hg_memory.identity.identity_recorder import IdentityRecorder
        from hg_memory.identity.identity_extractor import IdentityExtractor
        from hg_memory.identity.identity_analytics import IdentityAnalytics
        from hg_memory.identity.config import get_identity_graph_db_path
        from hg_memory.identity.identity_health import health_check as get_identity_health
        from hg_memory.identity.identity_cache import IdentityCache
        from hg_memory.identity.identity_error_handler import IdentityErrorHandler
        
        # Verify all imports work
        self.assertIsNotNone(IdentitySearch)
        self.assertIsNotNone(IdentityGraphDatabase)
        self.assertIsNotNone(IdentityRecorder)
        self.assertIsNotNone(IdentityExtractor)
        self.assertIsNotNone(IdentityAnalytics)
        self.assertIsNotNone(get_identity_graph_db_path)
        self.assertIsNotNone(get_identity_health)
        self.assertIsNotNone(IdentityCache)
        self.assertIsNotNone(IdentityErrorHandler)
    
    def test_cli_imports(self):
        """Test CLI module imports"""
        try:
            from hg_memory.identity import identity_cli
            self.assertIsNotNone(identity_cli)
        except ImportError:
            # CLI is optional
            pass
    
    def test_comprehensive_statistics(self):
        """Test comprehensive statistics gathering"""
        stats = self.analytics.get_identity_statistics(agent_id=self.agent_id)
        
        # Verify all expected keys
        required_keys = [
            'total_entities', 'total_relations', 'total_versions',
            'total_patterns', 'entity_types', 'relation_types',
            'layers', 'platforms', 'timeline'
        ]
        for key in required_keys:
            self.assertIn(key, stats)
        
        # Verify layer distribution
        self.assertIn('identity', stats['layers'])
        self.assertIn('soul', stats['layers'])
        self.assertIn('heart', stats['layers'])
        self.assertIn('expression', stats['layers'])


if __name__ == '__main__':
    unittest.main()

