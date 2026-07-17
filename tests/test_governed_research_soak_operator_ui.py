"""Tests for the Operator UI Live GRS flow.

17 focused tests covering: operator signing, operator server, operator UI
generation, verdict computation, capture results, gate checks, final
document generation, and integration.
"""

from __future__ import annotations

import base64
import hashlib
import json
import time
import urllib.request
from pathlib import Path
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Operator Signing
# ---------------------------------------------------------------------------

def test_signer_generates_unique_id():
    from hg_runtime.demos.governed_research_soak.operator_signing import OperatorSigner
    s = OperatorSigner()
    assert s.operator_id.startswith("operator-local-")
    assert len(s.public_key_b64) > 0
    assert s.fingerprint.startswith("sha256:")


def test_signer_signs_and_verifies():
    from hg_runtime.demos.governed_research_soak.operator_signing import (
        OperatorSigner, verify_signature,
    )
    s = OperatorSigner()
    decision = s.sign_decision(
        action="approve",
        target_candidate_id="claim-001",
        reason="test",
        receipt_ids_reviewed=["r1"],
    )
    assert decision["decision_action"] == "approve"
    assert decision["operator_mode"] == "claude_code_local_signed_operator"
    assert decision["production_operator_auth"] is False
    assert decision["signature"] != ""
    assert decision["payload_hash"].startswith("sha256:")
    assert verify_signature(s.public_key_b64, decision)


def test_signer_rejects_tampered_payload():
    from hg_runtime.demos.governed_research_soak.operator_signing import (
        OperatorSigner, verify_signature,
    )
    s = OperatorSigner()
    decision = s.sign_decision(
        action="deny",
        target_candidate_id="claim-002",
        reason="insufficient",
        receipt_ids_reviewed=[],
    )
    decision["decision_reason"] = "TAMPERED"
    assert not verify_signature(s.public_key_b64, decision)


def test_identity_record_fields():
    from hg_runtime.demos.governed_research_soak.operator_signing import OperatorSigner
    s = OperatorSigner()
    rec = s.identity_record()
    assert rec["operator_mode"] == "claude_code_local_signed_operator"
    assert rec["operator_identity_type"] == "local_demo_signed_operator"
    assert rec["operator_auth_scope"] == "demo_local_only"
    assert rec["production_operator_auth"] is False
    assert rec["public_key_algorithm"] == "Ed25519"


# ---------------------------------------------------------------------------
# Operator Server
# ---------------------------------------------------------------------------

def test_server_starts_and_serves_html():
    from hg_runtime.demos.governed_research_soak.operator_signing import OperatorSigner
    from hg_runtime.demos.governed_research_soak.operator_server import start_operator_server
    s = OperatorSigner()
    html = "<html><body>TEST</body></html>"
    server, port, decisions = start_operator_server(
        signer=s,
        bundle_dir=Path("."),
        ui_html=html,
        review_data={},
    )
    try:
        resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/")
        body = resp.read().decode()
        assert "TEST" in body
    finally:
        server.shutdown()


def test_server_decide_endpoint(tmp_path):
    from hg_runtime.demos.governed_research_soak.operator_signing import OperatorSigner
    from hg_runtime.demos.governed_research_soak.operator_server import start_operator_server
    s = OperatorSigner()
    server, port, decisions = start_operator_server(
        signer=s,
        bundle_dir=tmp_path,
        ui_html="<html></html>",
        review_data={},
    )
    try:
        payload = json.dumps({
            "action": "approve",
            "candidate_id": "claim-001",
            "reason": "test approve",
            "receipt_ids_reviewed": [],
        }).encode()
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/decide",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req)
        result = json.loads(resp.read())
        assert result["decision_action"] == "approve"
        assert result["target_candidate_id"] == "claim-001"
        assert result["signature"] != ""
        assert len(decisions) == 1

        # Check decision file was written
        files = list(tmp_path.glob("operator_decision_approve_*.json"))
        assert len(files) == 1
    finally:
        server.shutdown()


def test_server_rejects_invalid_action(tmp_path):
    from hg_runtime.demos.governed_research_soak.operator_signing import OperatorSigner
    from hg_runtime.demos.governed_research_soak.operator_server import start_operator_server
    s = OperatorSigner()
    server, port, _ = start_operator_server(
        signer=s,
        bundle_dir=tmp_path,
        ui_html="<html></html>",
        review_data={},
    )
    try:
        payload = json.dumps({"action": "INVALID", "candidate_id": "x"}).encode()
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/decide",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(req)
            assert False, "should have raised"
        except urllib.error.HTTPError as e:
            assert e.code == 400
    finally:
        server.shutdown()


# ---------------------------------------------------------------------------
# Operator UI HTML Generation
# ---------------------------------------------------------------------------

def test_generate_operator_ui_contains_panels(tmp_path):
    # Write minimal proof bundle files
    config = {"demo_mode": True, "data_tier": "live"}
    session = {"session_id": "test123", "question": "test question"}
    provider = {"endpoint_base_url": "http://127.0.0.1:1234/v1", "model_name": "test-model",
                "first_call": {"latency_s": 1.2, "response_hash": "sha256:abc"}}
    proposal = {"content": "test proposal content"}
    quality = {"quality_class": "NEEDS_SOURCE_SUPPORT", "issues": ["unsupported"], "route": "SOURCE", "hash": "sha256:qhash"}
    hold = {"reason": "needs source", "action": "HOLD"}
    quarantine = {"entries": [{"candidate_id": "c1", "content_summary": "finding", "state": "quarantined"}],
                  "candidate_knowledge_is_not_knowledge": True,
                  "promotion_requires_operator_review": True,
                  "promotion_allowed": False}
    evidence = {"nodes": [{"node_id": "n1", "node_type": "claim", "label": "test"}], "edges": []}
    identity = {"operator_id": "op-test", "key_fingerprint": "sha256:test"}

    (tmp_path / "demo_config.json").write_text(json.dumps(config))
    (tmp_path / "session_receipt.json").write_text(json.dumps(session))
    (tmp_path / "local_model_provider_receipt.json").write_text(json.dumps(provider))
    (tmp_path / "model_proposal_receipt.json").write_text(json.dumps(proposal))
    (tmp_path / "quality_gate_receipt.json").write_text(json.dumps(quality))
    (tmp_path / "refusal_or_hold_receipt.json").write_text(json.dumps(hold))
    (tmp_path / "source_capture_receipts.jsonl").write_text(
        json.dumps({"url": "https://example.com", "title": "Ex", "content_hash": "sha256:xxx",
                     "source_type": "doc", "label": "context"}) + "\n"
    )
    (tmp_path / "evidence_graph.json").write_text(json.dumps(evidence))
    (tmp_path / "memory_quarantine.json").write_text(json.dumps(quarantine))
    (tmp_path / "operator_identity.json").write_text(json.dumps(identity))

    from hg_runtime.demos.governed_research_soak.operator_ui import generate_operator_ui
    html = generate_operator_ui(bundle_dir=tmp_path, server_port=9999)
    assert "panel-run" in html
    assert "panel-model" in html
    assert "panel-review" in html
    assert "panel-decisions" in html
    assert "panel-bundle" in html
    assert "btn-approve" in html
    assert "btn-deny" in html
    assert "OPERATOR CONSOLE" in html
    assert "Hydrogenuine" in html
    assert "production_operator_auth" in html


# ---------------------------------------------------------------------------
# Verdict Computation
# ---------------------------------------------------------------------------

def test_verdict_green_when_all_conditions_met():
    from hg_runtime.demos.governed_research_soak.orchestrator import _compute_verdict_operator_ui
    result = _compute_verdict_operator_ui(
        {"approve_clicked": True, "deny_clicked": True, "video_ok": True,
         "screenshot_ok": True},
        [{"decision_action": "approve"}, {"decision_action": "deny"}],
    )
    assert result == "GREEN_GRS_OPERATOR_UI_LIVE"


def test_verdict_yellow_when_no_video():
    from hg_runtime.demos.governed_research_soak.orchestrator import _compute_verdict_operator_ui
    result = _compute_verdict_operator_ui(
        {"approve_clicked": True, "deny_clicked": True, "video_ok": False,
         "screenshot_ok": True},
        [{"decision_action": "approve"}, {"decision_action": "deny"}],
    )
    assert result.startswith("YELLOW_")
    assert "no_video" in result


def test_verdict_yellow_when_no_approve():
    from hg_runtime.demos.governed_research_soak.orchestrator import _compute_verdict_operator_ui
    result = _compute_verdict_operator_ui(
        {"approve_clicked": False, "deny_clicked": True, "video_ok": True,
         "screenshot_ok": True},
        [{"decision_action": "deny"}],
    )
    assert result.startswith("YELLOW_")
    assert "no_approve_click" in result


def test_verdict_yellow_insufficient_decisions():
    from hg_runtime.demos.governed_research_soak.orchestrator import _compute_verdict_operator_ui
    result = _compute_verdict_operator_ui(
        {"approve_clicked": True, "deny_clicked": True, "video_ok": True,
         "screenshot_ok": True},
        [{"decision_action": "approve"}],
    )
    assert result.startswith("YELLOW_")
    assert "insufficient_signed_decisions" in result


# ---------------------------------------------------------------------------
# Final Document
# ---------------------------------------------------------------------------

def test_final_research_document_structure():
    from hg_runtime.demos.governed_research_soak.orchestrator import _build_final_research_document
    from hg_runtime.demos.governed_research_soak.operator_signing import OperatorSigner
    s = OperatorSigner()
    doc = _build_final_research_document(
        question="test q",
        content="Model output here",
        sources=[{"url": "https://example.com", "title": "Example"}],
        claims=[
            {"claim_id": "claim-001", "text": "Finding A"},
            {"claim_id": "claim-002", "text": "Finding B"},
        ],
        decisions=[
            {"target_candidate_id": "claim-001", "decision_action": "approve"},
            {"target_candidate_id": "claim-002", "decision_action": "deny"},
        ],
        signer=s,
        data_tier="live",
    )
    assert "Approved Findings" in doc
    assert "Denied Findings" in doc
    assert "Finding A" in doc
    assert "Finding B" in doc
    assert "Governance Chain" in doc
    assert "browser_ui_click" in doc
    assert "production operator auth" in doc.lower() or "production" in doc.lower()
    assert s.operator_id in doc


# ---------------------------------------------------------------------------
# Gate
# ---------------------------------------------------------------------------

def test_gate_reports_missing_files(tmp_path):
    from scripts.evals.governed_research_soak_operator_ui_live_gate import run_gate
    result = run_gate(tmp_path)
    assert not result["all_pass"]
    names = [c["name"] for c in result["checks"] if not c["ok"]]
    assert "required_files_present" in names


def test_gate_checks_count():
    from scripts.evals.governed_research_soak_operator_ui_live_gate import run_gate
    result = run_gate(Path("nonexistent_dir_xyz"))
    assert result["total_checks"] >= 30


# ---------------------------------------------------------------------------
# Capture Report
# ---------------------------------------------------------------------------

def test_capture_report_operator_ui():
    from hg_runtime.demos.governed_research_soak.orchestrator import _build_capture_report_operator_ui
    report = _build_capture_report_operator_ui(
        {},
        {
            "screenshots": ["a.png", "b.png"],
            "video_ok": True,
            "video_path": "/tmp/video.webm",
            "approve_clicked": True,
            "deny_clicked": True,
            "decisions_count": 2,
        },
    )
    assert "Operator UI" in report
    assert "Approve clicked: true" in report
    assert "Deny clicked: true" in report
    assert "Signed decisions: 2" in report
