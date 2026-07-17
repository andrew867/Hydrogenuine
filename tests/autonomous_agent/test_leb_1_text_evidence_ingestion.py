"""LEB-1 text evidence ingestion tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from hg_runtime.local_evidence_bridge.ingestion_manifest import build_ingestion_manifest
from hg_runtime.local_evidence_bridge.ingestion_replay import replay_ingestion
from hg_runtime.local_evidence_bridge.redaction import redact_text
from hg_runtime.local_evidence_bridge.schemas import EvidenceBridgeError, PHASE19_VERDICT, PHASE24_STATUS
from hg_runtime.local_evidence_bridge.text_ingestion import ingest_text_source, resolve_approved_source

ROOT = Path(__file__).resolve().parents[2]


def _layer():
    paths = ["tests/fixtures/local_evidence/source_001.md", "tests/fixtures/local_evidence/source_002.txt"]
    rows = [ingest_text_source(ROOT, path, source_id=f"src-{i}") for i, path in enumerate(paths, start=1)]
    receipts = [r["evidence_receipt"] for r in rows]
    excerpts = [r["excerpt_receipt"] for r in rows]
    redactions = [r["redaction_record"] for r in rows]
    manifest = build_ingestion_manifest(paths, receipts, excerpts, redactions)
    replay = replay_ingestion(receipts, excerpts, redactions, manifest)
    return paths, receipts, excerpts, redactions, manifest, replay


def test_leb1_ingests_only_explicit_source_paths():
    paths, _, _, _, manifest, _ = _layer()
    assert manifest["explicit_source_paths"] == paths
    assert manifest["only_explicit_paths"] is True


def test_leb1_source_paths_inside_approved_fixture_directory():
    resolve_approved_source(ROOT, "tests/fixtures/local_evidence/source_001.md")


def test_leb1_rejects_path_traversal():
    with pytest.raises(EvidenceBridgeError):
        resolve_approved_source(ROOT, "tests/fixtures/local_evidence/../outside.md")


def test_leb1_rejects_unapproved_operator_inbox():
    with pytest.raises(EvidenceBridgeError):
        resolve_approved_source(ROOT, "operator_evidence/inbox/source.md")


def test_leb1_rejects_binary_file(tmp_path):
    binary = ROOT / "tests/fixtures/local_evidence/binary_fixture.bin"
    binary.write_bytes(b"a\x00b")
    try:
        with pytest.raises(EvidenceBridgeError):
            ingest_text_source(ROOT, "tests/fixtures/local_evidence/binary_fixture.bin", source_id="binary")
    finally:
        binary.unlink(missing_ok=True)


def test_leb1_secret_like_content_redacted():
    redacted, changed = redact_text("token sk-ABCDEFGHIJKLMNOPQRSTUVWX")
    assert changed is True
    assert "sk-ABCDEFGHIJKLMNOPQRSTUVWX" not in redacted


def test_leb1_evidence_receipt_does_not_claim_truth():
    _, receipts, _, _, _, _ = _layer()
    assert all(not r["evidence_receipt_is_truth"] for r in receipts)


def test_leb1_no_belief_promotion():
    _, receipts, excerpts, _, manifest, _ = _layer()
    assert all(not r["belief_promoted"] for r in receipts)
    assert all(not e["belief_promoted"] for e in excerpts)
    assert manifest["no_belief_promotion"] is True


def test_leb1_no_tool_authorization_or_live_effects():
    _, receipts, excerpts, _, _, _ = _layer()
    assert all(not r["tools_authorized"] for r in receipts)
    assert all(not r["live_external_side_effects_created"] for r in receipts + excerpts)


def test_leb1_replay_preserves_ingestion_hashes():
    *_, replay = _layer()
    assert replay["replay_preserves_ingestion_hashes"] is True


def test_leb1_replay_rejects_mutated_receipt():
    _, receipts, excerpts, redactions, manifest, _ = _layer()
    mutated = [dict(r) for r in receipts]
    mutated[0]["receipt_hash"] = "mutated"
    replay = replay_ingestion(mutated, excerpts, redactions, manifest)
    assert replay["replay_preserves_ingestion_hashes"] is False


def test_leb1_preserves_phase19_yellow():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")


def test_leb1_preserves_phase24_infrastructure_only():
    assert PHASE24_STATUS == "infrastructure_only"
