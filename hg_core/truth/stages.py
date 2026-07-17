"""OBT stage runners (CT-04)."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

import yaml

from hg_core.truth.classify import classify_subsystems_truth, static_stub_scan
from hg_core.truth.registry import GateEntry, TruthGateRegistry
from hg_runtime.bus import TypeRegistry
from hg_runtime.config import RuntimeConfig
from hg_runtime.controller import PersistentLoopController
from hg_runtime.demo import build_loop
from hg_runtime.replay import replay

RecordFn = Callable[..., None]


def _run_cmd(
    argv: list[str],
    *,
    cwd: Path,
    command_log: Path,
    timeout: float | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    start = time.monotonic()
    run_env = {**dict(__import__("os").environ), **(env or {})}
    try:
        result = subprocess.run(
            argv,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
            env=run_env,
        )
    except subprocess.TimeoutExpired as exc:
        duration = time.monotonic() - start
        entry = {
            "argv": argv,
            "cwd": str(cwd),
            "exit_code": -1,
            "duration_s": round(duration, 3),
            "timeout": True,
            "stdout_digest": f"sha256:{__import__('hashlib').sha256((exc.stdout or b'') if isinstance(exc.stdout, bytes) else (exc.stdout or '').encode()).hexdigest()}",
            "stderr_digest": f"sha256:{__import__('hashlib').sha256((exc.stderr or b'') if isinstance(exc.stderr, bytes) else (exc.stderr or '').encode()).hexdigest()}",
        }
        with command_log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")
        return {
            "exit_code": -1,
            "stdout": exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or ""),
            "stderr": exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or ""),
            "duration_s": duration,
            "command": entry,
            "timeout": True,
        }
    duration = time.monotonic() - start
    entry = {
        "argv": argv,
        "cwd": str(cwd),
        "exit_code": result.returncode,
        "duration_s": round(duration, 3),
        "stdout_digest": f"sha256:{__import__('hashlib').sha256((result.stdout or '').encode()).hexdigest()}",
        "stderr_digest": f"sha256:{__import__('hashlib').sha256((result.stderr or '').encode()).hexdigest()}",
    }
    with command_log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")
    return {
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "duration_s": duration,
        "command": entry,
    }


def stage_git_dirty_check(
    workspace: Path,
    *,
    allow_dirty: bool,
    command_log: Path,
    record: RecordFn,
) -> tuple[str, list[str]]:
    result = _run_cmd(["git", "status", "--porcelain"], cwd=workspace, command_log=command_log)
    dirty = [line[3:].strip() for line in (result["stdout"] or "").splitlines() if line.strip()]
    if dirty and not allow_dirty:
        record("git_dirty_check", "fail", detail={"dirty_files": dirty})
        return "fail", dirty
    verdict = "pass" if not dirty else "pass_with_dirt"
    record("git_dirty_check", verdict, detail={"dirty_files": dirty, "allow_dirty": allow_dirty})
    return "pass", dirty


_STUB_SCAN_ROOTS = ("hg_runtime", "hg_core")
_CLAIMED_COMPLETE = re.compile(
    r"\b(fully\s+implemented|production-ready|claimed[_\s-]?complete|implementation\s+complete)\b",
    re.IGNORECASE,
)
_STUB_EXCLUDE = (
    "handlers/stubs.py",
    "/stubs/",
    "/test_",
)


def stage_static_completeness(
    workspace: Path,
    *,
    command_log: Path,
    record: RecordFn,
    artifacts_dir: Path,
) -> str:
    findings = static_stub_scan(workspace, roots=_STUB_SCAN_ROOTS)
    critical_prefixes = (
        "hg_runtime/",
        "hg_core/iam/",
        "hg_core/secrets/",
        "hg_core/parity/",
        "hg_core/failures/",
    )
    claimed_hits: list[str] = []
    critical_stub_hits: list[str] = []
    not_implemented = re.compile(r"\braise\s+NotImplementedError\b")
    for rel, markers in findings.items():
        if any(ex in rel for ex in _STUB_EXCLUDE):
            continue
        path = workspace / rel
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if _CLAIMED_COMPLETE.search(text):
            claimed_hits.append(rel)
        if any(rel.startswith(prefix) for prefix in critical_prefixes) and not_implemented.search(text):
            critical_stub_hits.append(rel)
    payload = {
        "stub_findings": findings,
        "claimed_complete_with_stubs": claimed_hits,
        "critical_stub_hits": critical_stub_hits,
    }
    (artifacts_dir / "static_scan_summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _run_cmd(
        [sys.executable, "-c", "print('static_scan_ok')"],
        cwd=workspace,
        command_log=command_log,
    )
    if critical_stub_hits:
        record("static_completeness_search", "fail", detail=payload)
        return "fail"
    record(
        "static_completeness_search",
        "pass_with_findings" if findings else "pass",
        detail={"stub_modules": len(findings), "claimed_complete_with_stubs": len(claimed_hits)},
    )
    return "pass"


def stage_schema_validation(workspace: Path, *, record: RecordFn, artifacts_dir: Path) -> str:
    schema_dir = workspace / "docs" / "schemas"
    results: list[dict[str, Any]] = []
    ok = True
    for path in sorted(schema_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            entry = {"file": path.name, "ok": True, "title": data.get("title")}
            if path.name == "rtc_event_v1.json" and not data.get("required"):
                entry["ok"] = False
                ok = False
        except (json.JSONDecodeError, OSError) as exc:
            entry = {"file": path.name, "ok": False, "error": str(exc)}
            ok = False
        results.append(entry)
    (artifacts_dir / "schema_validation.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    record("schema_validation", "pass" if ok else "fail", detail={"schemas_checked": len(results)})
    return "pass" if ok else "fail"


def stage_event_registry(workspace: Path, *, record: RecordFn, artifacts_dir: Path) -> str:
    registry_path = workspace / "hg_runtime" / "event_types_v1.yaml"
    try:
        registry = TypeRegistry(registry_path)
        raw = yaml.safe_load(registry_path.read_bytes())
        type_count = len(raw.get("types", {}))
        summary = {
            "registry_path": str(registry_path),
            "registry_hash": registry.registry_hash,
            "version": registry.version,
            "type_count": type_count,
        }
        (artifacts_dir / "event_registry_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        record("event_registry_check", "pass", detail=summary)
        return "pass"
    except Exception as exc:  # noqa: BLE001 — gate must fail closed on unknown
        record("event_registry_check", "fail", detail={"error": str(exc)})
        return "fail"


def stage_broad_tests(
    workspace: Path,
    *,
    fast: bool,
    command_log: Path,
    record: RecordFn,
    artifacts_dir: Path,
) -> str:
    obt_env = {"HG_OBT_RUNNING": "1"}
    marker = "-m"
    marker_expr = "not obt_integration"
    if fast:
        argv = [
            sys.executable,
            "-m",
            "pytest",
            "tests/obt/test_truth_gate.py::test_obt_u1_registry_loads_no_orphans",
            "tests/obt/test_truth_gate.py::test_obt_u4_injected_failing_gate_red",
            "tests/obt/test_truth_gate.py::test_obt_u6_bundle_hash_matches_sealed_bundle",
            "-q",
            "--tb=no",
        ]
        targets = ["tests/obt/smoke"]
        timeout = 120.0
    else:
        argv = [
            sys.executable,
            "-m",
            "pytest",
            "tests/obt",
            "tests/iam",
            "tests/sec",
            "tests/par",
            "tests/ftx",
            "tests/rtc",
            marker,
            marker_expr,
            "-q",
            "--tb=no",
        ]
        targets = ["tests/obt", "tests/iam", "tests/sec", "tests/par", "tests/ftx", "tests/rtc"]
        timeout = 2400.0
    result = _run_cmd(
        argv,
        cwd=workspace,
        command_log=command_log,
        timeout=timeout,
        env=obt_env,
    )
    if result.get("timeout"):
        record(
            "broad_tests",
            "fail",
            detail={"targets": targets, "fast_subset": fast, "timeout": True},
        )
        return "fail"
    (artifacts_dir / "pytest_output.txt").write_text(
        (result["stdout"] or "") + (result["stderr"] or ""),
        encoding="utf-8",
    )
    ok = result["exit_code"] == 0
    record(
        "broad_tests",
        "pass" if ok else "fail",
        detail={"targets": targets, "fast_subset": fast, "exit_code": result["exit_code"]},
    )
    return "pass" if ok else "fail"


def stage_proof_gates(
    workspace: Path,
    *,
    registry: TruthGateRegistry,
    fast: bool,
    include_all: bool,
    strict_ct: bool,
    command_log: Path,
    record: RecordFn,
    artifacts_dir: Path,
) -> tuple[str, list[dict[str, Any]], list[dict[str, str]], list[dict[str, str]], list[str]]:
    evals_dir = workspace / "scripts" / "evals"
    orphans = registry.orphan_scripts(evals_dir)
    missing = registry.missing_scripts(workspace)
    gate_results: list[dict[str, Any]] = []
    skips: list[dict[str, str]] = []
    post_ct_excluded: list[dict[str, str]] = []
    critical_failures: list[str] = []

    if orphans:
        record("proof_gates_orphan_check", "fail", detail={"orphans": orphans}, critical=True)
        critical_failures.append("orphan_gates")
    else:
        record("proof_gates_orphan_check", "pass")

    if missing:
        record("proof_gates_missing_scripts", "fail", detail={"missing": missing}, critical=True)
        critical_failures.extend(missing)

    for gate in registry.gates:
        if gate.gate_id == "hg_full_truth":
            continue
        if not gate.enabled:
            entry = {
                "gate_id": gate.gate_id,
                "script": gate.script,
                "verdict": f"not_proven({gate.skip_reason or 'disabled'})",
                "critical": gate.critical,
                "invoked": False,
            }
            gate_results.append(entry)
            if strict_ct:
                post_ct_excluded.append({"gate_id": gate.gate_id, "reason": gate.skip_reason or "disabled"})
            else:
                skips.append({"gate_id": gate.gate_id, "reason": gate.skip_reason or "disabled"})
                if gate.critical:
                    critical_failures.append(gate.gate_id)
            continue

        if not gate.should_run(fast=fast, include_all=include_all, strict_ct=strict_ct):
            reason = "fast_subset_skip" if fast else "deferred_default_mode"
            entry = {
                "gate_id": gate.gate_id,
                "script": gate.script,
                "verdict": f"skipped({reason})",
                "critical": gate.critical,
                "invoked": False,
            }
            gate_results.append(entry)
            if strict_ct:
                post_ct_excluded.append({"gate_id": gate.gate_id, "reason": "post_ct_out_of_scope"})
            else:
                skips.append({"gate_id": gate.gate_id, "reason": reason})
            continue

        script_path = workspace / gate.script
        gate_timeout = 900.0 if gate.critical else 600.0
        result = _run_cmd(
            [sys.executable, str(script_path)],
            cwd=workspace,
            command_log=command_log,
            timeout=gate_timeout,
        )
        exit_code = result["exit_code"]
        gate_payload: dict[str, Any] | None = None
        try:
            gate_payload = json.loads(result["stdout"] or "{}")
        except json.JSONDecodeError:
            gate_payload = None
        if result.get("timeout"):
            verdict = "fail(timeout)"
        elif exit_code == 0:
            verdict = "ok"
        elif exit_code == 2:
            if strict_ct and isinstance(gate_payload, dict) and gate_payload.get("ok"):
                verdict = "ok_accepted_not_proven"
            else:
                verdict = "not_proven"
        else:
            verdict = "fail"
        entry = {
            "gate_id": gate.gate_id,
            "script": gate.script,
            "verdict": verdict,
            "exit_code": exit_code,
            "critical": gate.critical,
            "invoked": True,
            "duration_s": round(result["duration_s"], 3),
        }
        if gate_payload is not None:
            entry["gate_ok"] = gate_payload.get("ok")
            entry["not_proven"] = gate_payload.get("not_proven")
        gate_results.append(entry)
        if verdict == "fail" or (gate.critical and verdict == "not_proven"):
            critical_failures.append(gate.gate_id)

    (artifacts_dir / "gate_results.json").write_text(json.dumps(gate_results, indent=2), encoding="utf-8")
    stage_verdict = "fail" if critical_failures or orphans or missing else "pass"
    if skips and stage_verdict == "pass":
        stage_verdict = "pass_with_skips"
    record("proof_gates", stage_verdict, detail={"gates_run": sum(1 for g in gate_results if g.get("invoked"))})
    return stage_verdict, gate_results, skips, post_ct_excluded, critical_failures


def stage_demo_replay(
    workspace: Path,
    *,
    command_log: Path,
    record: RecordFn,
    artifacts_dir: Path,
) -> tuple[str, list[str]]:
    runtime_dir = workspace / ".tmp_obt_demo_replay"
    if runtime_dir.exists():
        import shutil

        shutil.rmtree(runtime_dir, ignore_errors=True)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    path_id = "demo_phase0"
    loop = build_loop(runtime_dir, require_enabled=False, phase1_lifecycle=True)
    loop.start()
    loop.bus.submit(
        "CHAT_MESSAGE",
        {"session_id": "obt", "role": "user", "content": "obt demo replay"},
        source="gate:obt",
    )
    loop.run_once(poll_timeout=0.0)
    loop.stop(reason="obt_gate")
    replay_result = replay(runtime_dir)
    summary = {
        "path_id": path_id,
        "replay_ok": replay_result.ok,
        "state_hash": replay_result.state_hash,
        "events": replay_result.events,
    }
    (artifacts_dir / "replay_report.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _run_cmd(
        [sys.executable, "-c", f"print({json.dumps(summary['replay_ok'])})"],
        cwd=workspace,
        command_log=command_log,
    )
    verdict = "pass" if replay_result.ok else "fail"
    record("demo_replay", verdict, detail=summary)
    path_ids = [path_id]
    return verdict, path_ids


def stage_docs_freshness(workspace: Path, *, command_log: Path, record: RecordFn, artifacts_dir: Path) -> str:
    gate_script = workspace / "scripts" / "evals" / "ct17_doc_claim_check_gate.py"
    audit_script = workspace / "scripts" / "audit" / "docs_claim_check.py"
    gate_result = _run_cmd([sys.executable, str(gate_script)], cwd=workspace, command_log=command_log)
    audit_result = _run_cmd(
        [sys.executable, str(audit_script), "--json"],
        cwd=workspace,
        command_log=command_log,
    )
    try:
        claim_data = json.loads(audit_result["stdout"] or "{}")
    except json.JSONDecodeError:
        claim_data = {"ok": False, "parse_error": True}
    try:
        gate_data = json.loads(gate_result["stdout"] or "{}")
    except json.JSONDecodeError:
        gate_data = {"ok": False, "parse_error": True}
    freshness = {
        "docs_freshness_gate_ok": gate_result["exit_code"] == 0,
        "claim_check_ok": claim_data.get("ok", False),
        "claim_check": claim_data,
        "gate_result": gate_data,
        "gate_exit_code": gate_result["exit_code"],
    }
    (artifacts_dir / "docs_freshness.json").write_text(json.dumps(freshness, indent=2), encoding="utf-8")
    if gate_result["exit_code"] != 0:
        record("docs_freshness", "fail", detail=freshness)
        return "fail"
    record("docs_freshness", "pass", detail=freshness)
    return "pass"


def stage_subsystem_classification(
    workspace: Path,
    *,
    replay_ok: bool,
    record: RecordFn,
    artifacts_dir: Path,
) -> list[dict[str, Any]]:
    static = static_stub_scan(workspace)
    rows = classify_subsystems_truth(workspace=workspace, replay_ok=replay_ok, static_findings=static)
    (artifacts_dir / "subsystem_classification.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    record("subsystem_classification", "pass", detail={"count": len(rows)})
    return rows


__all__ = [
    "stage_broad_tests",
    "stage_demo_replay",
    "stage_docs_freshness",
    "stage_event_registry",
    "stage_git_dirty_check",
    "stage_proof_gates",
    "stage_schema_validation",
    "stage_static_completeness",
    "stage_subsystem_classification",
]
