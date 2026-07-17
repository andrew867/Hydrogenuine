#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Performance benchmarks for knowledge engine.

Test indexing speed, search latency, memory usage, etc.
"""

import sys
import time
import tempfile
from pathlib import Path

import pytest


class TestPerformance:
    """Test performance benchmarks"""
    
    def test_indexing_speed(self, tmp_path):
        """Test indexing speed (target: < 1 second per file)"""
        from skills.knowledge.database import KnowledgeDatabase
        from skills.knowledge.indexer import KnowledgeIndexer
        from skills.knowledge.config import KnowledgeConfig, set_config
        
        config = KnowledgeConfig(
            workspace_root=tmp_path,
            database_path=tmp_path / "test.db",
            knowledge_dir=tmp_path / "knowledge"
        )
        set_config(config)
        
        # Create test file
        knowledge_dir = tmp_path / "knowledge" / "test"
        knowledge_dir.mkdir(parents=True, exist_ok=True)
        
        test_file = knowledge_dir / "test.md"
        test_file.write_text("# Test Document\n\nThis is a test document with some content.", encoding='utf-8')
        
        # Measure indexing time
        db = KnowledgeDatabase(str(config.get_database_path()))
        indexer = KnowledgeIndexer(database=db)
        
        start_time = time.time()
        success = indexer.index_file(test_file)
        elapsed = time.time() - start_time
        
        assert success, "Should index successfully"
        assert elapsed < 1.0, f"Indexing should be fast (< 1s), took {elapsed:.3f}s"
    
    def test_search_latency(self, tmp_path):
        """Test search latency (target: < 500ms p95)"""
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
        
        # Create and index test file
        knowledge_dir = tmp_path / "knowledge" / "test"
        knowledge_dir.mkdir(parents=True, exist_ok=True)
        
        test_file = knowledge_dir / "test.md"
        test_file.write_text("# Test Document\n\nThis is a test document.", encoding='utf-8')
        
        db = KnowledgeDatabase(str(config.get_database_path()))
        indexer = KnowledgeIndexer(database=db)
        indexer.index_file(test_file)
        
        # Measure search time
        engine = SearchEngine(db)
        
        latencies = []
        for _ in range(10):
            start_time = time.time()
            results = engine.search("test")
            elapsed = (time.time() - start_time) * 1000  # Convert to ms
            latencies.append(elapsed)
        
        avg_latency = sum(latencies) / len(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
        
        assert avg_latency < 500, f"Average search latency should be < 500ms, got {avg_latency:.2f}ms"
        assert p95_latency < 1000, f"P95 search latency should be < 1000ms, got {p95_latency:.2f}ms"
    
    def test_incremental_indexing(self, tmp_path):
        """Test that incremental indexing only processes changed files"""
        from skills.knowledge.database import KnowledgeDatabase
        from skills.knowledge.indexer import KnowledgeIndexer
        from skills.knowledge.config import KnowledgeConfig, set_config
        
        config = KnowledgeConfig(
            workspace_root=tmp_path,
            database_path=tmp_path / "test.db",
            knowledge_dir=tmp_path / "knowledge"
        )
        set_config(config)
        
        # Create test file
        knowledge_dir = tmp_path / "knowledge" / "test"
        knowledge_dir.mkdir(parents=True, exist_ok=True)
        
        test_file = knowledge_dir / "test.md"
        test_file.write_text("# Test Document\n\nOriginal content.", encoding='utf-8')
        
        db = KnowledgeDatabase(str(config.get_database_path()))
        indexer = KnowledgeIndexer(database=db)
        
        # First index
        stats1 = indexer.index_all()
        assert stats1['indexed'] == 1, "Should index new file"
        
        # Second index (no changes)
        stats2 = indexer.index_all()
        assert stats2['indexed'] == 0, "Should not re-index unchanged file"
        assert stats2['skipped'] == 1, "Should skip unchanged file"
        
        # Modify file
        test_file.write_text("# Test Document\n\nModified content.", encoding='utf-8')
        
        # Third index (file changed)
        stats3 = indexer.index_all()
        assert stats3['indexed'] == 1, "Should re-index changed file"
    
    def test_multiple_files_indexing(self, tmp_path):
        """Test indexing multiple files"""
        from skills.knowledge.database import KnowledgeDatabase
        from skills.knowledge.indexer import KnowledgeIndexer
        from skills.knowledge.config import KnowledgeConfig, set_config
        
        config = KnowledgeConfig(
            workspace_root=tmp_path,
            database_path=tmp_path / "test.db",
            knowledge_dir=tmp_path / "knowledge"
        )
        set_config(config)
        
        # Create multiple test files
        knowledge_dir = tmp_path / "knowledge" / "test"
        knowledge_dir.mkdir(parents=True, exist_ok=True)
        
        for i in range(10):
            test_file = knowledge_dir / f"test_{i}.md"
            test_file.write_text(f"# Test Document {i}\n\nContent {i}.", encoding='utf-8')
        
        db = KnowledgeDatabase(str(config.get_database_path()))
        indexer = KnowledgeIndexer(database=db)
        
        start_time = time.time()
        stats = indexer.index_all()
        elapsed = time.time() - start_time
        
        assert stats['indexed'] == 10, "Should index all 10 files"
        assert elapsed < 10.0, f"Should index 10 files quickly (< 10s), took {elapsed:.3f}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
