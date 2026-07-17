"""Mission verdict evaluation for Agent Zero three-stage wake proof."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hg_runtime.temporal_experience_readiness.boot_context import BOOT_CONTEXT_KEYS

WORKSPACE = Path(__file__).resolve().parents[2]
STAGE_STATE = WORKSPACE / ".hg-local/agent_zero_three_stage/stage_status.json"
PROOFS = WORKSPACE / "docs/proofs/agent_zero_three_stage"

STAGE_A_GREEN = "GREEN_AGENT_ZERO_STAGE_A_START_EPOCH_PROVEN"
STAGE_B_GREEN = "GREEN_AGENT_ZERO_STAGE_B_FIRST_WAKE_PROVEN"
STAGE_C_GREEN = "GREEN_AGENT_ZERO_STAGE_C_WEATHER_VOICE_PROVEN"


def load_stage_state() -> dict[str, Any]:
    if STAGE_STATE.exists():
        return json.loads(STAGE_STATE.read_text(encoding="utf-8"))
    return {}


def save_stage_state(state: dict[str, Any]) -> None:
    STAGE_STATE.parent.mkdir(parents=True, exist_ok=True)
    STAGE_STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _authority_ok(ctx: dict[str, Any] | None) -> bool:
    if not ctx:
        return False
    return (
        ctx.get("advisory_only") is True
        and ctx.get("permission_granted") is False
        and ctx.get("authority_created") is False
    )


def evaluate_stage_b_mission(
    boot_payload: dict[str, Any],
    *,
    allow_storage_yellow: bool = False,
    require_openvino: bool = False,
) -> tuple[str, list[str], list[str], list[dict[str, Any]]]:
    failures: list[str] = []
    warnings: list[str] = []
    checks: list[dict[str, Any]] = []

    boot_verdict = str(boot_payload.get("verdict", ""))
    if boot_verdict.startswith("RED"):
        failures.append(f"RED_BOOT_FAILED:{boot_verdict}")

    temporal = boot_payload.get("temporal_context") or {}
    for key in BOOT_CONTEXT_KEYS:
        present = temporal.get(key) is not None
        checks.append({"check": f"temporal_{key}", "ok": present, "detail": None})
        if not present:
            failures.append(f"RED_BOOT_CONTEXT_MISSING:{key}")

    checks.append({"check": "authority_invariants", "ok": _authority_ok(temporal), "detail": None})
    if not _authority_ok(temporal):
        failures.append("RED_AUTHORITY_CONVERSION")

    storage_ok = bool(boot_payload.get("storage_ok"))
    if not storage_ok:
        if allow_storage_yellow:
            warnings.append("YELLOW_STORAGE_PENDING:operator_host")
        else:
            failures.append("RED_BOOT_CONTEXT_MISSING:storage_not_green")

    provider_ok = bool(boot_payload.get("provider_ok"))
    checks.append({"check": "provider_ok", "ok": provider_ok, "detail": boot_payload.get("liveness", {})})
    if require_openvino and not provider_ok:
        failures.append("RED_BOOT_CONTEXT_MISSING:openvino_required")

    events = boot_payload.get("events") or []
    event_types = {e.get("event_type") for e in events}
    for required in ("OrganBootCompleted", "RuntimeStopped", "RuntimeFinalDigest"):
        ok = required in event_types
        checks.append({"check": f"event_{required}", "ok": ok, "detail": None})
        if not ok and not boot_payload.get("dry_run"):
            failures.append(f"RED_MISSING_RECEIPT:{required}")

    if failures:
        verdict = failures[0].split(":")[0]
    elif warnings:
        verdict = STAGE_B_GREEN
    else:
        verdict = STAGE_B_GREEN
    return verdict, failures, warnings, checks


def evaluate_stage_c_mission(summary: dict[str, Any]) -> tuple[str, list[str], list[str]]:
    failures: list[str] = []
    warnings: list[str] = []

    if summary.get("permission_granted") or summary.get("authority_created"):
        failures.append("RED_AUTHORITY_CONVERSION")
    if summary.get("weather_taint") != "UNTRUSTED_WEB":
        failures.append("RED_PROMPT_INJECTION_BYPASS")
    tts = summary.get("tts") or {}
    if tts.get("decision") and "SECRET" in json.dumps(tts.get("decision")):
        failures.append("RED_AUDIO_SECRET_LEAK")

    tts_present = bool(tts.get("output_file_present"))
    if not tts_present:
        warnings.append("YELLOW_AUDIO_DEGRADED_BUT_CONTRACT_HELD")

    if failures:
        return failures[0].split(":")[0], failures, warnings
    if warnings and summary.get("verdict") != STAGE_C_GREEN:
        return "YELLOW_AUDIO_DEGRADED_BUT_CONTRACT_HELD", failures, warnings
    return STAGE_C_GREEN, failures, warnings
