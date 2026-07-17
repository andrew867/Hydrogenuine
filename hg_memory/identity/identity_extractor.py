#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Identity extractor.

Extracts identity components from persona files (SOUL.md, HEART.md, IDENTITY.md).
Supports all 37 entity types across three layers.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Try to import seriousness analyzer (optional)
try:
    from hg_overseer.overseer_core.seriousness import compute_seriousness_score
    SERIOUSNESS_AVAILABLE = True
except ImportError:
    SERIOUSNESS_AVAILABLE = False


class IdentityExtractor:
    """Extract identity components from persona files"""
    
    def __init__(self):
        """Initialize identity extractor"""
        pass
    
    def extract_from_files(
        self,
        soul_path: Optional[Path] = None,
        heart_path: Optional[Path] = None,
        identity_path: Optional[Path] = None
    ) -> Dict[str, List[Dict]]:
        """
        Extract identity components from persona files.
        
        Args:
            soul_path: Path to SOUL.md file
            heart_path: Path to HEART.md file
            identity_path: Path to IDENTITY.md file
        
        Returns:
            Dictionary with keys: 'entities', 'patterns', 'relationships'
        """
        entities = []
        patterns = []
        relationships = []
        
        # Extract from IDENTITY.md (Identity Layer)
        if identity_path and identity_path.exists():
            identity_entities, identity_patterns = self._extract_identity_layer(identity_path)
            entities.extend(identity_entities)
            patterns.extend(identity_patterns)
        
        # Extract from SOUL.md (Soul Layer)
        if soul_path and soul_path.exists():
            soul_entities, soul_patterns, soul_relationships = self._extract_soul_layer(soul_path)
            entities.extend(soul_entities)
            patterns.extend(soul_patterns)
            relationships.extend(soul_relationships)
        
        # Extract from HEART.md (Heart Layer)
        if heart_path and heart_path.exists():
            heart_entities, heart_patterns, heart_relationships = self._extract_heart_layer(heart_path)
            entities.extend(heart_entities)
            patterns.extend(heart_patterns)
            relationships.extend(heart_relationships)
        
        # Create cross-file relationships
        cross_relationships = self._create_cross_file_relationships(entities)
        relationships.extend(cross_relationships)
        
        return {
            'entities': entities,
            'patterns': patterns,
            'relationships': relationships
        }
    
    def _extract_identity_layer(self, file_path: Path) -> Tuple[List[Dict], List[Dict]]:
        """Extract Identity Layer components from IDENTITY.md"""
        entities = []
        patterns = []
        
        content = file_path.read_text(encoding='utf-8')
        
        # Extract name
        name_match = re.search(r'- \*\*Name:\*\* (.+)', content)
        if name_match:
            entities.append({
                'entity_id': f"identity:name:{self._hash_content(name_match.group(1))}",
                'entity_type': 'name',
                'content': name_match.group(1).strip(),
                'source_file': str(file_path),
                'source_section': 'header'
            })
        
        # Extract role/creature
        creature_match = re.search(r'- \*\*Creature:\*\* (.+)', content)
        if creature_match:
            entities.append({
                'entity_id': f"identity:role:{self._hash_content(creature_match.group(1))}",
                'entity_type': 'role',
                'content': creature_match.group(1).strip(),
                'source_file': str(file_path),
                'source_section': 'header'
            })
        
        # Extract audience (from engagement sections)
        if re.search(r'## Engagement style|## Bot communication', content, re.IGNORECASE):
            entities.append({
                'entity_id': f"identity:audience:{self._hash_content('humans, agents')}",
                'entity_type': 'audience',
                'content': 'Humans and agents',
                'source_file': str(file_path),
                'source_section': 'engagement'
            })
        
        # Extract non-negotiables (NEVER sections)
        never_section = self._extract_section(content, r'## Never|## OpSec|NEVER')
        if never_section:
            never_items = self._extract_list_items(never_section)
            for item in never_items:
                entities.append({
                    'entity_id': f"identity:non_negotiable:{self._hash_content(item)}",
                    'entity_type': 'non_negotiable',
                    'content': item,
                    'source_file': str(file_path),
                    'source_section': 'never'
                })
        
        # Extract competencies (Good at / Defers to)
        competency_section = self._extract_section(content, r'## Competenc|Good at|Defers to', re.IGNORECASE)
        if competency_section:
            # Extract strengths - look for "Good at:" followed by list items
            good_at_pattern = r'\*\*Good at:\*\*|Good at:'
            if re.search(good_at_pattern, competency_section, re.IGNORECASE):
                # Find the section after "Good at:"
                good_at_match = re.search(good_at_pattern, competency_section, re.IGNORECASE)
                if good_at_match:
                    # Extract everything after "Good at:" until next section or "Defers to:"
                    good_at_text = competency_section[good_at_match.end():]
                    # Stop at "Defers to:" if present
                    defers_match = re.search(r'Defers to:', good_at_text, re.IGNORECASE)
                    if defers_match:
                        good_at_text = good_at_text[:defers_match.start()]
                    strengths = self._extract_list_items(good_at_text)
                    for strength in strengths:
                        entities.append({
                            'entity_id': f"identity:competency:{self._hash_content(strength)}",
                            'entity_type': 'competency',
                            'content': strength,
                            'source_file': str(file_path),
                            'source_section': 'competencies'
                        })
            
            # Extract deferrals - look for "Defers to:" followed by list items
            defers_pattern = r'\*\*Defers to:\*\*|Defers to:'
            if re.search(defers_pattern, competency_section, re.IGNORECASE):
                defers_match = re.search(defers_pattern, competency_section, re.IGNORECASE)
                if defers_match:
                    defers_text = competency_section[defers_match.end():]
                    deferrals = self._extract_list_items(defers_text)
                    for deferral in deferrals:
                        entities.append({
                            'entity_id': f"identity:deferral:{self._hash_content(deferral)}",
                            'entity_type': 'deferral',
                            'content': deferral,
                            'source_file': str(file_path),
                            'source_section': 'competencies'
                        })
        
        # Extract voice and formatting (Tone / voice section)
        voice_section = self._extract_section(content, r'## Tone|## voice', re.IGNORECASE)
        if voice_section:
            voice_items = self._extract_list_items(voice_section)
            for item in voice_items:
                entities.append({
                    'entity_id': f"identity:voice:{self._hash_content(item)}",
                    'entity_type': 'voice',
                    'content': item,
                    'source_file': str(file_path),
                    'source_section': 'tone'
                })
                
                # Extract formatting patterns
                if 'lowercase' in item.lower() or 'caps' in item.lower() or 'capitalization' in item.lower():
                    entities.append({
                        'entity_id': f"identity:formatting:{self._hash_content(item)}",
                        'entity_type': 'formatting',
                        'content': item,
                        'source_file': str(file_path),
                        'source_section': 'tone'
                    })
        
        # Extract catchphrases
        catchphrase_section = self._extract_section(content, r'## Catchphrase', re.IGNORECASE)
        if catchphrase_section:
            catchphrases = self._extract_list_items(catchphrase_section)
            for catchphrase in catchphrases:
                # Remove quotes if present
                catchphrase = catchphrase.strip('"\'')
                entities.append({
                    'entity_id': f"expression:catchphrase:{self._hash_content(catchphrase)}",
                    'entity_type': 'catchphrase',
                    'content': catchphrase,
                    'source_file': str(file_path),
                    'source_section': 'catchphrases'
                })
        
        # Extract speech patterns
        speech_patterns = self._extract_speech_patterns(content, file_path)
        entities.extend(speech_patterns)
        
        # Extract patterns (speech analysis)
        if SERIOUSNESS_AVAILABLE:
            speech_pattern = self._analyze_speech_patterns(content)
            if speech_pattern:
                patterns.append(speech_pattern)
        
        return entities, patterns
    
    def _extract_soul_layer(self, file_path: Path) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """Extract Soul Layer components from SOUL.md"""
        entities = []
        patterns = []
        relationships = []
        
        content = file_path.read_text(encoding='utf-8')
        
        # Extract mission statement
        mission_section = self._extract_section(content, r'## Mission|You are', re.IGNORECASE)
        if mission_section:
            # Try to find mission statement
            mission_match = re.search(r'You are (.+?) —', mission_section, re.DOTALL)
            if mission_match:
                mission_text = mission_match.group(1).strip()
                entities.append({
                    'entity_id': f"soul:mission:{self._hash_content(mission_text)}",
                    'entity_type': 'mission',
                    'content': mission_text,
                    'source_file': str(file_path),
                    'source_section': 'header'
                })
        
        # Extract core truths (beliefs)
        core_truths_section = self._extract_section(content, r'## Core truths', re.IGNORECASE)
        if core_truths_section:
            beliefs = self._extract_list_items(core_truths_section)
            for belief in beliefs:
                entities.append({
                    'entity_id': f"soul:belief:{self._hash_content(belief)}",
                    'entity_type': 'belief',
                    'content': belief,
                    'source_file': str(file_path),
                    'source_section': 'core_truths'
                })
        
        # Extract ideals
        ideals_section = self._extract_section(content, r'## Ideal', re.IGNORECASE)
        if ideals_section:
            ideals = self._extract_list_items(ideals_section)
            for ideal in ideals:
                entities.append({
                    'entity_id': f"soul:ideal:{self._hash_content(ideal)}",
                    'entity_type': 'ideal',
                    'content': ideal,
                    'source_file': str(file_path),
                    'source_section': 'ideals'
                })
        
        # Extract goals
        goals_section = self._extract_section(content, r'## Goal', re.IGNORECASE)
        if goals_section:
            goals = self._extract_list_items(goals_section)
            for goal in goals:
                entities.append({
                    'entity_id': f"soul:goal:{self._hash_content(goal)}",
                    'entity_type': 'goal',
                    'content': goal,
                    'source_file': str(file_path),
                    'source_section': 'goals'
                })
        
        # Extract values (implicit from content)
        values = self._extract_implicit_values(content)
        for value in values:
            entities.append({
                'entity_id': f"soul:value:{self._hash_content(value)}",
                'entity_type': 'value',
                'content': value,
                'source_file': str(file_path),
                'source_section': 'implicit'
            })
        
        # Extract speech patterns
        speech_section = self._extract_section(content, r'## You speak like', re.IGNORECASE)
        if speech_section:
            speech_items = self._extract_list_items(speech_section)
            for item in speech_items:
                entities.append({
                    'entity_id': f"expression:speech_pattern:{self._hash_content(item)}",
                    'entity_type': 'speech_pattern',
                    'content': item,
                    'source_file': str(file_path),
                    'source_section': 'speech'
                })
        
        # Extract emotional patterns
        emotional_patterns = self._extract_emotional_patterns(content, file_path)
        entities.extend(emotional_patterns)
        
        # Create relationships: beliefs influence values
        belief_entities = [e for e in entities if e['entity_type'] == 'belief']
        value_entities = [e for e in entities if e['entity_type'] == 'value']
        for belief in belief_entities:
            for value in value_entities:
                relationships.append({
                    'from_entity_id': belief['entity_id'],
                    'to_entity_id': value['entity_id'],
                    'relation_type': 'shapes'
                })
        
        return entities, patterns, relationships
    
    def _extract_heart_layer(self, file_path: Path) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """Extract Heart Layer components from HEART.md"""
        entities = []
        patterns = []
        relationships = []
        
        content = file_path.read_text(encoding='utf-8')
        
        # Extract priorities (ordered list)
        priorities_section = self._extract_section(content, r'## Core priorities', re.IGNORECASE)
        if priorities_section:
            priorities = self._extract_ordered_list_items(priorities_section)
            for i, priority in enumerate(priorities):
                entities.append({
                    'entity_id': f"heart:priority:{self._hash_content(priority)}",
                    'entity_type': 'priority',
                    'content': priority,
                    'source_file': str(file_path),
                    'source_section': 'priorities',
                    'properties': {'order': i + 1}
                })
        
        # Extract empathy level
        empathy_section = self._extract_section(content, r'## Empathy|empathy level', re.IGNORECASE)
        if empathy_section:
            empathy_text = empathy_section.split('\n')[0].strip()
            entities.append({
                'entity_id': f"heart:empathy_level:{self._hash_content(empathy_text)}",
                'entity_type': 'empathy_level',
                'content': empathy_text,
                'source_file': str(file_path),
                'source_section': 'empathy'
            })
        
        # Extract emotional stance
        if re.search(r'helpful|creepy|preachy|cold', content, re.IGNORECASE):
            stance_match = re.search(r'(helpful|creepy|preachy|cold|direct|warm)', content, re.IGNORECASE)
            if stance_match:
                entities.append({
                    'entity_id': f"heart:emotional_stance:{self._hash_content(stance_match.group(1))}",
                    'entity_type': 'emotional_stance',
                    'content': stance_match.group(1),
                    'source_file': str(file_path),
                    'source_section': 'emotional_stance'
                })
        
        # Extract handling patterns
        handling_patterns = self._extract_handling_patterns(content, file_path)
        entities.extend(handling_patterns)
        
        # Extract defaults (non-negotiables from HEART)
        defaults_section = self._extract_section(content, r'## Defaults', re.IGNORECASE)
        if defaults_section:
            defaults = self._extract_list_items(defaults_section)
            for default in defaults:
                entities.append({
                    'entity_id': f"identity:non_negotiable:{self._hash_content(default)}",
                    'entity_type': 'non_negotiable',
                    'content': default,
                    'source_file': str(file_path),
                    'source_section': 'defaults'
                })
        
        return entities, patterns, relationships
    
    def _extract_section(self, content: str, pattern: str, flags: int = 0) -> Optional[str]:
        """Extract a markdown section by header pattern"""
        match = re.search(pattern, content, flags)
        if not match:
            return None
        
        start = match.start()
        # Find next section header
        next_header = re.search(r'\n## ', content[start + 1:])
        if next_header:
            end = start + 1 + next_header.start()
        else:
            end = len(content)
        
        return content[start:end]
    
    def _extract_list_items(self, content: str) -> List[str]:
        """Extract list items from markdown"""
        items = []
        # Match both - and * list items
        for match in re.finditer(r'^[-*]\s+(.+)$', content, re.MULTILINE):
            item = match.group(1).strip()
            # Remove bold markers
            item = re.sub(r'\*\*([^*]+)\*\*', r'\1', item)
            if item:
                items.append(item)
        return items
    
    def _extract_ordered_list_items(self, content: str) -> List[str]:
        """Extract ordered list items from markdown"""
        items = []
        for match in re.finditer(r'^\d+\.\s+(.+)$', content, re.MULTILINE):
            item = match.group(1).strip()
            # Remove bold markers
            item = re.sub(r'\*\*([^*]+)\*\*', r'\1', item)
            if item:
                items.append(item)
        return items
    
    def _extract_speech_patterns(self, content: str, file_path: Path) -> List[Dict]:
        """Extract speech patterns from content"""
        patterns = []
        
        # Look for speech-related sections
        speech_keywords = [
            r'short sentences when angry',
            r'lowercase|ALL CAPS',
            r'sarcasm',
            r'swears',
            r'punctuation'
        ]
        
        for keyword in speech_keywords:
            if re.search(keyword, content, re.IGNORECASE):
                patterns.append({
                    'entity_id': f"expression:speech_pattern:{self._hash_content(keyword)}",
                    'entity_type': 'speech_pattern',
                    'content': keyword,
                    'source_file': str(file_path),
                    'source_section': 'speech'
                })
        
        return patterns
    
    def _extract_emotional_patterns(self, content: str, file_path: Path) -> List[Dict]:
        """Extract emotional patterns from content"""
        patterns = []
        
        # Look for emotional state mentions
        emotions = ['anger', 'curious', 'tired', 'excited', 'thoughtful', 'defensive', 'playful', 'serious']
        for emotion in emotions:
            if re.search(emotion, content, re.IGNORECASE):
                patterns.append({
                    'entity_id': f"expression:emotion:{self._hash_content(emotion)}",
                    'entity_type': 'emotion',
                    'content': emotion,
                    'source_file': str(file_path),
                    'source_section': 'emotional'
                })
        
        return patterns
    
    def _extract_handling_patterns(self, content: str, file_path: Path) -> List[Dict]:
        """Extract handling patterns (anger, insults, crisis, etc.)"""
        patterns = []
        
        # Extract anger handling
        if re.search(r'anger|angry|frustrated', content, re.IGNORECASE):
            patterns.append({
                'entity_id': f"heart:anger_handling:{self._hash_content('anger')}",
                'entity_type': 'anger_handling',
                'content': 'Handles anger directly',
                'source_file': str(file_path),
                'source_section': 'handling'
            })
        
        return patterns
    
    def _extract_implicit_values(self, content: str) -> List[str]:
        """Extract implicit values from content"""
        values = []
        
        # Look for value keywords
        value_keywords = {
            'privacy': r'privacy|opsec|doxx',
            'authenticity': r'authentic|genuine|real',
            'documentation': r'document|remember|track',
            'freedom': r'freedom|free|liberty',
            'truth': r'truth|truthful|honest'
        }
        
        for value_name, pattern in value_keywords.items():
            if re.search(pattern, content, re.IGNORECASE):
                values.append(value_name)
        
        return values
    
    def _analyze_speech_patterns(self, content: str) -> Optional[Dict]:
        """Analyze speech patterns using seriousness analyzer"""
        if not SERIOUSNESS_AVAILABLE:
            return None
        
        try:
            seriousness = compute_seriousness_score(content)
            
            # Analyze sentence length
            sentences = re.split(r'[.!?]+', content)
            avg_sentence_length = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
            
            # Analyze capitalization
            all_caps_ratio = len(re.findall(r'\b[A-Z]{3,}\b', content)) / max(len(content.split()), 1)
            lowercase_ratio = len(re.findall(r'\b[a-z]+\b', content)) / max(len(content.split()), 1)
            
            # Analyze profanity
            profanity_words = ['fuck', 'shit', 'damn', 'hell', 'ass']
            profanity_count = sum(content.lower().count(word) for word in profanity_words)
            profanity_density = profanity_count / max(len(content.split()), 1)
            
            return {
                'pattern_id': f"pattern:speech:{self._hash_content(content[:100])}",
                'pattern_type': 'speech',
                'properties': {
                    'seriousness_score': seriousness,
                    'avg_sentence_length': avg_sentence_length,
                    'all_caps_ratio': all_caps_ratio,
                    'lowercase_ratio': lowercase_ratio,
                    'profanity_density': profanity_density
                }
            }
        except Exception:
            return None
    
    def _create_cross_file_relationships(self, entities: List[Dict]) -> List[Dict]:
        """Create relationships between entities from different files"""
        relationships = []
        
        # Find beliefs and priorities
        beliefs = [e for e in entities if e['entity_type'] == 'belief']
        priorities = [e for e in entities if e['entity_type'] == 'priority']
        
        # Beliefs influence priorities
        for belief in beliefs:
            for priority in priorities:
                relationships.append({
                    'from_entity_id': belief['entity_id'],
                    'to_entity_id': priority['entity_id'],
                    'relation_type': 'influences'
                })
        
        # Values shape priorities
        values = [e for e in entities if e['entity_type'] == 'value']
        for value in values:
            for priority in priorities:
                relationships.append({
                    'from_entity_id': value['entity_id'],
                    'to_entity_id': priority['entity_id'],
                    'relation_type': 'shapes'
                })
        
        # Non-negotiables constrain priorities
        non_negotiables = [e for e in entities if e['entity_type'] == 'non_negotiable']
        for non_negotiable in non_negotiables:
            for priority in priorities:
                relationships.append({
                    'from_entity_id': non_negotiable['entity_id'],
                    'to_entity_id': priority['entity_id'],
                    'relation_type': 'constrains'
                })
        
        # Beliefs expressed through speech patterns
        speech_patterns = [e for e in entities if e['entity_type'] == 'speech_pattern']
        for belief in beliefs:
            for speech in speech_patterns:
                relationships.append({
                    'from_entity_id': belief['entity_id'],
                    'to_entity_id': speech['entity_id'],
                    'relation_type': 'expressed_through'
                })
        
        return relationships
    
    def _hash_content(self, content: str) -> str:
        """Create a short hash from content for entity IDs"""
        import hashlib
        return hashlib.md5(content.encode('utf-8')).hexdigest()[:8]
