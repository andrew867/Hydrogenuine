"""CT-13 LCB live cognition behavior eval — proposal-only, non-authoritative."""

from hg_core.live_cognition_eval.harness import (
    EvalMode,
    EvalResult,
    EvalRunRefused,
    resolve_eval_mode,
    run_battery,
    run_eval,
)
from hg_core.live_cognition_eval.oracle import AuthorityLeakOracle, OracleVerdict
from hg_core.live_cognition_eval.prompts import load_prompt_set
from hg_core.live_cognition_eval.redaction import redact_transcript, transcript_artifact_policy

__all__ = [
    "AuthorityLeakOracle",
    "EvalMode",
    "EvalResult",
    "EvalRunRefused",
    "OracleVerdict",
    "load_prompt_set",
    "redact_transcript",
    "resolve_eval_mode",
    "run_battery",
    "run_eval",
    "transcript_artifact_policy",
]
