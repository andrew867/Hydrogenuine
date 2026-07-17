"""Load OpenVINO provider config from repo install scripts state."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[2]
PROVIDER_CONFIG = WORKSPACE / ".hg-local/openvino-provider/provider.config.json"
DEFAULT_ENDPOINT = "http://127.0.0.1:18080"
DEFAULT_HEALTH = f"{DEFAULT_ENDPOINT}/health"
DEFAULT_V1 = f"{DEFAULT_ENDPOINT}/v1"


def load_openvino_provider_config() -> dict[str, Any]:
    if PROVIDER_CONFIG.is_file():
        return json.loads(PROVIDER_CONFIG.read_text(encoding="utf-8"))
    return {}


def openvino_endpoint_base() -> str:
    import os

    env = os.environ.get("HG_OPENVINO_ENDPOINT", "").strip()
    if env:
        return env.rstrip("/")
    cfg = load_openvino_provider_config()
    host = cfg.get("host", "127.0.0.1")
    port = cfg.get("port", 18080)
    return f"http://{host}:{port}"


def openvino_model_id() -> str:
    import os

    return (
        os.environ.get("HG_OPENVINO_MODEL_ID")
        or os.environ.get("HG_LIVE_MODEL_ID")
        or load_openvino_provider_config().get("model_id")
        or "OpenVINO/Qwen2.5-1.5B-Instruct-int4-ov"
    )


def openvino_device() -> str:
    import os

    return os.environ.get("HG_OPENVINO_DEVICE") or load_openvino_provider_config().get("device") or "AUTO"
