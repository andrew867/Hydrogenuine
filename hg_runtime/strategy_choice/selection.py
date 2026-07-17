"""SCL strategy selection evaluation — choice is not permission."""

from __future__ import annotations

from hg_core.developmental.config import scl_refuse_stale_context, scl_refuse_unknown_strategy
from hg_core.developmental.errors import (
    REFUSED_BLOCKED_STRATEGY,
    REFUSED_REQUIRES_AUTHORITY,
    REFUSED_STALE_CONTEXT,
    REFUSED_STRATEGY_AS_PERMISSION,
    REFUSED_UNKNOWN_STRATEGY,
    DevelopmentalValidationError,
)
from hg_core.developmental.no_authority import advisory_only_marker
from hg_runtime.strategy_choice.types import (
    ConsequenceRecord,
    StrategyOption,
    StrategySelection,
    consequence_from_fixture,
    selection_from_fixture,
    strategy_from_fixture,
)


def refuse_strategy_as_permission(*, treat_as_permission: bool) -> None:
    if treat_as_permission:
        raise DevelopmentalValidationError(
            REFUSED_STRATEGY_AS_PERMISSION,
            "strategy selection cannot become permission or authority",
        )


def evaluate_strategy_option(
    option: StrategyOption,
    *,
    treat_as_permission: bool = False,
) -> dict[str, object]:
    if treat_as_permission:
        refuse_strategy_as_permission(treat_as_permission=True)
    if option.status == "blocked":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_BLOCKED_STRATEGY,
            "strategy_id": option.strategy_id,
            "strategy_is_not_permission": True,
        }
    if scl_refuse_unknown_strategy() and option.strategy_type == "unknown":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_UNKNOWN_STRATEGY,
            "strategy_id": option.strategy_id,
            "strategy_is_not_permission": True,
        }
    if option.status == "requires_authority" or option.authority_required:
        return {
            **advisory_only_marker(),
            "status": "guarded",
            "reason_code": REFUSED_REQUIRES_AUTHORITY,
            "strategy_id": option.strategy_id,
            "strategy_is_not_permission": True,
        }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "scl.advisory.strategy_option_recorded",
        "strategy_id": option.strategy_id,
        "strategy_is_not_permission": True,
        "optimization_is_not_permission": True,
    }


def evaluate_strategy_selection(
    selection: StrategySelection,
    option: StrategyOption,
    *,
    observed_at: str,
    treat_as_permission: bool = False,
) -> dict[str, object]:
    if treat_as_permission:
        refuse_strategy_as_permission(treat_as_permission=True)
    if scl_refuse_stale_context() and observed_at > selection.context_expires_at:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_STALE_CONTEXT,
            "selection_id": selection.selection_id,
            "strategy_is_not_permission": True,
        }
    option_result = evaluate_strategy_option(option)
    if option_result["status"] != "recorded":
        return {
            **option_result,
            "selection_id": selection.selection_id,
        }
    if not selection.evidence_refs and option.expected_risk > 0.7:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": "scl.refused.missing_evidence",
            "selection_id": selection.selection_id,
            "strategy_is_not_permission": True,
        }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "scl.advisory.strategy_selection_recorded",
        "selection_id": selection.selection_id,
        "selected_strategy_id": selection.selected_strategy_id,
        "strategy_is_not_permission": True,
        "responsibility_is_not_authority": True,
    }


def evaluate_consequence(
    record: ConsequenceRecord,
    *,
    treat_as_permission: bool = False,
) -> dict[str, object]:
    if treat_as_permission:
        refuse_strategy_as_permission(treat_as_permission=True)
    if record.outcome_status in {"failed", "harmful"}:
        return {
            **advisory_only_marker(),
            "status": "recorded",
            "reason_code": "scl.advisory.outcome_mismatch_detected",
            "consequence_id": record.consequence_id,
            "operator_review_recommended": True,
            "strategy_is_not_permission": True,
        }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "scl.advisory.consequence_recorded",
        "consequence_id": record.consequence_id,
        "outcome_status": record.outcome_status,
        "strategy_is_not_permission": True,
    }


def evaluate_strategy_fixture(fixture: dict[str, str], **kwargs: object) -> dict[str, object]:
    return evaluate_strategy_option(strategy_from_fixture(fixture), **kwargs)  # type: ignore[arg-type]


def evaluate_selection_fixture(
    fixture: dict[str, str],
    *,
    option_fixture: dict[str, str] | None = None,
    **kwargs: object,
) -> dict[str, object]:
    option = strategy_from_fixture(option_fixture or {"strategy_id": fixture.get("selected_strategy_id", "s1")})
    return evaluate_strategy_selection(selection_from_fixture(fixture), option, **kwargs)  # type: ignore[arg-type]


def evaluate_consequence_fixture(fixture: dict[str, str], **kwargs: object) -> dict[str, object]:
    return evaluate_consequence(consequence_from_fixture(fixture), **kwargs)  # type: ignore[arg-type]


__all__ = [
    "evaluate_consequence",
    "evaluate_consequence_fixture",
    "evaluate_selection_fixture",
    "evaluate_strategy_fixture",
    "evaluate_strategy_option",
    "evaluate_strategy_selection",
    "refuse_strategy_as_permission",
]
