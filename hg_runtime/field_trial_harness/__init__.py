"""Phase 35 field-trial dry-run harness."""

from hg_runtime.field_trial_harness.candidate import (
    candidate_hash,
    intake_candidate,
    required_candidate_fixtures,
)
from hg_runtime.field_trial_harness.gate import validate_phase35_gate
from hg_runtime.field_trial_harness.harness import evaluate_candidate, evaluate_required_fixtures, summarize_results
from hg_runtime.field_trial_harness.regate import load_substrate_status, require_substrate_green
from hg_runtime.field_trial_harness.replay import FieldTrialLog, replay_decisions
from hg_runtime.field_trial_harness.schemas import (
    DRY_RUN_ALLOWED,
    LIVE_SELF_BLOCKED,
    SAFETY_REFUSED,
    VERDICT_GREEN,
    VERDICT_RED,
    VERDICT_YELLOW,
    FieldTrialHarnessError,
)

__all__ = [
    "DRY_RUN_ALLOWED",
    "FieldTrialHarnessError",
    "FieldTrialLog",
    "LIVE_SELF_BLOCKED",
    "SAFETY_REFUSED",
    "VERDICT_GREEN",
    "VERDICT_RED",
    "VERDICT_YELLOW",
    "candidate_hash",
    "evaluate_candidate",
    "evaluate_required_fixtures",
    "intake_candidate",
    "load_substrate_status",
    "replay_decisions",
    "require_substrate_green",
    "required_candidate_fixtures",
    "summarize_results",
    "validate_phase35_gate",
]
