#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Phase 8 (Overseer Access & Cross-Agent Identity Analysis).
"""

import unittest
import tempfile
import os
from pathlib import Path
from hg_memory.overseer_access import OverseerAccess, get_overseer_access
from hg_memory.identity.identity_graph_db import IdentityGraphDatabase
from hg_memory.identity.identity_search import IdentitySearch
from hg_memory.identity.config import get_identity_graph_db_path


class TestPhase8Overseer(unittest.TestCase):
    """Test Phase 8 overseer access for identity graphs"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.agent1_id = "test-agent-1"
        self.agent2_id = "test-agent-2"
        self.overseer_id = "overseer"
        
        # Create test identity databases
        for agent_id in [self.agent1_id, self.agent2_id]:
            identity_db_path = get_identity_graph_db_path(agent_id)
            identity_db_path.parent.mkdir(parents=True, exist_ok=True)
            identity_db = IdentityGraphDatabase(str(identity_db_path))
            
            # Insert test data
            identity_db.insert_entity(
                entity_id=f"test:{agent_id}:mission:1",
                entity_type="mission",
                content="Help users achieve their goals",
                agent_id=agent_id
            )
            identity_db.insert_entity(
                entity_id=f"test:{agent_id}:value:1",
                entity_type="value",
                content="Privacy and security",
                agent_id=agent_id
            )
            # Add a common value
            identity_db.insert_entity(
                entity_id=f"test:{agent_id}:value:common",
                entity_type="value",
                content="User autonomy",
                agent_id=agent_id
            )
        
        self.overseer = get_overseer_access()
    
    def tearDown(self):
        """Clean up"""
        import shutil
        shutil.rmtree(self.temp_dir)
        # Clean up identity databases
        for agent_id in [self.agent1_id, self.agent2_id]:
            identity_db_path = get_identity_graph_db_path(agent_id)
            if identity_db_path.exists():
                os.remove(identity_db_path)
                if identity_db_path.parent.exists():
                    try:
                        identity_db_path.parent.rmdir()
                    except OSError:
                        pass
    
    def test_search_agent_identity_overseer(self):
        """Test overseer can search agent identity"""
        results = self.overseer.search_agent_identity(
            requester_id=self.overseer_id,
            target_agent_id=self.agent1_id,
            query="privacy",
            limit=10
        )
        
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)
    
    def test_search_agent_identity_self(self):
        """Test agent can search own identity"""
        results = self.overseer.search_agent_identity(
            requester_id=self.agent1_id,
            target_agent_id=self.agent1_id,
            query="privacy",
            limit=10
        )
        
        self.assertIsInstance(results, list)
    
    def test_search_agent_identity_permission_denied(self):
        """Test agent cannot search other agent's identity"""
        with self.assertRaises(PermissionError):
            self.overseer.search_agent_identity(
                requester_id=self.agent1_id,
                target_agent_id=self.agent2_id,
                query="privacy",
                limit=10
            )
    
    def test_search_all_agents_identity(self):
        """Test overseer can search all agents' identity"""
        results = self.overseer.search_all_agents_identity(
            requester_id=self.overseer_id,
            query="privacy",
            limit_per_agent=10
        )
        
        self.assertIsInstance(results, dict)
        self.assertIn(self.agent1_id, results)
        self.assertIn(self.agent2_id, results)
    
    def test_search_all_agents_identity_permission_denied(self):
        """Test only overseer can search all agents"""
        with self.assertRaises(PermissionError):
            self.overseer.search_all_agents_identity(
                requester_id=self.agent1_id,
                query="privacy",
                limit_per_agent=10
            )
    
    def test_compare_identity_patterns(self):
        """Test comparing identity patterns across agents"""
        patterns = self.overseer.compare_identity_patterns(
            requester_id=self.overseer_id,
            agent_ids=[self.agent1_id, self.agent2_id]
        )
        
        self.assertIsInstance(patterns, dict)
        self.assertIn(self.agent1_id, patterns)
        self.assertIn(self.agent2_id, patterns)
        self.assertIn("entity_count", patterns[self.agent1_id])
        self.assertIn("layers", patterns[self.agent1_id])
    
    def test_compare_identity_patterns_permission_denied(self):
        """Test only overseer can compare identity patterns"""
        with self.assertRaises(PermissionError):
            self.overseer.compare_identity_patterns(
                requester_id=self.agent1_id,
                agent_ids=[self.agent1_id, self.agent2_id]
            )
    
    def test_find_common_identity_elements(self):
        """Test finding common identity elements"""
        common = self.overseer.find_common_identity_elements(
            requester_id=self.overseer_id,
            agent_ids=[self.agent1_id, self.agent2_id],
            min_agents=2
        )
        
        self.assertIsInstance(common, list)
        # Should find at least the common value
        self.assertGreater(len(common), 0)
    
    def test_find_common_identity_elements_permission_denied(self):
        """Test only overseer can find common elements"""
        with self.assertRaises(PermissionError):
            self.overseer.find_common_identity_elements(
                requester_id=self.agent1_id,
                agent_ids=[self.agent1_id, self.agent2_id]
            )
    
    def test_find_similar_identity_profiles(self):
        """Test finding similar identity profiles"""
        similar = self.overseer.find_similar_identity_profiles(
            requester_id=self.overseer_id,
            agent_ids=[self.agent1_id, self.agent2_id],
            similarity_threshold=0.0
        )
        
        self.assertIsInstance(similar, list)
        # Should find at least one pair
        self.assertGreater(len(similar), 0)
        self.assertIn("agent1", similar[0])
        self.assertIn("agent2", similar[0])
        self.assertIn("similarity", similar[0])
    
    def test_find_similar_identity_profiles_permission_denied(self):
        """Test only overseer can find similar profiles"""
        with self.assertRaises(PermissionError):
            self.overseer.find_similar_identity_profiles(
                requester_id=self.agent1_id,
                agent_ids=[self.agent1_id, self.agent2_id]
            )


if __name__ == '__main__':
    unittest.main()

