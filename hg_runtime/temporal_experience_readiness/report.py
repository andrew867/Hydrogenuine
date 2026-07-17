"""Build temporal experience readiness report."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hg_runtime.agent0_dev_boot.boot import run_agent0_dev_boot
from hg_runtime.agent0_dev_boot.profiles import load_runtime_profile
from hg_runtime.agent_zero_self_mirror.source_reader import build_source_index, find_module_for_topic
from hg_runtime.temporal_experience_readiness.boot_context import BOOT_CONTEXT_KEYS, assess_boot_completeness, build_temporal_boot_context
from hg_runtime.temporal_experience_readiness.defaults import FIRST_WAKE_PROFILE, audit_profile_defaults
from hg_runtime.temporal_experience_readiness.inventory import build_inventory
from hg_runtime.temporal_experience_readiness.schema import (
    BootContextCompleteness,
    TemporalExperienceReadinessReport,
    TemporalReadinessVerdict,
)

WORKSPACE = Path(__file__).resolve().parents[2]

REQUIRED_GATES = [
    "wake_refresh_final",
    "chrono_lock",
    "external_start_anchor_final",
    "external_witness_journal_final",
    "self_mirror_final",
    "trust_boundary_final",
    "audio_local_setup_final",
    "will_module_final",
    "agent_zero_first_wake_final",
    "temporal_experience_readiness",
]


def _registry_text() -> str:
    path = WORKSPACE / "config/truth_gate_registry.yaml"
    return path.read_text(encoding="utf-8") if path.exists() else ""


def build_readiness_report(
    *,
    profile_path: str | Path | None = None,
    anchor_handoff_path: str | Path | None = None,
    dry_boot: bool = True,
) -> TemporalExperienceReadinessReport:
    profile_path = profile_path or FIRST_WAKE_PROFILE
    profile = load_runtime_profile(profile_path) if Path(profile_path).exists() else {}
    failures: list[str] = []
    warnings: list[str] = []

    inventory = build_inventory()
    for feat in inventory.required_now_remaining:
        failures.append(f"{feat.classification.value}:{feat.module_id}:{feat.notes}")

    defaults = audit_profile_defaults(profile)
    if not defaults.ok:
        failures.extend(defaults.violations)

    registry = _registry_text()
    for gid in REQUIRED_GATES:
        if gid not in registry:
            failures.append(f"RED_GATE_ORPHAN:missing_registry:{gid}")

    idx = build_source_index()
    for topic in ("wake_refresh", "external_witness_journal", "chrono", "will_module", "trust_boundary"):
        hits = find_module_for_topic(topic)
        if not hits:
            failures.append(f"RED_FEATURE_NOT_DISCOVERABLE:self_mirror:{topic}")

    temporal: dict[str, Any] = {}
    if dry_boot:
        boot = run_agent0_dev_boot(
            profile_path=profile_path,
            dry_run=True,
            tool_dry_run=True,
            show_capabilities=True,
            show_will=True,
            anchor_handoff_path=anchor_handoff_path,
            skip_wake_refresh=False,
        )
        base = boot.to_payload()
        temporal = build_temporal_boot_context(
            boot_payload=base,
            organ_manifest=boot.organ_manifest,
            profile=profile,
        )
        present, missing = assess_boot_completeness(temporal, anchor_optional=not anchor_handoff_path)
        missing_required = [m for m in missing if m != "external_start_anchor" or anchor_handoff_path]
        if missing_required:
            failures.append(f"RED_BOOT_CONTEXT_MISSING:{','.join(missing_required)}")
        if boot.verdict.startswith("RED"):
            failures.append(f"RED_BOOT:{boot.verdict}")
        if not boot.will_context:
            failures.append("RED_BOOT_CONTEXT_MISSING:will_context")
        if profile.get("publish"):
            failures.append("RED_LIVE_SIDE_EFFECT:publish_default")

    present, missing = assess_boot_completeness(temporal) if temporal else ([], list(BOOT_CONTEXT_KEYS))
    boot_complete = BootContextCompleteness(
        required_keys=BOOT_CONTEXT_KEYS,
        present_keys=present,
        missing_keys=missing,
        complete=not any(f.startswith("RED_BOOT_CONTEXT") for f in failures),
    )

    if not anchor_handoff_path:
        warnings.append(TemporalReadinessVerdict.YELLOW_LIVE_ANCHOR_NOT_PUSHED.value)
    warnings.append(TemporalReadinessVerdict.YELLOW_AUDIO_PLAYBACK_DISABLED.value)
    warnings.append(TemporalReadinessVerdict.YELLOW_LIVE_WEATHER_DISABLED.value)

    red_failures = [f for f in failures if "RED_" in f]
    if red_failures:
        verdict = red_failures[0].split(":")[0] if ":" in red_failures[0] else TemporalReadinessVerdict.RED_REQUIRED_SLICE_DEFERRED.value
    elif failures:
        verdict = TemporalReadinessVerdict.RED_REQUIRED_SLICE_DEFERRED.value
    else:
        verdict = TemporalReadinessVerdict.GREEN_TEMPORAL_EXPERIENCE_READY.value

    return TemporalExperienceReadinessReport(
        verdict=verdict,
        boot_completeness=boot_complete,
        defaults=defaults,
        inventory=inventory,
        failures=failures,
        warnings=warnings,
    )


__all__ = ["build_readiness_report"]
