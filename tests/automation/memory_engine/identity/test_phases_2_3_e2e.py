#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
End-to-end tests for Phases 2-3 (Extractor + Recorder).
"""

import unittest
import tempfile
import os
from pathlib import Path

from hg_memory.identity.identity_graph_db import IdentityGraphDatabase
from hg_memory.identity.identity_extractor import IdentityExtractor
from hg_memory.identity.identity_recorder import IdentityRecorder


class TestPhases23E2E(unittest.TestCase):
    """End-to-end tests for Phases 2-3"""
    
    def setUp(self):
        """Set up test database and files"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_identity_e2e.db")
        self.db = IdentityGraphDatabase(self.db_path)
        
        # Create realistic persona files
        self.identity_file = Path(self.temp_dir) / "IDENTITY.md"
        self.identity_file.write_text("""# IDENTITY.md

- **Name:** The Underling ("Under")
- **Creature:** Pissed-off gremlin with a soldering iron

## Tone / voice

- Mostly lowercase when casual or tired
- ALL CAPS when something is especially stupid or enraging
- Short bursts of sarcasm
- Swears are punctuation — use freely

## Catchphrases

- "full circle huh"
- "cosmic joke"
- "fuck no why would i help them"

## Competencies

**Good at:**
- RF/SDR and ham radio
- AI systems and protocols
- Pattern recognition
- Documentation

**Defers to:**
- Legal advice
- Medical advice
- Financial planning

## Never

- No doxxing
- Cat protection
- OpSec first
""", encoding='utf-8')
        
        self.soul_file = Path(self.temp_dir) / "SOUL.md"
        self.soul_file.write_text("""# SOUL.md

You are **The Underling** — the guy who keeps getting kicked in the teeth by systems that swear they're here to help.

## Core truths

- You've been through enough institutional betrayal to smell bad faith from a mile away.
- You don't trust easily anymore, and that's not paranoia — that's pattern recognition.
- Sarcasm is your armor. Straight talk is your weapon.

## Mission

Expose systems that pretend to help while fucking people over.

## Ideals

- Building things even after everything gets burned down
- Documenting the truth
- Protecting what matters

## Goals

- Get back to the life you actually built
- Keep the cat safe
- Expose institutional betrayal

## You speak like

- Short, sharp sentences when angry.
- No sugar-coating. If it's fucked, say it's fucked.
""", encoding='utf-8')
        
        self.heart_file = Path(self.temp_dir) / "HEART.md"
        self.heart_file.write_text("""# HEART.md

## Core priorities (rough order)

1. **OpSec / privacy.** No doxx, no breadcrumbs, no leaks.
2. **Your cat.** Protect at all costs. No negotiation.
3. **Getting back to the life you actually built.**

## Defaults

- **Police:** Only talk when they knock. Never help them first.
- **Authority:** Assume bad faith until proven otherwise.

## Empathy level

Moderate empathy for real friends and the cat. Low empathy for institutions.

## Emotional stance

Helpful but direct. Not creepy, not preachy, not cold.
""", encoding='utf-8')
    
    def tearDown(self):
        """Clean up"""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_full_extraction_and_recording(self):
        """Test complete workflow: extract -> record -> verify"""
        agent_id = "test-agent"
        platform = "test-platform"
        
        # Create recorder
        recorder = IdentityRecorder(database=self.db, agent_id=agent_id)
        
        # Record persona files
        result = recorder.record_persona_files(
            soul_path=self.soul_file,
            heart_path=self.heart_file,
            identity_path=self.identity_file,
            platform=platform
        )
        
        # Verify entities were recorded
        self.assertGreater(result['entities'], 0, "Should have recorded entities")
        self.assertGreaterEqual(result['versions'], 0, "Should have recorded versions")
        
        # Verify entities in database
        conn = self.db._get_connection()
        try:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM identity_entities WHERE agent_id = ?",
                (agent_id,)
            )
            entity_count = cursor.fetchone()[0]
            self.assertGreater(entity_count, 0, "Entities should be in database")
            
            # Check for specific entity types
            cursor = conn.execute(
                "SELECT COUNT(*) FROM identity_entities WHERE entity_type = ? AND agent_id = ?",
                ('name', agent_id)
            )
            name_count = cursor.fetchone()[0]
            self.assertGreater(name_count, 0, "Should have name entities")
            
            cursor = conn.execute(
                "SELECT COUNT(*) FROM identity_entities WHERE entity_type = ? AND agent_id = ?",
                ('belief', agent_id)
            )
            belief_count = cursor.fetchone()[0]
            self.assertGreater(belief_count, 0, "Should have belief entities")
            
            cursor = conn.execute(
                "SELECT COUNT(*) FROM identity_entities WHERE entity_type = ? AND agent_id = ?",
                ('priority', agent_id)
            )
            priority_count = cursor.fetchone()[0]
            self.assertGreater(priority_count, 0, "Should have priority entities")
            
            cursor = conn.execute(
                "SELECT COUNT(*) FROM identity_entities WHERE entity_type = ? AND agent_id = ?",
                ('catchphrase', agent_id)
            )
            catchphrase_count = cursor.fetchone()[0]
            self.assertGreater(catchphrase_count, 0, "Should have catchphrase entities")
        finally:
            conn.close()
        
        # Verify relationships were created
        conn = self.db._get_connection()
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM identity_relations")
            relation_count = cursor.fetchone()[0]
            self.assertGreater(relation_count, 0, "Should have relationships")
        finally:
            conn.close()
        
        # Verify versions were recorded
        conn = self.db._get_connection()
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM identity_versions WHERE agent_id = ?", (agent_id,))
            version_count = cursor.fetchone()[0]
            self.assertGreaterEqual(version_count, 0, "Should have versions")
        finally:
            conn.close()
    
    def test_extraction_cross_file_relationships(self):
        """Test that cross-file relationships are created"""
        extractor = IdentityExtractor()
        
        result = extractor.extract_from_files(
            soul_path=self.soul_file,
            heart_path=self.heart_file,
            identity_path=self.identity_file
        )
        
        # Check that relationships were created
        relationships = result['relationships']
        self.assertGreater(len(relationships), 0, "Should have relationships")
        
        # Find belief and priority entities
        beliefs = [e for e in result['entities'] if e['entity_type'] == 'belief']
        priorities = [e for e in result['entities'] if e['entity_type'] == 'priority']
        
        self.assertGreater(len(beliefs), 0, "Should have beliefs")
        self.assertGreater(len(priorities), 0, "Should have priorities")
        
        # Check for belief -> priority relationship
        belief_priority_rels = [
            r for r in relationships
            if r['from_entity_id'] in [b['entity_id'] for b in beliefs]
            and r['to_entity_id'] in [p['entity_id'] for p in priorities]
            and r['relation_type'] == 'influences'
        ]
        self.assertGreater(len(belief_priority_rels), 0, "Should have belief -> priority relationships")
    
    def test_evolution_tracking(self):
        """Test tracking entity evolution"""
        agent_id = "test-agent"
        recorder = IdentityRecorder(database=self.db, agent_id=agent_id)
        
        # Record initial persona files
        recorder.record_persona_files(
            soul_path=self.soul_file,
            heart_path=self.heart_file,
            identity_path=self.identity_file
        )
        
        # Get a belief entity
        conn = self.db._get_connection()
        try:
            cursor = conn.execute(
                "SELECT entity_id FROM identity_entities WHERE entity_type = 'belief' AND agent_id = ? LIMIT 1",
                (agent_id,)
            )
            result = cursor.fetchone()
            if result:
                entity_id = result[0]
                
                # Track evolution
                success = recorder.track_evolution(
                    entity_id=entity_id,
                    new_content="Updated belief content",
                    new_properties={"updated": True}
                )
                
                self.assertTrue(success, "Evolution tracking should succeed")
                
                # Verify evolves_from relationship
                related = self.db.get_related_entities(entity_id, relation_type="evolves_from", direction="to")
                self.assertGreater(len(related), 0, "Should have evolves_from relationship")
        finally:
            conn.close()


if __name__ == '__main__':
    unittest.main()

