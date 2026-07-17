"""Required slice inventory for temporal experience readiness."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.temporal_experience_readiness.schema import FeatureClassification, RequiredSliceInventory, TemporalFeatureStatus

WORKSPACE = Path(__file__).resolve().parents[2]

MODULE_SPECS: list[tuple[str, str, str, bool]] = [
    ("authority_chain", "hg_runtime/authority_chain", "scripts/evals/authority_chain_gate.py", False),
    ("storage_artifact_vector", "hg_runtime/storage_artifact_vector", "scripts/evals/storage_artifact_vector_final_gate.py", True),
    ("model_provider_fabric", "hg_runtime/model_provider_fabric", "scripts/evals/model_provider_fabric_final_gate.py", True),
    ("tool_capability_fabric", "hg_runtime/tool_capability_fabric", "scripts/evals/tool_capability_fabric_final_gate.py", True),
    ("cloud_browser_tool_governance", "hg_runtime/cloud_browser_governance", "scripts/evals/cloud_browser_tool_governance_final_gate.py", False),
    ("will_module", "hg_runtime/will_module", "scripts/evals/will_module_final_gate.py", True),
    ("trust_boundary", "hg_runtime/trust_boundary", "scripts/evals/trust_boundary_final_gate.py", True),
    ("chrono", "hg_runtime/chrono", "scripts/evals/chrono_time_sync_gate.py", True),
    ("chrono_lock", "hg_runtime/chrono", "scripts/evals/chrono_lock_gate.py", True),
    ("external_start_anchor", "hg_runtime/external_start_anchor", "scripts/evals/external_start_anchor_final_gate.py", True),
    ("external_witness_journal", "hg_runtime/external_witness_journal", "scripts/evals/external_witness_journal_final_gate.py", True),
    ("anchor_signing", "hg_runtime/anchor_signing", "scripts/evals/signed_anchor_journal_final_gate.py", True),
    ("wake_refresh", "hg_runtime/wake_refresh", "scripts/evals/wake_refresh_final_gate.py", True),
    ("agent_zero_self_mirror", "hg_runtime/agent_zero_self_mirror", "scripts/evals/self_mirror_final_gate.py", True),
    ("audio_io", "hg_runtime/audio_io", "scripts/evals/audio_io_chrono_final_gate.py", True),
    ("audio_local_setup", "scripts/windows/audio", "scripts/evals/audio_local_setup_final_gate.py", True),
    ("agent_zero_first_wake", "scripts/dev/agent_zero_first_wake_mission.py", "scripts/evals/agent_zero_first_wake_final_gate.py", True),
    ("weather_voice_mission", "", "scripts/evals/weather_voice_contract_gate.py", False),
]

SELF_MIRROR_PATHS = {
    "wake_refresh": "hg_runtime/wake_refresh",
    "external_witness_journal": "hg_runtime/external_witness_journal",
    "external_start_anchor": "hg_runtime/external_start_anchor",
    "chrono": "hg_runtime/chrono",
    "will_module": "hg_runtime/will_module",
    "trust_boundary": "hg_runtime/trust_boundary",
    "audio_io": "hg_runtime/audio_io",
    "agent_zero_self_mirror": "hg_runtime/agent_zero_self_mirror",
}

BOOT_ATTACHED = {
    "wake_refresh", "chrono", "chrono_lock", "external_start_anchor", "external_witness_journal",
    "agent_zero_self_mirror", "will_module", "trust_boundary", "audio_io", "tool_capability_fabric",
    "model_provider_fabric", "storage_artifact_vector",
}


def _gate_registered(gate_script: str) -> bool:
    if not gate_script:
        return False
    registry_path = WORKSPACE / "config" / "truth_gate_registry.yaml"
    if not registry_path.exists():
        return False
    text = registry_path.read_text(encoding="utf-8")
    stem = Path(gate_script).name
    return stem in text


def build_inventory() -> RequiredSliceInventory:
    features: list[TemporalFeatureStatus] = []
    for module_id, pkg, gate, boot_default in MODULE_SPECS:
        if module_id == "weather_voice_mission":
            features.append(TemporalFeatureStatus(
                module_id=module_id,
                classification=FeatureClassification.FUTURE_WORK_ITEM,
                notes="lifecycle hooks exist; harness deferred",
            ))
            continue
        if module_id == "authority_chain":
            pkg_exists = (WORKSPACE / pkg).exists() if pkg else False
            features.append(TemporalFeatureStatus(
                module_id=module_id,
                classification=FeatureClassification.FUTURE_WORK_ITEM if not boot_default else FeatureClassification.REQUIRED_NOW_COMPLETE,
                package_path=pkg,
                boot_attached=False,
                notes="optional release chain",
            ))
            continue
        pkg_exists = bool(pkg) and (WORKSPACE / pkg).exists()
        if module_id == "agent_zero_first_wake":
            pkg_exists = (WORKSPACE / "scripts/dev/agent_zero_first_wake_mission.py").exists()
        if module_id == "audio_local_setup":
            pkg_exists = (WORKSPACE / "scripts/windows/audio").exists()
        if module_id == "storage_artifact_vector":
            pkg_exists = (WORKSPACE / gate).exists() if gate else False
        gate_exists = bool(gate) and (WORKSPACE / gate).exists()
        classification = FeatureClassification.REQUIRED_NOW_COMPLETE
        notes = ""
        if boot_default and not pkg_exists:
            classification = FeatureClassification.REQUIRED_NOW_BLOCKER
            notes = "package missing"
        elif boot_default and gate and not gate_exists:
            classification = FeatureClassification.REQUIRED_NOW_GATE_REGISTRY_GAP
            notes = "gate script missing"
        elif boot_default and gate and not _gate_registered(gate):
            classification = FeatureClassification.REQUIRED_NOW_GATE_REGISTRY_GAP
            notes = "gate not registered"
        elif not boot_default and not pkg_exists:
            classification = FeatureClassification.FUTURE_WORK_ITEM
            notes = "deferred optional module"
        features.append(TemporalFeatureStatus(
            module_id=module_id,
            classification=classification,
            package_path=pkg,
            boot_attached=module_id in BOOT_ATTACHED or boot_default,
            self_mirror_discoverable=module_id in SELF_MIRROR_PATHS and (WORKSPACE / SELF_MIRROR_PATHS.get(module_id, pkg)).exists(),
            gate_registered=_gate_registered(gate) if gate else False,
            default_enabled=boot_default,
            notes=notes,
        ))
    return RequiredSliceInventory(features=features)


__all__ = ["build_inventory"]
