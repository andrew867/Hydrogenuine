#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for identity recorder.
"""

import unittest
import tempfile
import os
from pathlib import Path

from hg_memory.identity.identity_graph_db import IdentityGraphDatabase
from hg_memory.identity.identity_recorder import IdentityRecorder


class TestIdentityRecorder(unittest.TestCase):
    """Test identity recorder"""
    
    def setUp(self):
        """Set up test database and files"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_identity.db")
        self.db = IdentityGraphDatabase(self.db_path)
        self.recorder = IdentityRecorder(database=self.db, agent_id="test-agent")
        
        # Create test persona files
        self.identity_file = Path(self.temp_dir) / "IDENTITY.md"
        self.identity_file.write_text("""# IDENTITY.md
- **Name:** The Underling
## Tone / voice
- Mostly lowercase
## Catchphrases
- "full circle huh"
""", encoding='utf-8')
        
        self.soul_file = Path(self.temp_dir) / "SOUL.md"
        self.soul_file.write_text("""# SOUL.md
## Core truths
- Institutional betrayal is real
""", encoding='utf-8')
        
        self.heart_file = Path(self.temp_dir) / "HEART.md"
        self.heart_file.write_text("""# HEART.md
## Core priorities
1. OpSec / privacy
""", encoding='utf-8')
    
    def tearDown(self):
        """Clean up test database and files"""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_record_persona_files(self):
        """Test recording persona files"""
        result = self.recorder.record_persona_files(
            soul_path=self.soul_file,
            heart_path=self.heart_file,
            identity_path=self.identity_file,
            platform="test-platform"
        )
        
        # Check that entities were recorded
        self.assertGreater(result['entities'], 0)
        self.assertGreaterEqual(result['versions'], 0)
        
        # Verify entities in database
        conn = self.db._get_connection()
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM identity_entities WHERE agent_id = ?", ("test-agent",))
            count = cursor.fetchone()[0]
            self.assertGreater(count, 0)
        finally:
            conn.close()
    
    def test_record_persona_update(self):
        """Test recording persona file update"""
        # Record initial version
        self.recorder.record_persona_files(identity_path=self.identity_file)
        
        # Update file
        before_content = self.identity_file.read_text(encoding='utf-8')
        after_content = before_content + "\n- **New catchphrase:** test"
        self.identity_file.write_text(after_content, encoding='utf-8')
        
        # Record update
        result = self.recorder.record_persona_update(
            persona_file="IDENTITY.md",
            file_path=self.identity_file,
            before_content=before_content,
            after_content=after_content
        )
        
        self.assertTrue(result)
        
        # Verify version was recorded
        conn = self.db._get_connection()
        try:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM identity_versions WHERE persona_file = ?",
                ("IDENTITY.md",)
            )
            count = cursor.fetchone()[0]
            self.assertGreater(count, 0)
        finally:
            conn.close()
    
    def test_track_evolution(self):
        """Test tracking entity evolution"""
        # Insert initial entity
        self.db.insert_entity(
            entity_id="test:entity:1",
            entity_type="belief",
            content="Original belief"
        )
        
        # Track evolution
        result = self.recorder.track_evolution(
            entity_id="test:entity:1",
            new_content="Updated belief",
            new_properties={"updated": True}
        )
        
        self.assertTrue(result)
        
        # Verify evolves_from relationship was created
        related = self.db.get_related_entities("test:entity:1", relation_type="evolves_from", direction="to")
        self.assertGreater(len(related), 0)


if __name__ == '__main__':
    unittest.main()

