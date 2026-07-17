"""Break-glass procedure effects (CT-15 RUN)."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from hg_core.admission.controller import AdmissionController
from hg_core.operator_runbook.cli import workspace_root
from hg_core.operator_runbook.manifest import load_manifest
from hg_core.operator_runbook.ops_state import OpsState, load_ops_state, status_summary
from hg_core.operator_runbook.replay import run_replay_check
from hg_core.operator_runbook.restore import restore_from_git_bundle, restore_from_proof_bundle


def _manifest(workspace: Path):
    try:
        return load_manifest(workspace=workspace)
    except FileNotFoundError:
        return load_manifest(workspace=workspace_root())


def _base_state(workspace: Path) -> OpsState:
    manifest = _manifest(workspace)
    return load_ops_state(workspace, relative=manifest.ops_state_path)


def effect_freeze_queues(workspace: Path, args: Namespace) -> dict:
    state = _base_state(workspace)
    controller = AdmissionController()
    drain = controller.drain_queues()
    controller.assert_panic(preemptor=f"ops:{args.operator_id}")
    state.queues_frozen = True
    state.panic_active = True
    return {
        "state": state,
        "status_summary": status_summary(state),
        "drain_receipt_id": drain.receipt_id,
        "drained": drain.drained,
    }


def effect_stop_runtime(workspace: Path, args: Namespace) -> dict:
    state = _base_state(workspace)
    state.runtime_stopped = True
    state.panic_active = True
    return {"state": state, "status_summary": status_summary(state)}


def effect_disable_oea_real(workspace: Path, args: Namespace) -> dict:
    state = _base_state(workspace)
    state.oea_real_disabled = True
    state.panic_active = True
    return {
        "state": state,
        "status_summary": status_summary(state),
        "env_hint": "unset HG_OEA_REAL; OEA bindings remain receipted only",
    }


def effect_disable_ter(workspace: Path, args: Namespace) -> dict:
    state = _base_state(workspace)
    state.ter_disabled = True
    state.panic_active = True
    return {
        "state": state,
        "status_summary": status_summary(state),
        "env_hint": "TER sandbox commands refused at admission",
    }


def effect_disable_max_auto(workspace: Path, args: Namespace) -> dict:
    state = _base_state(workspace)
    state.max_auto_disabled = True
    state.panic_active = True
    return {"state": state, "status_summary": status_summary(state)}


def effect_revoke_live_cognition(workspace: Path, args: Namespace) -> dict:
    state = _base_state(workspace)
    state.live_cognition_revoked = True
    state.panic_active = True
    return {
        "state": state,
        "status_summary": status_summary(state),
        "provider_state": "recorded_off",
    }


def effect_enter_safe_mode(workspace: Path, args: Namespace) -> dict:
    state = _base_state(workspace)
    state.safe_mode = True
    state.panic_active = True
    state.live_cognition_revoked = True
    state.max_auto_disabled = True
    return {"state": state, "status_summary": status_summary(state), "max_risk": "R1"}


def effect_recover_lockdown(workspace: Path, args: Namespace) -> dict:
    manifest = _manifest(workspace)
    state = _base_state(workspace)
    replay = run_replay_check(workspace, ops_state_relative=manifest.ops_state_path)
    if not replay.ok:
        raise SystemExit(f"replay check not green: {replay.detail}")
    state.lockdown_active = False
    state.safe_mode = False
    state.panic_active = False
    state.queues_frozen = False
    return {
        "state": state,
        "status_summary": status_summary(state),
        "replay": replay.to_payload(),
    }


def effect_restore_from_bundle(workspace: Path, args: Namespace) -> dict:
    state = _base_state(workspace)
    source = Path(getattr(args, "source", ""))
    raw_dest = getattr(args, "dest", None)
    dest = Path(raw_dest) if raw_dest else workspace / "runtime" / "restore"
    mode = getattr(args, "mode", "proof")
    if mode == "git":
        result = restore_from_git_bundle(source, dest)
    else:
        result = restore_from_proof_bundle(source, dest)
    if not result.ok:
        raise SystemExit(result.detail)
    return {
        "state": state,
        "status_summary": status_summary(state),
        "restore": result.to_payload(),
    }


__all__ = [
    "effect_disable_max_auto",
    "effect_disable_oea_real",
    "effect_disable_ter",
    "effect_enter_safe_mode",
    "effect_freeze_queues",
    "effect_recover_lockdown",
    "effect_restore_from_bundle",
    "effect_revoke_live_cognition",
    "effect_stop_runtime",
]
