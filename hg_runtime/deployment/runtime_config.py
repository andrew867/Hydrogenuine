"""Runtime configuration loader for Docker deployment.

Fixture mode is default. Live effects disabled by default.
Remote providers disabled by default. .hg-local not required.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


_REQUIRED_ENV_KEYS = [
    "HG_MODE", "HG_RUNTIME_PROFILE", "HG_PROOF_DIR", "HG_REPORT_DIR",
    "HG_STATE_DIR", "HG_DB_URL", "HG_DISABLE_REMOTE_PROVIDERS",
    "HG_DISABLE_LIVE_EFFECTS", "HG_REQUIRE_OPERATOR_REVIEW",
    "HG_LMSTUDIO_BASE_URL", "HG_LMSTUDIO_SELECTED_MODEL",
    "HG_LMSTUDIO_ALLOWED_MODELS", "HG_LMSTUDIO_FORBIDDEN_PATTERNS",
    "HG_OPENVINO_MODEL_DIR", "HG_ALLOW_MODEL_DOWNLOADS",
    "HG_PROVIDER_LOCAL_OPENVINO_CONFIGURED", "HG_COGNITIVE_SOAK_ACTIVE",
]

_SECRET_KEYS = {"HG_DB_URL", "HG_STORAGE_POSTGRES_DSN", "HG_GATEWAY_POSTGRES_DSN"}


@dataclass
class RuntimeConfig:
    mode: str = "fixture"
    profile: str = "fixture"
    proof_dir: str = "/data/proofs"
    report_dir: str = "/data/reports"
    state_dir: str = "/data/state"
    db_url: str = "sqlite:////data/state/hydrogenuine.sqlite3"
    disable_remote_providers: bool = True
    disable_live_effects: bool = True
    require_operator_review: bool = True
    lmstudio_base_url: str = "http://host.docker.internal:1234/v1"
    lmstudio_selected_model: str = "google/gemma-4-e4b"
    lmstudio_allowed_models: list[str] = field(default_factory=lambda: ["google/gemma-4-e4b"])
    lmstudio_forbidden_patterns: list[str] = field(default_factory=lambda: ["deepseek", "offensive", "uncensored", "30b"])
    openvino_model_dir: str = "/models/openvino"
    allow_model_downloads: bool = False
    provider_openvino_configured: bool = False
    cognitive_soak_active: bool = True


def _bool_env(key: str, default: bool) -> bool:
    val = os.environ.get(key, "").lower()
    if val in ("1", "true", "yes"):
        return True
    if val in ("0", "false", "no"):
        return False
    return default


def load_runtime_config() -> RuntimeConfig:
    allowed_raw = os.environ.get("HG_LMSTUDIO_ALLOWED_MODELS", "google/gemma-4-e4b")
    forbidden_raw = os.environ.get("HG_LMSTUDIO_FORBIDDEN_PATTERNS", "deepseek,offensive,uncensored,30b")
    return RuntimeConfig(
        mode=os.environ.get("HG_MODE", "fixture"),
        profile=os.environ.get("HG_RUNTIME_PROFILE", "fixture"),
        proof_dir=os.environ.get("HG_PROOF_DIR", "/data/proofs"),
        report_dir=os.environ.get("HG_REPORT_DIR", "/data/reports"),
        state_dir=os.environ.get("HG_STATE_DIR", "/data/state"),
        db_url=os.environ.get("HG_DB_URL", "sqlite:////data/state/hydrogenuine.sqlite3"),
        disable_remote_providers=_bool_env("HG_DISABLE_REMOTE_PROVIDERS", True),
        disable_live_effects=_bool_env("HG_DISABLE_LIVE_EFFECTS", True),
        require_operator_review=_bool_env("HG_REQUIRE_OPERATOR_REVIEW", True),
        lmstudio_base_url=os.environ.get("HG_LMSTUDIO_BASE_URL", "http://host.docker.internal:1234/v1"),
        lmstudio_selected_model=os.environ.get("HG_LMSTUDIO_SELECTED_MODEL", "google/gemma-4-e4b"),
        lmstudio_allowed_models=[m.strip() for m in allowed_raw.split(",") if m.strip()],
        lmstudio_forbidden_patterns=[p.strip() for p in forbidden_raw.split(",") if p.strip()],
        openvino_model_dir=os.environ.get("HG_OPENVINO_MODEL_DIR", "/models/openvino"),
        allow_model_downloads=_bool_env("HG_ALLOW_MODEL_DOWNLOADS", False),
        provider_openvino_configured=_bool_env("HG_PROVIDER_LOCAL_OPENVINO_CONFIGURED", False),
        cognitive_soak_active=_bool_env("HG_COGNITIVE_SOAK_ACTIVE", True),
    )


def redacted_config(cfg: RuntimeConfig) -> dict:
    d = {
        "mode": cfg.mode,
        "profile": cfg.profile,
        "proof_dir": cfg.proof_dir,
        "report_dir": cfg.report_dir,
        "state_dir": cfg.state_dir,
        "db_url": "***REDACTED***",
        "disable_remote_providers": cfg.disable_remote_providers,
        "disable_live_effects": cfg.disable_live_effects,
        "require_operator_review": cfg.require_operator_review,
        "lmstudio_base_url": cfg.lmstudio_base_url,
        "lmstudio_selected_model": cfg.lmstudio_selected_model,
        "lmstudio_allowed_models": cfg.lmstudio_allowed_models,
        "lmstudio_forbidden_patterns": cfg.lmstudio_forbidden_patterns,
        "openvino_model_dir": cfg.openvino_model_dir,
        "allow_model_downloads": cfg.allow_model_downloads,
        "provider_openvino_configured": cfg.provider_openvino_configured,
        "cognitive_soak_active": cfg.cognitive_soak_active,
    }
    return d


def ensure_data_dirs(cfg: RuntimeConfig) -> None:
    for d in (cfg.proof_dir, cfg.report_dir, cfg.state_dir):
        Path(d).mkdir(parents=True, exist_ok=True)


def required_env_keys() -> list[str]:
    return _REQUIRED_ENV_KEYS[:]
