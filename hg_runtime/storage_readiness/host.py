"""Host storage readiness — Docker-canonical proof with honest host adapter."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[2]
CACHE = WORKSPACE / ".hg-local/stage_status/storage_readiness.json"
CANONICAL_PROOFS = WORKSPACE / "docs/proofs/storage_artifact_vector/STORAGE-HARDENED"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _latest_green_proof() -> Path | None:
    if not CANONICAL_PROOFS.exists():
        return None
    candidates = sorted(CANONICAL_PROOFS.iterdir(), reverse=True)
    for d in candidates:
        manifest = d / "manifest.json"
        if manifest.exists():
            data = json.loads(manifest.read_text(encoding="utf-8"))
            if data.get("ok") is True:
                return d
    return None


def _verify_proof_dir(proof_dir: Path) -> bool:
    manifest = proof_dir / "manifest.json"
    summary = proof_dir / "artifacts" / "summary.json"
    if not manifest.exists():
        return False
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if data.get("ok") is not True:
        return False
    if summary.exists():
        s = json.loads(summary.read_text(encoding="utf-8"))
        return bool(s.get("db_healthy", {}).get("healthy")) and bool(
            s.get("pgvector_available", {}).get("available")
        )
    return True


def _docker_available() -> bool:
    """Fast preflight: is the Docker CLI + daemon reachable? Never blocks long."""
    try:
        proc = subprocess.run(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            capture_output=True, text=True, timeout=5, check=False)
        return proc.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def _run_docker_storage_gate(workspace: Path) -> tuple[bool, dict[str, Any]]:
    # Preflight so a missing/unresponsive Docker daemon fails fast instead of
    # blocking on the 600s `docker compose run` (e.g. CI images without Docker).
    if not _docker_available():
        return False, {"ok": False, "source": "docker_unavailable",
                       "detail": "docker CLI/daemon not reachable for the "
                                 "storage-readiness probe"}
    proc = subprocess.run(
        [
            "docker",
            "compose",
            "run",
            "--rm",
            "hg-proof",
            "python",
            "scripts/evals/storage_artifact_vector_final_gate.py",
        ],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
        timeout=600,
    )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = {"ok": False, "detail": (proc.stdout or proc.stderr)[-2000:]}
    ok = proc.returncode == 0 and payload.get("ok") is True
    payload["source"] = "docker_compose_hg_proof"
    payload["returncode"] = proc.returncode
    return ok, payload


def _run_host_storage_gate(workspace: Path) -> tuple[bool, dict[str, Any]]:
    proc = subprocess.run(
        [sys.executable, "scripts/evals/storage_artifact_vector_final_gate.py"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
        timeout=600,
    )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = {"ok": False, "detail": (proc.stdout or proc.stderr)[-2000:]}
    ok = proc.returncode == 0 and payload.get("ok") is True
    payload["source"] = "host_direct"
    return ok, payload


def resolve_storage_readiness(
    workspace: Path | None = None,
    *,
    refresh: bool = False,
    prefer_docker: bool = True,
) -> tuple[bool, dict[str, Any]]:
    """Return (ok, payload). Canonical path is Docker hg-proof when host DSN absent."""
    ws = workspace or WORKSPACE
    dsn = os.environ.get("HG_STORAGE_POSTGRES_DSN", "").strip()
    # Advisory-only smoke paths (dev boot, CI unit tests) must not spin up the live
    # Docker/host storage gate — that runs a full container gate (minutes). When set,
    # resolve from the canonical proof reference / cache instead, quickly + honestly.
    skip_live_gate = os.environ.get("HG_STORAGE_READINESS_SKIP_GATE", "").strip().lower() \
        in ("1", "true", "yes")

    if not refresh and CACHE.exists():
        cached = json.loads(CACHE.read_text(encoding="utf-8"))
        proof_dir = cached.get("proof_dir")
        if cached.get("ok") and proof_dir and _verify_proof_dir(Path(proof_dir)):
            return True, cached

    ok = False
    payload: dict[str, Any] = {
        "schema": "storage-readiness",
        "timestamp_utc": _utc_now(),
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }

    if dsn and not skip_live_gate:
        ok, gate_payload = _run_host_storage_gate(ws)
        payload["source"] = "host_dsn"
        payload["gate"] = gate_payload
    elif prefer_docker and not skip_live_gate:
        ok, gate_payload = _run_docker_storage_gate(ws)
        payload["gate"] = gate_payload
        payload["source"] = gate_payload.get("source", "docker")
    else:
        proof = _latest_green_proof()
        if proof and _verify_proof_dir(proof):
            ok = True
            payload["source"] = "canonical_proof_ref"
            payload["proof_dir"] = str(proof)
        else:
            ok = False
            payload["source"] = "unavailable"
            payload["reason"] = "HG_STORAGE_POSTGRES_DSN unset and no verified canonical proof"

    if ok:
        proof_dir = payload.get("gate", {}).get("proof_dir") or payload.get("proof_dir")
        if not proof_dir:
            latest = _latest_green_proof()
            proof_dir = str(latest) if latest else None
        payload["ok"] = True
        payload["verdict"] = "GREEN_STORAGE_PREP_READY"
        payload["proof_dir"] = proof_dir
    else:
        payload["ok"] = False
        payload["verdict"] = "RED_STORAGE_NOT_READY"
        if not dsn:
            payload["host_dsn_absent"] = True
            payload["classification"] = "gate_invocation_mismatch_windows_host_no_postgres_dsn"

    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return ok, payload


__all__ = ["resolve_storage_readiness"]
