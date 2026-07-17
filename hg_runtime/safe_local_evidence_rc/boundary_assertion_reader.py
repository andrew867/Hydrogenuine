"""Read boundary assertions for SLE-RC validation."""

from __future__ import annotations

from hg_runtime.safe_local_evidence_rc.schemas import BOUNDARY_ASSERTION_IDS


def read_assertion_keys(assertions: list[dict]) -> set[str]:
    return {row["assertion_key"] for row in assertions}


def all_required_assertions_present(assertions: list[dict]) -> bool:
    return set(BOUNDARY_ASSERTION_IDS) <= read_assertion_keys(assertions)
