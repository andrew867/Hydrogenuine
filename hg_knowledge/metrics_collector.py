#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Metrics collection for knowledge engine.

Tracks search performance, compares old vs new system,
and stores metrics for analysis.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from .config import get_config


class MetricsCollector:
    """Collect and store metrics for knowledge engine"""

    def __init__(self, metrics_dir: Optional[Path] = None):
        """
        Initialize metrics collector.

        Args:
            metrics_dir: Directory for metrics files (defaults to knowledge/metrics/)
        """
        if metrics_dir is None:
            config = get_config()
            metrics_dir = config.get_metrics_dir()

        self.metrics_dir = Path(metrics_dir)
        self.metrics_dir.mkdir(parents=True, exist_ok=True)

        self.comparison_file = self.metrics_dir / "comparison.json"
        self.performance_file = self.metrics_dir / "performance.jsonl"

    def record_search(
        self,
        system: str,
        query: str,
        result_count: int,
        latency_ms: float,
        language: Optional[str] = None,
        success: bool = True,
    ):
        """
        Record a search operation.

        Args:
            system: "new" or "legacy"
            query: Search query
            result_count: Number of results returned
            latency_ms: Search latency in milliseconds
            language: Optional language code
            success: Whether search was successful
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "system": system,
            "query": query,
            "result_count": result_count,
            "latency_ms": latency_ms,
            "language": language or "unknown",
            "success": success,
        }

        with open(self.performance_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def record_indexing(
        self,
        files_indexed: int,
        files_skipped: int,
        files_errors: int,
        total_time_ms: float,
    ):
        """
        Record indexing operation.

        Args:
            files_indexed: Number of files indexed
            files_skipped: Number of files skipped (unchanged)
            files_errors: Number of errors
            total_time_ms: Total indexing time in milliseconds
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "operation": "indexing",
            "files_indexed": files_indexed,
            "files_skipped": files_skipped,
            "files_errors": files_errors,
            "total_time_ms": total_time_ms,
        }

        with open(self.performance_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def get_stats(self, hours: int = 24) -> Dict:
        """
        Get metrics statistics (alias for get_comparison_stats).
        """
        return self.get_comparison_stats(hours=hours)

    def get_comparison_stats(self, hours: int = 24) -> Dict:
        """
        Get comparison statistics between old and new systems.

        Args:
            hours: Number of hours to look back

        Returns:
            Dictionary with comparison statistics
        """
        if not self.performance_file.exists():
            return {
                "new_system": {"count": 0, "avg_latency_ms": 0, "success_rate": 0},
                "legacy_system": {"count": 0, "avg_latency_ms": 0, "success_rate": 0},
            }

        cutoff_time = time.time() - (hours * 3600)

        new_searches = []
        legacy_searches = []

        with open(self.performance_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if entry.get("operation") == "indexing":
                        continue

                    entry_time = datetime.fromisoformat(
                        entry["timestamp"]
                    ).timestamp()
                    if entry_time < cutoff_time:
                        continue

                    if entry["system"] == "new":
                        new_searches.append(entry)
                    elif entry["system"] == "legacy":
                        legacy_searches.append(entry)
                except Exception:
                    continue

        def calc_stats(searches: List[Dict]) -> Dict:
            if not searches:
                return {"count": 0, "avg_latency_ms": 0, "success_rate": 0}

            latencies = [s["latency_ms"] for s in searches]
            successes = [s["success"] for s in searches]

            return {
                "count": len(searches),
                "avg_latency_ms": sum(latencies) / len(latencies),
                "min_latency_ms": min(latencies),
                "max_latency_ms": max(latencies),
                "success_rate": sum(successes) / len(successes) if successes else 0,
            }

        return {
            "new_system": calc_stats(new_searches),
            "legacy_system": calc_stats(legacy_searches),
            "period_hours": hours,
        }

    def get_metrics_for_bose(self) -> Dict:
        """
        Get metrics formatted for Bose dashboard integration.

        Returns:
            Dictionary with metrics for overseer
        """
        stats = self.get_comparison_stats(hours=24)

        new_stats = stats["new_system"]
        legacy_stats = stats["legacy_system"]

        total_searches = new_stats["count"] + legacy_stats["count"]

        return {
            "search_latency_ms": (
                new_stats["avg_latency_ms"] if new_stats["count"] > 0 else 0
            ),
            "search_success_rate": (
                new_stats["success_rate"] if new_stats["count"] > 0 else 0
            ),
            "total_searches_24h": total_searches,
            "new_system_usage": (
                new_stats["count"] / total_searches if total_searches > 0 else 0
            ),
            "legacy_system_usage": (
                legacy_stats["count"] / total_searches if total_searches > 0 else 0
            ),
            "latency_improvement_pct": (
                (
                    (legacy_stats["avg_latency_ms"] - new_stats["avg_latency_ms"])
                    / legacy_stats["avg_latency_ms"]
                    * 100
                )
                if legacy_stats["avg_latency_ms"] > 0
                and new_stats["avg_latency_ms"] > 0
                else 0
            ),
        }

    def save_comparison(self, comparison_data: Dict):
        """
        Save comparison data to JSON file.

        Args:
            comparison_data: Comparison statistics dictionary
        """
        with open(self.comparison_file, "w", encoding="utf-8") as f:
            json.dump(comparison_data, f, indent=2, ensure_ascii=False)

    def load_comparison(self) -> Optional[Dict]:
        """
        Load comparison data from JSON file.

        Returns:
            Comparison data or None if not found
        """
        if not self.comparison_file.exists():
            return None

        with open(self.comparison_file, "r", encoding="utf-8") as f:
            return json.load(f)
