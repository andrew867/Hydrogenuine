"""Quantum-2 staged activation operator service."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from hg_quantum.activation import (
    disable_module,
    enable_shadow_mode,
    get_activation_dashboard,
    get_activation_history,
    get_divergence_review,
    promote_to_live,
)
from hg_quantum.production_shadow_runner import (
    assess_go_no_go,
    execute_fingerprint_codec_live_flip,
    execute_shadow_first_live_flips,
    get_live_activation_summary,
    run_all_shadow_workloads,
)
from hg_quantum.production_validation import (
    assess_post_live_divergence,
    get_validation_dashboard,
    run_all_validation_workloads,
)


def _workspace_root() -> Path:
    try:
        from hg_lib.config import get_workspace_root

        return Path(get_workspace_root())
    except Exception:
        return Path(".")


def activation_state() -> Dict[str, Any]:
    return get_activation_dashboard(_workspace_root())


def activation_history(limit: int = 50) -> Dict[str, Any]:
    return get_activation_history(limit=limit, workspace_root=_workspace_root())


def divergence_review(component: str) -> Dict[str, Any]:
    return get_divergence_review(component, workspace_root=_workspace_root())


def enable_shadow(component: str, *, actor_id: str, rationale: str) -> Dict[str, Any]:
    return enable_shadow_mode(component, actor_id=actor_id, rationale=rationale, workspace_root=_workspace_root())


def promote_live(component: str, *, actor_id: str, rationale: str, sign_off: bool) -> Dict[str, Any]:
    return promote_to_live(
        component,
        actor_id=actor_id,
        rationale=rationale,
        sign_off=sign_off,
        workspace_root=_workspace_root(),
    )


def disable(component: str, *, actor_id: str, rationale: str) -> Dict[str, Any]:
    return disable_module(component, actor_id=actor_id, rationale=rationale, workspace_root=_workspace_root())


def run_shadow_workloads() -> Dict[str, Any]:
    root = _workspace_root()
    batch = run_all_shadow_workloads(workspace_root=root)
    go = assess_go_no_go(root)
    return {"ok": True, "batch": batch, "go_no_go": go}


def go_no_go_state() -> Dict[str, Any]:
    return assess_go_no_go(_workspace_root())


def flip_fingerprint_codec_live(*, actor_id: str, rationale: str) -> Dict[str, Any]:
    return execute_fingerprint_codec_live_flip(
        actor_id=actor_id,
        rationale=rationale,
        workspace_root=_workspace_root(),
    )


def flip_shadow_first_live(*, actor_id: str, rationale: str) -> Dict[str, Any]:
    return execute_shadow_first_live_flips(
        actor_id=actor_id,
        rationale=rationale,
        workspace_root=_workspace_root(),
    )


def live_activation_summary() -> Dict[str, Any]:
    return get_live_activation_summary(_workspace_root())


def run_production_validation() -> Dict[str, Any]:
    return run_all_validation_workloads(workspace_root=_workspace_root())


def production_validation_status() -> Dict[str, Any]:
    return get_validation_dashboard(_workspace_root())


def production_divergence_report() -> Dict[str, Any]:
    return assess_post_live_divergence(_workspace_root())
