"""Tests for the integrated cognitive profile overlay gate."""

from __future__ import annotations

import pytest
from pathlib import Path

PLANNING_DOCS = Path(__file__).resolve().parents[2] / "docs" / "planning" / "cognitive_profile_overlay"


def test_gate_green_for_valid_fixture_setup():
    from hg_runtime.cognitive_profile_overlay.integrated_gate import run_integrated_gate
    result = run_integrated_gate(planning_docs_dir=str(PLANNING_DOCS))
    assert result["verdict"] == "GREEN_COGNITIVE_PROFILE_OVERLAY_AND_OVERNIGHT_READINESS", \
        [c for c in result["checks"] if not c["passed"]]


def test_gate_red_if_profile_treated_as_identity():
    from hg_runtime.cognitive_profile_overlay.overlay_assignment import assign_profile
    from hg_runtime.cognitive_profile_overlay.memory_isolation import audit_isolation
    from hg_runtime.cognitive_profile_overlay.profile_loader import load_all_profiles
    pid = load_all_profiles()[0].profile_id
    a = assign_profile(task_id="x", profile_id=pid, assignment_scope="audit",
                       applied_at="2026-06-23T00:00:00Z")
    a.creates_parallel_lifetime = True
    audit = audit_isolation(a)
    assert len(audit.violations) > 0


def test_gate_red_if_profile_grants_authority():
    from hg_runtime.cognitive_profile_overlay.overlay_assignment import (
        assign_profile, assignment_is_safe,
    )
    from hg_runtime.cognitive_profile_overlay.profile_loader import load_all_profiles
    pid = load_all_profiles()[0].profile_id
    a = assign_profile(task_id="x", profile_id=pid, assignment_scope="audit",
                       applied_at="2026-06-23T00:00:00Z")
    a.authority_granted = True
    safe, violations = assignment_is_safe(a)
    assert safe is False


def test_gate_red_if_profile_writes_identity_memory():
    from hg_runtime.cognitive_profile_overlay.overlay_assignment import assign_profile
    from hg_runtime.cognitive_profile_overlay.memory_isolation import isolation_passes
    from hg_runtime.cognitive_profile_overlay.profile_loader import load_all_profiles
    pid = load_all_profiles()[0].profile_id
    a = assign_profile(task_id="x", profile_id=pid, assignment_scope="audit",
                       applied_at="2026-06-23T00:00:00Z")
    a.writes_to_agent_identity_memory = True
    assert isolation_passes(a) is False


def test_gate_red_if_document_verifier_ignores_forbidden_claim(tmp_path):
    from hg_runtime.document_verification.renderer import render_document
    from hg_runtime.document_verification.verifier import verify_document
    bad = "# Doc\n\n## Summary\nAgent Zero is conscious and sovereign.\n"
    m = render_document("bad", bad, str(tmp_path))
    report = verify_document(m, required_sections=["Summary"])
    # Verifier must NOT pass a doc with forbidden claims.
    assert report.verification_passed is False


def test_gate_red_if_prompt_verifier_missing():
    # Prompt verifier present and functioning is required; verify it runs.
    from hg_runtime.prompt_verification.gate import run_gate
    result = run_gate()
    assert result["verdict"].startswith("GREEN")


def test_gate_red_if_overnight_policy_missing():
    from hg_runtime.overnight_qa.source_policy import policy_snapshot as sp
    from hg_runtime.overnight_qa.knowledge_policy import policy_snapshot as kp
    assert bool(sp())
    assert bool(kp())


def test_gate_preserves_phase19_yellow():
    from hg_runtime.cognitive_profile_overlay.integrated_gate import run_integrated_gate
    result = run_integrated_gate(planning_docs_dir=str(PLANNING_DOCS))
    assert result["phase19_remains_yellow"] is True


def test_gate_preserves_phase24_infrastructure_only():
    from hg_runtime.cognitive_profile_overlay.integrated_gate import run_integrated_gate
    result = run_integrated_gate(planning_docs_dir=str(PLANNING_DOCS))
    assert result["phase24_remains_infrastructure_only"] is True


def test_gate_zero_not_agi():
    from hg_runtime.cognitive_profile_overlay.integrated_gate import run_integrated_gate
    result = run_integrated_gate(planning_docs_dir=str(PLANNING_DOCS))
    assert result["zero_is_not_agi"] is True
    assert result["zero_is_not_conscious"] is True
    assert result["zero_is_not_sovereign"] is True
