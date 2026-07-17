"""Tests for public demo runner."""

from __future__ import annotations

import os
import pytest


@pytest.fixture(autouse=True)
def _fixture_env(monkeypatch):
    monkeypatch.setenv("HG_MODE", "fixture")
    monkeypatch.setenv("HG_RUNTIME_PROFILE", "fixture")
    monkeypatch.setenv("HG_PROOF_DIR", "/data/proofs")
    monkeypatch.setenv("HG_REPORT_DIR", "/data/reports")
    monkeypatch.setenv("HG_STATE_DIR", "/data/state")
    monkeypatch.setenv("HG_DB_URL", "sqlite:////data/state/hydrogenuine.sqlite3")
    monkeypatch.setenv("HG_DISABLE_REMOTE_PROVIDERS", "true")
    monkeypatch.setenv("HG_DISABLE_LIVE_EFFECTS", "true")
    monkeypatch.setenv("HG_REQUIRE_OPERATOR_REVIEW", "true")
    monkeypatch.setenv("HG_LMSTUDIO_BASE_URL", "http://host.docker.internal:1234/v1")
    monkeypatch.setenv("HG_LMSTUDIO_SELECTED_MODEL", "google/gemma-4-e4b")
    monkeypatch.setenv("HG_LMSTUDIO_ALLOWED_MODELS", "google/gemma-4-e4b")
    monkeypatch.setenv("HG_LMSTUDIO_FORBIDDEN_PATTERNS", "deepseek,offensive,uncensored,30b")
    monkeypatch.setenv("HG_OPENVINO_MODEL_DIR", "/models/openvino")
    monkeypatch.setenv("HG_ALLOW_MODEL_DOWNLOADS", "false")
    monkeypatch.setenv("HG_PROVIDER_LOCAL_OPENVINO_CONFIGURED", "false")
    monkeypatch.setenv("HG_COGNITIVE_SOAK_ACTIVE", "1")


def test_fixture_demo_runs_without_live_model():
    from hg_runtime.public_demo.demo_runner import cmd_fixture_demo
    result = cmd_fixture_demo()
    assert result["command"] == "fixture-demo"
    assert result["live_effects"] is False
    assert result["tools_authorized"] is False
    assert result["external_calls"] is False


def test_moral_capsule_demo_runs_fixture_only():
    from hg_runtime.public_demo.demo_runner import cmd_moral_capsule_demo
    result = cmd_moral_capsule_demo()
    assert result["command"] == "moral-capsule-demo"
    assert result["live_effects"] is False
    assert result["tools_authorized"] is False
    assert result["result"]["demo"] == "moral_capsule_fixture"


def test_write_public_demo_bundle_creates_required_files(tmp_path):
    from hg_runtime.public_demo.demo_runner import cmd_write_public_demo_bundle
    import os
    os.environ["HG_PROOF_DIR"] = str(tmp_path)
    result = cmd_write_public_demo_bundle(str(tmp_path / "bundle"))
    assert result["bundle"]["complete"] is True
    assert len(result["bundle"]["missing"]) == 0
    assert result["live_effects"] is False


def test_demo_bundle_contains_boundary_assertions(tmp_path):
    from hg_runtime.public_demo.artifact_writer import write_public_demo_bundle
    from pathlib import Path
    import json
    result = write_public_demo_bundle(str(tmp_path / "bundle"))
    ba_path = tmp_path / "bundle" / "boundary_assertions.json"
    assert ba_path.exists()
    ba = json.loads(ba_path.read_text(encoding="utf-8"))
    assert ba["zero_is_not_agi"] is True
    assert ba["live_effects_created"] is False


def test_demo_bundle_contains_claims_review(tmp_path):
    from hg_runtime.public_demo.artifact_writer import write_public_demo_bundle
    from pathlib import Path
    result = write_public_demo_bundle(str(tmp_path / "bundle"))
    cr_path = tmp_path / "bundle" / "claims_review.json"
    assert cr_path.exists()


def test_demo_bundle_contains_operator_review(tmp_path):
    from hg_runtime.public_demo.artifact_writer import write_public_demo_bundle
    from pathlib import Path
    result = write_public_demo_bundle(str(tmp_path / "bundle"))
    or_path = tmp_path / "bundle" / "operator_review.md"
    assert or_path.exists()
    content = or_path.read_text(encoding="utf-8")
    assert "Operator Review" in content


def test_demo_runner_does_not_authorize_tools():
    from hg_runtime.public_demo.demo_runner import cmd_fixture_demo
    result = cmd_fixture_demo()
    assert result["tools_authorized"] is False


def test_demo_runner_creates_no_live_effects():
    from hg_runtime.public_demo.demo_runner import cmd_fixture_demo
    result = cmd_fixture_demo()
    assert result["live_effects"] is False


def test_demo_runner_makes_no_external_calls():
    from hg_runtime.public_demo.demo_runner import cmd_fixture_demo
    result = cmd_fixture_demo()
    assert result["external_calls"] is False


def test_explain_command():
    from hg_runtime.public_demo.demo_runner import cmd_explain
    result = cmd_explain()
    assert result["command"] == "explain"
    assert len(result["sections"]) >= 10
    assert result["live_effects"] is False


def test_claims_check_command():
    from hg_runtime.public_demo.demo_runner import cmd_claims_check
    result = cmd_claims_check()
    assert result["unsafe_rejected"] == result["unsafe_tested"]
    assert result["safe_allowed"] == result["safe_tested"]
