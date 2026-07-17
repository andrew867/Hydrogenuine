"""Healthcheck module — reports mode, not secrets."""

from __future__ import annotations

import json
import sys

from .runtime_config import load_runtime_config, redacted_config


def run_health_check() -> dict:
    cfg = load_runtime_config()
    redacted = redacted_config(cfg)
    return {
        "healthy": True,
        "mode": cfg.mode,
        "profile": cfg.profile,
        "remote_providers_disabled": cfg.disable_remote_providers,
        "live_effects_disabled": cfg.disable_live_effects,
        "operator_review_required": cfg.require_operator_review,
        "model_downloads_allowed": cfg.allow_model_downloads,
        "fixture_safe": cfg.mode == "fixture",
    }


if __name__ == "__main__":
    result = run_health_check()
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["healthy"] else 1)
