"""
Pack3 Phase 5: Gateway metrics — request/tool/approval counters and latencies; Prometheus export.

Stores last N trace IDs for hg_diag export.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any, Dict, List

# In-memory counters
_lock = threading.Lock()
_requests_total = 0
_errors_total = 0
_tool_calls_total = 0
_tool_errors_total = 0
_tool_latency_seconds: List[float] = []  # last N for summary
_tool_latency_max = 100
_approvals_created_total = 0
_approvals_resolved_total = 0
_approval_latency_seconds: List[float] = []
_approval_latency_max = 100
_policy_denials_total = 0  # 403/503 from policy or breaker
_trace_ids: deque = deque(maxlen=200)  # last 200 for diag dump


def record_request(success: bool = True, trace_id: str | None = None) -> None:
    with _lock:
        global _requests_total, _errors_total
        _requests_total += 1
        if not success:
            _errors_total += 1
        if trace_id:
            _trace_ids.append({"trace_id": trace_id, "ts": time.time()})


def record_tool_call(success: bool = True, latency_s: float | None = None) -> None:
    with _lock:
        global _tool_calls_total, _tool_errors_total, _tool_latency_seconds
        _tool_calls_total += 1
        if not success:
            _tool_errors_total += 1
        if latency_s is not None:
            _tool_latency_seconds.append(latency_s)
            if len(_tool_latency_seconds) > _tool_latency_max:
                _tool_latency_seconds.pop(0)


def record_approval_created() -> None:
    with _lock:
        global _approvals_created_total
        _approvals_created_total += 1


def record_approval_resolved(latency_s: float | None = None) -> None:
    with _lock:
        global _approvals_resolved_total, _approval_latency_seconds
        _approvals_resolved_total += 1
        if latency_s is not None:
            _approval_latency_seconds.append(latency_s)
            if len(_approval_latency_seconds) > _approval_latency_max:
                _approval_latency_seconds.pop(0)


def record_policy_denial() -> None:
    with _lock:
        global _policy_denials_total
        _policy_denials_total += 1


def append_trace_id(trace_id: str) -> None:
    with _lock:
        _trace_ids.append({"trace_id": trace_id, "ts": time.time()})


def get_metrics() -> Dict[str, Any]:
    with _lock:
        tool_lat = _tool_latency_seconds
        app_lat = _approval_latency_seconds
        return {
            "gateway_requests_total": _requests_total,
            "gateway_errors_total": _errors_total,
            "gateway_tool_calls_total": _tool_calls_total,
            "gateway_tool_errors_total": _tool_errors_total,
            "gateway_tool_latency_seconds": list(tool_lat),
            "gateway_approvals_created_total": _approvals_created_total,
            "gateway_approvals_resolved_total": _approvals_resolved_total,
            "gateway_approval_latency_seconds": list(app_lat),
            "gateway_policy_denials_total": _policy_denials_total,
        }


def get_last_trace_ids(n: int = 50) -> List[Dict[str, Any]]:
    """Last N trace IDs with timestamp for hg_diag."""
    with _lock:
        return list(_trace_ids)[-n:]


def format_prometheus() -> str:
    lines = [
        "# HELP gateway_requests_total Total gateway API requests",
        "# TYPE gateway_requests_total counter",
        f"gateway_requests_total {_requests_total}",
        "# HELP gateway_errors_total Total gateway API errors",
        "# TYPE gateway_errors_total counter",
        f"gateway_errors_total {_errors_total}",
        "# HELP gateway_tool_calls_total Total tool invocations",
        "# TYPE gateway_tool_calls_total counter",
        f"gateway_tool_calls_total {_tool_calls_total}",
        "# HELP gateway_tool_errors_total Total tool invocation errors",
        "# TYPE gateway_tool_errors_total counter",
        f"gateway_tool_errors_total {_tool_errors_total}",
        "# HELP gateway_approvals_created_total Total approvals created",
        "# TYPE gateway_approvals_created_total counter",
        f"gateway_approvals_created_total {_approvals_created_total}",
        "# HELP gateway_approvals_resolved_total Total approvals resolved",
        "# TYPE gateway_approvals_resolved_total counter",
        f"gateway_approvals_resolved_total {_approvals_resolved_total}",
        "# HELP gateway_policy_denials_total Total policy/breaker denials (403/503)",
        "# TYPE gateway_policy_denials_total counter",
        f"gateway_policy_denials_total {_policy_denials_total}",
    ]
    with _lock:
        if _tool_latency_seconds:
            avg = sum(_tool_latency_seconds) / len(_tool_latency_seconds)
            lines.append("# HELP gateway_tool_latency_seconds_avg Average tool latency (last N)")
            lines.append("# TYPE gateway_tool_latency_seconds_avg gauge")
            lines.append(f"gateway_tool_latency_seconds_avg {avg}")
        if _approval_latency_seconds:
            avg = sum(_approval_latency_seconds) / len(_approval_latency_seconds)
            lines.append("# HELP gateway_approval_latency_seconds_avg Average approval resolve latency (last N)")
            lines.append("# TYPE gateway_approval_latency_seconds_avg gauge")
            lines.append(f"gateway_approval_latency_seconds_avg {avg}")
    return "\n".join(lines) + "\n"
