"""CT-15 RUN operator runbook / break-glass tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from hg_core.operator_runbook.lint import lint_runbook_docs
from hg_core.operator_runbook.manifest import REQUIRED_PROCEDURES, load_manifest, manifest_hash
from hg_core.operator_runbook.ops_state import load_ops_state, status_summary
from hg_core.operator_runbook.receipts import load_receipts, record_emergency_receipt
from hg_core.operator_runbook.replay import run_replay_check

WORKSPACE = Path(__file__).resolve().parents[2]
PYTHON = sys.executable


def test_manifest_validates() -> None:
    manifest = load_manifest(workspace=WORKSPACE)
    assert manifest.manifest_hash.startswith("sha256:")
    assert set(REQUIRED_PROCEDURES).issubset({p.procedure_id for p in manifest.procedures})


def test_manifest_hash_anchored() -> None:
    path = WORKSPACE / "config" / "operator_runbook_manifest_v1.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert payload["manifest_hash"] == manifest_hash(payload)


def test_runbook_lint_passes() -> None:
    result = lint_runbook_docs(WORKSPACE)
    assert result.ok, result.issues


@pytest.mark.parametrize("script_rel", [p.script for p in load_manifest(workspace=WORKSPACE).procedures])
def test_procedure_help(script_rel: str) -> None:
    script = WORKSPACE / script_rel
    result = subprocess.run([PYTHON, str(script), "--help"], cwd=WORKSPACE, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_break_glass_requires_confirm(tmp_path: Path) -> None:
    _seed_drill_workspace(tmp_path)
    result = subprocess.run(
        [PYTHON, str(WORKSPACE / "scripts/ops/freeze_queues.py"), "--operator-id", "op:local", "--workspace", str(tmp_path)],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0


def test_break_glass_records_receipt(tmp_path: Path) -> None:
    _seed_drill_workspace(tmp_path)
    result = subprocess.run(
        [
            PYTHON,
            str(WORKSPACE / "scripts/ops/freeze_queues.py"),
            "--operator-id",
            "op:local",
            "--confirm",
            "freeze_queues",
            "--workspace",
            str(tmp_path),
            "--json",
        ],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    manifest = load_manifest(workspace=WORKSPACE)
    receipts = load_receipts(tmp_path, receipts_relative=manifest.emergency_receipts_path)
    assert receipts
    assert receipts[-1]["procedure_id"] == "freeze_queues"


def test_panic_safe_mode_status_visible(tmp_path: Path) -> None:
    _seed_drill_workspace(tmp_path)
    subprocess.run(
        [
            PYTHON,
            str(WORKSPACE / "scripts/ops/enter_safe_mode.py"),
            "--operator-id",
            "op:local",
            "--confirm",
            "enter_safe_mode",
            "--workspace",
            str(tmp_path),
        ],
        cwd=WORKSPACE,
        check=True,
    )
    status = subprocess.run(
        [
            PYTHON,
            str(WORKSPACE / "scripts/ops/ops_status.py"),
            "--operator-id",
            "op:local",
            "--workspace",
            str(tmp_path),
            "--json",
        ],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(status.stdout)
    assert payload["status"]["safe_mode"] is True
    assert payload["status"]["panic_active"] is True
    assert payload["status"]["mode"] == "safe_mode"


def test_recover_lockdown_refuses_bad_replay(tmp_path: Path) -> None:
    manifest = load_manifest(workspace=WORKSPACE)
    state = load_ops_state(tmp_path, relative=manifest.ops_state_path)
    state.lockdown_active = True
    from hg_core.operator_runbook.ops_state import save_ops_state

    save_ops_state(tmp_path, state, relative=manifest.ops_state_path)
    bundle = tmp_path / "bad_bundle"
    bundle.mkdir()
    (bundle / "manifest.json").write_text('{"file_hashes": {"missing.json": "sha256:00"}}', encoding="utf-8")
    replay = run_replay_check(
        tmp_path,
        ops_state_relative=manifest.ops_state_path,
        proof_bundle=bundle,
    )
    assert not replay.ok


def test_emergency_receipt_never_skipped(tmp_path: Path) -> None:
    receipt = record_emergency_receipt(
        tmp_path,
        procedure_id="test",
        operator_id="op:local",
        scope="panic",
        payload={"action": "drill"},
        ledger_reachable=False,
    )
    assert receipt["reconciliation_status"] == "pending_reconciliation"
    rows = load_receipts(tmp_path, receipts_relative="runtime/ops/emergency_receipts.jsonl")
    assert rows


def _seed_drill_workspace(target: Path) -> None:
    (target / "runtime" / "ops").mkdir(parents=True, exist_ok=True)
