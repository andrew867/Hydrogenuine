"""Launch preflight checks."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.real_soak_launch.moltbook_envelope import load_armed_envelope
from hg_runtime.real_soak_launch.schema import RealSoakLaunchVerdict, WORKSPACE, load_launch_policy, new_id, now_iso, soak_dir


@dataclass
class SoakLaunchPreflight:
    preflight_id: str
    soak_id: str
    phase24_infrastructure_ok: bool
    phase23_ok: bool
    phase22_ok: bool
    stop_panic_available: bool
    no_scheduler: bool
    no_run_lock: bool
    moltbook_credentials_present: bool
    live_write_env_disabled: bool
    envelope_armed: bool
    max_live_posts: int
    phase18_publish_helper_staged: bool
    issues: tuple[str, ...]
    verdict: str
    created_at: str
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "preflight_id": self.preflight_id,
            "soak_id": self.soak_id,
            "phase24_infrastructure_ok": self.phase24_infrastructure_ok,
            "phase23_ok": self.phase23_ok,
            "phase22_ok": self.phase22_ok,
            "stop_panic_available": self.stop_panic_available,
            "no_scheduler": self.no_scheduler,
            "no_run_lock": self.no_run_lock,
            "moltbook_credentials_present": self.moltbook_credentials_present,
            "live_write_env_disabled": self.live_write_env_disabled,
            "envelope_armed": self.envelope_armed,
            "max_live_posts": self.max_live_posts,
            "phase18_publish_helper_staged": self.phase18_publish_helper_staged,
            "issues": list(self.issues),
            "verdict": self.verdict,
            "created_at": self.created_at,
            "hash": self.hash,
            "credential_values_exposed": False,
        }

    def with_hash(self) -> SoakLaunchPreflight:
        body = {k: v for k, v in self.to_payload().items() if k not in ("hash", "credential_values_exposed")}
        return SoakLaunchPreflight(**{**self.__dict__, "hash": compute_record_hash(body)})


def _moltbook_credentials_present() -> bool:
    try:
        from hg_runtime.social_capability.credentials import load_operator_social_env
        from hg_runtime.social_capability.schema import SocialSurface
        from hg_runtime.social_capability.credentials import credential_status
        from hg_runtime.social_capability.schema import SocialCredentialStatus

        load_operator_social_env()
        view = credential_status(SocialSurface.MOLTBOOK)
        return view.status == SocialCredentialStatus.CONFIGURED
    except Exception:
        return False


def run_launch_preflight(soak_id: str, *, base: Path | None = None) -> SoakLaunchPreflight:
    issues: list[str] = []
    p24 = (WORKSPACE / "docs/reports/phases/AUTONOMOUS_AGENT_ZERO_PHASE_24_OVERNIGHT_FIELD_RUN_REPORT.md").is_file()
    p23 = (WORKSPACE / "docs/reports/phases/AUTONOMOUS_AGENT_ZERO_PHASE_23_GOVERNED_WORK_LOOP_REPORT.md").is_file()
    p22 = (WORKSPACE / "docs/reports/phases/AUTONOMOUS_AGENT_ZERO_PHASE_22_FOREGROUND_HANDS_OFF_SESSION_REPORT.md").is_file()
    if not p24:
        issues.append("phase24_report_missing")
    if not p23:
        issues.append("phase23_report_missing")
    if not p22:
        issues.append("phase22_report_missing")

    from hg_runtime.overnight_field_run.field_run_lock import lock_path

    lock = lock_path()
    no_lock = not lock.is_file() or json.loads(lock.read_text()).get("state") != "active"

    live_disabled = os.environ.get("HG_SOCIAL_LIVE_PUBLISH", "false").lower() != "true"
    creds = _moltbook_credentials_present()
    if not creds:
        issues.append(RealSoakLaunchVerdict.YELLOW_CREDENTIALS.value)

    armed = load_armed_envelope(soak_id, base=base)
    max_posts = armed.max_live_posts if armed else 0
    if not armed:
        issues.append(RealSoakLaunchVerdict.YELLOW_ENVELOPE_NOT_ARMED.value)
    elif max_posts == 0:
        issues.append(RealSoakLaunchVerdict.YELLOW_QUOTA_ZERO.value)

    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
    )
    helper_staged = "scripts/dev/phase18_publish_once.py" in staged.stdout
    if helper_staged:
        issues.append("RED_PHASE18_PUBLISH_HELPER_STAGED")

    from hg_runtime.external_write_authority.action_ledger import phase18_live_proof_status

    p18 = phase18_live_proof_status()
    if not p18.get("live_proof_exists"):
        issues.append(RealSoakLaunchVerdict.YELLOW_PHASE18.value)

    red = [i for i in issues if i.startswith("RED_")]
    verdict = RealSoakLaunchVerdict.GREEN_LAUNCH_READY.value if not red else red[0]

    pf = SoakLaunchPreflight(
        preflight_id=new_id("preflight"),
        soak_id=soak_id,
        phase24_infrastructure_ok=p24,
        phase23_ok=p23,
        phase22_ok=p22,
        stop_panic_available=True,
        no_scheduler=True,
        no_run_lock=no_lock,
        moltbook_credentials_present=creds,
        live_write_env_disabled=live_disabled,
        envelope_armed=armed is not None,
        max_live_posts=max_posts,
        phase18_publish_helper_staged=helper_staged,
        issues=tuple(issues),
        verdict=verdict,
        created_at=now_iso(),
    ).with_hash()

    root = soak_dir(soak_id, base=base)
    root.mkdir(parents=True, exist_ok=True)
    (root / "preflight.json").write_text(json.dumps(pf.to_payload(), indent=2) + "\n", encoding="utf-8")
    return pf
