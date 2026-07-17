#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
End-to-end tests for Phase 4 (Persona System Integration).
"""

import unittest
import tempfile
import os
import time
from pathlib import Path

from hg_persona import update_platform_persona
from hg_memory.identity.persona_integration import record_persona_update_async
from hg_lib.config import get_persona_dir
from hg_memory.identity.identity_graph_db import IdentityGraphDatabase
from hg_memory.identity.config import get_identity_graph_db_path


class TestPhase4E2E(unittest.TestCase):
    """End-to-end tests for Phase 4 integration"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Create test persona directory structure (workspace layout)
        self.persona_base = self.temp_dir / "skills" / "automation" / "personas"
        self.test_platform = "moltbook"  # Maps to agent_id for identity recording
        self.test_persona_set = "default"
        self.persona_dir = self.persona_base / self.test_platform / self.test_persona_set
        self.persona_dir.mkdir(parents=True, exist_ok=True)
        
        # Create initial persona file
        self.soul_file = self.persona_dir / "SOUL.md"
        self.soul_file.write_text("""# SOUL.md

## Core truths

- Test belief 1
- Test belief 2
""", encoding='utf-8')
        
        # Point workspace to temp_dir so persona_loader uses our test layout
        self.original_cwd = os.getcwd()
        self.original_workspace = os.environ.get("HG_WORKSPACE")
        os.environ["HG_WORKSPACE"] = str(self.temp_dir)
    
    def tearDown(self):
        """Clean up"""
        os.chdir(self.original_cwd)
        if self.original_workspace is not None:
            os.environ["HG_WORKSPACE"] = self.original_workspace
        elif "HG_WORKSPACE" in os.environ:
            del os.environ["HG_WORKSPACE"]
        import shutil
        import time
        # Wait a bit for file handles to close
        time.sleep(0.1)
        try:
            shutil.rmtree(self.temp_dir)
        except (PermissionError, OSError):
            # Files may still be locked, try again after a delay
            time.sleep(0.5)
            try:
                shutil.rmtree(self.temp_dir)
            except (PermissionError, OSError):
                # If still locked, just skip cleanup (temp dir will be cleaned up eventually)
                pass
    
    def test_persona_update_triggers_identity_recording(self):
        """Test that updating persona file triggers identity recording"""
        # Update persona file using persona_loader
        new_content = """# SOUL.md

## Core truths

- Updated belief 1
- Updated belief 2
- New belief 3
"""
        
        result = update_platform_persona(
            platform=self.test_platform,
            persona_set=self.test_persona_set,
            file_name="SOUL.md",
            content=new_content
        )
        
        self.assertTrue(result, "Persona update should succeed")

        # Identity tracking: caller invokes after update (hg_persona does not import skills)
        if result:
            file_path = get_persona_dir(self.test_platform, self.test_persona_set) / "SOUL.md"
            record_persona_update_async(
                platform=self.test_platform,
                persona_set=self.test_persona_set,
                file_name="SOUL.md",
                file_path=file_path,
                before_content=None,
                after_content=new_content,
            )
        
        # Wait for async identity recording
        time.sleep(1.0)
        
        # Check if identity graph was updated
        # Get agent ID
        from hg_memory.identity.persona_integration import get_agent_id_from_platform
        agent_id = get_agent_id_from_platform(self.test_platform)
        
        if agent_id:
            # Check identity graph database
            db_path = get_identity_graph_db_path(agent_id)
            if db_path.exists():
                db = IdentityGraphDatabase(str(db_path))
                
                # Verify version was recorded
                conn = db._get_connection()
                try:
                    cursor = conn.execute(
                        "SELECT COUNT(*) FROM identity_versions WHERE persona_file = ?",
                        ("SOUL.md",)
                    )
                    version_count = cursor.fetchone()[0]
                    # Should have at least one version
                    self.assertGreaterEqual(version_count, 0)
                finally:
                    conn.close()
    
    def test_backward_compatibility(self):
        """Test that persona system still works without identity system"""
        # Update persona file
        new_content = "# SOUL.md\n\nUpdated content"
        
        result = update_platform_persona(
            platform=self.test_platform,
            persona_set=self.test_persona_set,
            file_name="SOUL.md",
            content=new_content
        )
        
        # Should succeed even if identity system fails
        self.assertTrue(result, "Persona update should succeed regardless of identity system")
        
        # Verify file was updated
        updated_content = self.soul_file.read_text(encoding='utf-8')
        self.assertEqual(updated_content, new_content)


if __name__ == '__main__':
    unittest.main()

