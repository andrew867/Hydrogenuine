"""Capability broker policy loader."""

from __future__ import annotations

import json
from pathlib import Path

from hg_runtime.capability_broker.schema import CapabilityPolicy

WORKSPACE = Path(__file__).resolve().parents[2]
DEFAULT_POLICY_PATH = WORKSPACE / "configs/agent_zero/capability_broker_policy.json"


def load_capability_broker_policy(*, path: Path | None = None) -> CapabilityPolicy:
    policy_path = path or DEFAULT_POLICY_PATH
    if not policy_path.is_file():
        return CapabilityPolicy()
    data = json.loads(policy_path.read_text(encoding="utf-8"))
    return CapabilityPolicy(
        external_side_effects_allowed=data.get("external_side_effects_allowed", False),
        live_writes_allowed=data.get("live_writes_allowed", False),
        browser_side_effects_allowed=data.get("browser_side_effects_allowed", False),
        hardware_actuation_allowed=data.get("hardware_actuation_allowed", False),
        unknown_actions_allowed=data.get("unknown_actions_allowed", False),
        disabled_actions_allowed=data.get("disabled_actions_allowed", False),
        operator_absence_expands_authority=data.get("operator_absence_expands_authority", False),
        fixture_runtime_truth_allowed=data.get("fixture_runtime_truth_allowed", False),
        dry_run_action_admission_allowed=data.get("dry_run_action_admission_allowed", False),
        provider_unavailable_blocks_provider_required_actions=data.get(
            "provider_unavailable_blocks_provider_required_actions", True
        ),
        live_read_unavailable_blocks_read_required_actions=data.get(
            "live_read_unavailable_blocks_read_required_actions", True
        ),
        stop_panic_blocks_all_non_emergency_actions=data.get(
            "stop_panic_blocks_all_non_emergency_actions", True
        ),
        decision_receipt_required=data.get("decision_receipt_required", True),
        decision_hash_required=data.get("decision_hash_required", True),
        hidden_chain_of_thought_storage_allowed=data.get(
            "hidden_chain_of_thought_storage_allowed", False
        ),
        secret_storage_allowed=data.get("secret_storage_allowed", False),
        policy_refs=[str(policy_path.relative_to(WORKSPACE)).replace("\\", "/")],
    )


__all__ = ["DEFAULT_POLICY_PATH", "load_capability_broker_policy"]
