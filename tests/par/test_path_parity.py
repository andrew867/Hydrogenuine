"""CT-03 PAR path parity tests."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from hg_core.parity.bundle import PathParityError, require_runtime_path_id, seal_runtime_bundle_manifest
from hg_core.parity.citations import lint_markdown_file, lint_reports
from hg_core.parity.manifest import REQUIRED_SUBSYSTEMS, load_manifest, manifest_hash
from hg_core.parity.paths import RUNTIME_PATH_LABELS
from hg_core.parity.types import EvidenceClaim

WORKSPACE = Path(__file__).resolve().parents[2]


def test_runtime_path_labels_closed_set():
    assert "demo_phase0" in RUNTIME_PATH_LABELS
    assert "phase1_integrated" in RUNTIME_PATH_LABELS
    assert "dep_appliance" in RUNTIME_PATH_LABELS


def test_manifest_load_and_hash_anchor():
    manifest = load_manifest()
    assert manifest.schema == "path_parity_manifest_v1"
    assert manifest.manifest_hash.startswith("sha256:")
    assert set(manifest.subsystems.keys()) == set(REQUIRED_SUBSYSTEMS)


def test_bundle_refuses_unstamped_path():
    with pytest.raises(PathParityError, match="missing path_id"):
        require_runtime_path_id(None)
    with pytest.raises(PathParityError, match="unknown"):
        require_runtime_path_id("connective_tissue/pack01")


def test_bundle_accepts_stamped_path(tmp_path):
    seal_runtime_bundle_manifest(proof_dir=tmp_path, path_id="demo_phase0")
    data = json.loads((tmp_path / "runtime_path_manifest.json").read_text(encoding="utf-8"))
    assert data["runtime_path_id"] == "demo_phase0"


def test_evidence_claim_requires_path():
    claim = EvidenceClaim(
        claim_id="c1",
        path_id="demo_phase0",
        summary="replay determinism on stub handlers",
        state_hash="sha256:abc",
    )
    payload = claim.to_payload()
    assert payload["path_id"] == "demo_phase0"


def test_lint_refuses_demo_hash_as_integrated_claim(tmp_path):
    manifest = load_manifest()
    bad_report = tmp_path / "bad.md"
    digest = "a" * 64
    bad_report.write_text(
        f".tmp_sotu_refresh_demo_10 proves integrated HAL at sha256:{digest}.\n",
        encoding="utf-8",
    )
    findings = lint_markdown_file(
        bad_report,
        manifest=manifest,
        hash_sources={},
        workspace=tmp_path,
    )
    assert any(f.reason_code == "demo_hash_as_integrated_claim" for f in findings)


def test_lint_allows_labeled_demo_claim(tmp_path):
    manifest = load_manifest()
    ok_report = tmp_path / "ok.md"
    ok_report.write_text(
        "path_id: demo_phase0 — reducer replay sha256:" + "b" * 64 + ".\n",
        encoding="utf-8",
    )
    findings = lint_markdown_file(
        ok_report,
        manifest=manifest,
        hash_sources={},
        workspace=tmp_path,
    )
    assert findings == []


def test_lint_unknown_file_fails_closed(tmp_path):
    manifest = load_manifest()
    missing = tmp_path / "missing.md"
    findings = lint_markdown_file(
        missing,
        manifest=manifest,
        hash_sources={},
        workspace=tmp_path,
    )
    assert findings and findings[0].reason_code == "missing_evidence"


def test_manifest_hash_recompute():
    path = WORKSPACE / "config" / "path_parity_manifest_v1.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["manifest_hash"] == manifest_hash(payload)


def test_reports_lint_runs_on_workspace():
    result = lint_reports(WORKSPACE)
    assert "ok" in result
    assert "findings" in result
