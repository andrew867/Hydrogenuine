"""Intel GPU telemetry probe — best effort, optional."""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any


def probe_intel_gpu() -> dict[str, float]:
    """Return GPU utilization metrics when Intel tooling is present."""
    metrics: dict[str, float] = {}
    if shutil.which("xpu-smi"):
        try:
            proc = subprocess.run(
                ["xpu-smi", "discovery"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if proc.returncode == 0 and proc.stdout:
                metrics["intel_gpu_discovery_ok"] = 1.0
        except (OSError, subprocess.TimeoutExpired):
            metrics["intel_gpu_discovery_ok"] = 0.0
    # Windows Intel GPU via typeperf is optional; keep contract-only when absent.
    if not metrics:
        metrics["intel_gpu_available"] = 0.0
    else:
        metrics.setdefault("intel_gpu_available", 1.0)
    return metrics


def probe_gpu_json() -> dict[str, Any]:
    return {"metrics": probe_intel_gpu(), "source": "best_effort"}


__all__ = ["probe_gpu_json", "probe_intel_gpu"]
