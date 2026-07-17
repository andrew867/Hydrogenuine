"""P26 read-only recall query helpers."""

from __future__ import annotations

from hg_runtime.experience_ledger.recall_record import build_recall_query
from hg_runtime.experience_ledger.schemas import ExperienceLedgerBoundaryError, RECALL_QUERY_TYPES


def make_query(query_type: str, value: str, query_id: str | None = None) -> dict:
    if query_type not in RECALL_QUERY_TYPES:
        raise ExperienceLedgerBoundaryError(f"unsupported_recall_query:{query_type}")
    return build_recall_query(query_id=query_id or f"query-{query_type}-{value}", query_type=query_type, value=value)

