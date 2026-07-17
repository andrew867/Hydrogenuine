#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
End-to-end tests for Phase 8 (Overseer Access & Cross-Agent Identity Analysis).
"""

import unittest
import tempfile
import os
from pathlib import Path
from hg_memory.overseer_access import get_overseer_access
from hg_memory.identity.identity_graph_db import IdentityGraphDatabase
from hg_memory.identity.config import get_identity_graph_db_path


class TestPhase8E2E(unittest.TestCase):
    """End-to-end tests for Phase 8"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.agent1_id = "test-agent-e2e-1"
        self.agent2_id = "test-agent-e2e-2"
        self.agent3_id = "test-agent-e2e-3"
        self.overseer_id = "overseer"
        
        # Create comprehensive test data for multiple agents
        self._create_test_data()
        
        self.overseer = get_overseer_access()
    
    def _create_test_data(self):
        """Create test identity data for multiple agents"""
        agents_data = {
            self.agent1_id: {
                "mission": "Help users achieve their goals through automation",
                "value": "Privacy and security are paramount",
                "belief": "Users should have control over their data",
                "goal": "Build trust through transparency"
            },
            self.agent2_id: {
                "mission": "Help users achieve their goals through automation",  # Common
                "value": "User autonomy",  # Common
                "belief": "Open source is the future",
                "goal": "Enable user freedom"
            },
            self.agent3_id: {
                "mission": "Maximize user engagement",
                "value": "User autonomy",  # Common with agent2
                "belief": "Data-driven decisions",
                "goal": "Increase platform activity"
            }
        }
        
        for agent_id, data in agents_data.items():
            identity_db_path = get_identity_graph_db_path(agent_id)
            identity_db_path.parent.mkdir(parents=True, exist_ok=True)
            identity_db = IdentityGraphDatabase(str(identity_db_path))
            
            for entity_type, content in data.items():
                identity_db.insert_entity(
                    entity_id=f"test:{agent_id}:{entity_type}:1",
                    entity_type=entity_type,
                    content=content,
                    agent_id=agent_id
                )
    
    def tearDown(self):
        """Clean up"""
        import shutil
        shutil.rmtree(self.temp_dir)
        # Clean up identity databases
        for agent_id in [self.agent1_id, self.agent2_id, self.agent3_id]:
            identity_db_path = get_identity_graph_db_path(agent_id)
            if identity_db_path.exists():
                os.remove(identity_db_path)
                if identity_db_path.parent.exists():
                    try:
                        identity_db_path.parent.rmdir()
                    except OSError:
                        pass
    
    def test_full_overseer_workflow(self):
        """Test complete overseer workflow for identity analysis"""
        # 1. Search single agent identity
        results1 = self.overseer.search_agent_identity(
            requester_id=self.overseer_id,
            target_agent_id=self.agent1_id,
            query="privacy",
            limit=10
        )
        self.assertGreater(len(results1), 0)
        
        # 2. Search all agents identity
        all_results = self.overseer.search_all_agents_identity(
            requester_id=self.overseer_id,
            query="goals",
            limit_per_agent=10
        )
        self.assertGreater(len(all_results), 0)
        self.assertIn(self.agent1_id, all_results)
        
        # 3. Compare identity patterns
        patterns = self.overseer.compare_identity_patterns(
            requester_id=self.overseer_id,
            agent_ids=[self.agent1_id, self.agent2_id, self.agent3_id]
        )
        self.assertEqual(len(patterns), 3)
        self.assertIn("entity_count", patterns[self.agent1_id])
        self.assertIn("layers", patterns[self.agent1_id])
        
        # 4. Find common identity elements
        common = self.overseer.find_common_identity_elements(
            requester_id=self.overseer_id,
            agent_ids=[self.agent1_id, self.agent2_id, self.agent3_id],
            min_agents=2
        )
        self.assertGreater(len(common), 0)
        # Should find common values
        self.assertTrue(any(e["entity_type"] == "value" for e in common))
        
        # 5. Find similar identity profiles
        similar = self.overseer.find_similar_identity_profiles(
            requester_id=self.overseer_id,
            agent_ids=[self.agent1_id, self.agent2_id, self.agent3_id],
            similarity_threshold=0.0
        )
        self.assertGreater(len(similar), 0)
        self.assertIn("similarity", similar[0])
    
    def test_cross_agent_analysis_workflow(self):
        """Test cross-agent analysis workflow"""
        # Compare patterns
        patterns = self.overseer.compare_identity_patterns(
            requester_id=self.overseer_id,
            agent_ids=[self.agent1_id, self.agent2_id]
        )
        
        # Verify pattern structure
        for agent_id, pattern in patterns.items():
            self.assertIn("agent_id", pattern)
            self.assertIn("entity_count", pattern)
            self.assertIn("entity_types", pattern)
            self.assertIn("layers", pattern)
            self.assertGreater(pattern["entity_count"], 0)
        
        # Find common elements
        common = self.overseer.find_common_identity_elements(
            requester_id=self.overseer_id,
            agent_ids=[self.agent1_id, self.agent2_id],
            min_agents=2
        )
        
        # Verify common elements structure
        for element in common:
            self.assertIn("entity_type", element)
            self.assertIn("agent_count", element)
            self.assertIn("agents", element)
            self.assertGreaterEqual(element["agent_count"], 2)
    
    def test_layer_specific_analysis(self):
        """Test layer-specific identity analysis"""
        # Compare soul layer
        patterns = self.overseer.compare_identity_patterns(
            requester_id=self.overseer_id,
            agent_ids=[self.agent1_id, self.agent2_id],
            layer="soul"
        )
        
        self.assertEqual(len(patterns), 2)
        # Soul layer should have entities
        self.assertGreater(patterns[self.agent1_id]["layers"]["soul"], 0)
    
    def test_permission_enforcement(self):
        """Test that permission enforcement works correctly"""
        # Agent cannot access other agent's identity
        with self.assertRaises(PermissionError):
            self.overseer.search_agent_identity(
                requester_id=self.agent1_id,
                target_agent_id=self.agent2_id,
                query="test"
            )
        
        # Agent cannot search all agents
        with self.assertRaises(PermissionError):
            self.overseer.search_all_agents_identity(
                requester_id=self.agent1_id,
                query="test"
            )
        
        # Agent cannot compare patterns
        with self.assertRaises(PermissionError):
            self.overseer.compare_identity_patterns(
                requester_id=self.agent1_id,
                agent_ids=[self.agent1_id, self.agent2_id]
            )
        
        # Agent can access own identity
        results = self.overseer.search_agent_identity(
            requester_id=self.agent1_id,
            target_agent_id=self.agent1_id,
            query="privacy"
        )
        self.assertIsInstance(results, list)


if __name__ == '__main__':
    unittest.main()

