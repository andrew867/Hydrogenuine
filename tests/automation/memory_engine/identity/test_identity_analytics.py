#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for identity analytics.
"""

import unittest
import tempfile
import os
from pathlib import Path

from hg_memory.identity.identity_graph_db import IdentityGraphDatabase
from hg_memory.identity.identity_analytics import IdentityAnalytics
from hg_memory.identity.config import get_identity_graph_db_path


class TestIdentityAnalytics(unittest.TestCase):
    """Test identity analytics"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.agent_id = "test-analytics-agent"
        
        # Create test database
        identity_db_path = get_identity_graph_db_path(self.agent_id)
        identity_db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = IdentityGraphDatabase(str(identity_db_path))
        
        # Insert test data
        self.db.insert_entity(
            entity_id="test:mission:1",
            entity_type="mission",
            content="Help users",
            agent_id=self.agent_id
        )
        self.db.insert_entity(
            entity_id="test:value:1",
            entity_type="value",
            content="Privacy",
            agent_id=self.agent_id
        )
        self.db.insert_relation(
            from_entity_id="test:mission:1",
            to_entity_id="test:value:1",
            relation_type="aligns_with"
        )
        
        self.analytics = IdentityAnalytics(self.db)
    
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
    
    def test_get_identity_statistics(self):
        """Test getting identity statistics"""
        stats = self.analytics.get_identity_statistics(agent_id=self.agent_id)
        
        self.assertIn('total_entities', stats)
        self.assertIn('total_relations', stats)
        self.assertIn('entity_types', stats)
        self.assertIn('layers', stats)
        self.assertGreater(stats['total_entities'], 0)
    
    def test_get_evolution_report(self):
        """Test getting evolution report"""
        report = self.analytics.get_evolution_report(agent_id=self.agent_id, days=30)
        
        self.assertIn('period_days', report)
        self.assertIn('total_evolutions', report)
        self.assertIn('evolutions_by_type', report)
        self.assertIn('most_evolved_entities', report)
        self.assertIn('evolution_timeline', report)
    
    def test_get_conflict_report(self):
        """Test getting conflict report"""
        report = self.analytics.get_conflict_report(agent_id=self.agent_id)
        
        self.assertIn('total_conflicts', report)
        self.assertIn('conflicts_by_type', report)
        self.assertIn('conflicting_pairs', report)
    
    def test_get_layer_analysis(self):
        """Test getting layer analysis"""
        analysis = self.analytics.get_layer_analysis(agent_id=self.agent_id)
        
        self.assertIn('identity', analysis)
        self.assertIn('soul', analysis)
        self.assertIn('heart', analysis)
        self.assertIn('expression', analysis)
        
        for layer in ['identity', 'soul', 'heart', 'expression']:
            self.assertIn('count', analysis[layer])
            self.assertIn('entities', analysis[layer])
            self.assertIn('types', analysis[layer])
    
    def test_get_version_history_report(self):
        """Test getting version history report"""
        report = self.analytics.get_version_history_report(agent_id=self.agent_id)
        
        self.assertIn('total_versions', report)
        self.assertIn('files', report)
        self.assertIn('SOUL.md', report['files'])
        self.assertIn('HEART.md', report['files'])
        self.assertIn('IDENTITY.md', report['files'])
    
    def test_get_relationship_network(self):
        """Test getting relationship network"""
        network = self.analytics.get_relationship_network(agent_id=self.agent_id)
        
        self.assertIn('total_nodes', network)
        self.assertIn('total_edges', network)
        self.assertIn('relation_distribution', network)
        self.assertIn('most_connected_entities', network)
        self.assertIn('isolated_entities', network)
        self.assertGreater(network['total_nodes'], 0)


if __name__ == '__main__':
    unittest.main()

