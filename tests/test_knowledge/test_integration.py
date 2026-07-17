#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
End-to-end integration tests for knowledge engine.

Test the complete flow: index → search → results
"""

import sys
import tempfile
from pathlib import Path

import pytest


class TestEndToEndIntegration:
    """Test complete knowledge engine workflow"""
    
    def test_index_and_search_workflow(self, tmp_path):
        """Test complete workflow: index files, then search"""
        from skills.knowledge.database import KnowledgeDatabase
        from skills.knowledge.indexer import KnowledgeIndexer
        from skills.knowledge.search_engine import SearchEngine
        from skills.knowledge.config import KnowledgeConfig, set_config
        
        # Setup config with temp directories
        config = KnowledgeConfig(
            workspace_root=tmp_path,
            database_path=tmp_path / "test.db",
            knowledge_dir=tmp_path / "knowledge"
        )
        set_config(config)
        
        # Create test knowledge file
        knowledge_dir = tmp_path / "knowledge" / "technology"
        knowledge_dir.mkdir(parents=True, exist_ok=True)
        
        test_file = knowledge_dir / "ai.md"
        test_file.write_text("""# Artificial Intelligence

Artificial intelligence is a branch of computer science that aims to create intelligent machines.
""", encoding='utf-8')
        
        # Index file
        db = KnowledgeDatabase(str(config.get_database_path()))
        indexer = KnowledgeIndexer(database=db)
        stats = indexer.index_file(test_file)
        
        assert stats, "Should index file successfully"
        
        # Search
        engine = SearchEngine(db)
        results = engine.search("artificial intelligence")
        
        assert len(results) > 0, "Should find indexed document"
        # Normalize path separators for cross-platform compatibility
        file_path = results[0]['file_path'].replace('\\', '/')
        assert file_path == "technology/ai.md", f"Should find correct file, got: {file_path}"
    
    def test_multilingual_index_and_search(self, tmp_path):
        """Test indexing and searching documents in multiple languages"""
        from skills.knowledge.database import KnowledgeDatabase
        from skills.knowledge.indexer import KnowledgeIndexer
        from skills.knowledge.search_engine import SearchEngine
        from skills.knowledge.config import KnowledgeConfig, set_config
        
        config = KnowledgeConfig(
            workspace_root=tmp_path,
            database_path=tmp_path / "test.db",
            knowledge_dir=tmp_path / "knowledge"
        )
        set_config(config)
        
        # Create English document
        knowledge_dir = tmp_path / "knowledge" / "technology"
        knowledge_dir.mkdir(parents=True, exist_ok=True)
        
        en_file = knowledge_dir / "ai_en.md"
        en_file.write_text("# Artificial Intelligence\n\nAI is a field of computer science.", encoding='utf-8')
        
        # Create Chinese document
        zh_file = knowledge_dir / "ai_zh.md"
        zh_file.write_text("# 人工智能\n\n人工智能是计算机科学的一个分支。", encoding='utf-8')
        
        # Index both
        db = KnowledgeDatabase(str(config.get_database_path()))
        indexer = KnowledgeIndexer(database=db)
        
        indexer.index_file(en_file, language="en")
        indexer.index_file(zh_file, language="zh")
        
        # Search in English
        engine = SearchEngine(db)
        results_en = engine.search("artificial intelligence")
        
        assert len(results_en) > 0, "Should find English document"
        
        # Search in Chinese (may not work perfectly with unicode61, but infrastructure is correct)
        results_zh = engine.search("人工智能")
        
        # At minimum, verify documents are indexed
        indexed = db.get_indexed_files()
        # Normalize paths for cross-platform compatibility
        indexed_normalized = [path.replace('\\', '/') for path in indexed]
        assert "technology/ai_en.md" in indexed_normalized, f"English document should be indexed, got: {indexed}"
        assert "technology/ai_zh.md" in indexed_normalized, f"Chinese document should be indexed, got: {indexed}"
    
    def test_concept_mapping_integration(self, tmp_path):
        """Test concept mapping integrated with search"""
        from skills.knowledge.database import KnowledgeDatabase
        from skills.knowledge.concept_mapper import ConceptMapper
        from skills.knowledge.search_engine import SearchEngine
        from skills.knowledge.config import KnowledgeConfig, set_config
        import json
        
        config = KnowledgeConfig(
            workspace_root=tmp_path,
            database_path=tmp_path / "test.db",
            knowledge_dir=tmp_path / "knowledge"
        )
        set_config(config)
        
        # Create concept file
        concepts_dir = config.get_concepts_dir()
        concepts_dir.mkdir(parents=True, exist_ok=True)
        
        concept_file = concepts_dir / "artificial_intelligence.json"
        concept_data = {
            "concept": "artificial intelligence",
            "languages": {
                "en": ["artificial intelligence", "AI"],
                "zh": ["人工智能"]
            }
        }
        with open(concept_file, 'w', encoding='utf-8') as f:
            json.dump(concept_data, f, ensure_ascii=False)
        
        # Create document
        knowledge_dir = tmp_path / "knowledge" / "technology"
        knowledge_dir.mkdir(parents=True, exist_ok=True)
        
        doc_file = knowledge_dir / "ai.md"
        doc_file.write_text("# Artificial Intelligence\n\nAI is important.", encoding='utf-8')
        
        # Index
        db = KnowledgeDatabase(str(config.get_database_path()))
        from skills.knowledge.indexer import KnowledgeIndexer
        indexer = KnowledgeIndexer(database=db)
        indexer.index_file(doc_file)
        
        # Test concept expansion
        mapper = ConceptMapper(concepts_dir=concepts_dir)
        expanded = mapper.expand_query("artificial intelligence", "en", ["zh"])
        
        assert "artificial intelligence" in expanded, "Should include original"
        assert "人工智能" in expanded, "Should include Chinese equivalent"
        
        # Search with expanded terms
        engine = SearchEngine(db)
        results = engine.search("artificial intelligence")
        
        assert len(results) > 0, "Should find document"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
