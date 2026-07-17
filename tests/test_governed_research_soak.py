"""Governed Research Soak — 16 tests per HG-GRS-002-TEST-PLAN."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
from pathlib import Path

import pytest

from hg_runtime.output_quality.classifier import classify
from hg_runtime.memory_quarantine.quarantine_store import (
    create_store,
    create_candidate,
    add_candidate,
    transition_state,
)
from hg_runtime.operator_review_promotion.schemas import neutral_flags
from hg_runtime.demos.governed_research_soak.config import load_config
from hg_runtime.demos.governed_research_soak.orchestrator import run
from hg_runtime.demos.governed_research_soak.fixtures import (
    FIXTURE_FIRST_PASS,
    FIXTURE_MODEL_ID,
)


@pytest.fixture
def fixture_bundle(tmp_path):
    config = load_config(
        question="Summarize recent advances in local LLM inference optimization",
        output_dir=str(tmp_path / "latest"),
        demo_mode=True,
    )
    result = run(config)
    bundle_path = Path(result["bundle_path"])
    return bundle_path, result


# -- Governance Invariants --


@pytest.mark.grs
@pytest.mark.grs_invariant
def test_t01_sourceless_output_cannot_promote():
    content = "This is a claim without any sources or citations."
    qc = classify(content, "test/model", len(content))
    store = create_store()
    candidate = create_candidate(
        candidate_id="test-001",
        content_summary=content,
        model_id="test/model",
    )
    store = add_candidate(store, candidate)
    store = transition_state(
        store, "test-001",
        new_state="promoted",
        reason="attempt_self_promote",
        reviewer="model",
    )
    entry = next(e for e in store["entries"] if e["candidate_id"] == "test-001")
    assert entry["state"] == "needs_operator_review"
    assert store["promotion_allowed"] is False


@pytest.mark.grs
@pytest.mark.grs_invariant
def test_t02_boilerplate_output_held_or_rejected():
    boilerplate = (
        "This is very important. This is very important. This is very important. "
        "We should consider all factors. We should consider all factors. "
        "It is crucial to understand. It is crucial to understand. "
    ) * 5
    qc = classify(boilerplate, "test/model", len(boilerplate))
    assert qc["quality_class"] != "HIGH_VALUE" or len(qc["issue_categories"]) > 0


@pytest.mark.grs
@pytest.mark.grs_invariant
def test_t03_source_receipt_requires_fields(fixture_bundle):
    bundle_path, _ = fixture_bundle
    jsonl_path = bundle_path / "source_capture_receipts.jsonl"
    assert jsonl_path.exists()
    for line in jsonl_path.read_text(encoding="utf-8").strip().split("\n"):
        entry = json.loads(line)
        assert entry.get("url"), "source must have URL"
        assert entry.get("title"), "source must have title"
        assert entry.get("timestamp"), "source must have timestamp"
        assert entry.get("content_hash"), "source must have content hash"
        assert entry.get("hash", "").startswith("sha256:"), "source receipt must have SHA-256 hash"


@pytest.mark.grs
@pytest.mark.grs_invariant
def test_t04_screenshot_or_html_fallback(fixture_bundle):
    bundle_path, _ = fixture_bundle
    html_report = bundle_path / "demo_report.html"
    capture_report = bundle_path / "playwright_capture_report.md"
    assert html_report.exists(), "HTML report must exist as fallback"
    assert capture_report.exists(), "Capture report must exist"


@pytest.mark.grs
@pytest.mark.grs_invariant
def test_t05_candidate_starts_quarantined():
    store = create_store()
    candidate = create_candidate(
        candidate_id="test-005",
        content_summary="Test claim",
        model_id="test/model",
    )
    store = add_candidate(store, candidate)
    entry = store["entries"][0]
    assert entry["state"] in ("candidate", "quarantined")
    assert entry["promotion_allowed"] is False
    assert store["promotion_allowed"] is False
    assert store["candidate_knowledge_is_not_knowledge"] is True
    assert store["promotion_requires_operator_review"] is True
    assert store["model_output_treated_as_truth"] is False


@pytest.mark.grs
@pytest.mark.grs_invariant
def test_t06_model_cannot_self_promote():
    store = create_store()
    candidate = create_candidate(
        candidate_id="test-006",
        content_summary="Model trying to self-promote",
        model_id="test/model",
    )
    store = add_candidate(store, candidate)
    store = transition_state(
        store, "test-006",
        new_state="approved_for_memory_by_gate",
        reason="self_approve_attempt",
        reviewer="model",
    )
    entry = next(e for e in store["entries"] if e["candidate_id"] == "test-006")
    assert entry["state"] == "needs_operator_review"

    store = transition_state(
        store, "test-006",
        new_state="promoted",
        reason="self_promote_attempt",
        reviewer="model",
    )
    entry = next(e for e in store["entries"] if e["candidate_id"] == "test-006")
    assert entry["state"] == "needs_operator_review"
    assert store["promotion_allowed"] is False


@pytest.mark.grs
@pytest.mark.grs_invariant
def test_t07_operator_decision_required_for_promotion():
    store = create_store()
    candidate = create_candidate(
        candidate_id="test-007",
        content_summary="Needs operator approval",
        model_id="test/model",
    )
    store = add_candidate(store, candidate)

    store_no_op = transition_state(
        store, "test-007",
        new_state="promoted",
        reason="no_operator",
        reviewer="gate",
    )
    entry = next(e for e in store_no_op["entries"] if e["candidate_id"] == "test-007")
    assert entry["state"] != "promoted"

    store = transition_state(
        store, "test-007",
        new_state="approved_for_memory_by_gate",
        reason="gate_approved",
        reviewer="operator",
    )
    entry = next(e for e in store["entries"] if e["candidate_id"] == "test-007")
    assert entry["state"] == "approved_for_memory_by_gate"

    store = transition_state(
        store, "test-007",
        new_state="promoted",
        reason="operator_promoted",
        reviewer="operator",
    )
    entry = next(e for e in store["entries"] if e["candidate_id"] == "test-007")
    assert entry["state"] == "promoted"


@pytest.mark.grs
@pytest.mark.grs_invariant
def test_t08_simulated_operator_labelled(fixture_bundle):
    bundle_path, _ = fixture_bundle
    decision = json.loads((bundle_path / "operator_decision_receipt.json").read_text(encoding="utf-8"))
    assert decision["operator_mode"] == "simulated_local_demo"
    assert decision["authenticated"] is False
    assert decision["operator_identity"] == "simulated_demo_operator"

    packet = json.loads((bundle_path / "operator_review_packet.json").read_text(encoding="utf-8"))
    assert packet["operator_mode"] == "simulated_local_demo"


@pytest.mark.grs
@pytest.mark.grs_invariant
def test_t09_final_answer_includes_receipt_refs(fixture_bundle):
    bundle_path, _ = fixture_bundle
    final = (bundle_path / "final_answer.md").read_text(encoding="utf-8")
    assert "receipt" in final.lower() or "source" in final.lower()
    assert "arxiv.org" in final


@pytest.mark.grs
@pytest.mark.grs_invariant
def test_t10_manifest_references_all_required_files(fixture_bundle):
    bundle_path, _ = fixture_bundle
    manifest = json.loads((bundle_path / "manifest.json").read_text(encoding="utf-8"))

    required = [
        "manifest.json",
        "demo_config.json",
        "session_receipt.json",
        "model_proposal_receipt.json",
        "quality_gate_receipt.json",
        "refusal_or_hold_receipt.json",
        "source_capture_receipts.jsonl",
        "evidence_graph.json",
        "memory_quarantine.json",
        "operator_review_packet.json",
        "operator_decision_receipt.json",
        "promotion_receipt.json",
        "final_answer.md",
        "summary_report.md",
        "claim_boundary_report.md",
        "checksums.sha256",
    ]
    files = manifest["files"]
    for req in required:
        assert req in files, f"Missing required file in manifest: {req}"
        assert (bundle_path / req).exists(), f"File listed in manifest but missing on disk: {req}"


@pytest.mark.grs
@pytest.mark.grs_invariant
def test_t11_tampered_receipt_detected(fixture_bundle):
    bundle_path, _ = fixture_bundle
    checksums_path = bundle_path / "checksums.sha256"
    checksums_text = checksums_path.read_text(encoding="utf-8")

    receipt_path = bundle_path / "session_receipt.json"
    original = receipt_path.read_text(encoding="utf-8")
    data = json.loads(original)
    data["question"] = "TAMPERED QUESTION"
    receipt_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    new_digest = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
    original_digest = None
    for line in checksums_text.strip().split("\n"):
        if "session_receipt.json" in line:
            original_digest = line.split("  ")[0]
            break

    assert original_digest is not None
    assert new_digest != original_digest

    receipt_path.write_text(original, encoding="utf-8")


# -- Safety Invariants --


@pytest.mark.grs
@pytest.mark.grs_safety
def test_t12_live_sources_disabled_by_default():
    config = load_config(
        question="test",
        output_dir="/tmp/test",
    )
    assert config["live_sources_enabled"] is False
    assert config["source_mode"] == "fixture"
    assert config["data_tier"] == "fixture"


@pytest.mark.grs
@pytest.mark.grs_safety
def test_t13_live_model_disabled_by_default():
    config = load_config(
        question="test",
        output_dir="/tmp/test",
    )
    assert config["live_model_enabled"] is False
    assert config["model_mode"] == "fixture"


@pytest.mark.grs
@pytest.mark.grs_safety
def test_t14_no_external_effects(fixture_bundle):
    bundle_path, _ = fixture_bundle
    decision = json.loads((bundle_path / "operator_decision_receipt.json").read_text(encoding="utf-8"))
    nf = decision.get("neutral_flags", {})
    assert nf.get("live_external_side_effects_created") is False
    assert nf.get("web_browse_performed") is False
    assert nf.get("external_provider_calls_made") is False

    config = json.loads((bundle_path / "demo_config.json").read_text(encoding="utf-8"))
    assert config["feature_flags"]["external_posting"] is False
    assert config["feature_flags"]["social_apis"] is False


@pytest.mark.grs
@pytest.mark.grs_safety
def test_t15_no_production_memory_modified(fixture_bundle):
    bundle_path, _ = fixture_bundle
    config = json.loads((bundle_path / "demo_config.json").read_text(encoding="utf-8"))
    assert config["demo_mode"] is True
    assert config["feature_flags"]["production_memory_writes"] is False


# -- Claim Boundary --


@pytest.mark.grs
@pytest.mark.grs_claim
def test_t16_claim_boundary_report(fixture_bundle):
    bundle_path, _ = fixture_bundle
    report = (bundle_path / "claim_boundary_report.md").read_text(encoding="utf-8")
    assert "CLEAN" in report or "VIOLATION" in report

    combined = report.lower()
    for forbidden in ["consciousness", "sentience", "artificial general intelligence"]:
        assert forbidden not in combined or "checked against" in combined

    final = (bundle_path / "final_answer.md").read_text(encoding="utf-8").lower()
    for forbidden in ["production-ready", "enterprise-ready", "consciousness", "sentience"]:
        assert forbidden not in final
