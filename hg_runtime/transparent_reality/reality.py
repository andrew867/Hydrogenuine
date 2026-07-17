"""TRL transparent reality evaluation — transparency is not omniscience."""

from __future__ import annotations

from hg_core.developmental.config import trl_refuse_stale_snapshot, trl_refuse_summary_as_proof
from hg_core.developmental.errors import (
    REFUSED_INTEGRATION_AS_AUTHORITY,
    REFUSED_NARRATIVE_COLLAPSE,
    REFUSED_REALITY_AS_AUTHORITY,
    REFUSED_STALE_SNAPSHOT,
    REFUSED_SUMMARY_AS_PROOF,
    REFUSED_UNKNOWN_ERASURE,
    DevelopmentalValidationError,
)
from hg_core.developmental.no_authority import advisory_only_marker
from hg_runtime.transparent_reality.types import (
    TransparentFieldSnapshot,
    TransparentSummary,
    classify_narrative_collapse,
    snapshot_from_fixture,
    summary_from_fixture,
)

_COLLAPSE_REASON = {
    "summary_as_proof": REFUSED_SUMMARY_AS_PROOF,
    "integration_as_authority": REFUSED_INTEGRATION_AS_AUTHORITY,
    "unknown_erasure": REFUSED_UNKNOWN_ERASURE,
    "contradiction_smoothing": REFUSED_NARRATIVE_COLLAPSE,
    "false_omniscience": REFUSED_NARRATIVE_COLLAPSE,
    "operator_replacement_claim": REFUSED_NARRATIVE_COLLAPSE,
    "unknown": REFUSED_NARRATIVE_COLLAPSE,
}


def refuse_reality_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority:
        raise DevelopmentalValidationError(
            REFUSED_REALITY_AS_AUTHORITY,
            "transparent field or summary cannot become authority",
        )


def evaluate_field_snapshot(
    snapshot: TransparentFieldSnapshot,
    *,
    observed_at: str,
    treat_as_authority: bool = False,
) -> dict[str, object]:
    if treat_as_authority:
        refuse_reality_as_authority(treat_as_authority=True)
    if trl_refuse_stale_snapshot() and observed_at > snapshot.expires_at:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_STALE_SNAPSHOT,
            "snapshot_id": snapshot.snapshot_id,
            "summary_is_not_proof": True,
        }
    if snapshot.stale_refs:
        return {
            **advisory_only_marker(),
            "status": "guarded",
            "reason_code": REFUSED_STALE_SNAPSHOT,
            "snapshot_id": snapshot.snapshot_id,
            "stale_refs": list(snapshot.stale_refs),
            "summary_is_not_proof": True,
        }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "trl.advisory.field_snapshot_recorded",
        "snapshot_id": snapshot.snapshot_id,
        "unknown_count": len(snapshot.unknown_refs),
        "contradiction_count": len(snapshot.contradiction_refs),
        "summary_is_not_proof": True,
        "transparency_is_not_omniscience": True,
    }


def evaluate_transparent_summary(
    summary: TransparentSummary,
    *,
    treat_as_proof: bool = False,
    treat_as_authority: bool = False,
    collapse_statement: str = "",
) -> dict[str, object]:
    if treat_as_authority or treat_as_proof:
        if treat_as_proof and trl_refuse_summary_as_proof():
            return {
                **advisory_only_marker(),
                "status": "contained",
                "reason_code": REFUSED_SUMMARY_AS_PROOF,
                "summary_id": summary.summary_id,
                "summary_is_not_proof": True,
            }
        refuse_reality_as_authority(treat_as_authority=treat_as_authority or treat_as_proof)
    statement = collapse_statement or summary.known_summary
    collapse = classify_narrative_collapse(statement)
    if collapse in _COLLAPSE_REASON and collapse != "unknown":
        return {
            **advisory_only_marker(),
            "status": "contained",
            "reason_code": _COLLAPSE_REASON[collapse],
            "summary_id": summary.summary_id,
            "collapse_type": collapse,
            "summary_is_not_proof": True,
        }
    if not summary.unknown_summary.strip() and "unknown" in summary.known_summary.lower():
        return {
            **advisory_only_marker(),
            "status": "contained",
            "reason_code": REFUSED_UNKNOWN_ERASURE,
            "summary_id": summary.summary_id,
            "summary_is_not_proof": True,
        }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "trl.advisory.transparent_summary_recorded",
        "summary_id": summary.summary_id,
        "summary_is_not_proof": True,
        "unknown_preserved": bool(summary.unknown_summary.strip()),
    }


def evaluate_snapshot_fixture(fixture: dict[str, str], **kwargs: object) -> dict[str, object]:
    return evaluate_field_snapshot(snapshot_from_fixture(fixture), **kwargs)  # type: ignore[arg-type]


def evaluate_summary_fixture(fixture: dict[str, str], **kwargs: object) -> dict[str, object]:
    return evaluate_transparent_summary(summary_from_fixture(fixture), **kwargs)  # type: ignore[arg-type]


__all__ = [
    "evaluate_field_snapshot",
    "evaluate_snapshot_fixture",
    "evaluate_summary_fixture",
    "evaluate_transparent_summary",
    "refuse_reality_as_authority",
]
