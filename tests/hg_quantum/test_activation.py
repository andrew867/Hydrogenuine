from __future__ import annotations

import json

import pytest

from hg_quantum.activation import (
    disable_module,
    enable_shadow_mode,
    get_activation_dashboard,
    promote_to_live,
)
from hg_quantum.config import get_quantum_config, is_quantum2_enabled, is_quantum2_shadow
from hg_quantum.shadow_telemetry import record_shadow_event


@pytest.fixture
def q2_workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    (tmp_path / "memory" / "overseer").mkdir(parents=True)
    return tmp_path


def test_enable_shadow_persists_config(q2_workspace):
    result = enable_shadow_mode("shell_model", actor_id="op", rationale="shadow trial", workspace_root=q2_workspace)
    assert result["ok"] is True
    assert result["mode"] == "shadow"
    cfg_path = q2_workspace / "memory" / "overseer" / "quantum_config.json"
    assert cfg_path.exists()
    data = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert data["quantum2"]["shell_model"]["enabled"] is False
    assert data["quantum2"]["shell_model"]["shadow"] is True
    assert is_quantum2_shadow("shell_model", q2_workspace) is True
    assert is_quantum2_enabled("shell_model", q2_workspace) is False


def test_promote_fingerprint_codec_without_control_group(q2_workspace):
    result = promote_to_live(
        "fingerprint_codec",
        actor_id="op",
        rationale="P-E1 pass",
        sign_off=True,
        workspace_root=q2_workspace,
    )
    assert result["ok"] is True
    assert is_quantum2_enabled("fingerprint_codec", q2_workspace) is True
    assert is_quantum2_shadow("fingerprint_codec", q2_workspace) is False


def test_promote_shell_requires_shadow_events_and_control_group(q2_workspace):
    enable_shadow_mode("shell_model", workspace_root=q2_workspace)
    blocked = promote_to_live("shell_model", sign_off=True, workspace_root=q2_workspace)
    assert blocked["ok"] is False
    record_shadow_event("shell_model", "offset_compare", {"diverged": True}, workspace_root=q2_workspace)
    still_blocked = promote_to_live("shell_model", sign_off=True, workspace_root=q2_workspace)
    assert still_blocked["ok"] is False
    assert "control-group" in still_blocked["error"]


def test_mediator_registry_live_blocked(q2_workspace):
    enable_shadow_mode("mediator_registry", workspace_root=q2_workspace)
    blocked = promote_to_live("mediator_registry", sign_off=True, workspace_root=q2_workspace)
    assert blocked["ok"] is False
    assert "stay shadow" in blocked["error"]


def test_disable_module(q2_workspace):
    enable_shadow_mode("barbell_topology", workspace_root=q2_workspace)
    disable_module("barbell_topology", workspace_root=q2_workspace)
    cfg = get_quantum_config(q2_workspace)
    block = cfg["quantum2"]["barbell_topology"]
    assert block["enabled"] is False
    assert block["shadow"] is False


def test_activation_dashboard_lists_modules(q2_workspace):
    dash = get_activation_dashboard(q2_workspace)
    assert dash["ok"] is True
    assert len(dash["modules"]) == 5
    components = {m["component"] for m in dash["modules"]}
    assert "fingerprint_codec" in components
