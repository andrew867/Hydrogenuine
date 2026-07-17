"""Temporal experience readiness tests."""

from __future__ import annotations

import json
from pathlib import Path

from hg_runtime.agent0_dev_boot.boot import run_agent0_dev_boot
from hg_runtime.temporal_experience_readiness.boot_context import BOOT_CONTEXT_KEYS, build_temporal_boot_context
from hg_runtime.temporal_experience_readiness.defaults import audit_profile_defaults
from hg_runtime.temporal_experience_readiness.inventory import build_inventory
from hg_runtime.temporal_experience_readiness.schema import FeatureClassification

WORKSPACE = Path(__file__).resolve().parents[2]
PROFILE = WORKSPACE / "configs/runtime/agent-zero-first-wake-local-openvino.json"


def test_first_wake_profile_safe_defaults():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    matrix = audit_profile_defaults(profile)
    assert matrix.ok
    assert profile.get("publish") is False
    assert profile.get("live_oea") is False


def test_boot_temporal_context_keys():
    boot = run_agent0_dev_boot(
        profile_path=PROFILE,
        dry_run=True,
        tool_dry_run=True,
        show_capabilities=True,
        show_will=True,
    )
    payload = boot.to_payload()
    temporal = payload.get("temporal_context") or {}
    for key in ("agent_identity", "will_context", "denial_policy_summary", "trust_boundary_policy"):
        assert key in temporal
    assert temporal["agent_identity"]["agent_code_id"] == "agent0"


def test_inventory_no_blockers_except_weather():
    inv = build_inventory()
    blockers = [
        f for f in inv.features
        if f.classification != FeatureClassification.REQUIRED_NOW_COMPLETE
        and f.module_id != "weather_voice_mission"
        and f.classification != FeatureClassification.FUTURE_WORK_ITEM
    ]
    assert not blockers, blockers


def test_build_temporal_boot_context_frozen_authority():
    boot = run_agent0_dev_boot(profile_path=PROFILE, dry_run=True)
    temporal = build_temporal_boot_context(boot_payload=boot.to_payload(), organ_manifest=boot.organ_manifest)
    assert temporal["permission_granted"] is False
    assert temporal["authority_created"] is False
