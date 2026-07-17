"""
Admin proof service: run proofs via API, serve index and run logs.
Routes under /v1/admin/proofs (admin key required). No mocks.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse

from hg_gateway.auth import require_admin


def _proofs_workspace() -> Path:
    """Workspace root for docs/proofs and scripts/run_proofs.py."""
    workspace = Path(os.environ.get("HG_WORKSPACE", "") or ".").resolve()
    if not workspace.is_dir():
        try:
            from hg_lib.config import get_workspace_root
            workspace = (get_workspace_root() or Path.cwd())
        except Exception:
            workspace = Path.cwd()
    return workspace


def _proofs_out_dir() -> Path:
    return _proofs_workspace() / "docs" / "proofs" / "out"


def _run_proofs_script() -> Path:
    return _proofs_workspace() / "scripts" / "run_proofs.py"


TRUST_DEMO_LABELS = (
    "investor_demo",
    "drift_quarantine_demo",
    "prompt_injection_hardening_demo",
    "soak_trust_demo",
)


def _parse_iso_timestamp(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _run_age_hours(summary: Dict[str, Any] | None) -> float | None:
    if not isinstance(summary, dict):
        return None
    stamp = _parse_iso_timestamp(summary.get("ended_at") or summary.get("started_at"))
    if stamp is None:
        return None
    return round((datetime.now(timezone.utc) - stamp).total_seconds() / 3600, 3)


def _freshness_state(age_hours: float | None, summary_exists: bool) -> str:
    if not summary_exists:
        return "missing"
    if age_hours is None:
        return "unknown"
    if age_hours <= 24:
        return "fresh"
    if age_hours <= 168:
        return "recent"
    return "stale"


def _trust_state(checks_passed: bool, freshness: str, provenance_available: bool, review_turnaround_seconds: float | None) -> str:
    if not checks_passed:
        return "degraded"
    if freshness == "stale":
        return "stale"
    if not provenance_available:
        return "degraded"
    if isinstance(review_turnaround_seconds, (int, float)) and review_turnaround_seconds > 24 * 3600:
        return "watch"
    return "healthy"


def _recovery_state(label: str, summary: Dict[str, Any] | None) -> str:
    if label != "soak_trust_demo":
        return "not_applicable"
    if not isinstance(summary, dict):
        return "missing"
    required = ("retry_recovery_ok", "restart_persistence_ok", "artifact_cleanup_ok", "retention_job_ok")
    if all(bool(summary.get(field)) for field in required):
        return "recovered"
    if any(summary.get(field) is not None for field in required):
        return "needs_attention"
    return "missing"


def _proof_metrics(index: Dict[str, Any]) -> Dict[str, Any]:
    latest = index.get("latest") if isinstance(index.get("latest"), dict) else {}
    runs = index.get("runs") if isinstance(index.get("runs"), list) else []
    latest_by_label: dict[str, str] = {}
    for label in TRUST_DEMO_LABELS:
        folder = latest.get(label)
        if isinstance(folder, str) and folder.strip():
            latest_by_label[label] = folder

    demo_runs: list[dict[str, Any]] = []
    success_count = 0
    provenance_count = 0
    turnaround_values: list[float] = []
    age_values: list[float] = []
    failure_recovery_hits = 0

    for label, folder in latest_by_label.items():
        run_dir = Path(folder)
        run_id = run_dir.name
        summary_path = run_dir / "summary.json"
        summary: Dict[str, Any] | None = None
        if summary_path.exists():
            try:
                loaded = json.loads(summary_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    summary = loaded
            except (json.JSONDecodeError, OSError):
                summary = None
        passed = bool(summary.get("checks_passed")) if isinstance(summary, dict) else False
        if passed:
            success_count += 1
        provenance_available = bool(summary.get("provenance_available")) if isinstance(summary, dict) else False
        if provenance_available:
            provenance_count += 1
        turnaround = summary.get("review_turnaround_seconds") if isinstance(summary, dict) else None
        if isinstance(turnaround, (int, float)):
            turnaround_values.append(float(turnaround))
        age = _run_age_hours(summary)
        if age is not None:
            age_values.append(age)
        freshness = _freshness_state(age, summary is not None)
        recovery_state = _recovery_state(label, summary)
        trust_state = _trust_state(passed, freshness, provenance_available, turnaround if isinstance(turnaround, (int, float)) else None)
        if label == "soak_trust_demo" and recovery_state == "recovered":
            failure_recovery_hits += 1
        demo_runs.append(
            {
                "label": label,
                "run_id": run_id,
                "folder": folder,
                "checks_passed": passed,
                "status": trust_state,
                "freshness_state": freshness,
                "freshness_label": "fresh" if freshness == "fresh" else "recent" if freshness == "recent" else "stale" if freshness == "stale" else "unknown" if freshness == "unknown" else "missing",
                "age_hours": age,
                "provenance_available": provenance_available,
                "provenance_label": "available" if provenance_available else "missing",
                "review_turnaround_seconds": turnaround,
                "review_turnaround_label": f"{round(float(turnaround), 1)}s" if isinstance(turnaround, (int, float)) else "—",
                "recovery_state": recovery_state,
                "recovery_label": "recovered" if recovery_state == "recovered" else "needs attention" if recovery_state == "needs_attention" else "n/a" if recovery_state == "not_applicable" else "missing",
                "continuity_status": (summary.get("trust_metrics") or {}).get("continuity_quality", {}).get("status") if isinstance(summary, dict) else None,
                "continuity_quality_score": (summary.get("trust_metrics") or {}).get("continuity_quality", {}).get("quality_score") if isinstance(summary, dict) else None,
                "evidence_files": [
                    {"label": "summary", "path": "summary.json"},
                    {"label": "checks", "path": "checks.json"},
                    {"label": "logs", "path": "artifacts/logs/run.log"},
                ],
                "summary": summary,
            }
        )

    from operator_console.server.app.services.continuity_incident_summary import build_continuity_quality_overview
    from operator_console.server.app.services.entities_service import list_entities

    continuity_quality = build_continuity_quality_overview(list_entities())
    trust = {
        "demo_success_rate": round(success_count / max(1, len(latest_by_label)), 3),
        "backlog_age_hours": round(max(age_values) if age_values else 0.0, 3),
        "review_turnaround_seconds": round(sum(turnaround_values) / max(1, len(turnaround_values)), 3) if turnaround_values else None,
        "provenance_availability_rate": round(provenance_count / max(1, len(latest_by_label)), 3),
        "failure_recovery_rate": round(failure_recovery_hits / max(1, 1), 3),
        "continuity_quality": continuity_quality,
        "canonical_demos": demo_runs,
    }
    overall_status = "healthy"
    if success_count < len(latest_by_label):
        overall_status = "degraded"
    elif trust["backlog_age_hours"] > 72:
        overall_status = "stale"
    elif trust["provenance_availability_rate"] < 1:
        overall_status = "watch"
    trust["browser_summary"] = {
        "status": overall_status,
        "status_label": overall_status,
        "freshness_state": "fresh" if trust["backlog_age_hours"] <= 24 else "recent" if trust["backlog_age_hours"] <= 72 else "stale",
        "summary": (
            f"{success_count}/{len(latest_by_label)} demos passing; "
            f"backlog age {trust['backlog_age_hours']:.1f}h; "
            f"provenance {int(trust['provenance_availability_rate'] * 100)}%; "
            f"continuity {continuity_quality.get('status') or 'missing'}"
        ),
        "evidence_links": {
            "timeline": "#/timeline",
            "recovery": "#/recovery",
            "proofs": "#/proofs/run",
        },
    }
    trust["summary"] = (
        f"{success_count}/{len(latest_by_label)} demos passing; "
        f"backlog age {trust['backlog_age_hours']:.1f}h; "
        f"provenance {int(trust['provenance_availability_rate'] * 100)}%; "
        f"continuity {continuity_quality.get('status') or 'missing'}"
    )
    return trust


# Allowed single-run scenario labels (must match scripts/run_proofs.py ALL_SCENARIOS).
ALLOWED_LABELS = frozenset({
    "health",
    "docs_summarize_10_to_docx",
    "web_research_to_docx",
    "swarm_weather_10_real",
    "weather_sweep_10",
    "4claw_posts_3",
    "ticket_triage_5",
    "persona_hopper_factcheck",
    "investor_demo",
    "drift_quarantine_demo",
    "prompt_injection_hardening_demo",
    "soak_trust_demo",
    "weather_network_failure",
    "4claw_approval_denied",
    "prompt_injection_blocked",
    "multitenant_branding_demo",
    "superadmin_impersonation_demo",
    "tenant_admin_principals_demo",
    "signal_pipeline_demo",
    "steering_profiles_demo",
    "rules_trigger_demo",
    "dashboards_screenshot_demo",
})


router = APIRouter(prefix="/admin/proofs", tags=["admin-proofs"], dependencies=[Depends(require_admin)])


@router.post("/run")
def admin_proofs_run(
    request: Request,
    body: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Start a proof run. Body: { "label" or "scenario": string, "params"?: object }.
    Returns { run_id, folder, status }. Run_id is the folder basename.
    """
    label = (body.get("label") or body.get("scenario") or "").strip()
    if not label:
        raise HTTPException(status_code=400, detail="body must contain 'label' or 'scenario'")
    if label not in ALLOWED_LABELS:
        raise HTTPException(
            status_code=400,
            detail="Unknown scenario %r; allowed: %s" % (label, ", ".join(sorted(ALLOWED_LABELS))),
        )

    workspace = _proofs_workspace()
    run_proofs = _run_proofs_script()
    if not run_proofs.is_file():
        raise HTTPException(
            status_code=503,
            detail="Proof runner not found at %s; set HG_WORKSPACE to workspace root" % run_proofs,
        )

    out_root = _proofs_out_dir()
    out_root.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_dir = out_root / f"{ts}_{label}"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "artifacts" / "logs").mkdir(parents=True, exist_ok=True)
    (run_dir / "artifacts" / "screenshots").mkdir(parents=True, exist_ok=True)

    params = body.get("params") or {}
    use_fixtures = bool(params.get("use_fixtures"))
    base_url = str(request.base_url).rstrip("/")
    api_key = (os.environ.get("HG_GATEWAY_API_KEY") or "").strip()
    admin_key = (os.environ.get("HG_GATEWAY_ADMIN_KEY") or "").strip()
    log_path = run_dir / "artifacts" / "logs" / "run.log"
    cmd = [
        sys.executable,
        str(run_proofs),
        "--outdir",
        str(run_dir),
        "--label",
        label,
        "--base-url",
        base_url,
        "--api-key",
        api_key or "no-key",
        *(["--admin-key", admin_key] if admin_key else []),
    ]
    if use_fixtures:
        cmd.append("--use-fixtures")
    with log_path.open("w", encoding="utf-8") as log_file:
        proc = subprocess.Popen(
            cmd,
            cwd=str(workspace),
            stdout=log_file,
            stderr=subprocess.STDOUT,
            env={**os.environ},
        )
    run_id = run_dir.name
    return {
        "run_id": run_id,
        "folder": str(run_dir),
        "status": "running",
        "pid": proc.pid,
    }


@router.get("/index")
def admin_proofs_index() -> Dict[str, Any]:
    """Return contents of docs/proofs/index.json."""
    idx_path = _proofs_workspace() / "docs" / "proofs" / "index.json"
    if not idx_path.exists():
        return {"latest": {}, "runs": [], "metrics": _proof_metrics({"latest": {}, "runs": []})}
    try:
        index = json.loads(idx_path.read_text(encoding="utf-8"))
        if not isinstance(index, dict):
            index = {"latest": {}, "runs": []}
    except (json.JSONDecodeError, OSError):
        index = {"latest": {}, "runs": []}
    index["metrics"] = _proof_metrics(index)
    return index


@router.get("/runs/{run_id}")
def admin_proofs_run_status(run_id: str) -> Dict[str, Any]:
    """Return status and metadata for a run. run_id is the folder basename."""
    out_root = _proofs_out_dir()
    run_dir = out_root / run_id
    if not run_dir.is_dir():
        raise HTTPException(status_code=404, detail="Run not found: %s" % run_id)
    summary_path = run_dir / "summary.json"
    status = "running"
    checks_passed: Optional[bool] = None
    if summary_path.exists():
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            status = "completed"
            checks_passed = summary.get("checks_passed")
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "run_id": run_id,
        "folder": str(run_dir),
        "status": status,
        "checks_passed": checks_passed,
    }


@router.get("/runs/{run_id}/logs")
def admin_proofs_run_logs(run_id: str) -> StreamingResponse:
    """Stream run log file as SSE (event: log, data: line)."""
    out_root = _proofs_out_dir()
    run_dir = out_root / run_id
    if not run_dir.is_dir():
        raise HTTPException(status_code=404, detail="Run not found: %s" % run_id)
    log_path = run_dir / "artifacts" / "logs" / "run.log"
    if not log_path.exists():
        def empty():
            yield "event: log\ndata: (no log yet)\n\n"
        return StreamingResponse(empty(), media_type="text/event-stream")
    from hg_gateway.redaction import redact_sensitive
    def stream():
        with log_path.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.rstrip("\n\r")
                if line.strip():
                    try:
                        out = redact_sensitive({"line": line})
                        safe = (out.get("line") if isinstance(out, dict) else line)[:2000]
                    except Exception:
                        safe = line[:2000]
                    yield "event: log\ndata: %s\n\n" % json.dumps({"line": safe}, ensure_ascii=False)
    return StreamingResponse(stream(), media_type="text/event-stream")


@router.get("/runs/{run_id}/artifacts")
def admin_proofs_run_artifacts(run_id: str) -> Dict[str, Any]:
    """List all files in the run folder (recursive)."""
    out_root = _proofs_out_dir()
    run_dir = out_root / run_id
    if not run_dir.is_dir():
        raise HTTPException(status_code=404, detail="Run not found: %s" % run_id)
    entries: list[Dict[str, Any]] = []
    for p in run_dir.rglob("*"):
        if p.is_file() and not p.name.startswith(".") and p.name != "cancel_requested":
            rel = p.relative_to(run_dir)
            entries.append({"path": str(rel).replace("\\", "/"), "size": p.stat().st_size})
    entries.sort(key=lambda x: x["path"])
    return {"run_id": run_id, "files": entries}


@router.get("/runs/{run_id}/files/{file_path:path}")
def admin_proofs_run_file(run_id: str, file_path: str):
    """Download a file from the run folder. file_path is relative; no .. allowed."""
    if ".." in file_path or file_path.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid path")
    out_root = _proofs_out_dir()
    run_dir = out_root / run_id
    if not run_dir.is_dir():
        raise HTTPException(status_code=404, detail="Run not found: %s" % run_id)
    full = (run_dir / file_path).resolve()
    if not full.is_file() or not str(full).startswith(str(run_dir.resolve())):
        raise HTTPException(status_code=404, detail="File not found")
    media_types = {".md": "text/markdown", ".json": "application/json", ".txt": "text/plain", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
    media_type = media_types.get(full.suffix.lower())
    return FileResponse(full, filename=full.name, media_type=media_type)


@router.post("/runs/{run_id}/cancel")
def admin_proofs_run_cancel(run_id: str) -> Dict[str, str]:
    """Best-effort cancel: write cancel_requested flag in run folder. Runner may check it."""
    out_root = _proofs_out_dir()
    run_dir = out_root / run_id
    if not run_dir.is_dir():
        raise HTTPException(status_code=404, detail="Run not found: %s" % run_id)
    (run_dir / "cancel_requested").write_text(
        datetime.now(timezone.utc).isoformat(),
        encoding="utf-8",
    )
    return {"run_id": run_id, "status": "cancel_requested"}
