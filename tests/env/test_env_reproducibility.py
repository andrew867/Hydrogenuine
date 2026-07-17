"""CT-16 ENV environment reproducibility tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from hg_core.env.deps import check_required_modules
from hg_core.env.doctor import run_env_doctor
from hg_core.env.manifest import load_manifest, manifest_hash
from hg_core.env.redact import redact_env_value, snapshot_env
from hg_core.env.repro_report import build_repro_report

WORKSPACE = Path(__file__).resolve().parents[2]
PYTHON = sys.executable


def test_manifest_validates() -> None:
    manifest = load_manifest(workspace=WORKSPACE)
    assert manifest.manifest_hash.startswith("sha256:")
    assert manifest.package_lock_path == "requirements-frozen.txt"


def test_manifest_hash_anchored() -> None:
    path = WORKSPACE / "config" / "env_manifest_v1.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert payload["manifest_hash"] == manifest_hash(payload)


def test_env_doctor_passes_baseline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("HG_RTC_COGNITION_LIVE", raising=False)
    monkeypatch.setenv("HG_NO_NETWORK", "1")
    result = run_env_doctor(WORKSPACE, mode="baseline")
    assert result.ok, result.report.get("failures")
    assert result.report["offline"] is True
    assert "OPENAI_API_KEY" in result.report["optional_features"]


def test_missing_optional_live_does_not_fail_baseline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("HG_RTC_COGNITION_API_KEY", raising=False)
    monkeypatch.delenv("HG_RTC_COGNITION_LIVE", raising=False)
    result = run_env_doctor(WORKSPACE, mode="baseline")
    assert result.ok
    assert "OPENAI_API_KEY" in result.report["live_features_missing"]


def test_missing_required_module_fails_clearly() -> None:
    result = check_required_modules(("pytest", "this_module_does_not_exist_env_ct16"))
    assert not result.ok
    assert "required_module_missing" in result.detail


def test_env_output_redacts_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-secret-value-abcdefghijklmnop")
    assert redact_env_value("OPENAI_API_KEY", os.environ["OPENAI_API_KEY"]) == "[REDACTED]"
    snap = snapshot_env(("OPENAI_API_KEY",))
    assert snap["OPENAI_API_KEY"] == "[REDACTED]"
    result = run_env_doctor(WORKSPACE, mode="baseline")
    raw = json.dumps(result.report)
    assert "sk-test-secret" not in raw
    assert result.report["env_snapshot"].get("OPENAI_API_KEY") == "[REDACTED]"


def test_repro_report_emits_versions_and_hashes() -> None:
    report = build_repro_report(WORKSPACE, mode="baseline")
    assert report["manifest_hash"].startswith("sha256:")
    assert report["package_lock"]["hash"].startswith("sha256:")
    assert report["python"]["version"]
    assert report["report_hash"].startswith("sha256:")


def test_env_doctor_cli_baseline() -> None:
    result = subprocess.run(
        [PYTHON, str(WORKSPACE / "scripts/env/env_doctor.py"), "--mode", "baseline", "--json"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        env={k: v for k, v in os.environ.items() if k not in {"OPENAI_API_KEY", "HG_RTC_COGNITION_API_KEY"}},
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True


def test_repro_report_cli() -> None:
    result = subprocess.run(
        [PYTHON, str(WORKSPACE / "scripts/env/repro_report.py"), "--mode", "baseline"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["doctor_ok"] is True
    assert "report_hash" in payload
