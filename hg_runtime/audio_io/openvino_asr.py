"""Experimental OpenVINO Whisper ASR probe — separate from faster-whisper.

faster-whisper uses CTranslate2 and does not become OpenVINO by configuration.
This module probes optional OpenVINO/optimum/intel stacks for a future adapter.
It is non-blocking: absence returns honest YELLOW, never RED for the main STT path.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

OPENVINO_ASR_UNAVAILABLE = "YELLOW_OPENVINO_ASR_EXPERIMENTAL_UNAVAILABLE"
OPENVINO_ASR_READY = "GREEN_OPENVINO_ASR_EXPERIMENTAL_READY"
OPENVINO_ASR_PROBE_OK = "GREEN_OPENVINO_ASR_EXPERIMENTAL_PROBE_OK"


@dataclass
class OpenVINOASRConfig:
    provider_id: str = "openvino-asr-experimental"
    enabled: bool = False
    backend: str = "openvino_asr_experimental"
    model_dir: str = ".hg-local/audio_models/openvino-asr/"
    device: str = "CPU"
    local_only: bool = True
    advisory_only: bool = True
    permission_granted: bool = False
    authority_created: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OpenVINOASRConfig:
        cfg = cls()
        for key, value in data.items():
            if key.startswith("_"):
                continue
            if hasattr(cfg, key):
                setattr(cfg, key, value)
        return cfg


def _imports_available() -> dict[str, bool]:
    status: dict[str, bool] = {}
    for name in ("openvino", "optimum", "transformers"):
        try:
            __import__(name)
            status[name] = True
        except ImportError:
            status[name] = False
    return status


def model_dir_present(cfg: OpenVINOASRConfig) -> bool:
    path = Path(cfg.model_dir)
    if not path.exists():
        return False
    return any(path.rglob("*.xml")) or any(path.rglob("*.bin"))


def probe(cfg: OpenVINOASRConfig | None = None) -> dict[str, Any]:
    """Return a non-blocking probe snapshot for doctor/gates."""
    cfg = cfg or OpenVINOASRConfig()
    imports = _imports_available()
    model_present = model_dir_present(cfg)
    implemented = False  # full adapter not wired in this pass
    if not implemented:
        verdict = OPENVINO_ASR_PROBE_OK
        reason = "experimental adapter not implemented; structural probe ok"
    elif not any(imports.values()):
        verdict = OPENVINO_ASR_UNAVAILABLE
        reason = "openvino/optimum/transformers not installed"
    elif not model_present:
        verdict = OPENVINO_ASR_UNAVAILABLE
        reason = "OpenVINO ASR model absent"
    else:
        verdict = OPENVINO_ASR_READY
        reason = "experimental stack present"

    return {
        "schema": "openvino-asr-probe",
        "provider_id": cfg.provider_id,
        "backend": cfg.backend,
        "enabled": cfg.enabled,
        "imports": imports,
        "model_dir": cfg.model_dir,
        "model_present": model_present,
        "implemented": implemented,
        "device": cfg.device,
        "verdict": verdict,
        "reason": reason,
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }


__all__ = [
    "OPENVINO_ASR_READY",
    "OPENVINO_ASR_UNAVAILABLE",
    "OpenVINOASRConfig",
    "model_dir_present",
    "probe",
]
