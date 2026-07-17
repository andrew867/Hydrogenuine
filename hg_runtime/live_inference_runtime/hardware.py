"""INFER-LIVE hardware profile detection — no live model execution."""

from __future__ import annotations

import os
import platform
from pathlib import Path
from typing import Any

from hg_core.infer_live.errors import REFUSED_INSUFFICIENT_HARDWARE
from hg_core.infer_live.no_authority import advisory_only_marker
from hg_runtime.live_inference_runtime.model_registry import backend_priority
from hg_runtime.live_inference_runtime.types import (
    BackendKind,
    BackendReadiness,
    HardwareProfile,
    hardware_from_fixture,
)

MINIMUM_RAM_GB = 16
DEFAULT_MODEL_CACHE = Path.home() / ".cache" / "hydrogenuine" / "models"


def _detect_cpu_features() -> tuple[str, ...]:
    features: list[str] = []
    machine = platform.machine().lower()
    if machine in ("x86_64", "amd64"):
        features.append("x86_64")
        features.append("AVX2")
    elif machine in ("aarch64", "arm64"):
        features.append("aarch64")
    else:
        features.append(machine or "unknown")
    return tuple(features)


def _fixture_igpu_available() -> bool:
    """Non-authoritative readiness probe; does not invoke OpenVINO."""
    env = os.environ.get("HG_INFER_IGPU_AVAILABLE", "auto").lower()
    if env in ("1", "true", "yes"):
        return True
    if env in ("0", "false", "no"):
        return False
    return platform.system() == "Windows"


def _fixture_nvidia_detected() -> bool:
    env = os.environ.get("HG_INFER_NVIDIA_DETECTED", "auto").lower()
    if env in ("1", "true", "yes"):
        return True
    if env in ("0", "false", "no"):
        return False
    return False


def detect_hardware_profile(*, fixture: dict[str, Any] | None = None) -> HardwareProfile:
    """Detect hardware profile without live model execution."""
    if fixture:
        return hardware_from_fixture(fixture)

    cpu_features = _detect_cpu_features()
    ram_gb = MINIMUM_RAM_GB
    try:
        import ctypes

        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):  # type: ignore[attr-defined]
            ram_gb = max(MINIMUM_RAM_GB, int(stat.ullTotalPhys // (1024**3)))
    except Exception:
        ram_gb = MINIMUM_RAM_GB

    has_avx2 = "AVX2" in cpu_features or "aarch64" in cpu_features
    meets_minimum = has_avx2 and ram_gb >= MINIMUM_RAM_GB

    return HardwareProfile(
        profile_id="infer-hw:detected",
        cpu_features=cpu_features,
        igpu_available=_fixture_igpu_available(),
        ram_gb=ram_gb,
        model_cache_path=str(DEFAULT_MODEL_CACHE),
        meets_minimum_profile=meets_minimum,
        nvidia_detected=_fixture_nvidia_detected(),
        nvidia_required=False,
    )


def check_backend_readiness(
    hardware: HardwareProfile,
    *,
    readiness_check_only: bool = True,
) -> list[BackendReadiness]:
    """Backend availability checks are non-authoritative."""
    backends: list[BackendReadiness] = []

    igpu_ok = hardware.igpu_available and hardware.meets_minimum_profile
    backends.append(
        BackendReadiness(
            backend="openvino_igpu",
            available=igpu_ok,
            readiness_check_only=readiness_check_only,
            notes="OpenVINO Intel iGPU first-class; check only",
        )
    )

    cpu_ok = hardware.meets_minimum_profile and ("AVX2" in hardware.cpu_features or "aarch64" in hardware.cpu_features)
    backends.append(
        BackendReadiness(
            backend="openvino_cpu",
            available=cpu_ok,
            readiness_check_only=readiness_check_only,
            notes="OpenVINO CPU fallback first-class; check only",
        )
    )

    backends.append(
        BackendReadiness(
            backend="vllm_openvino_planned",
            available=False,
            readiness_check_only=True,
            notes="vLLM/OpenVINO planned/caveated — not required for minimum profile",
        )
    )

    backends.append(
        BackendReadiness(
            backend="cuda_optional",
            available=hardware.nvidia_detected,
            readiness_check_only=True,
            notes="CUDA/NVIDIA optional acceleration only — never required",
        )
    )

    return backends


def select_backend(
    hardware: HardwareProfile,
    *,
    preferred: BackendKind | None = None,
) -> BackendKind:
    """Select backend by priority; fails closed to CPU if iGPU unavailable."""
    if hardware.nvidia_required:
        return "none"
    readiness = {r.backend: r for r in check_backend_readiness(hardware)}
    order = backend_priority()
    if preferred and preferred != "cuda_optional" and readiness.get(preferred, BackendReadiness(preferred, False, True)).available:
        return preferred
    for backend in order:
        if backend == "cuda_optional":
            continue
        if readiness.get(backend) and readiness[backend].available:
            return backend
    if readiness.get("openvino_cpu") and readiness["openvino_cpu"].available:
        return "openvino_cpu"
    return "none"


def validate_minimum_hardware(hardware: HardwareProfile) -> dict[str, object]:
    if not hardware.meets_minimum_profile or hardware.nvidia_required:
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "reason_code": REFUSED_INSUFFICIENT_HARDWARE,
            "hardware": hardware.to_payload(),
            "permission_granted": False,
        }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "infer.advisory.hardware_ok",
        "hardware": hardware.to_payload(),
        "backend_readiness": [b.to_payload() for b in check_backend_readiness(hardware)],
        "permission_granted": False,
    }


__all__ = [
    "check_backend_readiness",
    "detect_hardware_profile",
    "select_backend",
    "validate_minimum_hardware",
]
