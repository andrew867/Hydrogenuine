"""Process metrics probe — CPU/RAM/uptime without external deps."""

from __future__ import annotations

import os
import time
from typing import Any

_START = time.time()


def probe_process_metrics() -> dict[str, float]:
    metrics: dict[str, float] = {"process_uptime_seconds": round(time.time() - _START, 1)}
    try:
        import psutil  # type: ignore

        proc = psutil.Process(os.getpid())
        mem = proc.memory_info()
        metrics["process_rss_mb"] = round(mem.rss / (1024 * 1024), 2)
        metrics["process_cpu_percent"] = float(proc.cpu_percent(interval=0.0) or 0.0)
        vm = psutil.virtual_memory()
        metrics["system_ram_used_percent"] = float(vm.percent)
        metrics["system_ram_available_mb"] = round(vm.available / (1024 * 1024), 1)
    except Exception:
        metrics["memory_pressure"] = 0.0
    else:
        metrics["memory_pressure"] = metrics.get("system_ram_used_percent", 0.0)
    return metrics


def probe_basic_cpu() -> dict[str, Any]:
    out: dict[str, Any] = {"available": False}
    try:
        import psutil  # type: ignore

        out["available"] = True
        out["cpu_count"] = psutil.cpu_count(logical=True)
        out["cpu_percent"] = psutil.cpu_percent(interval=0.05)
    except Exception as exc:
        out["detail"] = str(exc)
    return out


__all__ = ["probe_basic_cpu", "probe_process_metrics"]
