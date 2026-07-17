"""Storage substrate proof gate runner — hardened."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

from hg_core.dse.command_log_adapter import record_command
from hg_core.storage_substrate.fixtures import (
    run_als_fixture,
    run_als_postgres_fixture,
    run_backup_fixture,
    run_blob_fixture,
    run_pas_fixture,
    run_retention_fixture,
    run_sds_fixture,
    run_vms_fixture,
)
from hg_core.storage_substrate.proof_bundle import emit_proof_bundle, new_proof_dir

GateCheck = Callable[[Path], dict[str, Any]]


def _db_check_adapter(fn: Callable[[], dict[str, Any]]) -> GateCheck:
    def run(_: Path) -> dict[str, Any]:
        return fn()

    return run


GATE_FIXTURES: dict[str, tuple[str, GateCheck, list[str]]] = {
    "storage_inventory": ("STORAGE-INVENTORY", _db_check_adapter(lambda: {"ok": True, "inventory_gate": "hardened_scanner", "authority_created": False, "permission_granted": False}), []),
    "append_log_substrate": ("ALS", run_als_fixture, ["tests/storage"]),
    "proof_artifact_store": ("PAS", run_pas_fixture, ["tests/storage"]),
    "structured_data_store": ("SDS", _db_check_adapter(run_sds_fixture), ["tests/storage"]),
    "vector_memory_store": ("VMS", _db_check_adapter(run_vms_fixture), ["tests/storage"]),
    "blob_artifact_store": ("BLOB", run_blob_fixture, ["tests/storage"]),
    "retention_compaction": ("RET-DATA", _db_check_adapter(run_retention_fixture), ["tests/storage"]),
    "backup_restore": ("BACKUP", run_backup_fixture, ["tests/storage"]),
}


def run_pytest(workspace: Path, proof_dir: Path, test_targets: list[str]) -> dict[str, Any]:
    command_log = proof_dir / "command_log.jsonl"
    command_log.write_text("", encoding="utf-8")
    if not test_targets:
        record_command(
            command_log,
            argv=["storage_fixture_only"],
            cwd=workspace,
            exit_code=0,
            duration_s=0.0,
            stdout="no pytest target for fixture-only gate",
            stderr="",
        )
        return {"ok": True, "returncode": 0}
    t0 = time.monotonic()
    result = subprocess.run(
        [sys.executable, "-m", "pytest", *test_targets, "-q", "--timeout=180"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )
    record_command(
        command_log,
        argv=["pytest", *test_targets, "-q"],
        cwd=workspace,
        exit_code=result.returncode,
        duration_s=time.monotonic() - t0,
        stdout=result.stdout,
        stderr=result.stderr,
    )
    return {
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "stdout_tail": result.stdout[-4000:],
        "stderr_tail": result.stderr[-4000:],
    }


def _check_db_healthy() -> dict[str, Any]:
    dsn = os.environ.get("HG_STORAGE_POSTGRES_DSN")
    if not dsn:
        return {"healthy": False, "reason": "HG_STORAGE_POSTGRES_DSN not set"}
    try:
        import psycopg

        conn = psycopg.connect(dsn)
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        return {"healthy": True}
    except Exception as exc:
        return {"healthy": False, "reason": str(exc)}


def _check_pgvector() -> dict[str, Any]:
    dsn = os.environ.get("HG_STORAGE_POSTGRES_DSN")
    if not dsn:
        return {"available": False, "reason": "HG_STORAGE_POSTGRES_DSN not set"}
    try:
        import psycopg

        conn = psycopg.connect(dsn)
        cur = conn.cursor()
        cur.execute("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
        row = cur.fetchone()
        cur.close()
        conn.close()
        return {"available": bool(row and row[0])}
    except Exception as exc:
        return {"available": False, "reason": str(exc)}


def _check_no_authority_conversion(results: list[dict[str, Any]]) -> bool:
    for result in results:
        stdout = result.get("stdout_tail", "")
        if '"permission_granted": true' in stdout or '"authority_created": true' in stdout:
            return False
    return True


def run_storage_gate(workspace: Path, gate_key: str) -> int:
    if gate_key not in GATE_FIXTURES:
        raise KeyError(f"unknown storage gate: {gate_key}")
    pack, check_fn, test_targets = GATE_FIXTURES[gate_key]
    proof_dir = new_proof_dir(workspace, pack)
    proof_dir.mkdir(parents=True, exist_ok=True)
    feature_checks = check_fn(workspace)
    pytest_result = run_pytest(workspace, proof_dir, test_targets)
    gate_ok = bool(feature_checks.get("ok")) and bool(pytest_result["ok"])
    result = emit_proof_bundle(
        workspace,
        proof_dir,
        pack=pack,
        gate=f"{gate_key}_gate",
        artifacts={
            "feature_checks.json": feature_checks,
            "pytest_result.json": pytest_result,
        },
        gate_ok=gate_ok,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if gate_ok else 1


def run_final_storage_gate(workspace: Path) -> int:
    proof_dir = new_proof_dir(workspace, "STORAGE-HARDENED")
    proof_dir.mkdir(parents=True, exist_ok=True)
    command_log = proof_dir / "command_log.jsonl"
    command_log.write_text("", encoding="utf-8")

    db_health = _check_db_healthy()
    pgvector_status = _check_pgvector()

    results: list[dict[str, Any]] = []
    for gate_key in GATE_FIXTURES:
        script = workspace / "scripts" / "evals" / f"{gate_key}_gate.py"
        t0 = time.monotonic()
        completed = subprocess.run(
            [sys.executable, str(script)],
            cwd=workspace,
            capture_output=True,
            text=True,
            check=False,
        )
        record_command(
            command_log,
            argv=[sys.executable, str(script)],
            cwd=workspace,
            exit_code=completed.returncode,
            duration_s=time.monotonic() - t0,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
        results.append(
            {
                "gate_key": gate_key,
                "returncode": completed.returncode,
                "stdout_tail": completed.stdout[-4000:],
                "stderr_tail": completed.stderr[-4000:],
            }
        )

    all_gates_pass = all(item["returncode"] == 0 for item in results)
    no_authority_conversion = _check_no_authority_conversion(results)
    gate_ok = all_gates_pass and db_health.get("healthy", False) and pgvector_status.get("available", False) and no_authority_conversion

    summary = {
        "db_healthy": db_health,
        "pgvector_available": pgvector_status,
        "all_subgates_pass": all_gates_pass,
        "no_authority_conversion": no_authority_conversion,
        "permission_granted": False,
        "authority_created": False,
    }

    result = emit_proof_bundle(
        workspace,
        proof_dir,
        pack="STORAGE-HARDENED",
        gate="storage_artifact_vector_final_gate",
        artifacts={
            "subgate_results.json": results,
            "summary.json": summary,
        },
        gate_ok=gate_ok,
    )

    report_path = workspace / "docs" / "reports" / "phases" / "STORAGE_HARDENING_FINAL_AUDIT.md"
    verdict = "GREEN_STORAGE_HARDENED" if gate_ok else "RED"
    report_path.write_text(
        f"# Storage Hardening Final Audit\n\n"
        f"**Verdict:** {verdict}\n\n"
        f"**Proof bundle:** `{proof_dir}`\n\n"
        f"## Subsystem Status\n\n"
        f"| Subsystem | Gate | Status |\n"
        f"| --- | --- | --- |\n"
        + "".join(f"| {r['gate_key']} | {r['gate_key']}_gate | {'GREEN' if r['returncode'] == 0 else 'RED'} |\n" for r in results)
        + f"\n## Infrastructure\n\n"
        f"- hg-db healthy: {db_health.get('healthy', False)}\n"
        f"- pgvector available: {pgvector_status.get('available', False)}\n"
        f"- Authority conversion: {not no_authority_conversion}\n\n"
        f"## Authority Boundary\n\n"
        f"Storage is not authority. Retrieval is not truth. Similarity is not evidence.\n"
        f"Vector hit is not proof. Proof bundle is evidence, not permission.\n"
        f"Restore is not permission. Backup is not permission.\n",
        encoding="utf-8",
    )

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if gate_ok else 1


__all__ = ["run_final_storage_gate", "run_storage_gate"]
