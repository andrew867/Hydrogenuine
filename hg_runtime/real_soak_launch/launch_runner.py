"""Real soak launch runner."""

from __future__ import annotations

import json
import os
from dataclasses import replace
from pathlib import Path

from hg_runtime.overnight_field_run.field_run_config import build_default_field_run_config
from hg_runtime.overnight_field_run.field_run_postflight import load_postflight as load_field_postflight
from hg_runtime.overnight_field_run.field_run_runner import run_overnight_field_session
from hg_runtime.overnight_field_run.schema import FieldRunMode
from hg_runtime.overnight_field_run.wake_report import load_wake_report
from hg_runtime.real_soak_launch.errors import RealSoakLaunchError
from hg_runtime.real_soak_launch.launch_postflight import SoakLaunchPostflight, load_postflight, write_postflight
from hg_runtime.real_soak_launch.launch_preflight import run_launch_preflight
from hg_runtime.real_soak_launch.launch_receipts import make_receipt, persist_receipt
from hg_runtime.real_soak_launch.moltbook_envelope import load_armed_envelope
from hg_runtime.real_soak_launch.schema import RealSoakLaunchVerdict, now_iso, soak_dir
from hg_runtime.real_soak_launch.soak_launch_config import build_launch_config


def _ensure_safe_env() -> None:
    os.environ.setdefault("HG_SOCIAL_LIVE_PUBLISH", "false")
    os.environ.setdefault("HG_SOCIAL_LIVE_REPLY", "false")
    os.environ.setdefault("HG_ENABLE_LIVE_SOCIAL_WRITES", "false")
    os.environ.setdefault("HG_LIVE_BROWSER_ENABLED", "false")
    os.environ.setdefault("HG_EXTERNAL_SEND_ENABLED", "false")


def _live_posts_allowed(soak_id: str, *, base: Path | None = None) -> bool:
    env = (
        os.environ.get("HG_SOCIAL_LIVE_PUBLISH", "false").lower() == "true"
        or os.environ.get("HG_ENABLE_LIVE_SOCIAL_WRITES", "false").lower() == "true"
    )
    armed = load_armed_envelope(soak_id, base=base)
    return bool(env and armed and armed.max_live_posts > 0 and armed.is_armed() and not armed.is_expired())


def run_real_soak_start(soak_id: str, *, base: Path | None = None) -> SoakLaunchPostflight:
    """Foreground blocking soak — Phase 24 field run + Phase 23 governed work."""
    _ensure_safe_env()
    if _live_posts_allowed(soak_id, base=base) is False:
        _ensure_safe_env()

    preflight = run_launch_preflight(soak_id, base=base)
    if preflight.verdict.startswith("RED_"):
        raise RealSoakLaunchError(preflight.verdict)

    persist_receipt(make_receipt(soak_id, "start", preflight.verdict), base=base)
    os.environ["HG_REAL_SOAK_SOAK_ID"] = soak_id
    config = build_launch_config(soak_id=soak_id)
    root = soak_dir(soak_id, base=base)
    root.mkdir(parents=True, exist_ok=True)
    (root / "launch_config.json").write_text(json.dumps(config.to_payload(), indent=2) + "\n", encoding="utf-8")

    armed = load_armed_envelope(soak_id, base=base)
    field_config = build_default_field_run_config(
        field_run_id=soak_id,
        mode=FieldRunMode.OPERATOR_FIELD_RUN.value,
    )
    live_ok = _live_posts_allowed(soak_id, base=base)
    field_config = replace(
        field_config,
        external_side_effects_allowed=live_ok,
        live_writes_allowed=live_ok,
    )
    if armed:
        (root / "moltbook_envelope_ref.json").write_text(
            json.dumps({"envelope_id": armed.envelope_id, "max_live_posts": armed.max_live_posts}, indent=2) + "\n",
            encoding="utf-8",
        )

    field_pf = run_overnight_field_session(field_config)
    wake = load_wake_report(soak_id)
    pf = SoakLaunchPostflight(
        postflight_id=f"soak-pf-{soak_id}",
        soak_id=soak_id,
        verdict=field_pf.verdict if not field_pf.verdict.startswith("RED_") else field_pf.verdict,
        live_posts_used=0,
        external_side_effect_count=field_pf.external_side_effect_count,
        wake_report_ref=wake.wake_report_id if wake else "",
        field_run_postflight_ref=field_pf.postflight_id,
        infrastructure_only=False,
        created_at=now_iso(),
    ).with_hash()
    if not _live_posts_allowed(soak_id, base=base):
        pf = SoakLaunchPostflight(
            **{**pf.__dict__, "verdict": RealSoakLaunchVerdict.YELLOW_QUOTA_ZERO.value}
        ).with_hash()
    write_postflight(pf, base=base)
    persist_receipt(make_receipt(soak_id, "stop", pf.verdict), base=base)
    return pf
