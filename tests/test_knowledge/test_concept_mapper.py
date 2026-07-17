#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for concept mapper.

Test-driven development: Write tests BEFORE implementing concept_mapper.py
"""

import sys
import tempfile
import json
from pathlib import Path

import pytest


class TestConceptMapper:
    """Test concept mapping functionality"""
    
    def test_load_concept_file(self, tmp_path):
        """Test loading concept definition from JSON file"""
        from skills.knowledge.concept_mapper import ConceptMapper
        
        # Create concept file
        concept_file = tmp_path / "brother.json"
        concept_data = {
            "concept": "brother",
            "languages": {
                "en": ["brother"],
                "zh": ["哥哥", "弟弟", "兄弟"],
                "ja": ["兄", "弟", "兄弟"],
                "es": ["hermano"]
            },
            "semantic_variants": {
                "zh": {
                    "older_brother": "哥哥",
                    "younger_brother": "弟弟",
                    "generic": "兄弟"
                }
            }
        }
        with open(concept_file, 'w', encoding='utf-8') as f:
            json.dump(concept_data, f, ensure_ascii=False)
        
        # Create mapper with concepts directory
        mapper = ConceptMapper(concepts_dir=tmp_path)
        
        # Load concept
        concept = mapper.get_concept("brother")
        
        assert concept is not None, "Should load concept"
        assert concept['concept'] == "brother", "Should have correct concept name"
        assert "zh" in concept['languages'], "Should have Chinese translations"
        assert "哥哥" in concept['languages']['zh'], "Should include 哥哥"
    
    def test_get_related_terms(self, tmp_path):
        """Test getting related terms in target language"""
        from skills.knowledge.concept_mapper import ConceptMapper
        
        # Create concept file
        concept_file = tmp_path / "brother.json"
        concept_data = {
            "concept": "brother",
            "languages": {
                "en": ["brother"],
                "zh": ["哥哥", "弟弟", "兄弟"]
            }
        }
        with open(concept_file, 'w', encoding='utf-8') as f:
            json.dump(concept_data, f, ensure_ascii=False)
        
        mapper = ConceptMapper(concepts_dir=tmp_path)
        
        # Get related terms in Chinese
        terms = mapper.get_related("brother", target_language="zh")
        
        assert isinstance(terms, list), "Should return list of terms"
        assert len(terms) > 0, "Should return at least one term"
        assert "哥哥" in terms or "弟弟" in terms or "兄弟" in terms, "Should include Chinese terms"
    
    def test_expand_query_with_concepts(self, tmp_path):
        """Test query expansion using concept mappings"""
        from skills.knowledge.concept_mapper import ConceptMapper
        
        # Create concept file
        concept_file = tmp_path / "brother.json"
        concept_data = {
            "concept": "brother",
            "languages": {
                "en": ["brother"],
                "zh": ["哥哥", "弟弟", "兄弟"]
            }
        }
        with open(concept_file, 'w', encoding='utf-8') as f:
            json.dump(concept_data, f, ensure_ascii=False)
        
        mapper = ConceptMapper(concepts_dir=tmp_path)
        
        # Expand query
        expanded = mapper.expand_query("brother", query_language="en", target_languages=["zh"])
        
        assert isinstance(expanded, list), "Should return list of terms"
        assert "brother" in expanded, "Should include original term"
        # Should include Chinese equivalents
        assert any(term in expanded for term in ["哥哥", "弟弟", "兄弟"]), "Should include Chinese terms"
    
    def test_semantic_variants(self, tmp_path):
        """Test language-specific semantic variants"""
        from skills.knowledge.concept_mapper import ConceptMapper
        
        # Create concept file with semantic variants
        concept_file = tmp_path / "brother.json"
        concept_data = {
            "concept": "brother",
            "languages": {
                "en": ["brother"],
                "zh": ["哥哥", "弟弟", "兄弟"]
            },
            "semantic_variants": {
                "zh": {
                    "older_brother": "哥哥",
                    "younger_brother": "弟弟",
                    "generic": "兄弟"
                }
            }
        }
        with open(concept_file, 'w', encoding='utf-8') as f:
            json.dump(concept_data, f, ensure_ascii=False)
        
        mapper = ConceptMapper(concepts_dir=tmp_path)
        
        # Get semantic variant
        variant = mapper.get_semantic_variant("brother", "zh", "older_brother")
        
        assert variant == "哥哥", "Should return correct semantic variant"
    
    def test_multiple_concepts(self, tmp_path):
        """Test loading multiple concept files"""
        from skills.knowledge.concept_mapper import ConceptMapper
        
        # Create multiple concept files
        concepts = [
            {
                "concept": "brother",
                "languages": {"en": ["brother"], "zh": ["兄弟"]}
            },
            {
                "concept": "sister",
                "languages": {"en": ["sister"], "zh": ["姐妹"]}
            }
        ]
        
        for concept_data in concepts:
            concept_file = tmp_path / f"{concept_data['concept']}.json"
            with open(concept_file, 'w', encoding='utf-8') as f:
                json.dump(concept_data, f, ensure_ascii=False)
        
        mapper = ConceptMapper(concepts_dir=tmp_path)
        
        # Load both concepts
        brother = mapper.get_concept("brother")
        sister = mapper.get_concept("sister")
        
        assert brother is not None, "Should load brother concept"
        assert sister is not None, "Should load sister concept"
        assert brother['concept'] == "brother", "Should have correct concept name"
        assert sister['concept'] == "sister", "Should have correct concept name"
    
    def test_concept_not_found(self, tmp_path):
        """Test handling of non-existent concepts"""
        from skills.knowledge.concept_mapper import ConceptMapper
        
        mapper = ConceptMapper(concepts_dir=tmp_path)
        
        # Try to get non-existent concept
        concept = mapper.get_concept("nonexistent")
        
        assert concept is None, "Should return None for non-existent concept"
    
    def test_query_expansion_integration(self, tmp_path):
        """Test query expansion integrated with search"""
        from skills.knowledge.concept_mapper import ConceptMapper
        
        # Create concept file (use concept name as filename for easier lookup)
        concept_file = tmp_path / "artificial_intelligence.json"
        concept_data = {
            "concept": "artificial intelligence",
            "languages": {
                "en": ["artificial intelligence", "AI"],
                "zh": ["人工智能", "AI"]
            }
        }
        with open(concept_file, 'w', encoding='utf-8') as f:
            json.dump(concept_data, f, ensure_ascii=False)
        
        mapper = ConceptMapper(concepts_dir=tmp_path)
        
        # Expand query for cross-language search
        expanded = mapper.expand_query(
            "artificial intelligence",
            query_language="en",
            target_languages=["zh"]
        )
        
        assert "artificial intelligence" in expanded, "Should include original"
        assert "人工智能" in expanded, f"Should include Chinese equivalent, got: {expanded}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
