"""GRS feature flags and mode configuration."""

from __future__ import annotations

import os


def load_config(
    *,
    question: str,
    output_dir: str,
    demo_mode: bool = True,
    live_model: bool = False,
    live_sources: bool = False,
    playwright_capture: bool = False,
    model_base_url: str = "",
    model_name: str = "",
    require_live_model: bool = False,
) -> dict:
    live_model = live_model or os.environ.get("HG_GRS_LIVE_MODEL") == "1"
    live_sources = live_sources or os.environ.get("HG_GRS_LIVE_SOURCES") == "1"
    require_live_model = require_live_model or os.environ.get("HG_GRS_REQUIRE_LIVE_MODEL") == "1"

    model_base_url = model_base_url or os.environ.get(
        "HG_GRS_MODEL_BASE_URL", "http://127.0.0.1:1234/v1",
    )
    model_name = model_name or os.environ.get("HG_GRS_MODEL_NAME", "")

    model_mode = "live" if live_model else "fixture"
    source_mode = "live" if live_sources else "fixture"

    if live_model and live_sources:
        data_tier = "live"
    elif live_model or live_sources:
        data_tier = "mixed"
    else:
        data_tier = "fixture"

    return {
        "demo_mode": demo_mode,
        "question": question,
        "output_dir": output_dir,
        "model_mode": model_mode,
        "source_mode": source_mode,
        "data_tier": data_tier,
        "live_model_enabled": live_model,
        "live_sources_enabled": live_sources,
        "require_live_model": require_live_model,
        "model_base_url": model_base_url,
        "model_name": model_name,
        "cloud_providers_enabled": os.environ.get("HG_CLOUD_PROVIDERS_ENABLED", "false").lower() == "true",
        "playwright_available": playwright_capture,
        "operator_mode": "simulated_local_demo",
        "feature_flags": {
            "external_posting": False,
            "social_apis": False,
            "production_memory_writes": False,
            "live_external_effects": False,
        },
    }
