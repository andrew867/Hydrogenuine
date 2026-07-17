"""OpenVINO runtime probe — integrates with model provider fabric health."""

from __future__ import annotations

from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[2]


def probe_openvino_runtime(*, allow_network: bool = True) -> dict[str, Any]:
    from hg_runtime.model_provider_fabric.config_loader import load_registry
    from hg_runtime.model_provider_fabric.openvino_probe import probe_openvino_health

    cloud_path = WORKSPACE / "configs/model_providers/cloud_providers.example.json"
    registry = load_registry(extra_paths=[cloud_path] if cloud_path.exists() else None)
    ov = next(
        (p for p in registry.providers.values() if p.provider_type in {"openvino_windows", "openvino_inprocess"} and p.enabled),
        None,
    )
    runtime_version: str | None = None
    try:
        import openvino  # type: ignore

        runtime_version = getattr(openvino, "__version__", None)
    except Exception:
        runtime_version = None

    if not ov:
        return {
            "present": bool(runtime_version),
            "runtime_version": runtime_version,
            "reachable": False,
            "healthy": False,
            "model_loaded": False,
            "resolved_device": None,
            "verdict": "YELLOW_PROVIDER_UNREACHABLE",
            "detail": "no enabled OpenVINO provider in registry",
        }

    health = probe_openvino_health(ov) if allow_network else None
    if health is None:
        return {
            "present": bool(runtime_version),
            "runtime_version": runtime_version,
            "reachable": False,
            "healthy": False,
            "model_loaded": False,
            "resolved_device": None,
            "verdict": "YELLOW_NETWORK_DISABLED",
            "detail": "network probes disabled",
        }
    return {
        "present": True,
        "runtime_version": runtime_version,
        "reachable": health.reachable,
        "healthy": health.healthy,
        "model_loaded": health.model_loaded,
        "resolved_device": health.resolved_device,
        "verdict": health.openvino_verdict,
        "detail": health.detail,
        "fallback_stub": health.fallback_stub,
    }


__all__ = ["probe_openvino_runtime"]
