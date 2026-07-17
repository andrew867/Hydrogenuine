from __future__ import annotations

import json
from pathlib import Path

from hg_embodied.isaac_bridge.behavioral_tests import load_scenarios, run_scenario_suite


def test_run_scenario_suite_from_eval_fixture(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    fixture = Path(__file__).resolve().parents[2] / "evals" / "embodied" / "behavioral_scenarios.json"
    scenarios = load_scenarios(fixture)
    results = run_scenario_suite(
        robot_config={"robot_id": "robot-1"},
        environment_config={"scene_id": "table_block"},
        entity_id="ent-1",
        scenarios=scenarios,
    )
    assert len(results) == 2
    assert all(r.passed for r in results)
