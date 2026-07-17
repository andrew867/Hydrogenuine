"""P26 recall query/result builders."""

from __future__ import annotations

from hg_runtime.experience_ledger.hashing import with_hash
from hg_runtime.experience_ledger.schemas import ExperienceLedgerBoundaryError, assert_neutral, neutral_flags


def build_recall_query(*, query_id: str, query_type: str, value: str) -> dict:
    query = {
        "record_type": "recall_query_v1",
        "schema_version": "1",
        "query_id": query_id,
        "query_type": query_type,
        "value": value,
        "read_only": True,
        "recall_treated_as_authority": False,
        **neutral_flags(),
    }
    with_hash(query, "recall_hash")
    assert_neutral(query)
    return query


def build_recall_result(*, result_id: str, query: dict, memory_records: list[dict]) -> dict:
    if not all(record.get("provenance_refs") for record in memory_records):
        raise ExperienceLedgerBoundaryError("missing_provenance_for_recall")
    result = {
        "record_type": "recall_result_v1",
        "schema_version": "1",
        "result_id": result_id,
        "query_id": query["query_id"],
        "query_hash": query["recall_hash"],
        "memory_refs": [r["memory_id"] for r in memory_records],
        "memory_hashes": [r["memory_hash"] for r in memory_records],
        "provenance_refs": sorted({ref for r in memory_records for ref in r["provenance_refs"]}),
        "read_only": True,
        "recall_is_authority": False,
        "recall_treated_as_authority": False,
        **neutral_flags(),
    }
    with_hash(result, "recall_hash")
    assert_neutral(result)
    return result

