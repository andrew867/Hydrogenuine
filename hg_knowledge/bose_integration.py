#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bose dashboard integration for knowledge engine.

Integrates knowledge engine metrics with overseer Bose analysis system.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from .metrics_collector import MetricsCollector
from .config import get_config


class BoseIntegration:
    """Integrate knowledge engine with Bose dashboard"""

    def __init__(self, metrics_collector: Optional[MetricsCollector] = None):
        """
        Initialize Bose integration.

        Args:
            metrics_collector: MetricsCollector instance (creates new if None)
        """
        if metrics_collector is None:
            metrics_collector = MetricsCollector()

        self.metrics_collector = metrics_collector
        self.agent_id = "knowledge-search-engine"

    def log_metrics_to_timeseries(self):
        """
        Log knowledge engine metrics to overseer timeseries file.

        Logs to memory/overseer/timeseries.jsonl in the format expected by Bose.
        """
        config = get_config()
        workspace_root = config.workspace_root

        timeseries_file = workspace_root / "memory" / "overseer" / "timeseries.jsonl"
        timeseries_file.parent.mkdir(parents=True, exist_ok=True)

        metrics = self.metrics_collector.get_metrics_for_bose()

        entry = {
            "timestamp": datetime.now().isoformat(),
            "agents": {
                self.agent_id: {
                    "search_latency_ms": metrics.get("search_latency_ms", 0),
                    "search_success_rate": metrics.get("search_success_rate", 0),
                    "total_searches_24h": metrics.get("total_searches_24h", 0),
                    "new_system_usage": metrics.get("new_system_usage", 0),
                    "legacy_system_usage": metrics.get("legacy_system_usage", 0),
                    "latency_improvement_pct": metrics.get(
                        "latency_improvement_pct", 0
                    ),
                }
            },
        }

        with open(timeseries_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def get_agent_metrics(self) -> Dict:
        """
        Get current agent metrics for Bose analysis.

        Returns:
            Dictionary with agent metrics
        """
        return self.metrics_collector.get_metrics_for_bose()

    def register_with_overseer(self):
        """
        Register knowledge engine as monitored agent with overseer.

        Logs initial metrics to establish the agent in the overseer system.
        """
        self.log_metrics_to_timeseries()
