#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Metrics collection for memory engine.

Tracks search performance, compares graph vs file system usage,
and stores metrics for analysis.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from hg_memory.config import get_config


class MemoryMetricsCollector:
    """Collect and store metrics for memory engine"""

    def __init__(self, metrics_dir: Optional[Path] = None):
        """
        Initialize metrics collector.

        Args:
            metrics_dir: Directory for metrics files (defaults to memory/memory_system_metrics/)
        """
        if metrics_dir is None:
            config = get_config()
            workspace_root = config.workspace_root
            metrics_dir = workspace_root / "memory" / "memory_system_metrics"

        self.metrics_dir = Path(metrics_dir)
        self.metrics_dir.mkdir(parents=True, exist_ok=True)

        self.performance_file = self.metrics_dir / "performance.jsonl"
        self.comparison_file = self.metrics_dir / "comparison.json"

    def record_search(
        self,
        system: str,
        query: str,
        result_count: int,
        latency_ms: float,
        language: Optional[str] = None,
        success: bool = True,
        search_type: Optional[str] = None
    ):
        """
        Record a search operation.

        Args:
            system: "graph" or "file" (graph-based vs file-based search)
            query: Search query
            result_count: Number of results returned
            latency_ms: Search latency in milliseconds
            language: Optional language code
            success: Whether search was successful
            search_type: Optional search type (e.g., "agent_memory", "context", "unified")
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "system": system,
            "query": query,
            "result_count": result_count,
            "latency_ms": latency_ms,
            "language": language or "unknown",
            "success": success,
            "search_type": search_type or "unknown"
        }

        # Append to performance log
        with open(self.performance_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    def record_indexing(
        self,
        agent_id: Optional[str] = None,
        files_indexed: int = 0,
        files_skipped: int = 0,
        files_errors: int = 0,
        total_time_ms: float = 0,
        entities_created: int = 0,
        relations_created: int = 0
    ):
        """
        Record indexing operation.

        Args:
            agent_id: Optional agent ID
            files_indexed: Number of files indexed
            files_skipped: Number of files skipped (unchanged)
            files_errors: Number of errors
            total_time_ms: Total indexing time in milliseconds
            entities_created: Number of entities created (for context graph)
            relations_created: Number of relations created (for context graph)
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "operation": "indexing",
            "agent_id": agent_id,
            "files_indexed": files_indexed,
            "files_skipped": files_skipped,
            "files_errors": files_errors,
            "total_time_ms": total_time_ms,
            "entities_created": entities_created,
            "relations_created": relations_created
        }

        with open(self.performance_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    def record_graph_query(
        self,
        query_type: str,
        agent_id: Optional[str] = None,
        result_count: int = 0,
        latency_ms: float = 0,
        success: bool = True
    ):
        """
        Record a graph query operation.

        Args:
            query_type: Type of query (e.g., "decision_chain", "connected_entities", "temporal")
            agent_id: Optional agent ID
            result_count: Number of results
            latency_ms: Query latency in milliseconds
            success: Whether query was successful
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "operation": "graph_query",
            "query_type": query_type,
            "agent_id": agent_id,
            "result_count": result_count,
            "latency_ms": latency_ms,
            "success": success
        }

        with open(self.performance_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    def get_comparison_stats(self, hours: int = 24) -> Dict:
        """
        Get comparison statistics between graph and file systems.

        Args:
            hours: Number of hours to look back

        Returns:
            Dictionary with comparison statistics
        """
        if not self.performance_file.exists():
            return {
                "graph_system": {"count": 0, "avg_latency_ms": 0, "success_rate": 0},
                "file_system": {"count": 0, "avg_latency_ms": 0, "success_rate": 0}
            }

        cutoff_time = time.time() - (hours * 3600)

        graph_searches = []
        file_searches = []

        with open(self.performance_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if entry.get('operation') in ['indexing', 'graph_query']:
                        continue

                    # Parse timestamp
                    entry_time = datetime.fromisoformat(entry['timestamp']).timestamp()
                    if entry_time < cutoff_time:
                        continue

                    if entry['system'] == 'graph':
                        graph_searches.append(entry)
                    elif entry['system'] == 'file':
                        file_searches.append(entry)
                except Exception:
                    continue

        def calc_stats(searches: List[Dict]) -> Dict:
            if not searches:
                return {"count": 0, "avg_latency_ms": 0, "success_rate": 0, "avg_result_count": 0}

            latencies = [s['latency_ms'] for s in searches]
            successes = [s['success'] for s in searches]
            result_counts = [s['result_count'] for s in searches]

            return {
                "count": len(searches),
                "avg_latency_ms": sum(latencies) / len(latencies),
                "min_latency_ms": min(latencies),
                "max_latency_ms": max(latencies),
                "success_rate": sum(successes) / len(successes) if successes else 0,
                "avg_result_count": sum(result_counts) / len(result_counts) if result_counts else 0
            }

        return {
            "graph_system": calc_stats(graph_searches),
            "file_system": calc_stats(file_searches),
            "period_hours": hours
        }

    def get_graph_query_stats(self, hours: int = 24) -> Dict:
        """
        Get statistics for graph queries.

        Args:
            hours: Number of hours to look back

        Returns:
            Dictionary with graph query statistics
        """
        if not self.performance_file.exists():
            return {
                "total_queries": 0,
                "query_types": {},
                "avg_latency_ms": 0,
                "success_rate": 0
            }

        cutoff_time = time.time() - (hours * 3600)

        queries = []
        query_types = {}

        with open(self.performance_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if entry.get('operation') != 'graph_query':
                        continue

                    entry_time = datetime.fromisoformat(entry['timestamp']).timestamp()
                    if entry_time < cutoff_time:
                        continue

                    queries.append(entry)
                    query_type = entry.get('query_type', 'unknown')
                    query_types[query_type] = query_types.get(query_type, 0) + 1
                except Exception:
                    continue

        if not queries:
            return {
                "total_queries": 0,
                "query_types": {},
                "avg_latency_ms": 0,
                "success_rate": 0
            }

        latencies = [q['latency_ms'] for q in queries]
        successes = [q['success'] for q in queries]

        return {
            "total_queries": len(queries),
            "query_types": query_types,
            "avg_latency_ms": sum(latencies) / len(latencies),
            "success_rate": sum(successes) / len(successes) if successes else 0
        }

    def get_metrics_for_bose(self) -> Dict:
        """
        Get metrics formatted for Bose dashboard integration.

        Returns:
            Dictionary with metrics for overseer
        """
        stats = self.get_comparison_stats(hours=24)
        graph_stats = stats['graph_system']
        file_stats = stats['file_system']

        total_searches = graph_stats['count'] + file_stats['count']

        graph_query_stats = self.get_graph_query_stats(hours=24)

        return {
            "memory_search_latency_ms": graph_stats['avg_latency_ms'] if graph_stats['count'] > 0 else 0,
            "memory_search_success_rate": graph_stats['success_rate'] if graph_stats['count'] > 0 else 0,
            "graph_query_count_24h": graph_stats['count'],
            "file_read_count_24h": file_stats['count'],
            "graph_query_operations_24h": graph_query_stats['total_queries'],
            "system_preference_ratio": (
                graph_stats['count'] / total_searches if total_searches > 0 else 0
            ),
            "latency_improvement_pct": (
                ((file_stats['avg_latency_ms'] - graph_stats['avg_latency_ms']) / file_stats['avg_latency_ms'] * 100)
                if file_stats['avg_latency_ms'] > 0 and graph_stats['avg_latency_ms'] > 0
                else 0
            ),
            "avg_result_count": graph_stats.get('avg_result_count', 0)
        }

    def save_comparison(self, comparison_data: Dict):
        """
        Save comparison data to JSON file.

        Args:
            comparison_data: Comparison statistics dictionary
        """
        with open(self.comparison_file, 'w', encoding='utf-8') as f:
            json.dump(comparison_data, f, indent=2, ensure_ascii=False)

    def load_comparison(self) -> Optional[Dict]:
        """
        Load comparison data from JSON file.

        Returns:
            Comparison data or None if not found
        """
        if not self.comparison_file.exists():
            return None

        with open(self.comparison_file, 'r', encoding='utf-8') as f:
            return json.load(f)
