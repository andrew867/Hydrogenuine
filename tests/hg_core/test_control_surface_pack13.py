"""
Control Surface Pack 13: Public launch kit — conformance runner, demo, baseline results, verify page.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


def test_conformance_runner_produces_report(tmp_path: Path) -> None:
    """Run conformance script on empty dir; expect report with conformance, connector, benchmarks, artifacts."""
    root = Path(__file__).resolve().parent.parent.parent
    script = root / "scripts" / "run_conformance_pack13.py"
    if not script.exists():
        pytest.skip("run_conformance_pack13.py not found")
    result = subprocess.run(
        [sys.executable, str(script), str(tmp_path), "-o", str(tmp_path / "out.json")],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(root),
    )
    assert result.returncode in (0, 1)
    out_file = tmp_path / "out.json"
    assert out_file.exists()
    report = json.loads(out_file.read_text(encoding="utf-8"))
    assert "run_id" in report
    assert "suite_version" in report
    assert report["suite_version"] == "v0.1"
    assert "conformance" in report
    assert "result" in report["conformance"] or "ok" in report["conformance"]
    assert "connector" in report
    assert "benchmarks" in report
    assert "artifacts" in report
    assert isinstance(report["artifacts"], list)


def test_conformance_runner_baseline_flag_writes_md(tmp_path: Path) -> None:
    """With --baseline, baseline_results.md is written with suite version and hashes."""
    root = Path(__file__).resolve().parent.parent.parent
    script = root / "scripts" / "run_conformance_pack13.py"
    if not script.exists():
        pytest.skip("run_conformance_pack13.py not found")
    subprocess.run(
        [sys.executable, str(script), str(tmp_path), "--baseline"],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(root),
    )
    baseline = tmp_path / "baseline_results.md"
    assert baseline.exists()
    text = baseline.read_text(encoding="utf-8")
    assert "PROJECT_NAME_PLACEHOLDER" in text or "Baseline" in text
    assert "Suite version" in text or "suite_version" in text
    assert "Conformance" in text
    assert "Limitations" in text or "redactions" in text


def test_verify_our_claims_page_exists() -> None:
    """Verify our claims page is in docs/public."""
    root = Path(__file__).resolve().parent.parent.parent
    page = root / "docs" / "public" / "verify_our_claims.md"
    assert page.exists()
    text = page.read_text(encoding="utf-8")
    assert "verify" in text.lower()
    assert "bundle_verify" in text or "baseline" in text


def test_slide_narrative_outline_exists() -> None:
    """Slide narrative outline is in docs/collateral."""
    root = Path(__file__).resolve().parent.parent.parent
    outline = root / "docs" / "collateral" / "slide_narrative_outline.md"
    assert outline.exists()
    text = outline.read_text(encoding="utf-8")
    assert "Problem" in text or "Solution" in text
    assert "conformance" in text.lower() or "benchmark" in text.lower()


def test_docker_compose_demo_template_exists() -> None:
    """Docker-compose demo template uses PROJECT_NAME_PLACEHOLDER."""
    root = Path(__file__).resolve().parent.parent.parent
    dc = root / "docs" / "demo" / "docker-compose.demo.yml"
    assert dc.exists()
    text = dc.read_text(encoding="utf-8")
    assert "project_placeholder" in text or "PROJECT_NAME" in text
