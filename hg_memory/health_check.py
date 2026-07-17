#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Health checks and monitoring for memory engine.

Provides health status, metrics export, and observability.
"""

import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from hg_memory.config import get_config
from hg_memory.error_handling import check_database_integrity
from hg_memory.performance import get_performance_monitor, get_query_cache
from hg_gateway.shared_storage import use_shared_gateway_db


class HealthCheck:
    """Health check for memory engine"""

    def __init__(self):
        """Initialize health check"""
        self.config = get_config()

    def check_database_health(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Check health of agent memory database.

        Args:
            agent_id: Optional agent ID (checks all if None)

        Returns:
            Dictionary with health status
        """
        if agent_id:
            db_path = self.config.get_agent_memory_db_path(agent_id)
            return self._check_single_database(db_path, f"agent_memory_{agent_id}")

        # Check all agent databases
        workspace_root = self.config.workspace_root
        automation_dir = workspace_root / "memory" / "automation"

        results = {}
        if automation_dir.exists():
            for item in automation_dir.iterdir():
                if item.is_dir() and item.name.startswith("automation-"):
                    agent_id = item.name.replace("automation-", "", 1)
                    db_path = self.config.get_agent_memory_db_path(agent_id)
                    results[agent_id] = self._check_single_database(db_path, f"agent_memory_{agent_id}")

        return results

    def _check_single_database(self, db_path: Path, db_name: str) -> Dict[str, Any]:
        """Check health of a single database"""
        status = {
            "database": db_name,
            "exists": db_path.exists() or use_shared_gateway_db(db_path),
            "integrity": False,
            "size_bytes": 0,
            "table_count": 0,
            "error": None
        }

        if not status["exists"]:
            status["error"] = "Database file not found"
            return status

        try:
            if use_shared_gateway_db(db_path):
                status["table_count"] = self._shared_table_count(db_name)
                status["integrity"] = True
            else:
                status["size_bytes"] = db_path.stat().st_size
                status["integrity"] = check_database_integrity(db_path)
            if status["integrity"] and not use_shared_gateway_db(db_path):
                conn = sqlite3.connect(str(db_path))
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
                status["table_count"] = len(cursor.fetchall())
                conn.close()
        except Exception as e:
            status["error"] = str(e)

        return status

    def _shared_table_count(self, db_name: str) -> int:
        from hg_gateway.db import get_connection

        table_groups = {
            "context_graph": ["memory_context_entities", "memory_context_relations"],
        }
        if db_name.startswith("agent_memory_"):
            table_groups[db_name] = ["memory_agent_documents", "memory_entities", "memory_facts"]
        tables = table_groups.get(db_name)
        if not tables:
            with get_connection() as conn:
                row = conn.execute("SELECT COUNT(*) FROM _schema_version").fetchone()
            return 1 if row else 0
        with get_connection() as conn:
            return sum(1 for table in tables if self._shared_table_has_rows_or_exists(conn, table))

    @staticmethod
    def _shared_table_has_rows_or_exists(conn: Any, table: str) -> bool:
        try:
            conn.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone()
            return True
        except Exception:
            return False

    def check_context_graph_health(self) -> Dict[str, Any]:
        """
        Check health of context graph database.

        Returns:
            Dictionary with health status
        """
        db_path = self.config.get_context_graph_db_path()
        return self._check_single_database(db_path, "context_graph")

    def get_overall_health(self) -> Dict[str, Any]:
        """
        Get overall health status of memory engine.

        Returns:
            Dictionary with overall health status
        """
        agent_health = self.check_database_health()
        context_health = self.check_context_graph_health()

        # Count healthy vs unhealthy
        agent_count = len(agent_health)
        healthy_agents = sum(1 for h in agent_health.values() if h.get("integrity", False))

        overall_status = "healthy"
        if not context_health.get("integrity", False):
            overall_status = "degraded"
        if healthy_agents < agent_count * 0.8:  # Less than 80% healthy
            overall_status = "degraded"
        if healthy_agents == 0:
            overall_status = "unhealthy"

        return {
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "agent_databases": {
                "total": agent_count,
                "healthy": healthy_agents,
                "details": agent_health
            },
            "context_database": context_health,
            "performance": get_performance_monitor().get_stats("search", hours=1),
            "cache": get_query_cache().get_stats()
        }

    def export_metrics_prometheus(self) -> str:
        """
        Export metrics in Prometheus-compatible format.

        Returns:
            Prometheus metrics as string
        """
        health = self.get_overall_health()
        monitor = get_performance_monitor()
        cache = get_query_cache()

        lines = []

        # Health status
        status_value = 1 if health["status"] == "healthy" else 0
        lines.append(f'memory_engine_health{{status="{health["status"]}"}} {status_value}')

        # Database counts
        lines.append(f'memory_engine_agent_databases_total {health["agent_databases"]["total"]}')
        lines.append(f'memory_engine_agent_databases_healthy {health["agent_databases"]["healthy"]}')

        # Performance metrics
        perf_stats = health.get("performance", {})
        if perf_stats.get("count", 0) > 0:
            lines.append(f'memory_engine_search_avg_duration_ms {perf_stats["avg_duration_ms"]}')
            lines.append(f'memory_engine_search_p95_duration_ms {perf_stats["p95_duration_ms"]}')
            lines.append(f'memory_engine_search_success_rate {perf_stats["success_rate"]}')

        # Cache metrics
        cache_stats = cache.get_stats()
        lines.append(f'memory_engine_cache_size {cache_stats["size"]}')
        lines.append(f'memory_engine_cache_max_size {cache_stats["max_size"]}')

        return "\n".join(lines)


# Global health check instance
_health_check: Optional[HealthCheck] = None


def get_health_check() -> HealthCheck:
    """Get global health check instance"""
    global _health_check
    if _health_check is None:
        _health_check = HealthCheck()
    return _health_check


def health_check() -> Dict[str, Any]:
    """
    Convenience function for health check.

    Returns:
        Overall health status
    """
    return get_health_check().get_overall_health()
