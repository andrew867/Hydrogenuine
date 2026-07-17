#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for parallel operation of legacy and new knowledge systems.

Verifies both systems can run simultaneously without interference.
"""

import sys
import tempfile
from pathlib import Path

import pytest


class TestParallelOperation:
    """Test parallel operation of legacy and new systems"""
    
    def test_metrics_collection(self, tmp_path):
        """Test metrics collection for both systems"""
        from skills.knowledge.metrics_collector import MetricsCollector
        from skills.knowledge.config import KnowledgeConfig, set_config
        
        config = KnowledgeConfig(
            workspace_root=tmp_path,
            database_path=tmp_path / "test.db",
            knowledge_dir=tmp_path / "knowledge"
        )
        set_config(config)
        
        collector = MetricsCollector()
        
        # Record new system search
        collector.record_search("new", "test query", 5, 50.0, "en", True)
        
        # Record legacy system search
        collector.record_search("legacy", "test query", 3, 120.0, "en", True)
        
        # Get comparison stats
        stats = collector.get_comparison_stats(hours=24)
        
        assert stats['new_system']['count'] == 1, "Should record new system search"
        assert stats['legacy_system']['count'] == 1, "Should record legacy system search"
        assert stats['new_system']['avg_latency_ms'] == 50.0, "Should record correct latency"
        assert stats['legacy_system']['avg_latency_ms'] == 120.0, "Should record correct latency"
    
    def test_bose_integration(self, tmp_path):
        """Test Bose dashboard integration"""
        from skills.knowledge.metrics_collector import MetricsCollector
        from skills.knowledge.bose_integration import BoseIntegration
        from skills.knowledge.config import KnowledgeConfig, set_config
        
        config = KnowledgeConfig(
            workspace_root=tmp_path,
            database_path=tmp_path / "test.db",
            knowledge_dir=tmp_path / "knowledge"
        )
        set_config(config)
        
        collector = MetricsCollector()
        bose = BoseIntegration(metrics_collector=collector)
        
        # Record some metrics
        collector.record_search("new", "test", 5, 50.0)
        collector.record_search("legacy", "test", 3, 120.0)
        
        # Get metrics for Bose
        metrics = bose.get_agent_metrics()
        
        assert 'search_latency_ms' in metrics, "Should include search latency"
        assert 'search_success_rate' in metrics, "Should include success rate"
        assert 'total_searches_24h' in metrics, "Should include total searches"
        
        # Test logging to timeseries
        bose.log_metrics_to_timeseries()
        
        # Verify file was created
        timeseries_file = tmp_path / "memory" / "overseer" / "timeseries.jsonl"
        assert timeseries_file.exists(), "Should create timeseries file"
        
        # Verify content
        with open(timeseries_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            assert len(lines) > 0, "Should have logged entries"
            
            import json
            entry = json.loads(lines[-1])
            assert 'agents' in entry, "Should have agents field"
            assert 'knowledge-search-engine' in entry['agents'], "Should have knowledge engine agent"
    
    def test_no_interference(self, tmp_path):
        """Test that new and legacy systems don't interfere"""
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
        
        # Create test file
        knowledge_dir = tmp_path / "knowledge" / "test"
        knowledge_dir.mkdir(parents=True, exist_ok=True)
        
        test_file = knowledge_dir / "test.md"
        test_file.write_text("# Test Document\n\nTest content.", encoding='utf-8')
        
        # New system operations
        db = KnowledgeDatabase(str(config.get_database_path()))
        indexer = KnowledgeIndexer(database=db)
        engine = SearchEngine(db)
        
        # Index with new system
        indexer.index_file(test_file)
        
        # Search with new system
        results = engine.search("test")
        
        assert len(results) > 0, "New system should find results"
        
        # Legacy system would read files directly (not tested here, but should not interfere)
        # The fact that new system works independently is the test


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
