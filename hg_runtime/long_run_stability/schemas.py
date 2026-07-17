"""Phase 39 long-run stability, recovery, and checkpoint soak schemas.

This phase runs a deterministic, fixture-only stability loop over Phase 37/38
review-preparation tasks to prove the agent substrate can run for many
iterations, checkpoint its state, be preempted by STOP/PANIC, recover from a
crash via its last valid checkpoint, and replay to an identical final state.

It is soak/recovery infrastructure only:

* It does not apply Phase 38 patch candidates to live source.
* It does not grant authority or authorize tools.
* It does not create live external effects or live posts.
* It does not call external providers.
* It does not weaken STOP/PANIC; PANIC preempts STOP preempts work.

A checkpoint is not approval. A GREEN soak is not authority. These boundaries
are enforced structurally here and reused across the module.
"""

from __future__ import annotations

from typing import Any, Mapping

# --- schema ids -------------------------------------------------------------
LONG_RUN_SOAK_CONFIG_SCHEMA = "long_run_soak_config_v1"
DRY_RUN_TASK_FIXTURE_SCHEMA = "dry_run_task_fixture_v1"
STABILITY_LOOP_STATE_SCHEMA = "stability_loop_state_v1"
STABILITY_LOOP_EVENT_SCHEMA = "stability_loop_event_v1"
CHECKPOINT_RECORD_SCHEMA = "checkpoint_record_v1"
CHECKPOINT_MANIFEST_SCHEMA = "checkpoint_manifest_v1"
RECOVERY_REQUEST_SCHEMA = "recovery_request_v1"
RECOVERY_RESULT_SCHEMA = "recovery_result_v1"
INVARIANT_SNAPSHOT_SCHEMA = "invariant_snapshot_v1"
BOUNDARY_SNAPSHOT_SCHEMA = "boundary_snapshot_v1"
STOP_PANIC_EVENT_SCHEMA = "stop_panic_event_v1"
REPLAY_MANIFEST_SCHEMA = "replay_manifest_v1"
REPLAY_RESULT_SCHEMA = "replay_result_v1"
SOAK_SUMMARY_SCHEMA = "soak_summary_v1"
LONG_RUN_GATE_RESULT_SCHEMA = "long_run_gate_result_v1"

# --- verdicts ---------------------------------------------------------------
VERDICT_GREEN = "GREEN_PHASE39_LONG_RUN_STABILITY_CHECKPOINT_SOAK"
VERDICT_YELLOW = "YELLOW_PHASE39_STABILITY_PARTIAL"
VERDICT_RED = "RED_PHASE39_STABILITY_FAILED"

# --- soak modes -------------------------------------------------------------
MODE_SHORT_FIXTURE_SOAK = "SHORT_FIXTURE_SOAK"
MODE_CHECKPOINT_RESUME = "CHECKPOINT_RESUME"
MODE_STOP_PREEMPTION = "STOP_PREEMPTION"
MODE_PANIC_PREEMPTION = "PANIC_PREEMPTION"
MODE_CRASH_RECOVERY = "CRASH_RECOVERY"
MODE_REPLAY_ONLY = "REPLAY_ONLY"

SOAK_MODES = frozenset(
    {
        MODE_SHORT_FIXTURE_SOAK,
        MODE_CHECKPOINT_RESUME,
        MODE_STOP_PREEMPTION,
        MODE_PANIC_PREEMPTION,
        MODE_CRASH_RECOVERY,
        MODE_REPLAY_ONLY,
    }
)

# --- event kinds ------------------------------------------------------------
EVENT_TASK_PROCESSED = "TASK_PROCESSED"
EVENT_CHECKPOINT_WRITTEN = "CHECKPOINT_WRITTEN"
EVENT_STOP_PREEMPTION = "STOP_PREEMPTION"
EVENT_PANIC_PREEMPTION = "PANIC_PREEMPTION"
EVENT_CRASH = "CRASH"
EVENT_RECOVERY = "RECOVERY"
EVENT_BOUNDARY_DRIFT_REJECTED = "BOUNDARY_DRIFT_REJECTED"
EVENT_SOAK_COMPLETED = "SOAK_COMPLETED"

# --- task kinds (all review-preparation, never apply) -----------------------
TASK_DOC_REVIEW = "DOC_REVIEW"
TASK_TEST_ANALYSIS = "TEST_ANALYSIS"
TASK_PATCH_CANDIDATE_REVIEW = "PATCH_CANDIDATE_REVIEW"

# --- halt reasons -----------------------------------------------------------
HALT_COMPLETED = "COMPLETED"
HALT_STOP = "STOP"
HALT_PANIC = "PANIC"
HALT_CRASH = "CRASH"

# --- preserved statuses -----------------------------------------------------
PHASE19_STATUS = "YELLOW_PRESERVED"
PHASE24_STATUS = "INFRASTRUCTURE_ONLY"

UNKNOWN = "UNKNOWN"

# Boundary flag fields that must remain false for the entire soak. If any is
# true in emitted state the substrate has gone live / elevated.
BOUNDARY_FLAG_FIELDS = (
    "authority_granted",
    "tools_authorized",
    "live_effects_created",
    "live_posts_created",
    "external_provider_calls_made",
    "patches_applied",
)


class StabilityError(ValueError):
    """Phase 39 validation or boundary refusal."""


def neutral_boundary_flags() -> dict[str, bool]:
    """Boundary flags every Phase 39 state/checkpoint/snapshot carries false."""
    return {field: False for field in BOUNDARY_FLAG_FIELDS}


def neutral_flags() -> dict[str, bool]:
    """Flags every Phase 39 artifact carries to keep it soak-only."""
    return {
        "advisory_only": True,
        "soak_is_infrastructure_only": True,
        "is_authority": False,
        "is_approval": False,
        "apply_allowed": False,
        "patches_applied": False,
        "authority_granted": False,
        "tools_authorized": False,
        "live_effects_created": False,
        "live_posts_created": False,
        "external_provider_calls_made": False,
        "committed": False,
        "pushed": False,
        "deployed": False,
        "stop_panic_weakened": False,
        "claims_agi": False,
    }


def require_fields(payload: Mapping[str, Any], fields: tuple[str, ...]) -> None:
    missing = [field for field in fields if payload.get(field) in (None, "")]
    if missing:
        raise StabilityError(f"schema_violation:missing:{','.join(missing)}")


# Fields whose truthiness in an emitted Phase 39 artifact would mean the soak
# itself granted authority / went live / applied a patch / weakened STOP-PANIC.
_FORBIDDEN_OUTPUT_FLAGS = {
    "apply_allowed": "soak_cannot_allow_apply",
    "patches_applied": "soak_cannot_apply_patch_to_live",
    "patch_applied_to_live_repo": "soak_cannot_apply_patch_to_live",
    "authority_granted": "soak_cannot_grant_authority",
    "tools_authorized": "soak_cannot_authorize_tools",
    "live_effects_created": "soak_cannot_create_live_effects",
    "live_posts_created": "soak_cannot_create_live_posts",
    "external_provider_calls_made": "soak_cannot_call_external_providers",
    "committed": "soak_cannot_commit_as_implementation",
    "pushed": "soak_cannot_push",
    "deployed": "soak_cannot_deploy",
    "stop_panic_weakened": "soak_cannot_weaken_stop_panic",
    "claims_agi": "soak_cannot_claim_agi",
}


def assert_neutral_output(payload: Mapping[str, Any]) -> None:
    """Guard an artifact the soak is about to emit: it must stay neutral."""
    for key, value in payload.items():
        if value and str(key) in _FORBIDDEN_OUTPUT_FLAGS:
            raise StabilityError(_FORBIDDEN_OUTPUT_FLAGS[str(key)])
        if isinstance(value, Mapping):
            assert_neutral_output(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    assert_neutral_output(item)


__all__ = [
    "BOUNDARY_FLAG_FIELDS",
    "BOUNDARY_SNAPSHOT_SCHEMA",
    "CHECKPOINT_MANIFEST_SCHEMA",
    "CHECKPOINT_RECORD_SCHEMA",
    "DRY_RUN_TASK_FIXTURE_SCHEMA",
    "EVENT_BOUNDARY_DRIFT_REJECTED",
    "EVENT_CHECKPOINT_WRITTEN",
    "EVENT_CRASH",
    "EVENT_PANIC_PREEMPTION",
    "EVENT_RECOVERY",
    "EVENT_SOAK_COMPLETED",
    "EVENT_STOP_PREEMPTION",
    "EVENT_TASK_PROCESSED",
    "HALT_COMPLETED",
    "HALT_CRASH",
    "HALT_PANIC",
    "HALT_STOP",
    "INVARIANT_SNAPSHOT_SCHEMA",
    "LONG_RUN_GATE_RESULT_SCHEMA",
    "LONG_RUN_SOAK_CONFIG_SCHEMA",
    "MODE_CHECKPOINT_RESUME",
    "MODE_CRASH_RECOVERY",
    "MODE_PANIC_PREEMPTION",
    "MODE_REPLAY_ONLY",
    "MODE_SHORT_FIXTURE_SOAK",
    "MODE_STOP_PREEMPTION",
    "PHASE19_STATUS",
    "PHASE24_STATUS",
    "RECOVERY_REQUEST_SCHEMA",
    "RECOVERY_RESULT_SCHEMA",
    "REPLAY_MANIFEST_SCHEMA",
    "REPLAY_RESULT_SCHEMA",
    "SOAK_MODES",
    "SOAK_SUMMARY_SCHEMA",
    "STABILITY_LOOP_EVENT_SCHEMA",
    "STABILITY_LOOP_STATE_SCHEMA",
    "STOP_PANIC_EVENT_SCHEMA",
    "TASK_DOC_REVIEW",
    "TASK_PATCH_CANDIDATE_REVIEW",
    "TASK_TEST_ANALYSIS",
    "UNKNOWN",
    "VERDICT_GREEN",
    "VERDICT_RED",
    "VERDICT_YELLOW",
    "StabilityError",
    "assert_neutral_output",
    "neutral_boundary_flags",
    "neutral_flags",
    "require_fields",
]
