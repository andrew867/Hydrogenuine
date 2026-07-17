"""Provider hook configuration for OpenVINO Watchtower telemetry."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = WORKSPACE / "configs/openvino_watchtower/provider_hooks.json"


@dataclass(frozen=True)
class ProviderHooksConfig:
    enabled: bool = True
    strict_mode: bool = False
    capture_chunks: bool = True
    capture_payload_hash: bool = True
    capture_raw_prompt: bool = False
    capture_raw_output: bool = False
    redaction_required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "strict_mode": self.strict_mode,
            "capture_chunks": self.capture_chunks,
            "capture_payload_hash": self.capture_payload_hash,
            "capture_raw_prompt": self.capture_raw_prompt,
            "capture_raw_output": self.capture_raw_output,
            "redaction_required": self.redaction_required,
        }


def load_provider_hooks_config(path: Path | None = None) -> ProviderHooksConfig:
    cfg_path = path or DEFAULT_CONFIG
    data: dict[str, Any] = {}
    if cfg_path.is_file():
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
    return ProviderHooksConfig(
        enabled=bool(data.get("enabled", True)),
        strict_mode=bool(data.get("strict_mode", False)),
        capture_chunks=bool(data.get("capture_chunks", True)),
        capture_payload_hash=bool(data.get("capture_payload_hash", True)),
        capture_raw_prompt=bool(data.get("capture_raw_prompt", False)),
        capture_raw_output=bool(data.get("capture_raw_output", False)),
        redaction_required=bool(data.get("redaction_required", True)),
    )


__all__ = ["ProviderHooksConfig", "load_provider_hooks_config"]
