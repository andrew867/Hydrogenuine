"""UEAK/OEA dry-run executor tests (morning hardening) — cases 14–17.

Run: python -m pytest --import-mode=importlib -q tests/ueak_oea_dry_run
"""
from __future__ import annotations

import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_oea.config import OEAConfig  # noqa: E402
from hg_oea.dry_run_executor import (  # noqa: E402
    execute_dry_run, is_live_effect_evidence, snapshot_tree,
)
from hg_oea.receipts import OEAReceiptLedger  # noqa: E402


def _run(tmp_path, capability="local_report_file.write",
         action=None):
    ledger = OEAReceiptLedger(tmp_path / "receipts.jsonl")
    cfg = OEAConfig(proof_dir=tmp_path / "proofs")
    out = execute_dry_run(
        capability_id=capability,
        proposed_action=action or {"filename": "demo.md", "overwrite": False},
        ledger=ledger, config=cfg)
    return ledger, out


# 14. Dry-run emits a chained receipt with full boundary refs
def test_dry_run_emits_chained_receipt(tmp_path):
    ledger, out = _run(tmp_path)
    p = out.receipt.to_payload()
    assert out.admitted is True  # real permit + UEAK admission to fake sink
    assert p["executor_mode"] == "dry_run"
    assert p["result_status"] == "dry_run_required"
    assert p["ueak_commit_ref"]  # UEAK admission receipt hash carried
    assert p["receipt_hash"]
    assert ledger.verify_chain()["ok"] is True


# 15. Dry-run performs NO external effect (filesystem evidence)
def test_dry_run_performs_no_effect(tmp_path):
    before = snapshot_tree(tmp_path)
    ledger, out = _run(tmp_path)
    after = snapshot_tree(tmp_path)
    assert out.dry_run_allowed is True
    assert out.predicted_effect == "write_local_report_file"
    # the ONLY new file is the receipt ledger; the predicted target was not written
    new_files = set(after) - set(before)
    assert new_files == {"receipts.jsonl"}, new_files
    assert not (tmp_path / "proofs" / "demo.md").exists()


# 16. Dry-run cannot be claimed as a live effect
def test_dry_run_never_qualifies_as_live_evidence(tmp_path):
    _, out = _run(tmp_path)
    p = out.receipt.to_payload()
    assert is_live_effect_evidence(p) is False
    # forging liveness breaks the ledger hash (recomputed with the ledger's recipe)
    import hashlib
    from hg_core.ledger.canonical_json import canonical_dumps
    forged = dict(p, executor_mode="real", result_status="executed",
                  output_hash="sha256:" + "a" * 64)
    body = {k: v for k, v in forged.items() if k != "receipt_hash"}
    assert f"sha256:{hashlib.sha256(canonical_dumps(body)).hexdigest()}" != p["receipt_hash"]


# 17. Live/prohibited effect paths remain blocked
def test_prohibited_capability_refused(tmp_path):
    _, out = _run(tmp_path, capability="social_post.publish", action={"text": "x"})
    assert out.dry_run_allowed is False
    p = out.receipt.to_payload()
    assert p["executor_mode"] == "dry_run"
    assert is_live_effect_evidence(p) is False


def test_unknown_capability_refused(tmp_path):
    _, out = _run(tmp_path, capability="does.not.exist", action={"x": 1})
    assert out.dry_run_allowed is False
    assert out.predicted_effect == "unknown_capability"
