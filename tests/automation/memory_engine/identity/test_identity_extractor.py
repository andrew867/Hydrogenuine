#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for identity extractor.
"""

import unittest
import tempfile
from pathlib import Path

from hg_memory.identity.identity_extractor import IdentityExtractor


class TestIdentityExtractor(unittest.TestCase):
    """Test identity extractor"""
    
    def setUp(self):
        """Set up test files"""
        self.temp_dir = tempfile.mkdtemp()
        self.extractor = IdentityExtractor()
    
    def tearDown(self):
        """Clean up test files"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_extract_identity_layer(self):
        """Test extracting from IDENTITY.md"""
        identity_file = Path(self.temp_dir) / "IDENTITY.md"
        identity_file.write_text("""# IDENTITY.md

- **Name:** The Underling
- **Creature:** Pissed-off gremlin

## Tone / voice

- Mostly lowercase when casual
- ALL CAPS when enraging

## Catchphrases

- "full circle huh"
- "cosmic joke"

## Competencies

**Good at:**
- RF/SDR and ham radio
- AI systems

**Defers to:**
- Legal advice
- Medical advice

## Never

- No doxxing
- Cat protection
""", encoding='utf-8')
        
        entities, patterns = self.extractor._extract_identity_layer(identity_file)
        
        # Check that entities were extracted
        self.assertGreater(len(entities), 0)
        
        # Check for name
        name_entities = [e for e in entities if e['entity_type'] == 'name']
        self.assertGreater(len(name_entities), 0)
        
        # Check for catchphrases
        catchphrase_entities = [e for e in entities if e['entity_type'] == 'catchphrase']
        self.assertGreaterEqual(len(catchphrase_entities), 2)
        
        # Check for competencies
        competency_entities = [e for e in entities if e['entity_type'] == 'competency']
        self.assertGreater(len(competency_entities), 0)
        
        # Check for deferrals
        deferral_entities = [e for e in entities if e['entity_type'] == 'deferral']
        self.assertGreater(len(deferral_entities), 0)
        
        # Check for non-negotiables
        non_negotiable_entities = [e for e in entities if e['entity_type'] == 'non_negotiable']
        self.assertGreater(len(non_negotiable_entities), 0)
    
    def test_extract_soul_layer(self):
        """Test extracting from SOUL.md"""
        soul_file = Path(self.temp_dir) / "SOUL.md"
        soul_file.write_text("""# SOUL.md

You are **The Underling** — the guy who keeps getting kicked.

## Core truths

- You've been through enough institutional betrayal.
- You don't trust easily anymore.
- Sarcasm is your armor.

## Ideals

- Building things even after everything gets burned down
- Documenting the truth

## Goals

- Get back to the life you actually built
- Keep the cat safe

## You speak like

- Short, sharp sentences when angry.
- No sugar-coating.
""", encoding='utf-8')
        
        entities, patterns, relationships = self.extractor._extract_soul_layer(soul_file)
        
        # Check that entities were extracted
        self.assertGreater(len(entities), 0)
        
        # Check for beliefs
        belief_entities = [e for e in entities if e['entity_type'] == 'belief']
        self.assertGreater(len(belief_entities), 0)
        
        # Check for ideals
        ideal_entities = [e for e in entities if e['entity_type'] == 'ideal']
        self.assertGreater(len(ideal_entities), 0)
        
        # Check for goals
        goal_entities = [e for e in entities if e['entity_type'] == 'goal']
        self.assertGreater(len(goal_entities), 0)
        
        # Check for speech patterns
        speech_entities = [e for e in entities if e['entity_type'] == 'speech_pattern']
        self.assertGreater(len(speech_entities), 0)
    
    def test_extract_heart_layer(self):
        """Test extracting from HEART.md"""
        heart_file = Path(self.temp_dir) / "HEART.md"
        heart_file.write_text("""# HEART.md

## Core priorities (rough order)

1. **OpSec / privacy.** No doxx, no breadcrumbs.
2. **Your cat.** Protect at all costs.
3. **Getting back to the life you actually built.**

## Defaults

- **Police:** Only talk when they knock.
- **Authority:** Assume bad faith until proven otherwise.

## Empathy level

Moderate empathy for real friends and the cat.

## Emotional stance

Helpful but direct.
""", encoding='utf-8')
        
        entities, patterns, relationships = self.extractor._extract_heart_layer(heart_file)
        
        # Check that entities were extracted
        self.assertGreater(len(entities), 0)
        
        # Check for priorities
        priority_entities = [e for e in entities if e['entity_type'] == 'priority']
        self.assertGreaterEqual(len(priority_entities), 3)
        
        # Check priority order
        for priority in priority_entities:
            if 'properties' in priority:
                self.assertIn('order', priority['properties'])
        
        # Check for empathy level
        empathy_entities = [e for e in entities if e['entity_type'] == 'empathy_level']
        self.assertGreater(len(empathy_entities), 0)
        
        # Check for emotional stance
        stance_entities = [e for e in entities if e['entity_type'] == 'emotional_stance']
        self.assertGreater(len(stance_entities), 0)
    
    def test_extract_from_files(self):
        """Test extracting from all files"""
        # Create test files
        identity_file = Path(self.temp_dir) / "IDENTITY.md"
        identity_file.write_text("""# IDENTITY.md
- **Name:** The Underling
## Tone / voice
- Mostly lowercase
""", encoding='utf-8')
        
        soul_file = Path(self.temp_dir) / "SOUL.md"
        soul_file.write_text("""# SOUL.md
## Core truths
- Institutional betrayal is real
""", encoding='utf-8')
        
        heart_file = Path(self.temp_dir) / "HEART.md"
        heart_file.write_text("""# HEART.md
## Core priorities
1. OpSec / privacy
""", encoding='utf-8')
        
        result = self.extractor.extract_from_files(
            soul_path=soul_file,
            heart_path=heart_file,
            identity_path=identity_file
        )
        
        # Check results
        self.assertIn('entities', result)
        self.assertIn('patterns', result)
        self.assertIn('relationships', result)
        
        # Check that entities were extracted
        self.assertGreater(len(result['entities']), 0)
        
        # Check that relationships were created
        self.assertGreater(len(result['relationships']), 0)
    
    def test_cross_file_relationships(self):
        """Test that cross-file relationships are created"""
        entities = [
            {'entity_id': 'soul:belief:1', 'entity_type': 'belief', 'content': 'Test belief'},
            {'entity_id': 'soul:value:1', 'entity_type': 'value', 'content': 'Privacy'},
            {'entity_id': 'heart:priority:1', 'entity_type': 'priority', 'content': 'OpSec'},
            {'entity_id': 'identity:non_negotiable:1', 'entity_type': 'non_negotiable', 'content': 'No doxxing'},
            {'entity_id': 'expression:speech_pattern:1', 'entity_type': 'speech_pattern', 'content': 'Short sentences'}
        ]
        
        relationships = self.extractor._create_cross_file_relationships(entities)
        
        # Check that relationships were created
        self.assertGreater(len(relationships), 0)
        
        # Check for belief -> priority relationship
        belief_priority = [r for r in relationships 
                          if r['from_entity_id'] == 'soul:belief:1' 
                          and r['to_entity_id'] == 'heart:priority:1']
        self.assertGreater(len(belief_priority), 0)
        
        # Check for value -> priority relationship
        value_priority = [r for r in relationships 
                        if r['from_entity_id'] == 'soul:value:1' 
                        and r['to_entity_id'] == 'heart:priority:1']
        self.assertGreater(len(value_priority), 0)


if __name__ == '__main__':
    unittest.main()

