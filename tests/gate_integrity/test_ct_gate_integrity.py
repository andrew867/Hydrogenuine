"""Batch CT-A gate integrity tests."""

from __future__ import annotations

import json
from pathlib import Path

from hg_core.gate_integrity.checks import (
    run_ct_gate_integrity_checks,
    validate_truth_report_integrity,
)
from hg_core.proof.command_log import record_command, validate_command_log
from hg_core.truth.report import build_report

WORKSPACE = Path(__file__).resolve().parents[2]


def test_strict_ct_skips_fail_closed() -> None:
    report = build_report(
        head="test",
        path_ids=["connective_tissue/pack04"],
        stages=[],
        gate_results=[],
        subsystem_classification=[],
        skips=[{"gate_id": "demo", "reason": "deferred_default_mode"}],
        fast_subset=False,
        allow_dirty=False,
        dirty_files=[],
        registry_hash="sha256:" + "a" * 64,
        critical_failures=[],
        strict_ct_mode=True,
    )
    assert report.verdict == "red"
    checks = validate_truth_report_integrity(report.to_payload())
    assert any(c.check_id == "strict_ct_zero_skips" and not c.ok for c in checks)


def test_default_mode_skips_not_plain_green() -> None:
    report = build_report(
        head="test",
        path_ids=["connective_tissue/pack04"],
        stages=[],
        gate_results=[],
        subsystem_classification=[],
        skips=[{"gate_id": "demo", "reason": "deferred_default_mode"}],
        fast_subset=False,
        allow_dirty=False,
        dirty_files=[],
        registry_hash="sha256:" + "a" * 64,
        critical_failures=[],
        strict_ct_mode=False,
    )
    assert report.verdict == "green_with_skips"
    checks = validate_truth_report_integrity(report.to_payload())
    assert all(c.ok for c in checks)


def test_missing_command_log_fails_validation(tmp_path: Path) -> None:
    ok, findings = validate_command_log(tmp_path / "missing.jsonl")
    assert not ok
    assert findings[0].check == "missing"


def test_empty_command_log_fails_validation(tmp_path: Path) -> None:
    log_path = tmp_path / "command_log.jsonl"
    log_path.write_text("", encoding="utf-8")
    ok, findings = validate_command_log(log_path)
    assert not ok
    assert findings[0].check == "empty"


def test_command_log_records_argv_and_exit_code(tmp_path: Path) -> None:
    log_path = tmp_path / "command_log.jsonl"
    record_command(
        log_path,
        argv=["pytest", "tests/example", "-q"],
        cwd=WORKSPACE,
        exit_code=0,
        duration_s=0.5,
        stdout="ok",
        stderr="",
    )
    ok, findings = validate_command_log(log_path)
    assert ok, findings
    entry = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert entry["argv"] == ["pytest", "tests/example", "-q"]
    assert entry["exit_code"] == 0
    assert entry["stdout_digest"].startswith("sha256:")


def test_ct_gate_integrity_checks_green() -> None:
    result = run_ct_gate_integrity_checks(WORKSPACE)
    assert result["ok"], result.get("critical_failures", result)


def test_no_orphan_eval_scripts() -> None:
    from hg_core.truth.registry import load_registry

    registry = load_registry()
    orphans = registry.orphan_scripts(WORKSPACE / "scripts" / "evals")
    assert orphans == [], f"orphan gates: {orphans}"


def test_obt_strict_green_bundle_referenced() -> None:
    result = run_ct_gate_integrity_checks(WORKSPACE)
    assert result.get("obt_strict_bundle"), result


def test_crosspack_checks_in_result() -> None:
    result = run_ct_gate_integrity_checks(WORKSPACE)
    assert result["crosspack"]["ok"], result["crosspack"]
