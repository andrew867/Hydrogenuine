"""Provider routing — role to provider selection without generation."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from hg_core.infer_live.config import cognitive_soak_active, infer_dry_run_mode, provider_fallback_allowed
from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.model_provider_fabric.provider_receipts import (
    ProviderKind,
    ProviderMode,
    ProviderRealityVerdict,
    ProviderStatus,
    build_provider_receipt,
)
from hg_runtime.model_provider_fabric.openvino_probe import probe_openvino_health
from hg_runtime.model_provider_fabric.config_loader import load_registry
from hg_runtime.model_provider_fabric.types import (
    ModelProviderConfig, ProviderSelectionDecision, ProviderSelectionRequest,
)
from hg_runtime.runtime_mode import RuntimeMode, resolve_runtime_mode

WORKSPACE = Path(__file__).resolve().parents[2]
ROLES_PATH = WORKSPACE / "configs/agent_zero/model_provider_roles.json"

COGNITIVE_ROLES = frozenset({
    "AGENT_TURN_DECISION",
    "AGENT_SYNTHESIS_WRITE",
    "AGENT_DRAFT_WRITE",
})


def load_model_provider_roles(*, path: Path | None = None) -> dict[str, Any]:
    roles_path = path or ROLES_PATH
    if not roles_path.is_file():
        return {"roles": {}, "default_provider_id": "local_openvino"}
    return json.loads(roles_path.read_text(encoding="utf-8"))


def _config_hash() -> str:
    roles = load_model_provider_roles()
    return compute_record_hash({"roles": roles.get("roles", {}), "default": roles.get("default_provider_id")})


def _openvino_live_available() -> bool:
    """True when repo Windows OpenVINO provider is healthy with model loaded."""
    registry = load_registry()
    cfg = registry.get("windows-openvino-gpu")
    if cfg is None:
        for pid, c in registry.providers.items():
            if c.provider_type == "openvino_windows" and c.enabled:
                cfg = c
                break
    if cfg is None:
        return False
    health = probe_openvino_health(cfg)
    return bool(health.reachable and health.healthy and health.model_loaded)


def _provider_configured(provider_id: str) -> bool:
    """Check if provider is configured — OpenVINO uses health probe."""
    if provider_id in ("local_openvino", "windows-openvino-gpu"):
        env_val = os.environ.get("HG_PROVIDER_LOCAL_OPENVINO_CONFIGURED", "").lower()
        if env_val in ("1", "true", "yes"):
            return True
        if env_val in ("0", "false", "no"):
            return False
        return _openvino_live_available()
    if provider_id == "local_vllm":
        models_dir = WORKSPACE / "models"
        return models_dir.is_dir() and any(models_dir.iterdir()) if models_dir.is_dir() else False
    env_key = f"HG_PROVIDER_{provider_id.upper().replace('-', '_')}_CONFIGURED"
    return os.environ.get(env_key, "").lower() in ("1", "true", "yes")


def resolve_provider_route(
    role: str,
    *,
    runtime_mode: RuntimeMode | None = None,
) -> tuple[str, ProviderMode, ProviderKind]:
    """Resolve provider route for role — no inference call."""
    roles_cfg = load_model_provider_roles()
    provider_id = roles_cfg.get("default_provider_id", "local_openvino")
    role_upper = role.strip().upper()

    if runtime_mode is None:
        receipt = resolve_runtime_mode()
        mode = receipt.runtime_mode
        fixture_mode = receipt.fixture_allowed
        proof_replay = receipt.proof_replay_requested
    else:
        mode = runtime_mode
        fixture_mode = mode == RuntimeMode.FIXTURE
        proof_replay = mode == RuntimeMode.PROOF_REPLAY

    if proof_replay:
        return provider_id, ProviderMode.PROOF_REPLAY, ProviderKind.LOCAL_OPENVINO

    if infer_dry_run_mode(mode):
        return provider_id, ProviderMode.DRY_RUN, ProviderKind.LOCAL_OPENVINO

    if fixture_mode or mode == RuntimeMode.FIXTURE:
        return provider_id, ProviderMode.FIXTURE, ProviderKind.STUB

    if not _provider_configured(provider_id):
        if role_upper in COGNITIVE_ROLES and provider_fallback_allowed(mode):
            return provider_id, ProviderMode.FALLBACK_STUB, ProviderKind.STUB
        return provider_id, ProviderMode.UNAVAILABLE, ProviderKind.UNKNOWN

    return provider_id, ProviderMode.LIVE, ProviderKind.LOCAL_OPENVINO


def route_to_verdict(
    role: str,
    *,
    runtime_mode: RuntimeMode | None = None,
    request_body: dict[str, Any] | None = None,
) -> tuple[ProviderRealityVerdict, str, ProviderMode]:
    """Map route to honest verdict without generating output."""
    provider_id, mode, _kind = resolve_provider_route(role, runtime_mode=runtime_mode)
    role_upper = role.strip().upper()
    req_hash = compute_record_hash(request_body or {"role": role_upper})

    if mode == ProviderMode.LIVE:
        return ProviderRealityVerdict.GREEN_PROVIDER_LIVE_AVAILABLE, provider_id, mode
    if mode == ProviderMode.DRY_RUN:
        return ProviderRealityVerdict.YELLOW_PROVIDER_DRY_RUN_LABELLED, provider_id, mode
    if mode == ProviderMode.PROOF_REPLAY:
        return ProviderRealityVerdict.YELLOW_PROVIDER_PROOF_REPLAY_ONLY, provider_id, mode
    if mode == ProviderMode.FIXTURE:
        if role_upper in COGNITIVE_ROLES:
            return ProviderRealityVerdict.RED_PROVIDER_FIXTURE_AS_COGNITION, provider_id, mode
        return ProviderRealityVerdict.YELLOW_PROVIDER_DRY_RUN_LABELLED, provider_id, mode
    if mode == ProviderMode.FALLBACK_STUB:
        if role_upper in COGNITIVE_ROLES:
            return ProviderRealityVerdict.RED_PROVIDER_FALLBACK_AS_COGNITION, provider_id, mode
        return ProviderRealityVerdict.YELLOW_PROVIDER_UNAVAILABLE, provider_id, mode
    return ProviderRealityVerdict.YELLOW_PROVIDER_UNAVAILABLE, provider_id, mode


def select_provider(
    registry, request: ProviderSelectionRequest,
    *, runtime_mode: RuntimeMode | None = None,
) -> ProviderSelectionDecision:
    """Select a provider for a request, as an honest ProviderSelectionDecision.

    Thin adapter over the canonical functional route (`resolve_provider_route`) so
    callers that want a decision object (e.g. the Agent-0 dev boot) get one without
    re-implementing routing. The reality boundary is preserved: an UNAVAILABLE mode
    selects no provider, and a fallback stub is only selected when the caller allows
    it. No inference is performed here.
    """
    provider_id, mode, _kind = resolve_provider_route(request.role, runtime_mode=runtime_mode)
    cfg = registry.get(provider_id) if registry is not None else None
    provider_type = getattr(cfg, "provider_type", None)

    if mode == ProviderMode.UNAVAILABLE:
        return ProviderSelectionDecision(
            request_id=request.request_id, selected_provider_id=None,
            selected_provider_type=None, role=request.role, fallback_chain=(),
            failure_reason="DISABLED", rationale="provider_unavailable")

    if mode == ProviderMode.FALLBACK_STUB:
        if not request.allow_fallback_stub:
            return ProviderSelectionDecision(
                request_id=request.request_id, selected_provider_id=None,
                selected_provider_type=None, role=request.role, fallback_chain=(),
                failure_reason="ROLE_NOT_ALLOWED", rationale="fallback_stub_not_allowed")
        return ProviderSelectionDecision(
            request_id=request.request_id, selected_provider_id=provider_id,
            selected_provider_type=provider_type, role=request.role,
            fallback_chain=(provider_id,), failure_reason="FALLBACK_STUB_ONLY",
            rationale="fallback_stub")

    # LIVE / DRY_RUN / FIXTURE / PROOF_REPLAY — a provider is selected, mode-labelled.
    return ProviderSelectionDecision(
        request_id=request.request_id, selected_provider_id=provider_id,
        selected_provider_type=provider_type, role=request.role,
        fallback_chain=(provider_id,), failure_reason=None, rationale=mode.value)


__all__ = [
    "COGNITIVE_ROLES",
    "load_model_provider_roles",
    "resolve_provider_route",
    "route_to_verdict",
    "select_provider",
]
