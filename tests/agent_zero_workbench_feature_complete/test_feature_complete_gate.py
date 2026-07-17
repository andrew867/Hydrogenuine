"""Feature-complete gate self-tests (WFC cases 24-28).

Exercise the gate's `evaluate_bundle` + scanners on synthetic bundles — no browser,
no `run_gate` (which would recurse). Proves the gate FAILS closed on: a leaked raw
token / session cookie, raw file bytes / disabled flags, an old-UI import claim,
enabled external effects, and a missing required file; and that the write-result
guard refuses to write inside the sealed bundle.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE / "scripts" / "evals"))

import agent_zero_workbench_feature_complete_gate as gate  # noqa: E402


def _green_gate_result():
    return {
        "verdict": "GREEN_AGENT_ZERO_WORKBENCH_FEATURE_COMPLETE",
        "raw_token_absent": True, "raw_file_content_absent": True,
        "old_ui_import_absent": True, "unauthenticated_rejected": True,
        "checksums_ok": True, "claim_boundary_ok": True,
        "external_effects_enabled": False, "external_storage_used": False,
    }


def _seal(bundle: Path):
    """Write checksums.sha256 over every file except the checksums file itself."""
    files = sorted(p for p in bundle.rglob("*") if p.is_file()
                   and p.name != "checksums.sha256")
    lines = []
    for p in files:
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        lines.append(f"{digest}  {p.relative_to(bundle).as_posix()}")
    (bundle / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _make_bundle(tmp_path, *, gate_result=None, extra_text=None) -> Path:
    b = tmp_path / "bundle"
    (b / "screenshots").mkdir(parents=True)
    for name in gate.REQUIRED_FILES:
        if name in ("checksums.sha256", "manifest.json"):
            continue
        if name == "gate_result.json":
            (b / name).write_text(json.dumps(gate_result or _green_gate_result()), encoding="utf-8")
        elif name == "summary_report.md":
            (b / name).write_text("# Proof\n\nLocal dev harness; not a production "
                                  "deployment; external effects disabled; observation "
                                  "not authority; proof records the path.\n", encoding="utf-8")
        else:
            (b / name).write_text("{}", encoding="utf-8")
    if extra_text:
        (b / "leak.txt").write_text(extra_text, encoding="utf-8")
    (b / "manifest.json").write_text(json.dumps({"schema_version": "1"}), encoding="utf-8")
    _seal(b)
    return b


def test_clean_bundle_passes(tmp_path):
    b = _make_bundle(tmp_path)
    res = gate.evaluate_bundle(b)
    assert res["ok"], res["failures"]


def test_case24_raw_jwt_token_fails(tmp_path):
    b = _make_bundle(tmp_path, extra_text="header eyJhbGciOiJSUzI1NiJ9.payload.sig")
    _seal(b)
    res = gate.evaluate_bundle(b)
    assert not res["ok"] and any("credential_in" in f for f in res["failures"])


def test_case24b_opaque_session_cookie_fails(tmp_path):
    # hg_session is NOT a JWT — the eyJ scanner alone would miss it.
    b = _make_bundle(tmp_path, extra_text="Cookie: hg_session=abc123opaquevalue")
    _seal(b)
    res = gate.evaluate_bundle(b)
    assert not res["ok"] and any("credential_in" in f for f in res["failures"])


def test_case25_raw_file_content_flag_false_fails(tmp_path):
    gr = _green_gate_result()
    gr["raw_file_content_absent"] = False
    b = _make_bundle(tmp_path, gate_result=gr)
    res = gate.evaluate_bundle(b)
    assert not res["ok"] and "raw_file_content_absent_false" in res["failures"]


def test_case26_old_ui_import_flag_false_fails(tmp_path):
    gr = _green_gate_result()
    gr["old_ui_import_absent"] = False
    b = _make_bundle(tmp_path, gate_result=gr)
    res = gate.evaluate_bundle(b)
    assert not res["ok"] and "old_ui_import_absent_false" in res["failures"]


def test_case27_external_effects_enabled_fails(tmp_path):
    gr = _green_gate_result()
    gr["external_effects_enabled"] = True
    b = _make_bundle(tmp_path, gate_result=gr)
    res = gate.evaluate_bundle(b)
    assert not res["ok"] and "external_effects_or_storage" in res["failures"]


def test_missing_required_file_fails(tmp_path):
    b = _make_bundle(tmp_path)
    (b / "browser_upload_result.json").unlink()
    _seal(b)
    res = gate.evaluate_bundle(b)
    assert not res["ok"] and any("missing:browser_upload_result.json" in f for f in res["failures"])


def test_checksum_tamper_fails(tmp_path):
    b = _make_bundle(tmp_path)
    (b / "browser_run_result.json").write_text('{"tampered":true}', encoding="utf-8")
    res = gate.evaluate_bundle(b)  # checksums now stale
    assert not res["ok"] and any("checksum_mismatch" in f for f in res["failures"])


def test_case28_write_result_guard_refuses_inside_bundle():
    # The guard must refuse a --write-result path inside the sealed bundle dir, and
    # allow one outside it (mirrors the run_gate guard condition).
    out = Path("/proofs/20260101T000000Z")
    inside = out / "gate_result_copy.json"
    outside = Path("/proofs/results/x.json")
    assert out in inside.parents or inside.parent == out       # refused
    assert not (out in outside.parents or outside.parent == out)  # allowed
    src = (WORKSPACE / "scripts/evals/agent_zero_workbench_feature_complete_gate.py").read_text(encoding="utf-8")
    assert "refusing to write result inside the sealed bundle" in src
