"""
Metrics: ledger, materializers, scheduler, 2PC, retention, policy, sandbox.
In-memory counters; format_openmetrics() for Prometheus scrape.
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict

_lock = threading.Lock()
_ledger_appends = 0
_ledger_errors = 0
_materializer_runs: Dict[str, int] = {}
_materializer_errors: Dict[str, int] = {}
_materializer_last_lag_ts: Dict[str, float] = {}
_sandbox_executions = 0
_sandbox_denials = 0
_2pc_proposals = 0
_2pc_denials = 0
_retention_jobs = 0
_retention_tombstones = 0
# Control surface (Pack 4): stream, api, controls
_stream_connections = 0
_stream_reconnects = 0
_stream_lag_seconds: Dict[str, float] = {}
_stream_dropped_updates = 0
_api_requests = 0
_api_errors = 0
_api_rate_limit_hits = 0
_control_actions_attempted = 0
_control_actions_denied = 0
_control_quorum_waits = 0


def record_ledger_append(success: bool = True) -> None:
    with _lock:
        global _ledger_appends, _ledger_errors
        if success:
            _ledger_appends += 1
        else:
            _ledger_errors += 1


def record_materializer_run(name: str, success: bool = True, lag_seconds: float = 0.0) -> None:
    with _lock:
        global _materializer_runs, _materializer_errors, _materializer_last_lag_ts
        _materializer_runs[name] = _materializer_runs.get(name, 0) + 1
        if not success:
            _materializer_errors[name] = _materializer_errors.get(name, 0) + 1
        if lag_seconds >= 0:
            _materializer_last_lag_ts[name] = lag_seconds


def record_sandbox_run(executed: bool) -> None:
    with _lock:
        global _sandbox_executions, _sandbox_denials
        if executed:
            _sandbox_executions += 1
        else:
            _sandbox_denials += 1


def record_2pc_proposal(approved: bool) -> None:
    with _lock:
        global _2pc_proposals, _2pc_denials
        _2pc_proposals += 1
        if not approved:
            _2pc_denials += 1


def record_retention_job(tombstone_count: int) -> None:
    with _lock:
        global _retention_jobs, _retention_tombstones
        _retention_jobs += 1
        _retention_tombstones += tombstone_count


def record_stream_connection(reconnect: bool = False) -> None:
    with _lock:
        global _stream_connections, _stream_reconnects
        _stream_connections += 1
        if reconnect:
            _stream_reconnects += 1


def record_stream_lag(scope_id: str, lag_seconds: float) -> None:
    with _lock:
        global _stream_lag_seconds
        _stream_lag_seconds[scope_id] = lag_seconds


def record_stream_dropped(count: int = 1) -> None:
    with _lock:
        global _stream_dropped_updates
        _stream_dropped_updates += count


def record_api_request(success: bool = True, rate_limited: bool = False) -> None:
    with _lock:
        global _api_requests, _api_errors, _api_rate_limit_hits
        _api_requests += 1
        if rate_limited:
            _api_rate_limit_hits += 1
        if not success:
            _api_errors += 1


def record_control_action(attempted: bool, denied: bool, quorum_wait: bool = False) -> None:
    with _lock:
        global _control_actions_attempted, _control_actions_denied, _control_quorum_waits
        if attempted:
            _control_actions_attempted += 1
        if denied:
            _control_actions_denied += 1
        if quorum_wait:
            _control_quorum_waits += 1


def get_metrics() -> Dict[str, Any]:
    """Return current metrics as dict for API or dashboards."""
    with _lock:
        return {
            "ledger": {"appends": _ledger_appends, "errors": _ledger_errors},
            "materializers": {"runs": dict(_materializer_runs), "errors": dict(_materializer_errors), "last_lag_seconds": dict(_materializer_last_lag_ts)},
            "sandbox": {"executions": _sandbox_executions, "denials": _sandbox_denials},
            "2pc": {"proposals": _2pc_proposals, "denials": _2pc_denials},
            "retention": {"jobs": _retention_jobs, "tombstones": _retention_tombstones},
            "stream": {"connections": _stream_connections, "reconnects": _stream_reconnects, "lag_seconds": dict(_stream_lag_seconds), "dropped_updates": _stream_dropped_updates},
            "api": {"requests": _api_requests, "errors": _api_errors, "rate_limit_hits": _api_rate_limit_hits},
            "controls": {"actions_attempted": _control_actions_attempted, "actions_denied": _control_actions_denied, "quorum_waits": _control_quorum_waits},
        }


def format_openmetrics() -> str:
    """OpenMetrics/Prometheus text format."""
    with _lock:
        lines = [
            "# HELP hg_ledger_appends_total Total ledger appends",
            "# TYPE hg_ledger_appends_total counter",
            f"hg_ledger_appends_total {_ledger_appends}",
            "# HELP hg_ledger_errors_total Total ledger append errors",
            "# TYPE hg_ledger_errors_total counter",
            f"hg_ledger_errors_total {_ledger_errors}",
            "# HELP hg_sandbox_executions_total Total sandbox tool executions",
            "# TYPE hg_sandbox_executions_total counter",
            f"hg_sandbox_executions_total {_sandbox_executions}",
            "# HELP hg_sandbox_denials_total Total sandbox denials",
            "# TYPE hg_sandbox_denials_total counter",
            f"hg_sandbox_denials_total {_sandbox_denials}",
            "# HELP hg_2pc_proposals_total Total 2PC proposals",
            "# TYPE hg_2pc_proposals_total counter",
            f"hg_2pc_proposals_total {_2pc_proposals}",
            "# HELP hg_retention_jobs_total Total retention jobs run",
            "# TYPE hg_retention_jobs_total counter",
            f"hg_retention_jobs_total {_retention_jobs}",
        ]
        for name, count in _materializer_runs.items():
            lines.append(f"hg_materializer_runs_total{{materializer=\"{name}\"}} {count}")
        for name, count in _materializer_errors.items():
            lines.append(f"hg_materializer_errors_total{{materializer=\"{name}\"}} {count}")
        lines.append("# HELP hg_stream_connections_total Control surface stream connections")
        lines.append("# TYPE hg_stream_connections_total counter")
        lines.append(f"hg_stream_connections_total {_stream_connections}")
        lines.append("# HELP hg_stream_reconnects_total Control surface stream reconnects")
        lines.append("# TYPE hg_stream_reconnects_total counter")
        lines.append(f"hg_stream_reconnects_total {_stream_reconnects}")
        lines.append("# HELP hg_stream_dropped_updates_total Control surface dropped updates")
        lines.append("# TYPE hg_stream_dropped_updates_total counter")
        lines.append(f"hg_stream_dropped_updates_total {_stream_dropped_updates}")
        lines.append("# HELP hg_api_requests_total Control surface API requests")
        lines.append("# TYPE hg_api_requests_total counter")
        lines.append(f"hg_api_requests_total {_api_requests}")
        lines.append("# HELP hg_api_errors_total Control surface API errors")
        lines.append("# TYPE hg_api_errors_total counter")
        lines.append(f"hg_api_errors_total {_api_errors}")
        lines.append("# HELP hg_api_rate_limit_hits_total Control surface API rate limit hits")
        lines.append("# TYPE hg_api_rate_limit_hits_total counter")
        lines.append(f"hg_api_rate_limit_hits_total {_api_rate_limit_hits}")
        lines.append("# HELP hg_control_actions_attempted_total Control actions attempted")
        lines.append("# TYPE hg_control_actions_attempted_total counter")
        lines.append(f"hg_control_actions_attempted_total {_control_actions_attempted}")
        lines.append("# HELP hg_control_actions_denied_total Control actions denied")
        lines.append("# TYPE hg_control_actions_denied_total counter")
        lines.append(f"hg_control_actions_denied_total {_control_actions_denied}")
        return "\n".join(lines) + "\n"
