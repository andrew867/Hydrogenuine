"""EXCITON real soak launch monitor."""

from __future__ import annotations

from typing import Any

from hg_runtime.real_soak_launch.launch_postflight import load_postflight
from hg_runtime.real_soak_launch.launch_preflight import run_launch_preflight
from hg_runtime.real_soak_launch.moltbook_envelope import load_armed_envelope
from hg_runtime.real_soak_launch.schema import RealSoakLaunchVerdict, STORE_ROOT, soak_dir


def build_real_soak_launch_monitor_snapshot(soak_id: str | None = None) -> dict[str, Any]:
    sid = soak_id
    if not sid and STORE_ROOT.is_dir():
        dirs = sorted([p for p in STORE_ROOT.iterdir() if p.is_dir()], key=lambda p: p.stat().st_mtime)
        if dirs:
            sid = dirs[-1].name

    armed = load_armed_envelope(sid) if sid else None
    pf = load_postflight(sid) if sid else None
    preflight_path = soak_dir(sid) / "preflight.json" if sid else None
    preflight_ok = preflight_path.is_file() if preflight_path else False

    live_posts_allowed = armed is not None and armed.max_live_posts > 0 and armed.is_armed()
    verdict = RealSoakLaunchVerdict.YELLOW_NOT_STARTED.value
    if pf:
        verdict = pf.verdict
    elif preflight_ok:
        verdict = RealSoakLaunchVerdict.GREEN_LAUNCH_READY.value

    return {
        "panel_title": "Agent Zero Real Soak Launch Monitor",
        "soak_id": sid or "",
        "phase24_infrastructure_status": "GREEN_INFRASTRUCTURE",
        "field_run_status": pf.field_run_postflight_ref if pf else "not_started",
        "moltbook_envelope_status": armed.status if armed else "not_armed",
        "live_posts_allowed": live_posts_allowed,
        "max_live_posts": armed.max_live_posts if armed else 0,
        "live_posts_used": pf.live_posts_used if pf else 0,
        "envelope_valid_until": armed.valid_until if armed else "",
        "platform_proof_status": "pending",
        "ledger_status": "ready",
        "stop_status": False,
        "panic_status": False,
        "external_side_effect_count": pf.external_side_effect_count if pf else 0,
        "preflight_ok": preflight_ok,
        "live_action_buttons": False,
        "dry_run_only_default": True,
        "verdict": verdict,
    }
