"""CT-10 RET evidence retention lifecycle tests."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from hg_core.evidence_lifecycle.export import export_bundle
from hg_core.evidence_lifecycle.lifecycle import (
    REASON_IMMUTABLE,
    REASON_MISSING_SEC,
    REASON_NOT_EXPIRED,
    REASON_UNAUTHORIZED,
    ArtifactDescriptor,
    evaluate_deletion,
    is_temp_expired,
)
from hg_core.evidence_lifecycle.policy import load_policy, policy_hash
from hg_core.evidence_lifecycle.proof_bundle import validate_retained_proof_bundle
from hg_core.schema_compat.proof_bundle import validate_ct_proof_bundle_dir

WORKSPACE = Path(__file__).resolve().parents[2]


def test_proof_bundle_retained() -> None:
    policy = load_policy(workspace=WORKSPACE)
    bundles = sorted((WORKSPACE / "docs/proofs/connective_tissue/pack09").iterdir())
    assert bundles
    result = validate_retained_proof_bundle(bundles[-1], policy, workspace=WORKSPACE)
    assert result.retained
    assert result.ok


def test_temp_artifact_can_expire_by_policy() -> None:
    policy = load_policy(workspace=WORKSPACE)
    old = datetime.now(timezone.utc) - timedelta(hours=48)
    desc = ArtifactDescriptor("tmp1", ".tmp/gate_run", "temp", "runtime", old)
    assert is_temp_expired(desc, policy)
    decision = evaluate_deletion(desc, "runtime", policy)
    assert decision.allowed
    fresh = ArtifactDescriptor("tmp2", ".tmp/fresh", "temp", "runtime", datetime.now(timezone.utc))
    assert not is_temp_expired(fresh, policy)
    assert evaluate_deletion(fresh, "runtime", policy).reason_code == REASON_NOT_EXPIRED


def test_sensitive_artifact_requires_sec_handling() -> None:
    policy = load_policy(workspace=WORKSPACE)
    desc = ArtifactDescriptor(
        "cred1",
        "credentials/api.json",
        "sensitive",
        "sec",
        datetime.now(timezone.utc),
        sec_handled=False,
    )
    assert evaluate_deletion(desc, "sec", policy).reason_code == REASON_MISSING_SEC
    desc_ok = ArtifactDescriptor(
        "cred1",
        "credentials/api.json",
        "sensitive",
        "sec",
        datetime.now(timezone.utc),
        sec_handled=True,
    )
    assert evaluate_deletion(desc_ok, "sec", policy).allowed is False  # sensitive not deletable via temp path


def test_deletion_without_owner_or_policy_fails() -> None:
    policy = load_policy(workspace=WORKSPACE)
    desc = ArtifactDescriptor(
        "r1",
        "docs/proofs/connective_tissue/pack01/x",
        "proof",
        "ct_gates",
        datetime.now(timezone.utc),
    )
    assert evaluate_deletion(desc, "runtime", policy).reason_code == REASON_UNAUTHORIZED
    receipt = ArtifactDescriptor(
        "rcpt1",
        "hg_mel/receipts/r1.json",
        "receipt",
        "mel",
        datetime.now(timezone.utc),
    )
    assert evaluate_deletion(receipt, "mel", policy).reason_code == REASON_IMMUTABLE


def test_exported_bundle_includes_manifest_and_hashes(tmp_path: Path) -> None:
    policy = load_policy(workspace=WORKSPACE)
    source = tmp_path / "source"
    source.mkdir()
    (source / "data.json").write_text('{"ok": true}', encoding="utf-8")
    dest = tmp_path / "export"
    result = export_bundle(source, dest, policy, artifact_class="proof", sec_scan_applied=True)
    assert result.ok
    assert (dest / "export_manifest.json").exists()
    manifest = json.loads((dest / "export_manifest.json").read_text(encoding="utf-8"))
    assert manifest["file_hashes"]


def test_sensitive_export_without_sec_fails(tmp_path: Path) -> None:
    policy = load_policy(workspace=WORKSPACE)
    source = tmp_path / "sensitive_src"
    source.mkdir()
    (source / "secret.json").write_text('{"api_key": "sk-live-secret123"}', encoding="utf-8")
    dest = tmp_path / "sensitive_export"
    result = export_bundle(source, dest, policy, artifact_class="sensitive", sec_scan_applied=False)
    assert not result.ok
    assert "SEC" in result.detail or "redaction" in result.detail


def test_missing_artifact_in_proof_bundle_fails_gate(tmp_path: Path) -> None:
    bundles = sorted((WORKSPACE / "docs/proofs/connective_tissue/pack09").iterdir())
    src = bundles[-1]
    broken = tmp_path / "broken_bundle"
    shutil.copytree(src, broken)
    manifest = json.loads((broken / "manifest.json").read_text(encoding="utf-8"))
    # remove a hashed file
    first_key = next(iter(manifest["file_hashes"]))
    target = broken / first_key
    if target.exists():
        target.unlink()
    result = validate_ct_proof_bundle_dir(broken)
    assert not result.ok
    assert "missing" in result.detail


def test_policy_hash_anchored() -> None:
    policy = load_policy(workspace=WORKSPACE)
    assert policy.policy_hash.startswith("sha256:")
    assert "not execution authority" in policy.authority_note.lower()


def test_retention_recommendations_not_authority() -> None:
    policy = load_policy(workspace=WORKSPACE)
    assert policy.authority_note
