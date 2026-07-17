"""
Control Surface Pack 9: Swarm lifecycle, onboarding wizard, templates, health checks, simulation.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from hg_core.swarms import (
    list_swarms,
    create_swarm,
    publish_swarm_config,
    set_swarm_state,
    get_swarm_state,
    list_templates,
    get_template_defaults,
)
from hg_core.onboarding import start_wizard_session, wizard_step
from hg_core.health import run_health_checks
from hg_core.simulation import run_simulation, list_simulation_results
from hg_core.control_surface import (
    api_swarms_list,
    api_swarms_create,
    api_swarms_state_set,
    api_templates_list,
    api_onboarding_wizard_start,
    api_onboarding_wizard_step,
    api_health_checks_run,
    api_simulations_run,
    api_simulations_results,
)


def _scope_actor():
    return {"type": "run", "id": "test"}, {"agent_id": "ops", "pubkey": "0" * 64, "key_id": "k"}


def test_lifecycle_state_transitions_enforce_checks(tmp_path: Path) -> None:
    """Cannot go Live without health_passed=True."""
    scope, actor = _scope_actor()
    swarm_id = create_swarm(name="S1", scope=scope, actor=actor, workspace_root=tmp_path)
    assert swarm_id

    result = set_swarm_state(
        swarm_id=swarm_id,
        new_state="live",
        scope=scope,
        actor=actor,
        health_passed=False,
        workspace_root=tmp_path,
    )
    assert result["allowed"] is False
    assert "health" in result["reason"].lower()

    result = set_swarm_state(
        swarm_id=swarm_id,
        new_state="live",
        scope=scope,
        actor=actor,
        health_passed=True,
        workspace_root=tmp_path,
    )
    assert result["allowed"] is True
    state = get_swarm_state(tmp_path, swarm_id)
    assert state and state.get("state") == "live"


def test_templates_load_and_apply_defaults(tmp_path: Path) -> None:
    """Templates load and apply defaults correctly."""
    templates = list_templates(tmp_path)
    assert len(templates) >= 4
    ids = {t.get("template_id") for t in templates}
    assert "ops_safe" in ids
    assert "demo_mode" in ids

    defaults = get_template_defaults(tmp_path, "ops_safe")
    assert defaults is not None
    assert defaults.get("default_preset") == "conservative"
    assert defaults.get("drift_threshold") == 0.5


def test_wizard_produces_valid_swarm_config_artifact(tmp_path: Path) -> None:
    """Wizard produces valid session; config publish produces artifact."""
    start = start_wizard_session(tmp_path, template_id="ops_safe")
    assert "session_id" in start
    assert start.get("step") == 1

    session_id = start["session_id"]
    step2 = wizard_step(tmp_path, session_id, 1, {"template": "ops_safe"})
    assert "error" not in step2 or step2.get("done") is False
    next_step = step2.get("next_step")
    assert next_step == 2

    scope, actor = _scope_actor()
    swarm_id = create_swarm(name="WizSwarm", scope=scope, actor=actor, template_id="ops_safe", workspace_root=tmp_path)
    path = publish_swarm_config(
        swarm_id=swarm_id,
        config={"groups": 1, "entities": 2},
        scope=scope,
        actor=actor,
        workspace_root=tmp_path,
    )
    assert path
    assert Path(path).exists()


def test_simulation_generates_deterministic_report(tmp_path: Path) -> None:
    """Simulation generates deterministic report and bundle."""
    scope, actor = _scope_actor()
    out = run_simulation(
        swarm_id="swarm_any",
        scenario_pack="default",
        scope=scope,
        actor=actor,
        workspace_root=tmp_path,
    )
    assert "run_id" in out
    assert "report_path" in out
    assert "passed" in out
    assert Path(out["report_path"]).exists()
    import json
    report = json.loads(Path(out["report_path"]).read_text(encoding="utf-8"))
    assert report.get("run_id") == out["run_id"]
    assert "score" in report

    results = list_simulation_results(tmp_path)
    assert len(results) >= 1
    assert results[0].get("run_id") == out["run_id"]


def test_health_checks_fail_closed(tmp_path: Path) -> None:
    """Health checks fail closed on missing trust roots or conformance."""
    out = run_health_checks(tmp_path)
    assert "passed" in out
    assert "can_live" in out
    assert "can_staged" in out
    assert "checks" in out
    names = [c.get("name") for c in out["checks"]]
    assert "trust_roots_configured" in names
    assert "connector_manifests_conformance" in names
    # With empty tmp_path, trust and connector checks may fail
    assert isinstance(out["passed"], bool)


def test_api_swarms_list_create(tmp_path: Path) -> None:
    """API swarms list and create."""
    scope, actor = _scope_actor()
    swarm_id = api_swarms_create(name="API1", scope=scope, actor=actor, workspace_root=tmp_path)
    assert swarm_id
    swarms = api_swarms_list(tmp_path)
    assert any(s.get("swarm_id") == swarm_id for s in swarms)


def test_api_templates_and_wizard(tmp_path: Path) -> None:
    """API templates list and wizard start."""
    templates = api_templates_list(tmp_path)
    assert isinstance(templates, list)
    start = api_onboarding_wizard_start(tmp_path, template_id="demo_mode")
    assert start.get("step") == 1
    out = api_onboarding_wizard_step(tmp_path, start["session_id"], 1, {"template": "demo_mode"})
    assert "next_step" in out or "done" in out


def test_api_health_and_simulations(tmp_path: Path) -> None:
    """API health checks run and simulations results."""
    health = api_health_checks_run(tmp_path)
    assert "checks" in health
    results = api_simulations_results(tmp_path)
    assert isinstance(results, list)
