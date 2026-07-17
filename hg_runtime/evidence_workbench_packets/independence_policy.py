"""Independence policy for second-source evaluation."""

from __future__ import annotations

from hg_runtime.evidence_workbench_packets.schemas import SECOND_SOURCE_OUTCOMES


def evaluate_independence(
    *,
    source_ids: list[str],
    duplicate_primary: dict[str, str],
    conflict_source_ids: set[str],
    quarantine_source_ids: set[str],
    fever_source_ids: set[str],
    redaction_blocked_source_ids: set[str],
    second_source_required: bool,
) -> tuple[str, int]:
    """Return (outcome, independent_source_count). Does not determine truth."""
    logical_sources: set[str] = set()
    for sid in source_ids:
        logical_sources.add(duplicate_primary.get(sid, sid))

    if any(sid in conflict_source_ids for sid in source_ids):
        return "BLOCKED_BY_CONFLICT", len(logical_sources)
    if any(sid in quarantine_source_ids for sid in source_ids):
        return "BLOCKED_BY_QUARANTINE", len(logical_sources)
    if any(sid in fever_source_ids for sid in source_ids):
        return "BLOCKED_BY_FEVER", len(logical_sources)
    if any(sid in redaction_blocked_source_ids for sid in source_ids):
        return "BLOCKED_BY_REDACTION", len(logical_sources)

    if not second_source_required:
        return "SECOND_SOURCE_NOT_REQUIRED", len(logical_sources)

    if len(logical_sources) < 2:
        if len(source_ids) >= 2:
            return "SECOND_SOURCE_PRESENT_BUT_DUPLICATE", len(logical_sources)
        return "SECOND_SOURCE_REQUIRED_MISSING", len(logical_sources)

    if len(source_ids) > len(logical_sources):
        return "SECOND_SOURCE_PRESENT_BUT_NOT_INDEPENDENT", len(logical_sources)

    return "SECOND_SOURCE_PRESENT_REVIEW_READY", len(logical_sources)


def all_outcomes_exercised(outcomes: set[str]) -> bool:
    return SECOND_SOURCE_OUTCOMES <= outcomes
