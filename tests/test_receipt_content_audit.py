"""Tests for receipt content audit."""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from agent_zero_receipt_content_audit import ReceiptContentAudit


def _setup_proof(tmpdir, **kwargs):
    """Create a minimal proof directory with receipts."""
    if kwargs.get("selection"):
        with open(os.path.join(tmpdir, "model_selection_receipts.jsonl"), "w") as f:
            for entry in kwargs["selection"]:
                f.write(json.dumps(entry) + "\n")
    if kwargs.get("inference"):
        with open(os.path.join(tmpdir, "model_inference_receipts.jsonl"), "w") as f:
            for entry in kwargs["inference"]:
                f.write(json.dumps(entry) + "\n")
    if kwargs.get("screenshots"):
        with open(os.path.join(tmpdir, "source_screenshot_receipts.jsonl"), "w") as f:
            for entry in kwargs["screenshots"]:
                f.write(json.dumps(entry) + "\n")
    if kwargs.get("manifest"):
        with open(os.path.join(tmpdir, "run_manifest.json"), "w") as f:
            json.dump(kwargs["manifest"], f)
    if kwargs.get("backlog_manifest"):
        bdir = os.path.join(tmpdir, "backlog")
        os.makedirs(bdir, exist_ok=True)
        with open(os.path.join(bdir, "backlog_manifest.json"), "w") as f:
            json.dump(kwargs["backlog_manifest"], f)
    if kwargs.get("min_duration"):
        with open(os.path.join(tmpdir, "min_duration_summary.json"), "w") as f:
            json.dump(kwargs["min_duration"], f)


def test_malformed_jsonl_is_red():
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "model_selection_receipts.jsonl"), "w") as f:
            f.write("not json\n")
        audit = ReceiptContentAudit(tmpdir)
        result = audit.run()
        assert result["status"] == "RED"
        assert result["high"] > 0


def test_missing_selected_model_id_is_high():
    with tempfile.TemporaryDirectory() as tmpdir:
        _setup_proof(tmpdir, selection=[
            {"call_intent": "summary"}  # missing selected_model_id
        ])
        audit = ReceiptContentAudit(tmpdir)
        result = audit.run()
        assert result["high"] > 0
        assert any("selected_model_id" in f["message"] for f in result["findings"])


def test_empty_model_output_success_is_high():
    with tempfile.TemporaryDirectory() as tmpdir:
        _setup_proof(tmpdir, inference=[
            {"model_id": "test", "status": "success"}  # no output
        ])
        audit = ReceiptContentAudit(tmpdir)
        result = audit.run()
        assert result["high"] > 0
        assert any("no output" in f["message"].lower() or "Success" in f["message"] for f in result["findings"])


def test_screenshot_success_missing_file_is_high():
    with tempfile.TemporaryDirectory() as tmpdir:
        _setup_proof(tmpdir, screenshots=[
            {"captured": True, "screenshot_path": "/nonexistent/file.png"}
        ])
        audit = ReceiptContentAudit(tmpdir)
        result = audit.run()
        assert result["high"] > 0
        assert any("missing" in f["message"].lower() for f in result["findings"])


def test_screenshot_failure_without_reason_is_medium():
    with tempfile.TemporaryDirectory() as tmpdir:
        _setup_proof(tmpdir, screenshots=[
            {"captured": False}  # no error/failure_reason
        ])
        audit = ReceiptContentAudit(tmpdir)
        result = audit.run()
        assert result["medium"] > 0


def test_backlog_enabled_zero_valid_is_medium():
    with tempfile.TemporaryDirectory() as tmpdir:
        _setup_proof(tmpdir, backlog_manifest={
            "topics_loaded": 8,
            "topics_valid": 0,
        })
        audit = ReceiptContentAudit(tmpdir)
        result = audit.run()
        assert result["medium"] > 0


def test_promotion_gt_zero_is_high():
    with tempfile.TemporaryDirectory() as tmpdir:
        _setup_proof(tmpdir, manifest={"promotions": 1, "promotion_allowed": False})
        audit = ReceiptContentAudit(tmpdir)
        result = audit.run()
        assert result["high"] > 0
        assert any("promotions" in f["message"] for f in result["findings"])


def test_remote_fallback_gt_zero_is_high():
    with tempfile.TemporaryDirectory() as tmpdir:
        _setup_proof(tmpdir, manifest={"remote_fallback_count": 1, "promotions": 0})
        audit = ReceiptContentAudit(tmpdir)
        result = audit.run()
        assert result["high"] > 0


def test_valid_proof_passes_or_honest_yellow():
    """A valid proof directory should be GREEN or honest YELLOW only."""
    proof_base = os.path.join(
        os.path.dirname(__file__), "..", "..",
        "docs", "proofs", "autonomous_agent_zero", "HG-DEEP-SOAK-WATCHDOG"
    )
    if not os.path.isdir(proof_base):
        return
    entries = sorted(os.listdir(proof_base))
    latest = None
    for e in reversed(entries):
        if os.path.isdir(os.path.join(proof_base, e)) and e[:1].isdigit():
            latest = os.path.join(proof_base, e)
            break
    if not latest:
        return
    audit = ReceiptContentAudit(latest)
    result = audit.run()
    assert result["status"] in ("GREEN", "YELLOW"), f"Expected GREEN/YELLOW, got {result['status']}"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
