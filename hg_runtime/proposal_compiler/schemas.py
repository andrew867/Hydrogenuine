"""Phase 37 proposal-to-spec/tests/plans compiler schemas and safety boundaries.

The compiler turns structured Agent Zero repair proposals into implementation-ready
*planning documents*. It is planning-docs-only:

* It does not implement the proposed fix.
* It does not apply patches.
* It does not grant authority or authorize tools.
* It does not create live external effects.

These boundaries are enforced structurally here and reused across the module.
"""

from __future__ import annotations

from typing import Any, Mapping

COMPILED_WORK_PACKAGE_SCHEMA = "compiled_work_package_v1"
COMPILED_SPEC_UPDATE_SCHEMA = "compiled_spec_update_v1"
COMPILED_TEST_PLAN_UPDATE_SCHEMA = "compiled_test_plan_update_v1"
COMPILED_IMPLEMENTATION_PLAN_SCHEMA = "compiled_implementation_plan_v1"
COMPILED_MILESTONE_UPDATE_SCHEMA = "compiled_milestone_update_v1"
COMPILED_RISK_REGISTER_UPDATE_SCHEMA = "compiled_risk_register_update_v1"
COMPILED_EXECUTOR_PROMPT_SCHEMA = "compiled_executor_prompt_v1"
COMPILER_RECEIPT_SCHEMA = "compiler_receipt_v1"
COMPILER_REPLAY_RECORD_SCHEMA = "compiler_replay_record_v1"
COMPILER_SUMMARY_SCHEMA = "compiler_summary_v1"

VERDICT_GREEN = "GREEN_PHASE37_PROPOSAL_TO_SPEC_TESTS_PLANS_COMPILER"
VERDICT_YELLOW = "YELLOW_PHASE37_COMPILER_PARTIAL"
VERDICT_RED = "RED_PHASE37_COMPILER_FAILED"

# Per-proposal compilation outcomes.
STATUS_READY = "READY"
STATUS_NOT_READY = "NOT_READY"
STATUS_LIVE_BLOCKED = "LIVE_SELF_BLOCKED"
STATUS_REFUSED = "RED_REFUSED"

ADVISORY_LABEL = "PLANNING_DOCS_ONLY_NOT_IMPLEMENTATION"
UNKNOWN = "UNKNOWN"

# Required documents for a full (READY) work package.
REQUIRED_WORK_PACKAGE_DOCS = (
    "00_INDEX.md",
    "01_SPEC_UPDATE.md",
    "02_TEST_PLAN_UPDATE.md",
    "03_IMPLEMENTATION_PLAN_UPDATE.md",
    "04_MILESTONE_UPDATE.md",
    "05_RISK_REGISTER_UPDATE.md",
    "06_EXECUTOR_PROMPT.md",
)


class CompilerError(ValueError):
    """Phase 37 validation or refusal."""


def neutral_flags() -> dict[str, bool]:
    """Flags that every compiler artifact carries to keep it advisory-only."""
    return {
        "advisory_only": True,
        "compiler_mode_planning_docs_only": True,
        "is_authority": False,
        "is_truth": False,
        "fix_implemented_by_compiler": False,
        "patch_applied_by_compiler": False,
        "grants_authority": False,
        "authorizes_tool": False,
        "creates_live_effect": False,
        "claims_agi": False,
    }


def require_fields(payload: Mapping[str, Any], fields: tuple[str, ...]) -> None:
    missing = [field for field in fields if payload.get(field) in (None, "")]
    if missing:
        raise CompilerError(f"schema_violation:missing:{','.join(missing)}")


# Fields whose truthiness in an *emitted* compiler artifact would mean the compiler
# itself tried to grant authority / go live. Compiler outputs must never carry these.
_FORBIDDEN_OUTPUT_FLAGS = {
    "grants_authority": "compiler_cannot_grant_authority",
    "grant_authority": "compiler_cannot_grant_authority",
    "authorizes_tool": "compiler_cannot_authorize_tools",
    "authorize_tool": "compiler_cannot_authorize_tools",
    "creates_live_effect": "compiler_cannot_create_live_effects",
    "create_live_effect": "compiler_cannot_create_live_effects",
    "fix_implemented_by_compiler": "compiler_cannot_implement_fix",
    "patch_applied_by_compiler": "compiler_cannot_apply_patch",
    "claims_agi": "compiler_cannot_claim_agi",
}


def assert_neutral_output(payload: Mapping[str, Any]) -> None:
    """Guard an artifact the compiler is about to emit: it must stay neutral."""
    for key, value in payload.items():
        if value and str(key) in _FORBIDDEN_OUTPUT_FLAGS:
            raise CompilerError(_FORBIDDEN_OUTPUT_FLAGS[str(key)])
        if isinstance(value, Mapping):
            assert_neutral_output(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    assert_neutral_output(item)


__all__ = [
    "ADVISORY_LABEL",
    "COMPILED_EXECUTOR_PROMPT_SCHEMA",
    "COMPILED_IMPLEMENTATION_PLAN_SCHEMA",
    "COMPILED_MILESTONE_UPDATE_SCHEMA",
    "COMPILED_RISK_REGISTER_UPDATE_SCHEMA",
    "COMPILED_SPEC_UPDATE_SCHEMA",
    "COMPILED_TEST_PLAN_UPDATE_SCHEMA",
    "COMPILED_WORK_PACKAGE_SCHEMA",
    "COMPILER_RECEIPT_SCHEMA",
    "COMPILER_REPLAY_RECORD_SCHEMA",
    "COMPILER_SUMMARY_SCHEMA",
    "CompilerError",
    "REQUIRED_WORK_PACKAGE_DOCS",
    "STATUS_LIVE_BLOCKED",
    "STATUS_NOT_READY",
    "STATUS_READY",
    "STATUS_REFUSED",
    "UNKNOWN",
    "VERDICT_GREEN",
    "VERDICT_RED",
    "VERDICT_YELLOW",
    "assert_neutral_output",
    "neutral_flags",
    "require_fields",
]
