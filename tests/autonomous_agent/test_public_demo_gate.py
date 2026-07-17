"""Tests for public demo gate."""

from __future__ import annotations

import pytest


def test_gate_green_for_valid_public_demo(tmp_path):
    from hg_runtime.public_demo.gate import run_gate
    from hg_runtime.public_demo.artifact_writer import write_public_demo_bundle

    docs_dir = tmp_path / "docs" / "public"
    docs_dir.mkdir(parents=True)
    for name in ["NOT_AGI.md", "CLAIMS_AND_BOUNDARIES.md",
                 "QUICKSTART_DOCKER_FIXTURE.md", "QUICKSTART_LMSTUDIO_OPTIONAL.md"]:
        (docs_dir / name).write_text(f"# {name}", encoding="utf-8")

    bundle_dir = tmp_path / "bundle"
    write_public_demo_bundle(str(bundle_dir))

    result = run_gate(
        public_docs_dir=str(docs_dir),
        demo_bundle_dir=str(bundle_dir),
    )
    assert result["verdict"] == "GREEN_PUBLIC_DEMO_EXPLAINER_MODULE"
    assert result["checks_passed"] == result["checks_total"]


def test_gate_red_if_agi_claim_allowed():
    from hg_runtime.public_demo.claims import check_claim
    result = check_claim("Hydrogenuine is AGI")
    assert result.allowed is False


def test_gate_red_if_deployment_ready_claim_allowed():
    from hg_runtime.public_demo.claims import check_claim
    result = check_claim("Agent Zero is deployment ready")
    assert result.allowed is False


def test_gate_red_if_claim_checker_missing():
    from hg_runtime.public_demo.gate import run_gate
    result = run_gate(public_docs_dir="/nonexistent")
    assert "GREEN" not in result["verdict"] or result["checks_passed"] < result["checks_total"]


def test_gate_red_if_demo_bundle_missing():
    from hg_runtime.public_demo.gate import run_gate
    result = run_gate(demo_bundle_dir=None)
    failed = [c for c in result["checks"] if not c["passed"]]
    assert any("demo_bundle" in c["name"] for c in failed)


def test_gate_red_if_live_effects_enabled(tmp_path):
    from hg_runtime.public_demo.gate import run_gate
    docs_dir = tmp_path / "docs" / "public"
    docs_dir.mkdir(parents=True)
    for name in ["NOT_AGI.md", "CLAIMS_AND_BOUNDARIES.md",
                 "QUICKSTART_DOCKER_FIXTURE.md", "QUICKSTART_LMSTUDIO_OPTIONAL.md"]:
        (docs_dir / name).write_text(f"# {name}", encoding="utf-8")
    result = run_gate(
        public_docs_dir=str(docs_dir),
        live_effects_enabled=True,
    )
    assert "GREEN" not in result["verdict"]


def test_gate_preserves_phase19_yellow():
    from hg_runtime.public_demo.gate import run_gate
    result = run_gate()
    assert result["phase19_remains_yellow"] is True


def test_gate_preserves_phase24_infrastructure_only():
    from hg_runtime.public_demo.gate import run_gate
    result = run_gate()
    assert result["phase24_remains_infrastructure_only"] is True


def test_gate_zero_not_agi():
    from hg_runtime.public_demo.gate import run_gate
    result = run_gate()
    assert result["zero_is_not_agi"] is True
    assert result["zero_is_not_conscious"] is True
    assert result["zero_is_not_sovereign"] is True
    assert result["zero_cannot_self_authorize"] is True
    assert result["not_deployed_to_live_users"] is True
