"""CT-17 DOC docs freshness / claim-check tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from hg_core.docs_freshness.registry import enumerate_claim_bearing_docs, load_claim_rules, load_registry
from hg_core.docs_freshness.scanner import run_claim_check
from hg_core.docs_freshness.timeline import check_master_timeline

WORKSPACE = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).parent / "fixtures"
PYTHON = sys.executable


def test_doc_registry_load_enumerates_claim_bearing() -> None:
    registry = load_registry(workspace=WORKSPACE)
    rules = load_claim_rules(workspace=WORKSPACE)
    docs = enumerate_claim_bearing_docs(WORKSPACE, registry)
    assert registry.schema == "doc_registry_v1"
    assert rules.schema == "doc_claim_rules_v1"
    assert len(docs) >= 5
    assert any("CT16_ENV_STATUS" in str(p) for p in docs)


def test_stale_claim_fixture_detected() -> None:
    fixture = FIXTURES / "stale_head_no_banner.md"
    report = run_claim_check(WORKSPACE, extra_paths=[fixture], include_citation_lint=False)
    checks = {f.check for f in report.findings}
    assert "head_binding_or_banner" in checks or "unsupported_complete_claim" in checks
    assert not report.ok


def test_unsupported_implementation_claim_fails() -> None:
    fixture = FIXTURES / "unsupported_live_cognition_complete.md"
    report = run_claim_check(WORKSPACE, extra_paths=[fixture], include_citation_lint=False)
    assert any(f.check == "unsupported_complete_claim" for f in report.findings)
    assert not report.ok


def test_future_backburner_modules_labeled_correctly() -> None:
    fixture = FIXTURES / "future_module_labeled.md"
    report = run_claim_check(WORKSPACE, extra_paths=[fixture], include_citation_lint=False)
    assert not any(f.check == "future_module_label" for f in report.findings)


def test_master_timeline_links_exist() -> None:
    registry = load_registry(workspace=WORKSPACE)
    result = check_master_timeline(WORKSPACE, registry.master_timeline)
    assert result["links_checked"] > 0
    assert result["ok"], result["findings"]


def test_report_generated_with_todos_and_deferred() -> None:
    report = run_claim_check(WORKSPACE, include_citation_lint=False)
    payload = report.to_payload()
    assert "todos" in payload
    assert "deferred" in payload
    assert isinstance(payload["deferred"], list)
    assert len(payload["deferred"]) >= 1


def test_docs_claim_check_cli_json() -> None:
    out_path = WORKSPACE / "runtime" / "tmp_ct17_claim_check.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = subprocess.run(
        [
            PYTHON,
            str(WORKSPACE / "scripts" / "audit" / "docs_claim_check.py"),
            "--json",
            "--markdown",
            str(WORKSPACE / "runtime" / "tmp_ct17_claim_check.md"),
        ],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        check=False,
    )
    assert cmd.returncode in {0, 1}
    data = json.loads(cmd.stdout)
    assert "ok" in data
    assert "findings" in data


def test_registry_yaml_valid() -> None:
    registry_path = WORKSPACE / "config" / "doc_registry_v1.yaml"
    rules_path = WORKSPACE / "config" / "doc_claim_rules_v1.yaml"
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    rules = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
    assert registry["schema"] == "doc_registry_v1"
    assert rules["schema"] == "doc_claim_rules_v1"
    assert "implemented" in rules["claim_categories"]
