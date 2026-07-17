from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from hg_gateway.db import get_connection
from hg_core.receipts import create_sealed_receipt, receipt_is_fresh


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _runtime_environment() -> str:
    return (os.environ.get("HG_ENV") or "demo").strip().lower() or "demo"


def _env_truthy(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def demo_live_actions_enabled() -> bool:
    return _env_truthy("HG_DEMO_MODE") and _env_truthy("HG_DEMO_LIVE_ACTIONS_ENABLED")


def demo_backup_required() -> bool:
    explicit = (os.environ.get("HG_DEMO_BACKUP_REQUIRED") or "").strip().lower()
    if explicit in {"0", "false", "off", "no"}:
        return False
    if explicit in {"1", "true", "on", "yes"}:
        return True
    return not demo_live_actions_enabled()


def demo_backup_max_age_hours() -> float:
    raw = (os.environ.get("HG_DEMO_BACKUP_MAX_AGE_HOURS") or "168").strip()
    try:
        return max(1.0, float(raw))
    except ValueError:
        return 168.0


def release_gate_enforced() -> bool:
    explicit = (os.environ.get("HG_RELEASE_GATE_ENFORCED") or "").strip().lower()
    if explicit in {"0", "false", "off", "no"}:
        return False
    if explicit in {"1", "true", "on", "yes"}:
        return True
    return not demo_live_actions_enabled()


def _backups_root() -> Path:
    """Backups dir relative to workspace root so API/worker see it regardless of cwd."""
    workspace = os.environ.get("HG_WORKSPACE", "").strip()
    if workspace:
        return Path(workspace) / "backups"
    try:
        from hg_lib.config import get_workspace_root
        return get_workspace_root() / "backups"
    except Exception:
        return Path("backups")


def _latest_demo_backup_ok(max_age_hours: float) -> bool:
    root = _backups_root()
    if not root.exists():
        return False
    candidates = sorted((path for path in root.glob("demo-db-*") if path.is_dir()), key=lambda item: item.name, reverse=True)
    if not candidates:
        return False
    latest = candidates[0]
    try:
        created = datetime.strptime(latest.name.replace("demo-db-", ""), "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return False
    return created >= datetime.now(timezone.utc) - timedelta(hours=max_age_hours)


def ensure_demo_backup_stub(*, max_age_hours: float | None = None) -> str | None:
    """Create a lightweight demo backup marker when none exists within the freshness window."""
    hours = max_age_hours if max_age_hours is not None else demo_backup_max_age_hours()
    if _latest_demo_backup_ok(hours):
        return None
    root = _backups_root()
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = root / f"demo-db-{stamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    (backup_dir / "README.txt").write_text(
        "Demo backup marker created automatically for release-gate freshness checks.\n",
        encoding="utf-8",
    )
    return str(backup_dir)


def list_benchmark_sets() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM gate_benchmark_sets ORDER BY updated_at DESC, title ASC").fetchall()
    return [dict(row) for row in rows]


def create_benchmark_set(*, workflow_family: str, title: str, description: str | None, weights: dict[str, float]) -> dict[str, Any]:
    with get_connection() as conn:
        encoded_weights = json.dumps(weights, sort_keys=True)
        existing = conn.execute(
            """
            SELECT benchmark_set_id, created_at
            FROM gate_benchmark_sets
            WHERE workflow_family = ? AND title = ? AND COALESCE(description, '') = ? AND weights_json = ? AND active = 1
            ORDER BY updated_at DESC LIMIT 1
            """,
            (workflow_family, title, description or "", encoded_weights),
        ).fetchone()
        if existing:
            return {"benchmark_set_id": str(existing["benchmark_set_id"]), "created_at": str(existing["created_at"])}
        benchmark_set_id = str(uuid.uuid4())
        now = _iso_now()
        conn.execute(
            """
            INSERT INTO gate_benchmark_sets (benchmark_set_id, workflow_family, title, description, weights_json, active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (benchmark_set_id, workflow_family, title, description, encoded_weights, 1, now, now),
        )
    return {"benchmark_set_id": benchmark_set_id, "created_at": now}


def record_benchmark_run(*, benchmark_set_id: str, workflow_family: str, candidate_label: str, observations: dict[str, Any], actor_id: str | None = None, tenant_id: str = "default") -> dict[str, Any]:
    benchmark_run_id = str(uuid.uuid4())
    created_at = _iso_now()
    receipt = create_sealed_receipt(
        tenant_id=tenant_id,
        receipt_kind="gate_benchmark_run",
        subject_kind="benchmark_run",
        subject_id=benchmark_run_id,
        actor_id=actor_id,
        gate_family=workflow_family,
        payload={"benchmark_set_id": benchmark_set_id, "candidate_label": candidate_label, "observations": observations},
    )
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO gate_benchmark_runs (benchmark_run_id, benchmark_set_id, workflow_family, candidate_label, observations_json, actor_id, created_at, receipt_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (benchmark_run_id, benchmark_set_id, workflow_family, candidate_label, json.dumps(observations, sort_keys=True), actor_id, created_at, receipt["receipt_id"]),
        )
    return {"benchmark_run_id": benchmark_run_id, "receipt_id": receipt["receipt_id"], "created_at": created_at}


def _weighted_score(weights: dict[str, float], observations: dict[str, Any]) -> tuple[float, dict[str, float]]:
    breakdown: dict[str, float] = {}
    total_weight = 0.0
    total_score = 0.0
    for key, raw_weight in weights.items():
        weight = float(raw_weight)
        score = float(observations.get(key, 0.0) or 0.0)
        breakdown[key] = score
        total_weight += weight
        total_score += score * weight
    return (total_score / total_weight if total_weight else 0.0, breakdown)


def evaluate_benchmark_run(*, benchmark_run_id: str, policy_version_id: str | None = None, tenant_id: str = "default") -> dict[str, Any]:
    with get_connection() as conn:
        run_row = conn.execute("SELECT * FROM gate_benchmark_runs WHERE benchmark_run_id = ?", (benchmark_run_id,)).fetchone()
        if not run_row:
            raise KeyError(benchmark_run_id)
        set_row = conn.execute("SELECT * FROM gate_benchmark_sets WHERE benchmark_set_id = ?", (run_row["benchmark_set_id"],)).fetchone()
        if not set_row:
            raise KeyError(str(run_row["benchmark_set_id"]))
    observations = json.loads(str(run_row["observations_json"]))
    weights = json.loads(str(set_row["weights_json"]))
    weighted_score, breakdown = _weighted_score(weights, observations)
    p_h = float(observations.get("p_h", 0.0) or 0.0)
    p_ai = float(observations.get("p_ai", 0.0) or 0.0)
    p_h_odei = float(observations.get("p_h_odei", observations.get("p_h+odei", 0.0)) or 0.0)
    sigma = p_h_odei - max(p_h, p_ai)
    verdict = "eligible" if sigma >= 0.05 and weighted_score >= 0.7 else "watch" if sigma >= 0.0 and weighted_score >= 0.5 else "blocked"
    evaluation_id = str(uuid.uuid4())
    created_at = _iso_now()
    receipt = create_sealed_receipt(
        tenant_id=tenant_id,
        receipt_kind="gate_evaluation",
        subject_kind="benchmark_run",
        subject_id=benchmark_run_id,
        gate_family=str(run_row["workflow_family"]),
        policy_version_id=policy_version_id,
        payload={
            "benchmark_run_id": benchmark_run_id,
            "p_h": p_h,
            "p_ai": p_ai,
            "p_h_odei": p_h_odei,
            "sigma": sigma,
            "weighted_score": weighted_score,
            "verdict": verdict,
            "breakdown": breakdown,
        },
    )
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO gate_evaluations (
                evaluation_id, benchmark_run_id, workflow_family, policy_version_id,
                p_h, p_ai, p_h_odei, sigma, weighted_score, verdict, breakdown_json, created_at, receipt_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                evaluation_id,
                benchmark_run_id,
                run_row["workflow_family"],
                policy_version_id,
                p_h,
                p_ai,
                p_h_odei,
                sigma,
                weighted_score,
                verdict,
                json.dumps(breakdown, sort_keys=True),
                created_at,
                receipt["receipt_id"],
            ),
        )
    return {"evaluation_id": evaluation_id, "verdict": verdict, "sigma": sigma, "weighted_score": weighted_score, "receipt_id": receipt["receipt_id"]}


def list_gate_evaluations(*, workflow_family: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    sql = "SELECT * FROM gate_evaluations WHERE 1=1"
    params: list[Any] = []
    if workflow_family:
        sql += " AND workflow_family = ?"
        params.append(workflow_family)
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(row) for row in rows]


def create_release_verdict(*, workflow_family: str, target_kind: str, target_id: str, evaluation_id: str | None, verdict: str, reason: str | None = None, stale_after_hours: float = 24.0, tenant_id: str = "default") -> dict[str, Any]:
    created_at = _iso_now()
    stale_after_ts = (datetime.now(timezone.utc) + timedelta(hours=stale_after_hours)).isoformat().replace("+00:00", "Z")
    with get_connection() as conn:
        existing = conn.execute(
            """
            SELECT release_verdict_id, receipt_id, stale_after_ts
            FROM gate_release_verdicts
            WHERE workflow_family = ? AND target_kind = ? AND target_id = ? AND environment = ? AND COALESCE(evaluation_id, '') = ? AND verdict = ? AND COALESCE(reason, '') = ?
            ORDER BY created_at DESC LIMIT 1
            """,
            (workflow_family, target_kind, target_id, _runtime_environment(), evaluation_id or "", verdict, reason or ""),
        ).fetchone()
        if existing and str(existing["stale_after_ts"] or "") > created_at:
            return {
                "release_verdict_id": str(existing["release_verdict_id"]),
                "receipt_id": str(existing["receipt_id"]) if existing["receipt_id"] else None,
                "stale_after_ts": str(existing["stale_after_ts"]),
            }
    release_verdict_id = str(uuid.uuid4())
    receipt = create_sealed_receipt(
        tenant_id=tenant_id,
        receipt_kind="release_verdict",
        subject_kind=target_kind,
        subject_id=target_id,
        gate_family=workflow_family,
        payload={
            "workflow_family": workflow_family,
            "target_kind": target_kind,
            "target_id": target_id,
            "evaluation_id": evaluation_id,
            "verdict": verdict,
            "reason": reason,
            "environment": _runtime_environment(),
            "stale_after_ts": stale_after_ts,
        },
    )
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO gate_release_verdicts (
                release_verdict_id, workflow_family, target_kind, target_id, environment,
                evaluation_id, verdict, reason, stale_after_ts, created_at, receipt_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (release_verdict_id, workflow_family, target_kind, target_id, _runtime_environment(), evaluation_id, verdict, reason, stale_after_ts, created_at, receipt["receipt_id"]),
        )
    return {"release_verdict_id": release_verdict_id, "receipt_id": receipt["receipt_id"], "stale_after_ts": stale_after_ts}


def enforce_release_gate(*, workflow_family: str, target_kind: str = "workflow", target_id: str | None = None, max_age_hours: float = 24.0) -> dict[str, Any]:
    final_target_id = target_id or workflow_family
    environment = _runtime_environment()
    if environment == "demo" and demo_backup_required():
        backup_hours = demo_backup_max_age_hours() if max_age_hours == 24.0 else max_age_hours
        if not _latest_demo_backup_ok(max_age_hours=backup_hours):
            return {
                "ok": False,
                "blocked": True,
                "reason": f"missing demo backup within {int(backup_hours)}h",
                "code": "backup_required",
            }
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT * FROM gate_release_verdicts
            WHERE workflow_family = ? AND target_kind = ? AND target_id = ?
            ORDER BY created_at DESC LIMIT 1
            """,
            (workflow_family, target_kind, final_target_id),
        ).fetchone()
    if not row:
        return {"ok": False, "blocked": True, "reason": "missing release verdict", "code": "missing_verdict"}
    verdict = dict(row)
    if str(verdict.get("environment") or "") != environment:
        return {"ok": False, "blocked": True, "reason": "release verdict environment mismatch", "code": "env_mismatch"}
    stale_after_ts = str(verdict.get("stale_after_ts") or "")
    if stale_after_ts:
        try:
            stale_after = datetime.fromisoformat(stale_after_ts.replace("Z", "+00:00"))
            if stale_after < datetime.now(timezone.utc):
                return {"ok": False, "blocked": True, "reason": "release verdict is stale", "code": "stale_verdict"}
        except ValueError:
            return {"ok": False, "blocked": True, "reason": "release verdict has invalid freshness window", "code": "invalid_verdict"}
    elif not receipt_is_fresh(str(verdict["created_at"]), max_age_hours=max_age_hours):
        return {"ok": False, "blocked": True, "reason": "release verdict is stale", "code": "stale_verdict"}
    if str(verdict.get("verdict")) == "blocked":
        return {"ok": False, "blocked": True, "reason": str(verdict.get("reason") or "blocked by gate"), "code": "blocked"}
    return {"ok": True, "blocked": False, "reason": str(verdict.get("reason") or "eligible"), "code": "eligible", "release_verdict": verdict}


def get_release_gate_status(*, workflow_family: str, target_kind: str = "workflow", target_id: str | None = None, max_age_hours: float = 24.0) -> dict[str, Any]:
    status = enforce_release_gate(workflow_family=workflow_family, target_kind=target_kind, target_id=target_id, max_age_hours=max_age_hours)
    status["environment"] = _runtime_environment()
    backup_hours = demo_backup_max_age_hours() if max_age_hours == 24.0 else max_age_hours
    status["backup_ok"] = (
        _latest_demo_backup_ok(max_age_hours=backup_hours)
        if _runtime_environment() == "demo" and demo_backup_required()
        else True
    )
    status["backup_required"] = _runtime_environment() == "demo" and demo_backup_required()
    status["backup_max_age_hours"] = backup_hours if _runtime_environment() == "demo" else None
    return status
