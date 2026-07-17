"""CT-14 GLD golden end-to-end scenario tests."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from hg_core.golden_scenarios import (
    load_manifest,
    run_all_scenarios,
    run_scenario,
)
from hg_core.golden_scenarios.harness import narrative_trace
from hg_core.golden_scenarios.manifest import REQUIRED_SCENARIOS, manifest_hash
from hg_core.schema_compat.proof_bundle import validate_ct_proof_bundle_dir

WORKSPACE = Path(__file__).resolve().parents[2]


def test_golden_manifest_validates() -> None:
    manifest = load_manifest(workspace=WORKSPACE)
    assert manifest.manifest_hash.startswith("sha256:")
    assert set(REQUIRED_SCENARIOS).issubset({s.scenario_id for s in manifest.scenarios})
    assert manifest.path_id == "phase1_integrated"


def test_manifest_hash_anchored() -> None:
    path = WORKSPACE / "config" / "golden_scenarios_manifest_v1.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert payload["manifest_hash"] == manifest_hash(payload)


@pytest.mark.parametrize("scenario_id", REQUIRED_SCENARIOS)
def test_each_scenario_runs_or_skips_with_reason(scenario_id: str) -> None:
    manifest = load_manifest(workspace=WORKSPACE)
    spec = manifest.by_id(scenario_id)
    assert spec is not None
    result = run_scenario(spec, workspace=WORKSPACE)
    assert result.status in {"passed", "failed", "skipped"}
    if result.skipped:
        assert result.skip_reason


def test_expected_terminal_states_match() -> None:
    results = run_all_scenarios(workspace=WORKSPACE)
    failures = [r for r in results if not r.passed and not r.skipped]
    assert not failures, [r.to_payload() for r in failures]


def test_replay_matches() -> None:
    manifest = load_manifest(workspace=WORKSPACE)
    spec = manifest.by_id("replay_path")
    assert spec is not None
    result = run_scenario(spec, workspace=WORKSPACE)
    assert result.passed
    assert result.replay_hash is not None
    assert result.replay_hash.startswith("sha256:")


def test_no_fake_green_if_artifact_missing(tmp_path: Path) -> None:
    missing = tmp_path / "nonexistent" / "bundle"
    result = validate_ct_proof_bundle_dir(missing)
    assert not result.ok
    assert "missing manifest" in result.detail


def test_deterministic_narrative_trace() -> None:
    first = narrative_trace(run_all_scenarios(workspace=WORKSPACE))
    second = narrative_trace(run_all_scenarios(workspace=WORKSPACE))
    assert first == second


def test_proof_gate_path_references_bundle() -> None:
    manifest = load_manifest(workspace=WORKSPACE)
    spec = manifest.by_id("proof_gate_path")
    assert spec is not None
    result = run_scenario(spec, workspace=WORKSPACE)
    assert result.passed
    assert result.proof_bundle_ref
    assert "pack12" in result.proof_bundle_ref
