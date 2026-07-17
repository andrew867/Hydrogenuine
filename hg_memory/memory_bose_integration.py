#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BOSE dashboard integration for memory engine.

Integrates memory engine metrics with overseer Bose analysis system.
"""

import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

from hg_memory.memory_metrics import MemoryMetricsCollector
from hg_memory.config import get_config
from hg_gateway.shared_storage import append_overseer_timeseries, use_shared_gateway_db


class MemoryBoseIntegration:
    """Integrate memory engine with Bose dashboard"""

    def __init__(self, metrics_collector: Optional[MemoryMetricsCollector] = None):
        """
        Initialize BOSE integration.

        Args:
            metrics_collector: MemoryMetricsCollector instance (creates new if None)
        """
        if metrics_collector is None:
            metrics_collector = MemoryMetricsCollector()

        self.metrics_collector = metrics_collector
        self.agent_id = "memory-engine"
        self.config = get_config()

        # Get BOSE config
        bose_config = self.config.get_bose_config()
        if bose_config.get("enabled", True):
            self.enabled = True
        else:
            self.enabled = False

    def log_metrics_to_timeseries(self):
        """
        Log memory engine metrics to overseer timeseries file.

        Logs to memory/overseer/timeseries.jsonl in the format expected by BOSE.
        """
        if not self.enabled:
            return

        workspace_root = self.config.workspace_root

        timeseries_file = workspace_root / "memory" / "overseer" / "timeseries.jsonl"
        timeseries_file.parent.mkdir(parents=True, exist_ok=True)

        # Get metrics
        metrics = self.metrics_collector.get_metrics_for_bose()

        # Create entry in overseer format
        entry = {
            "timestamp": datetime.now().isoformat(),
            "agents": {
                self.agent_id: {
                    "memory_search_latency_ms": metrics.get("memory_search_latency_ms", 0),
                    "memory_search_success_rate": metrics.get("memory_search_success_rate", 0),
                    "graph_query_count_24h": metrics.get("graph_query_count_24h", 0),
                    "file_read_count_24h": metrics.get("file_read_count_24h", 0),
                    "graph_query_operations_24h": metrics.get("graph_query_operations_24h", 0),
                    "system_preference_ratio": metrics.get("system_preference_ratio", 0),
                    "latency_improvement_pct": metrics.get("latency_improvement_pct", 0),
                    "avg_result_count": metrics.get("avg_result_count", 0)
                }
            }
        }

        append_overseer_timeseries(entry)
        if not use_shared_gateway_db(timeseries_file):
            with open(timeseries_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    def get_agent_metrics(self) -> Dict:
        """
        Get current agent metrics for BOSE analysis.

        Returns:
            Dictionary with agent metrics
        """
        return self.metrics_collector.get_metrics_for_bose()

    def register_with_overseer(self):
        """
        Register memory engine as monitored agent with overseer.

        This is informational - the actual registration happens when
        metrics are logged to timeseries.jsonl. This method logs initial
        metrics to establish the agent in the overseer system.
        """
        if not self.enabled:
            return

        # Log initial metrics to establish agent in overseer
        self.log_metrics_to_timeseries()
