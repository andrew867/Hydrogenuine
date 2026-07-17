"""DSE-FOUNDATION gate runner."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_core.dse.command_log_adapter import record_command
from hg_core.dse.config import ensure_sandbox_dirs
from hg_core.dse.no_authority import check_dse_import_fences
from hg_core.dse.policy import RealSinkPolicy, SinkClass
from hg_core.dse.proof_bundle import emit_proof_bundle, new_proof_dir, sha256_file
from hg_core.dse.types import DurableSinkReceipt, SinkAdmissionDecision, SinkRollbackRecord
from hg_runtime.durable_side_effect.foundation import FIXTURE_CLOCK, load_foundation_fixtures, process_foundation_bundle


def git_head(workspace: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def run_dse_foundation_checks() -> dict[str, object]:
    from hg_core.iam.registry import clear_registry_cache, load_registry

    clear_registry_cache()
    load_registry()
    ensure_sandbox_dirs()
    checks: list[dict[str, object]] = []

    for sink_class in SinkClass:
        policy = RealSinkPolicy(sink_class=sink_class, tranche_id="DSE-FOUNDATION")
        checks.append(
            {
                "check_id": f"policy_{sink_class.value.lower()}",
                "ok": policy.is_in_scope(),
                "detail": sink_class.value,
            }
        )

    fences_ok, fence_detail = check_dse_import_fences()
    checks.append({"check_id": "import_fences", "ok": fences_ok, "detail": fence_detail if not fences_ok else "clean"})

    bundles = load_foundation_fixtures()
    valid = next(b for b in bundles if b["bundle_id"] == "dse-valid-file-sink")
    valid_result = process_foundation_bundle(valid, observed_at=FIXTURE_CLOCK)
    receipt = valid_result.get("receipt")
    checks.append(
        {
            "check_id": "valid_approved_durable_sink",
            "ok": valid_result.get("durable_write_performed") is True
            and valid_result.get("permission_granted") is False
            and isinstance(receipt, dict)
            and bool(receipt.get("receipt_hash")),
            "detail": valid_result.get("reason_code"),
        }
    )

    for bundle_id, key in (
        ("dse-missing-operator-approval", "admission"),
        ("dse-stale-approval", "admission"),
        ("dse-missing-iam", "admission"),
        ("dse-missing-tim", "admission"),
    ):
        bundle = next(b for b in bundles if b["bundle_id"] == bundle_id)
        result = process_foundation_bundle(bundle, observed_at=FIXTURE_CLOCK)
        adm = result.get("admission", {})
        checks.append(
            {
                "check_id": f"refusal_{bundle_id}",
                "ok": (adm.get("admitted") if isinstance(adm, dict) else False) is False,
                "detail": adm.get("reason_code") if isinstance(adm, dict) else None,
            }
        )

    bad_path = next(b for b in bundles if b["bundle_id"] == "dse-unauthorized-path")
    bad_path_result = process_foundation_bundle(bad_path, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "unauthorized_path_refusal",
            "ok": bad_path_result.get("durable_write_performed") is False,
            "detail": bad_path_result.get("reason_code"),
        }
    )

    secret = next(b for b in bundles if b["bundle_id"] == "dse-secret-leak")
    secret_result = process_foundation_bundle(secret, observed_at=FIXTURE_CLOCK)
    adm = secret_result.get("admission", {})
    checks.append(
        {
            "check_id": "secret_leak_refusal",
            "ok": (adm.get("admitted") if isinstance(adm, dict) else True) is False,
            "detail": adm.get("reason_code") if isinstance(adm, dict) else None,
        }
    )

    checks.append(
        {
            "check_id": "rollback_record_present",
            "ok": isinstance(valid_result.get("rollback"), dict),
            "detail": valid_result.get("rollback_reason_code"),
        }
    )

    checks.append(
        {
            "check_id": "core_types_instantiable",
            "ok": bool(SinkAdmissionDecision(False, "x", "y", "z", "r").to_payload())
            and bool(DurableSinkReceipt("r", "s", "t", "req", "tgt", "dig", "rb").receipt_hash())
            and bool(SinkRollbackRecord("rb", "r", "t", "tgt", "dig").to_payload()),
            "detail": "types ok",
        }
    )

    critical_failures = [str(c["check_id"]) for c in checks if not c["ok"]]
    return {"ok": not critical_failures, "critical_failures": critical_failures, "checks": checks}


def run_dse_foundation_gate(workspace: Path, *, gate_id: str = "dse_foundation_v1") -> int:
    proof_dir = new_proof_dir(workspace, "DSE-FOUNDATION")
    proof_dir.mkdir(parents=True, exist_ok=True)
    command_log = proof_dir / "command_log.jsonl"
    command_log.write_text("", encoding="utf-8")

    feature_checks = run_dse_foundation_checks()
    test_targets = ["tests/dse_foundation"]
    t0 = time.monotonic()
    test_cmd = subprocess.run(
        [sys.executable, "-m", "pytest", *test_targets, "-q", "--timeout=120"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )
    record_command(
        command_log,
        argv=["pytest", *test_targets, "-q"],
        cwd=workspace,
        exit_code=test_cmd.returncode,
        duration_s=time.monotonic() - t0,
        stdout=test_cmd.stdout,
        stderr=test_cmd.stderr,
    )

    gate_ok = feature_checks["ok"] and test_cmd.returncode == 0
    emit_proof_bundle(
        proof_dir,
        pack="DSE-FOUNDATION",
        gate=gate_id,
        head=git_head(workspace),
        artifacts={"dse_foundation_checks.json": feature_checks},
        gate_ok=gate_ok,
    )
    gate_result = {
        "gate": gate_id,
        "ok": gate_ok,
        "critical_failures": feature_checks.get("critical_failures", []),
        "proof_dir": str(proof_dir),
    }
    print(json.dumps(gate_result, indent=2))
    return 0 if gate_ok else 1


__all__ = ["run_dse_foundation_checks", "run_dse_foundation_gate"]
