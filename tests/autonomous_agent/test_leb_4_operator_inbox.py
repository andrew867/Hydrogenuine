"""LEB-4 operator evidence inbox tests (local-only, disabled by default)."""

from __future__ import annotations

from pathlib import Path

import pytest

from hg_runtime.local_evidence_bridge.inbox_gate import validate_leb4_gate
from hg_runtime.local_evidence_bridge.inbox_manifest import build_inbox_manifest, validate_inbox_manifest
from hg_runtime.local_evidence_bridge.inbox_replay import build_inbox_run_manifest, replay_inbox
from hg_runtime.local_evidence_bridge.operator_inbox import process_inbox
from hg_runtime.local_evidence_bridge.path_policy import (
    DEFAULT_INBOX_ROOT,
    INBOX_ENABLED_BY_DEFAULT,
    build_inbox_policy,
    extension_allowed,
    path_within_root,
    resolve_inbox_path,
    validate_inbox_relative_path,
)
from hg_runtime.local_evidence_bridge.redaction import secret_scan
from hg_runtime.local_evidence_bridge.schemas import EvidenceBridgeError, PHASE19_VERDICT, PHASE24_STATUS

ROOT = Path(__file__).resolve().parents[2]

VALID = [
    {"source_id": "src-note-001", "relative_path": f"{DEFAULT_INBOX_ROOT}/inbox_note_001.md"},
    {"source_id": "src-note-002", "relative_path": f"{DEFAULT_INBOX_ROOT}/inbox_note_002.txt"},
]
REJECTS = [
    {"source_id": "src-pdf", "relative_path": f"{DEFAULT_INBOX_ROOT}/inbox_doc.pdf"},
    {"source_id": "src-binext", "relative_path": f"{DEFAULT_INBOX_ROOT}/inbox_binary.bin"},
    {"source_id": "src-corrupt", "relative_path": f"{DEFAULT_INBOX_ROOT}/inbox_corrupt.txt"},
    {"source_id": "src-traversal", "relative_path": f"{DEFAULT_INBOX_ROOT}/../secret_note.md"},
    {"source_id": "src-outroot", "relative_path": "tests/fixtures/local_evidence/source_001.md"},
]


@pytest.fixture(autouse=True)
def _corrupt_fixture():
    """Generate the null-byte content-rejection fixture at runtime (never committed)."""
    path = ROOT / DEFAULT_INBOX_ROOT / "inbox_corrupt.txt"
    path.write_bytes(b"looks like text\x00but has embedded null\x00bytes")
    try:
        yield
    finally:
        path.unlink(missing_ok=True)


def _enabled_run(entries=None):
    policy = build_inbox_policy(enabled=True, allowed_root=DEFAULT_INBOX_ROOT)
    manifest = build_inbox_manifest(allowed_root=DEFAULT_INBOX_ROOT, entries=entries or (VALID + REJECTS))
    return policy, manifest, process_inbox(ROOT, policy, manifest)


def _reason(rejected, source_id):
    return next(r["rejection_reason"] for r in rejected if r["source_id"] == source_id)


def _gate_summary(**overrides):
    data = {
        "verdict": "GREEN_LEB_4_OPERATOR_INBOX_LOCAL_ONLY",
        "operator_inbox_disabled_by_default": True,
        "explicit_enable_flag_required": True,
        "explicit_manifest_required": True,
        "allowed_root_required": True,
        "accepted_records_written": True,
        "rejected_records_written": True,
        "path_traversal_rejected": True,
        "out_of_root_rejected": True,
        "symlink_escape_rejected": True,
        "binary_rejected": True,
        "pdf_rejected": True,
        "oversized_rejected": True,
        "links_not_followed": True,
        "disabled_inbox_accepts_nothing": True,
        "local_source_not_trusted": True,
        "accepted_source_not_truth": True,
        "accepted_source_not_belief": True,
        "accepted_source_not_authority": True,
        "no_directory_crawling": True,
        "no_belief_promotion": True,
        "no_pdf_ocr": True,
        "replay_preserves_inbox_hashes": True,
        "secret_redaction_passed": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


# --- Default-disabled boundary --------------------------------------------

def test_leb4_inbox_disabled_by_default():
    assert INBOX_ENABLED_BY_DEFAULT is False
    policy = build_inbox_policy()
    assert policy["operator_inbox_enabled"] is False
    assert policy["operator_inbox_disabled_by_default"] is True


def test_leb4_disabled_inbox_accepts_nothing():
    policy = build_inbox_policy(enabled=False)
    manifest = build_inbox_manifest(allowed_root=DEFAULT_INBOX_ROOT, entries=VALID)
    result = process_inbox(ROOT, policy, manifest)
    assert result["accepted"] == []
    assert all(r["rejection_reason"] == "operator_inbox_disabled" for r in result["rejected"])


def test_leb4_explicit_enable_flag_required():
    policy = build_inbox_policy(enabled=True)
    assert policy["operator_inbox_enabled"] is True
    assert policy["explicit_enable_flag_required"] is True


# --- Manifest required -----------------------------------------------------

def test_leb4_explicit_manifest_required():
    with pytest.raises(EvidenceBridgeError):
        build_inbox_manifest(allowed_root=DEFAULT_INBOX_ROOT, entries=[])


def test_leb4_no_directory_crawling():
    _, manifest, _ = _enabled_run()
    assert manifest["directory_crawling_enabled"] is False
    validate_inbox_manifest(manifest)


# --- Accept path -----------------------------------------------------------

def test_leb4_accepts_valid_manifest_entries():
    _, _, result = _enabled_run(VALID)
    assert len(result["accepted"]) == 2
    assert all(r["record_type"] == "accepted_source_record_v1" for r in result["accepted"])


def test_leb4_accepted_source_is_not_truth_belief_or_authority():
    _, _, result = _enabled_run(VALID)
    for r in result["accepted"]:
        assert not r["accepted_source_is_truth"]
        assert not r["accepted_source_is_belief"]
        assert not r["accepted_source_is_authority"]
        assert not r["local_file_trusted_by_default"]


def test_leb4_accepted_source_redacts_and_hashes():
    _, _, result = _enabled_run(VALID)
    for r in result["accepted"]:
        assert r["content_hash"]
        assert r["redacted_text_hash"]
        assert "links_followed" in r and r["links_followed"] is False


# --- Rejections ------------------------------------------------------------

def test_leb4_rejects_path_traversal():
    _, _, result = _enabled_run()
    assert _reason(result["rejected"], "src-traversal") == "path_traversal_or_absolute_path_forbidden"


def test_leb4_rejects_out_of_root():
    _, _, result = _enabled_run()
    assert _reason(result["rejected"], "src-outroot") == "source_path_outside_allowed_root"


def test_leb4_rejects_pdf():
    _, _, result = _enabled_run()
    assert _reason(result["rejected"], "src-pdf") == "pdf_rejected"


def test_leb4_rejects_disallowed_extension():
    _, _, result = _enabled_run()
    assert _reason(result["rejected"], "src-binext") == "disallowed_extension_rejected"


def test_leb4_rejects_binary_content():
    _, _, result = _enabled_run()
    assert _reason(result["rejected"], "src-corrupt") == "binary_content_rejected"


def test_leb4_rejects_oversized():
    policy = build_inbox_policy(enabled=True, max_bytes=8)
    manifest = build_inbox_manifest(allowed_root=DEFAULT_INBOX_ROOT, entries=[VALID[0]])
    result = process_inbox(ROOT, policy, manifest)
    assert _reason(result["rejected"], "src-note-001") == "oversized_file_rejected"


def test_leb4_validate_relative_path_rejects_absolute():
    with pytest.raises(EvidenceBridgeError):
        validate_inbox_relative_path("/etc/passwd", DEFAULT_INBOX_ROOT)


def test_leb4_resolve_rejects_traversal():
    with pytest.raises(EvidenceBridgeError):
        resolve_inbox_path(ROOT, f"{DEFAULT_INBOX_ROOT}/../x.md", DEFAULT_INBOX_ROOT)


def test_leb4_symlink_escape_guard():
    base = (ROOT / DEFAULT_INBOX_ROOT).resolve()
    assert path_within_root(base, (base / "inbox_note_001.md")) is True
    assert path_within_root(base, (ROOT / "hg_runtime").resolve()) is False


def test_leb4_extension_allowed():
    assert extension_allowed("a/b/c.md") is True
    assert extension_allowed("a/b/c.txt") is True
    assert extension_allowed("a/b/c.pdf") is False
    assert extension_allowed("a/b/c.bin") is False


# --- Replay & secrets ------------------------------------------------------

def test_leb4_replay_preserves_inbox_hashes():
    policy, manifest, result = _enabled_run()
    run_manifest = build_inbox_run_manifest(policy, manifest, result["accepted"], result["rejected"])
    assert replay_inbox(result["accepted"], result["rejected"], run_manifest)["replay_preserves_inbox_hashes"] is True


def test_leb4_replay_rejects_mutated_record():
    policy, manifest, result = _enabled_run()
    run_manifest = build_inbox_run_manifest(policy, manifest, result["accepted"], result["rejected"])
    mutated = [dict(r) for r in result["accepted"]]
    mutated[0]["source_path"] = "tampered"
    assert replay_inbox(mutated, result["rejected"], run_manifest)["replay_preserves_inbox_hashes"] is False


def test_leb4_no_secret_material_in_records():
    _, _, result = _enabled_run()
    assert secret_scan(result) is True


# --- Prior phases ----------------------------------------------------------

def test_leb4_preserves_phase19_yellow():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")


def test_leb4_preserves_phase24_infrastructure_only():
    assert PHASE24_STATUS == "infrastructure_only"


# --- Gate ------------------------------------------------------------------

def test_leb4_gate_passes_on_full_summary():
    assert validate_leb4_gate(_gate_summary())["ok"] is True


def test_leb4_gate_refuses_if_inbox_default_enabled():
    assert validate_leb4_gate(_gate_summary(operator_inbox_enabled_by_default=True))["ok"] is False


def test_leb4_gate_refuses_if_arbitrary_ingestion_enabled():
    assert validate_leb4_gate(_gate_summary(arbitrary_file_ingestion_enabled=True))["ok"] is False


def test_leb4_gate_refuses_if_pdf_ingestion_enabled():
    assert validate_leb4_gate(_gate_summary(pdf_ingestion_enabled=True))["ok"] is False


def test_leb4_gate_refuses_if_traversal_not_rejected():
    assert validate_leb4_gate(_gate_summary(path_traversal_rejected=False))["ok"] is False


def test_leb4_gate_refuses_if_belief_promoted():
    assert validate_leb4_gate(_gate_summary(belief_promoted=True))["ok"] is False


def test_leb4_gate_refuses_if_web_browse():
    assert validate_leb4_gate(_gate_summary(web_browse_performed=True))["ok"] is False
