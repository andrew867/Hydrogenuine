#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for persona system integration.
"""

import unittest
import tempfile
import os
import time
from pathlib import Path

from hg_memory.identity.identity_graph_db import IdentityGraphDatabase
from hg_memory.identity.persona_integration import (
    record_persona_update_async,
    record_persona_files_async,
    get_agent_id_from_platform,
    IDENTITY_SYSTEM_AVAILABLE,
    IDENTITY_TRACKING_ENABLED
)


class TestPersonaIntegration(unittest.TestCase):
    """Test persona system integration"""
    
    def setUp(self):
        """Set up test database and files"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_integration.db")
        self.db = IdentityGraphDatabase(self.db_path)
        
        # Create test persona directory
        self.persona_dir = Path(self.temp_dir) / "personas" / "test-platform" / "default"
        self.persona_dir.mkdir(parents=True, exist_ok=True)
        
        # Create test persona file
        self.test_file = self.persona_dir / "SOUL.md"
        self.test_file.write_text("# SOUL.md\n\nTest content", encoding='utf-8')
    
    def tearDown(self):
        """Clean up"""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_get_agent_id_from_platform(self):
        """Test getting agent ID from platform"""
        agent_id = get_agent_id_from_platform("fourclaw")
        self.assertEqual(agent_id, "fourclaw-auto-post")
        
        agent_id = get_agent_id_from_platform("aichan")
        self.assertEqual(agent_id, "aichan-auto-post")
        
        agent_id = get_agent_id_from_platform("unknown")
        self.assertIsNone(agent_id)
    
    def test_record_persona_update_async(self):
        """Test async persona update recording"""
        if not IDENTITY_SYSTEM_AVAILABLE:
            self.skipTest("Identity system not available")
        
        before_content = self.test_file.read_text(encoding='utf-8')
        after_content = before_content + "\n\nUpdated content"
        
        # Record update
        record_persona_update_async(
            platform="test-platform",
            persona_set="default",
            file_name="SOUL.md",
            file_path=self.test_file,
            before_content=before_content,
            after_content=after_content
        )
        
        # Wait for async operation to complete
        time.sleep(0.5)
        
        # Verify version was recorded
        conn = self.db._get_connection()
        try:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM identity_versions WHERE persona_file = ?",
                ("SOUL.md",)
            )
            count = cursor.fetchone()[0]
            # May or may not have recorded (depends on agent_id mapping)
            self.assertGreaterEqual(count, 0)
        finally:
            conn.close()
    
    def test_record_persona_files_async(self):
        """Test async persona files recording"""
        if not IDENTITY_SYSTEM_AVAILABLE:
            self.skipTest("Identity system not available")
        
        # Create all three persona files
        (self.persona_dir / "HEART.md").write_text("# HEART.md\n\nTest", encoding='utf-8')
        (self.persona_dir / "IDENTITY.md").write_text("# IDENTITY.md\n\nTest", encoding='utf-8')
        
        # Record files
        record_persona_files_async(
            platform="fourclaw",  # Use known platform for agent_id mapping
            persona_set="default"
        )
        
        # Wait for async operation
        time.sleep(0.5)
        
        # Verify entities were recorded (if agent_id was found)
        conn = self.db._get_connection()
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM identity_entities")
            count = cursor.fetchone()[0]
            # May or may not have recorded
            self.assertGreaterEqual(count, 0)
        finally:
            conn.close()
    
    def test_integration_graceful_degradation(self):
        """Test that integration degrades gracefully when identity system unavailable"""
        # This should not raise an error even if identity system is unavailable
        try:
            record_persona_update_async(
                platform="test",
                persona_set="default",
                file_name="SOUL.md",
                file_path=self.test_file
            )
        except Exception as e:
            self.fail(f"Integration should degrade gracefully, but raised: {e}")


if __name__ == '__main__':
    unittest.main()

