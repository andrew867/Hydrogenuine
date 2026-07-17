"""Central runtime mode resolution — fixture never default."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[1]
POLICY_PATH = WORKSPACE / "configs/agent_zero/runtime_mode_policy.json"


class RuntimeMode(str, Enum):
    PRODUCTION = "production"
    LOCAL_DEV = "local_dev"
    TEST = "test"
    FIXTURE = "fixture"
    DRY_RUN = "dry_run"
    PROOF_REPLAY = "proof_replay"


class RuntimeModeSource(str, Enum):
    ENV = "env"
    CONFIG = "config"
    DEFAULT = "default"
    TEST_HARNESS = "test_harness"


class RuntimeModeError(Exception):
    """Invalid or disallowed runtime mode request."""


@dataclass(frozen=True)
class RuntimeModeReceipt:
    runtime_mode: RuntimeMode
    source: RuntimeModeSource
    fixture_allowed: bool
    cognitive_soak_active: bool
    infer_dry_run_requested: bool
    proof_replay_requested: bool
    resolved_at: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "runtime_mode": self.runtime_mode.value,
            "source": self.source.value,
            "fixture_allowed": self.fixture_allowed,
            "cognitive_soak_active": self.cognitive_soak_active,
            "infer_dry_run_requested": self.infer_dry_run_requested,
            "proof_replay_requested": self.proof_replay_requested,
            "resolved_at": self.resolved_at,
            "reason": self.reason,
        }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _truthy(val: str | None) -> bool:
    return str(val or "").strip().lower() in ("1", "true", "yes", "on")


def _load_policy() -> dict[str, Any]:
    if POLICY_PATH.is_file():
        return json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    return {}


def cognitive_soak_active() -> bool:
    return _truthy(os.environ.get("HG_COGNITIVE_SOAK_ACTIVE"))


def runtime_mode_from_env() -> tuple[RuntimeMode | None, RuntimeModeSource, str]:
    raw = (os.environ.get("HG_RUNTIME_MODE") or "").strip().lower()
    if not raw:
        return None, RuntimeModeSource.DEFAULT, "HG_RUNTIME_MODE unset"
    try:
        mode = RuntimeMode(raw)
    except ValueError as exc:
        raise RuntimeModeError(f"unknown HG_RUNTIME_MODE: {raw}") from exc
    if mode == RuntimeMode.FIXTURE and not _truthy(os.environ.get("HG_ALLOW_FIXTURE_MODE")):
        raise RuntimeModeError("HG_RUNTIME_MODE=fixture requires HG_ALLOW_FIXTURE_MODE=true")
    if mode == RuntimeMode.PROOF_REPLAY and not _truthy(os.environ.get("HG_PROOF_REPLAY")):
        raise RuntimeModeError("HG_RUNTIME_MODE=proof_replay requires HG_PROOF_REPLAY=true")
    return mode, RuntimeModeSource.ENV, f"HG_RUNTIME_MODE={raw}"


def runtime_mode_from_config() -> tuple[RuntimeMode | None, RuntimeModeSource, str]:
    policy = _load_policy()
    raw = (policy.get("default_runtime_mode") or "").strip().lower()
    if not raw:
        return None, RuntimeModeSource.DEFAULT, "config default unset"
    try:
        return RuntimeMode(raw), RuntimeModeSource.CONFIG, "runtime_mode_policy.json"
    except ValueError:
        return None, RuntimeModeSource.DEFAULT, f"invalid config default: {raw}"


def resolve_runtime_mode(*, test_mode: bool = False) -> RuntimeModeReceipt:
    """Resolve current runtime mode. Never fixture unless explicitly allowed."""
    if test_mode:
        mode = RuntimeMode.TEST
        return RuntimeModeReceipt(
            runtime_mode=mode,
            source=RuntimeModeSource.TEST_HARNESS,
            fixture_allowed=True,
            cognitive_soak_active=cognitive_soak_active(),
            infer_dry_run_requested=_truthy(os.environ.get("HG_INFER_DRY_RUN")),
            proof_replay_requested=_truthy(os.environ.get("HG_PROOF_REPLAY")),
            resolved_at=_now_iso(),
            reason="explicit test_mode=True",
        )

    try:
        env_mode, source, reason = runtime_mode_from_env()
    except RuntimeModeError:
        raise

    if env_mode is not None:
        mode = env_mode
        src = source
    else:
        cfg_mode, cfg_src, cfg_reason = runtime_mode_from_config()
        mode = cfg_mode or RuntimeMode.LOCAL_DEV
        src = cfg_src if cfg_mode else RuntimeModeSource.DEFAULT
        reason = cfg_reason if cfg_mode else "default local_dev"

    fixture_allowed = mode in (RuntimeMode.FIXTURE, RuntimeMode.TEST)
    if mode == RuntimeMode.FIXTURE and not _truthy(os.environ.get("HG_ALLOW_FIXTURE_MODE")):
        fixture_allowed = False

    if cognitive_soak_active() and mode == RuntimeMode.FIXTURE:
        raise RuntimeModeError("cognitive soak cannot run in fixture mode")

    return RuntimeModeReceipt(
        runtime_mode=mode,
        source=src,
        fixture_allowed=fixture_allowed,
        cognitive_soak_active=cognitive_soak_active(),
        infer_dry_run_requested=_truthy(os.environ.get("HG_INFER_DRY_RUN")),
        proof_replay_requested=_truthy(os.environ.get("HG_PROOF_REPLAY")),
        resolved_at=_now_iso(),
        reason=reason,
    )


def is_fixture_mode() -> bool:
    try:
        return resolve_runtime_mode().runtime_mode == RuntimeMode.FIXTURE
    except RuntimeModeError:
        return False


def is_test_mode() -> bool:
    return resolve_runtime_mode().runtime_mode == RuntimeMode.TEST


def is_dry_run_mode() -> bool:
    return resolve_runtime_mode().runtime_mode == RuntimeMode.DRY_RUN


def is_proof_replay_mode() -> bool:
    return resolve_runtime_mode().runtime_mode == RuntimeMode.PROOF_REPLAY


__all__ = [
    "RuntimeMode",
    "RuntimeModeError",
    "RuntimeModeReceipt",
    "RuntimeModeSource",
    "cognitive_soak_active",
    "is_dry_run_mode",
    "is_fixture_mode",
    "is_proof_replay_mode",
    "is_test_mode",
    "resolve_runtime_mode",
    "runtime_mode_from_config",
    "runtime_mode_from_env",
]
